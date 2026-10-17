"""Offline analysis helpers: aggregate what the scraper returns.

Nothing here touches the network. These functions turn lists of ad detail
dicts (as returned by ``GoogleAdsTransparency.get_ad_detail``) into compact
summaries a person or a model can reason about, and guard against the one
resolution mistake that produces confidently wrong numbers: a domain that
resolves to its parent company's advertiser account.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

# Legal-form suffixes only. Words like "software" or "labs" look generic but
# are real discriminators between similarly named companies.
_STOP_TOKENS = {
    "inc", "llc", "ltd", "corp", "corporation", "company", "co", "the",
    "limited", "plc", "gmbh", "sa", "nv", "ag", "pte", "bv", "srl", "sas",
}

_ADVERTISER_ID = re.compile(r"^AR\d{10,}$")


def normalize_domain(value: str) -> str:
    """Reduce a URL or hostname to a bare registrable-looking host.

    ``https://www.Nike.com/us/`` -> ``nike.com``. Empty input stays empty.
    """
    v = value.strip().lower()
    v = re.sub(r"^[a-z][a-z0-9+.-]*://", "", v)
    v = v.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    v = v.split("@")[-1].split(":")[0]
    if v.startswith("www."):
        v = v[4:]
    return v.strip(".")


def looks_like_advertiser_id(value: str) -> bool:
    """True for Google advertiser ids such as ``AR18378488041124659201``."""
    return bool(_ADVERTISER_ID.match(value.strip()))


def name_tokens(text: str) -> set[str]:
    """Lower-cased word tokens minus legal-form noise."""
    return {
        t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and t not in _STOP_TOKENS
    }


def is_parent_entity(domain: str, advertiser_name: str, company: str = "") -> bool:
    """Does the resolved advertiser look like a different company than the domain?

    ``github.com`` resolves to "Microsoft Corporation" with tens of thousands
    of ads. Citing that as GitHub's ad count is wrong by orders of magnitude,
    and nothing in the response says so. This is a token-overlap heuristic:
    it flags, it does not filter, and callers should surface the flag.
    """
    want = name_tokens(company) | name_tokens(normalize_domain(domain).split(".")[0])
    got = name_tokens(advertiser_name)
    if not want or not got:
        return False
    return not (want & got)


def destination_host(url: str) -> str:
    """Host of an ad's destination URL, scheme-agnostic, without ``www.``."""
    if not url:
        return ""
    candidate = url if "://" in url else f"https://{url}"
    try:
        host = urlparse(candidate).hostname or ""
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _unique(values: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        key = v.strip()
        if key and key.lower() not in seen:
            seen.add(key.lower())
            out.append(key)
            if len(out) >= limit:
                break
    return out


def summarize_ads(ads: list[dict[str, Any]], top: int = 10) -> dict[str, Any]:
    """Aggregate a list of ad detail dicts into one summary.

    Returns counts and shares by format, the date range the sample was last
    shown, a de-duplicated sample of headlines, descriptions and CTA labels,
    and the destination hosts the ads send people to. Pure aggregation: no
    judgement about strategy is made here.
    """
    total = len(ads)
    by_format: Counter[str] = Counter(a.get("format") or "unknown" for a in ads)
    contents = [a.get("content") or {} for a in ads]

    dates = sorted(d for d in (a.get("last_shown") or "" for a in ads) if d)
    hosts: Counter[str] = Counter(
        h for h in (destination_host(c.get("destination_url", "")) for c in contents) if h
    )
    ctas: Counter[str] = Counter(
        c["button_label"].strip() for c in contents if c.get("button_label", "").strip()
    )

    return {
        "sampled": total,
        "by_format": dict(sorted(by_format.items())),
        "format_share": {
            k: round(v / total, 3) for k, v in sorted(by_format.items())
        } if total else {},
        "last_shown": {
            "earliest": dates[0] if dates else "",
            "latest": dates[-1] if dates else "",
        },
        "headlines": _unique([c.get("headline", "") for c in contents], top),
        "descriptions": _unique([c.get("description", "") for c in contents], 5),
        "cta_labels": [{"label": k, "count": v} for k, v in ctas.most_common(top)],
        "destination_hosts": [
            {"host": k, "count": v} for k, v in hosts.most_common(top)
        ],
        "with_video": sum(1 for c in contents if c.get("video_url")),
        "with_image": sum(1 for c in contents if c.get("image_url")),
    }
