"""Google Ads Transparency Center scraper.

Reverse-engineers Google's internal RPC endpoints to fetch advertiser info,
ad creatives, and ad details without an official API.
"""

from __future__ import annotations

import datetime
import html
import json
import re
import time
from typing import Any

import requests

from .analysis import (
    is_parent_entity,
    looks_like_advertiser_id,
    normalize_domain,
    summarize_ads,
)
from .config import ROTATING_ROUTES, _redact, proxy_routes
from .parser import decode_text_ad
from .regions import REGIONS

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # noqa: E501
    "accept-language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",  # noqa: E501
}

BASE_URL = "https://adstransparency.google.com"

_DATA_P_COPY = re.compile(
    r'data-p="%\.@\.\[1,\[&quot;(.*?)&quot;,&quot;(.*?)&quot;,&quot;(.*?)&quot;'
)

# Google throttles this endpoint per source IP and answers a bursty client with
# a 429 or a redirect to /sorry/. Space requests out and back off rather than
# hammering into a soft ban. Rotating routes exit from a new IP every request,
# so per-IP spacing buys nothing there and the census can move at real speed.
MIN_REQUEST_INTERVAL = 1.0
ROTATING_REQUEST_INTERVAL = 0.25
MAX_RETRIES = 5
# Blocks through a rotating route mean one dirty exit IP, not a burned route —
# retry in place this many times before advancing down the chain.
MAX_BLOCKS_PER_ROTATING_ROUTE = 2


class AdsTransparencyError(RuntimeError):
    """The Ads Transparency Center returned something we could not parse."""


class AdsTransparencyBlocked(AdsTransparencyError):
    """Google is rate-limiting or CAPTCHA-gating this source IP.

    The RPC endpoint is fine — the egress address is not. Wait the block out, or
    route the session through another IP: requests honours HTTPS_PROXY/ALL_PROXY,
    and the constructor takes an explicit ``proxy``.
    """


class GoogleAdsTransparency:
    """Client for the Google Ads Transparency Center."""

    def __init__(
        self,
        region: str = "anywhere",
        proxy: dict[str, str] | None = None,
        min_interval: float = MIN_REQUEST_INTERVAL,
    ):
        # An explicit proxy pins a single route; otherwise walk the config
        # chain (residential -> direct -> tunnel), advancing when a route is
        # banned or unreachable instead of hammering a dead exit IP.
        if proxy is not None:
            self._routes: list[tuple[str, str | dict[str, str] | None]] = [
                ("explicit", proxy)
            ]
        else:
            self._routes = [(name, url) for name, url in proxy_routes()]
        self._route_idx = 0

        self._min_interval = min_interval
        self._last_request = 0.0
        self._region = region
        self._region_num = 0
        self._use_region = region != "anywhere"
        if self._use_region:
            if region not in REGIONS:
                raise ValueError(
                    f"Region '{region}' is not supported. "
                    f"Use one of: {', '.join(sorted(REGIONS.keys()))}"
                )
            self._region_num = REGIONS[region]["1"]

        self._fresh_session()
        try:
            self._get_cookies()
        except AdsTransparencyError:
            if not self._next_egress():
                raise

    # --- Egress routes ---

    @property
    def _route_name(self) -> str:
        return self._routes[self._route_idx][0]

    def _route_is_rotating(self) -> bool:
        return self._route_name in ROTATING_ROUTES

    def _route_proxies(self) -> dict[str, str] | None:
        spec = self._routes[self._route_idx][1]
        if isinstance(spec, dict):
            return spec
        return {"http": spec, "https": spec} if spec else None

    def _route_hint(self) -> str:
        spec = self._routes[self._route_idx][1]
        url = spec if isinstance(spec, str) else ""
        if not url:
            return f" (via {self._route_name} route)"
        return f" (via {self._route_name} route {_redact(url)})"

    def _scrub(self, text: str) -> str:
        """Keep proxy credentials out of error text — callers persist it."""
        for _, spec in self._routes:
            if isinstance(spec, str) and spec and "@" in spec:
                creds = spec.partition("://")[2].rsplit("@", 1)[0]
                text = text.replace(creds, "…")
        return text

    def _fresh_session(self) -> None:
        # trust_env stays off so an ambient ALL_PROXY cannot silently reroute
        # us; cookies never travel between routes — Google ties them to an IP.
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.trust_env = False
        proxies = self._route_proxies()
        if proxies:
            self.session.proxies.update(proxies)
        self._last_request = 0.0

    def _next_egress(self) -> bool:
        """Advance to the next usable route, cookies included. False = none left."""
        while self._route_idx + 1 < len(self._routes):
            self._route_idx += 1
            self._fresh_session()
            try:
                self._get_cookies()
                return True
            except AdsTransparencyError:
                continue
        return False

    def _get_cookies(self) -> None:
        try:
            resp = self.session.get(BASE_URL, params={"region": self._region})
        except requests.exceptions.RequestException as exc:
            raise AdsTransparencyError(
                self._scrub(f"Could not reach {BASE_URL}{self._route_hint()}: {exc}")
            ) from exc
        self._raise_if_blocked(resp)

    def refresh_session(self, proxy: dict[str, str] | None = None) -> None:
        """Refresh session cookies, optionally pinning a new proxy."""
        if proxy is not None:
            self._routes = [("explicit", proxy)]
            self._route_idx = 0
        self._fresh_session()
        self._get_cookies()

    # --- Request plumbing ---

    def _throttle(self) -> None:
        """Space requests out so we stop earning soft bans."""
        interval = (
            min(self._min_interval, ROTATING_REQUEST_INTERVAL)
            if self._route_is_rotating()
            else self._min_interval
        )
        wait = interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    @staticmethod
    def _is_blocked(resp: requests.Response) -> bool:
        if resp.status_code == 429:
            return True
        if "/sorry/" in resp.url:
            return True
        if any("/sorry/" in r.headers.get("location", "") for r in resp.history):
            return True
        return "recaptcha" in resp.text[:4000].lower()

    def _raise_if_blocked(self, resp: requests.Response) -> None:
        if not self._is_blocked(resp):
            return
        raise AdsTransparencyBlocked(
            f"Google is blocking this source IP{self._route_hint()} (HTTP "
            f"{resp.status_code}, CAPTCHA interstitial) on {resp.url}. The "
            "endpoint itself is up — wait the block out or route the session "
            "through another IP."
        )

    def _rpc(
        self, path: str, req_body: dict[str, Any], authuser: str = ""
    ) -> dict[str, Any]:
        """POST one RPC and return decoded JSON, riding out blocks and dead routes.

        A blocked or unreachable rotating route retries in place — the next
        request exits from a new IP anyway. A blocked static route advances
        down the chain instead of backing off against a ban that will outlive
        any polite wait.
        """
        data = {"f.req": json.dumps(req_body)}
        blocked_on_route = 0
        for attempt in range(MAX_RETRIES):
            last_attempt = attempt == MAX_RETRIES - 1
            self._throttle()
            try:
                resp = self.session.post(
                    f"{BASE_URL}{path}", params={"authuser": authuser}, data=data
                )
            except requests.exceptions.RequestException as exc:
                if self._route_is_rotating() and not last_attempt:
                    continue
                if not last_attempt and self._next_egress():
                    blocked_on_route = 0
                    continue
                raise AdsTransparencyError(
                    self._scrub(f"Could not reach {path}{self._route_hint()}: {exc}")
                ) from exc
            if self._is_blocked(resp):
                if last_attempt:
                    self._raise_if_blocked(resp)
                blocked_on_route += 1
                if (
                    self._route_is_rotating()
                    and blocked_on_route <= MAX_BLOCKS_PER_ROTATING_ROUTE
                ):
                    time.sleep(1)
                    continue
                if self._next_egress():
                    blocked_on_route = 0
                    continue
                # Single route left and it is banned: the polite wait is all
                # that remains.
                try:
                    delay = float(resp.headers.get("retry-after", ""))
                except ValueError:
                    delay = 5 * 2**attempt
                time.sleep(delay)
                continue
            try:
                return resp.json()
            except (requests.exceptions.JSONDecodeError, ValueError) as exc:
                raise AdsTransparencyError(
                    f"{path} returned HTTP {resp.status_code} with an unparseable "
                    f"body: {resp.text[:200]!r}"
                ) from exc
        raise AdsTransparencyBlocked(
            f"{path} stayed blocked after {MAX_RETRIES} tries across every route."
        )

    # --- Search endpoints ---

    def search_suggestions(self, keyword: str) -> list[dict[str, Any]]:
        """Search for advertisers/domains matching a keyword."""
        res = self._rpc(
            "/anji/_/rpc/SearchService/SearchSuggestions",
            {"1": keyword, "2": 10, "3": 10},
            authuser="0",
        )
        return res.get("1", []) or []

    def search_advertiser_by_domain(self, domain: str) -> dict[str, Any] | None:
        """Find an advertiser by domain name.

        Returns {advertiser_id, name, ad_count} or None.
        """
        # Domain search requires domain in both field "1" and "3.12.1"
        req_body = {
            "1": domain,
            "2": 1,
            "3": {"12": {"1": domain}},
            "7": {"1": 1},
        }
        results = self._rpc(
            "/anji/_/rpc/SearchService/SearchCreatives", req_body
        ).get("1")

        if not results:
            return None

        ad = results[0]
        advertiser_id = ad.get("1", "")
        name = ad.get("12", "")

        # Try to get ad count via suggestion search
        ad_count = self._get_ad_count(name, advertiser_id)

        return {
            "advertiser_id": advertiser_id,
            "name": name,
            "ad_count": ad_count,
        }

    def search_advertisers(self, query: str) -> list[dict[str, Any]]:
        """Search for advertisers by keyword.

        Returns a list of {advertiser_id, name, region, ad_count} dicts.
        """
        suggestions = self.search_suggestions(query)
        results = []
        for suggestion in suggestions:
            if "1" in suggestion:
                info = suggestion["1"]
                ad_count = 0
                if info.get("4", {}).get("2", {}).get("2"):
                    ad_count = int(info["4"]["2"]["2"])
                results.append({
                    "advertiser_id": info.get("2", ""),
                    "name": info.get("1", ""),
                    "region": info.get("3", ""),
                    "ad_count": ad_count,
                })
            elif "2" in suggestion:
                # Domain result — resolve to advertiser
                domain = suggestion["2"].get("1", "")
                if domain:
                    adv = self.search_advertiser_by_domain(domain)
                    if adv:
                        results.append({**adv, "domain": domain})
        return results

    # --- Creative endpoints ---

    def get_creative_ids(
        self, advertiser_id: str, count: int = 40, next_page_id: str = ""
    ) -> list[str]:
        """Get creative IDs for an advertiser."""
        req_body: dict[str, Any] = {
            "2": min(count, 100),
            "3": {"12": {"1": "", "2": True}, "13": {"1": [advertiser_id]}},
            "7": {"1": 1},
        }
        if next_page_id:
            req_body["4"] = next_page_id
        if self._use_region:
            req_body["3"]["8"] = [self._region_num]

        res = self._rpc("/anji/_/rpc/SearchService/SearchCreatives", req_body)

        ads = res.get("1", [])
        ids = [ad["2"] for ad in ads if "2" in ad]
        next_token = res.get("2")

        if count <= 100 or not ids or next_token is None:
            return ids[:count]

        remaining = count - len(ids)
        ids.extend(self.get_creative_ids(advertiser_id, remaining, next_token))
        return ids

    def get_ad_detail(self, advertiser_id: str, creative_id: str) -> dict[str, Any]:
        """Get full details for a single ad creative."""
        payload = self._rpc(
            "/anji/_/rpc/LookupService/GetCreativeById",
            {"1": advertiser_id, "2": creative_id, "5": {"1": 1}},
            authuser="0",
        )
        ad = payload.get("1")
        if not isinstance(ad, dict):
            return {
                "advertiser_id": advertiser_id,
                "creative_id": creative_id,
                "format": "unknown",
                "last_shown": "",
                "content": {},
            }

        format_int = ad.get("8", 0)
        format_name = {1: "text", 2: "image", 3: "video"}.get(
            format_int, f"unknown ({format_int})"
        )

        # Extract date
        last_shown = ""
        try:
            last_shown = datetime.datetime.fromtimestamp(
                int(ad["4"]["1"])
            ).strftime("%Y-%m-%d")
        except (KeyError, TypeError, ValueError):
            pass

        # Extract ad link
        link = self._extract_ad_link(ad)

        # Build content based on format
        content: dict[str, str] = {}
        is_image_link = any(
            x in link for x in ["simgad", ".png", ".jpg", ".gif", "googlesyndication.com"]
        )

        if is_image_link:
            format_name = "image"
            content["image_url"] = link
        elif format_name == "text":
            content["preview_url"] = link
            decoded = decode_text_ad(link)
            if decoded:
                content.update(decoded)
            elif "content.js" in link:
                content.update(self._text_copy_from_renderer(link))
        elif format_name == "image":
            content["image_url"] = link
            content.update(self._resolve_preview(link))
        elif format_name == "video":
            content["preview_url"] = link
            resolved = self._resolve_preview(link)
            content.update(resolved)
            if "video_url" not in resolved:
                # Older creatives expose the stream directly instead of a YouTube id.
                fallback = self._resolve_video_url(link)
                content["video_url"] = fallback if fallback != link else link
        else:
            content["preview_url"] = link

        return {
            "advertiser_id": advertiser_id,
            "creative_id": creative_id,
            "format": format_name,
            "last_shown": last_shown,
            "content": content,
        }

    def get_ads(
        self, advertiser_name: str, count: int = 10
    ) -> list[dict[str, Any]]:
        """Search for an advertiser by name and return their ads with decoded content.

        This is a convenience method that combines search + creative fetch + detail lookup.
        """
        adv = self._resolve_by_name(advertiser_name)
        if not adv:
            return []
        advertiser_id = adv["advertiser_id"]
        resolved_name = adv["name"] or advertiser_name

        creative_ids = self.get_creative_ids(advertiser_id, count)
        ads = []
        for cid in creative_ids:
            detail = self.get_ad_detail(advertiser_id, cid)
            detail["advertiser_name"] = resolved_name
            ads.append(detail)
        return ads

    # --- Resolution + analysis ---

    def _resolve_by_name(self, advertiser_name: str) -> dict[str, Any] | None:
        """Resolve a name the way the Transparency Center's search box does.

        Exact (case-insensitive) name match first, then a domain suggestion,
        then the first advertiser suggestion. None when nothing matches.
        """
        suggestions = self.search_suggestions(advertiser_name)
        for s in suggestions:
            if "1" in s:
                info = s["1"]
                if info.get("1", "").lower() == advertiser_name.lower():
                    return self._suggestion_to_advertiser(info)
            elif "2" in s:
                domain = s["2"].get("1", "")
                adv = self.search_advertiser_by_domain(domain) if domain else None
                if adv:
                    return adv
        for s in suggestions:
            if "1" in s:
                return self._suggestion_to_advertiser(s["1"])
        return None

    @staticmethod
    def _suggestion_to_advertiser(info: dict[str, Any]) -> dict[str, Any]:
        try:
            ad_count = int(info["4"]["2"]["2"])
        except (KeyError, TypeError, ValueError):
            ad_count = 0
        return {
            "advertiser_id": info.get("2", ""),
            "name": info.get("1", ""),
            "ad_count": ad_count,
        }

    def resolve_advertiser(self, query: str) -> dict[str, Any] | None:
        """Turn an advertiser id, a domain, or a name into {advertiser_id, name, ad_count}.

        Ids pass straight through (name and ad_count unknown, left empty/0).
        Anything with a dot and no spaces is tried as a domain first, then as
        a name. None when nothing matches.
        """
        q = query.strip()
        if not q:
            return None
        if looks_like_advertiser_id(q):
            return {"advertiser_id": q, "name": "", "ad_count": 0}
        if "." in q and " " not in q:
            adv = self.search_advertiser_by_domain(normalize_domain(q))
            if adv:
                return adv
        return self._resolve_by_name(q)

    def compare_advertisers(
        self, domains: list[str], company_names: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        """Active ad count per domain, one lookup each, in input order.

        Every row carries a ``status``: ``ok`` (advertiser found), ``absent``
        (no advertiser registered for that domain, a genuine zero),
        ``blocked`` (rate-limited; NOT a zero) or ``error``. Once every egress
        route is blocked the remaining domains are marked ``blocked`` without
        further requests rather than hammering a ban.

        ``parent_entity`` flags rows whose advertiser name shares no token with
        the domain. Domain search returns whoever's ads mention the domain,
        which can be a parent company, a reseller or a stranger; do not cite
        those counts as the domain's own. ``company_names`` maps domain -> company
        name to sharpen that check.
        """
        names = {normalize_domain(k): v for k, v in (company_names or {}).items()}
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        exhausted = False
        for raw in domains:
            dom = normalize_domain(raw)
            if not dom or dom in seen:
                continue
            seen.add(dom)
            if exhausted:
                rows.append({
                    "domain": dom, "status": "blocked",
                    "note": "skipped: every egress route is blocked",
                })
                continue
            try:
                adv = self.search_advertiser_by_domain(dom)
            except AdsTransparencyBlocked as exc:
                exhausted = True
                rows.append({"domain": dom, "status": "blocked", "note": str(exc)[:300]})
                continue
            except AdsTransparencyError as exc:
                rows.append({"domain": dom, "status": "error", "note": str(exc)[:300]})
                continue
            if not adv:
                rows.append({
                    "domain": dom, "status": "absent", "ad_count": 0,
                    "note": "no Google advertiser is registered for this domain",
                })
                continue
            row: dict[str, Any] = {
                "domain": dom,
                "status": "ok",
                "advertiser_id": adv["advertiser_id"],
                "advertiser_name": adv["name"],
                "ad_count": adv["ad_count"],
                "parent_entity": is_parent_entity(dom, adv["name"], names.get(dom, "")),
            }
            if row["parent_entity"]:
                row["note"] = (
                    f"resolves to {adv['name']!r}, which shares no name token with "
                    f"{dom!r}: a parent company, a reseller, or an unrelated advertiser "
                    "whose ads mention this domain. Do not cite ad_count as this "
                    "domain's own."
                )
            rows.append(row)
        return rows

    def summarize_advertiser(self, advertiser: str, sample: int = 50) -> dict[str, Any]:
        """Format mix, copy sample and destinations for one advertiser.

        ``advertiser`` may be an id, a domain or a name. ``sample`` creatives
        are fetched (the ones the Transparency Center lists first) and
        aggregated with :func:`summarize_ads`. Costs roughly one to two
        requests per sampled creative.
        """
        adv = self.resolve_advertiser(advertiser)
        if not adv:
            return {
                "status": "absent", "query": advertiser,
                "note": "no advertiser matched this id, domain or name",
            }
        creative_ids = self.get_creative_ids(adv["advertiser_id"], sample)
        ads = [self.get_ad_detail(adv["advertiser_id"], cid) for cid in creative_ids]
        return {
            "status": "ok",
            "query": advertiser,
            "advertiser_id": adv["advertiser_id"],
            "advertiser_name": adv["name"],
            "active_ads": adv["ad_count"],
            "region": self._region,
            "sample": summarize_ads(ads),
        }

    # --- Creative asset resolution ---

    def _resolve_preview(self, link: str) -> dict[str, str]:
        """Pull real asset URLs and copy out of a content.js creative preview.

        Image and video creatives hand back a JavaScript renderer rather than the
        asset. The renderer embeds what we actually want: a `simgad` image path,
        and for video ads a `template_data` blob carrying the YouTube video_id
        plus the on-creative copy.
        """
        if "content.js" not in link:
            return {}
        try:
            body = self.session.get(link, timeout=20).text
        except requests.RequestException:
            return {}


        assets = self._parse_preview_body(body)
        simgad_id = assets.pop("simgad_id", "")
        if simgad_id:
            resolved = self._resolve_simgad(simgad_id)
            if resolved:
                assets["image_url"] = resolved
        return assets

    def _text_copy_from_renderer(self, link: str) -> dict[str, str]:
        """Copy for a text ad whose preview is a content.js renderer, not an overlay."""
        try:
            body = self.session.get(link, timeout=20).text
        except requests.RequestException:
            return {}
        parsed = self._parse_preview_body(body)
        return {
            k: parsed[k]
            for k in ("headline", "description", "destination_url")
            if parsed.get(k)
        }

    def _resolve_simgad(self, simgad_id: str) -> str:
        """Pick the URL form that actually serves this asset.

        Google files image creatives under either /simgad/<id> or
        /archive/simgad/<id> and 404s the other one, with no way to tell which
        from the id alone.
        """
        for form in ("simgad", "archive/simgad"):
            url = f"https://tpc.googlesyndication.com/{form}/{simgad_id}"
            try:
                resp = self.session.head(url, timeout=15, allow_redirects=True)
            except requests.RequestException:
                continue
            if resp.status_code == 200:
                return url
        return ""

    @staticmethod
    def _parse_preview_body(body: str) -> dict[str, str]:
        text = re.sub(
            r"\\+x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), body
        )
        assets: dict[str, str] = {}

        # Text ads rendered through content.js carry their copy in a data-p
        # attribute: an HTML-escaped array of [headline, description, display URL].
        copy = _DATA_P_COPY.search(text)
        if copy:
            headline, description, visurl = (html.unescape(g) for g in copy.groups())
            if headline:
                assets["headline"] = headline
            if description:
                assets["description"] = description
            if visurl:
                assets["destination_url"] = visurl

        image = re.search(r"simgad/(\d+)", text)
        if image:
            assets["simgad_id"] = image.group(1)

        wanted = {"video_id", "headline", "description", "body", "button_label"}
        for key, value in re.findall(r"'([a-z_]+)':\s*'([^']*)'", text):
            if key in wanted and value and key not in assets:
                assets[key] = value

        video_id = assets.pop("video_id", "")
        if video_id:
            assets["video_id"] = video_id
            assets["video_url"] = f"https://www.youtube.com/watch?v={video_id}"
        if "body" in assets and "description" not in assets:
            assets["description"] = assets.pop("body")
        assets.pop("body", None)
        return assets

    # --- Internal helpers ---

    def _get_ad_count(self, name: str, advertiser_id: str) -> int:
        """Look up ad count for an advertiser via suggestions."""
        suggestions = self.search_suggestions(name)
        for s in suggestions:
            if "1" in s and s["1"].get("2") == advertiser_id:
                try:
                    return int(s["1"]["4"]["2"]["2"])
                except (KeyError, TypeError, ValueError):
                    pass
        return 0

    @staticmethod
    def _extract_ad_link(ad: dict[str, Any]) -> str:
        """Extract the ad preview/content link from the API response."""
        creatives = ad.get("5") or []
        if not creatives:
            return ""
        creative = creatives[0]

        try:
            raw = creative["3"]["2"]
        except (KeyError, IndexError, TypeError):
            pass
        else:
            if 'src="' in raw:
                return raw.split('src="')[1].split('"')[0]
            if "'" in raw:
                return raw.split("'")[1]
            return raw

        # Each shape gets its own try — a miss on one must not abort the rest.
        for key_path in (("1", "4"), ("2", "4"), ("4",)):
            obj: Any = creative
            try:
                for k in key_path:
                    obj = obj[k]
            except (KeyError, IndexError, TypeError):
                continue
            if isinstance(obj, str) and obj:
                return obj
        return ""

    def _resolve_video_url(self, link: str) -> str:
        """Resolve a displayads link to its actual video URL."""
        if "displayads" not in link:
            return link
        try:
            resp = requests.post(link, timeout=10)
            txt = next(x for x in resp.text.split("CDATA[") if "googlevideo.com" in x)
            url = str(txt.split("]")[0]).encode("utf-8").decode("unicode_escape")
            return url.encode("utf-8").decode("unicode_escape")
        except Exception:
            return link
