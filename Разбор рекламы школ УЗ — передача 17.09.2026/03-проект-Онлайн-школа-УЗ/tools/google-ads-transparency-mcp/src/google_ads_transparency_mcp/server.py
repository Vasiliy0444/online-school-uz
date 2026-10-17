"""MCP server for the Google Ads Transparency Center."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .frames import (
    DEFAULT_FRAMES,
    DEFAULT_WIDTH,
    download_image,
    extract_video_frames,
)
from .scraper import GoogleAdsTransparency

mcp = FastMCP(
    "Google Ads Transparency",
    instructions=(
        "Look up any advertiser's Google ads — search by domain or keyword, "
        "retrieve ad creatives, decode text ad content, compare active ad "
        "counts across competitors and summarise an advertiser's format mix. "
        "No API key required."
    ),
)

_client: GoogleAdsTransparency | None = None


def _get_client() -> GoogleAdsTransparency:
    global _client
    if _client is None:
        _client = GoogleAdsTransparency()
    return _client


@mcp.tool()
def search_advertiser_by_domain(domain: str) -> dict | None:
    """Find an advertiser by their website domain.

    Args:
        domain: The domain to search for (e.g. "nike.com", "coinbase.com")

    Returns:
        Advertiser info with advertiser_id, name, and ad_count — or null if not found.
    """
    return _get_client().search_advertiser_by_domain(domain)


@mcp.tool()
def search_advertisers(query: str) -> list[dict]:
    """Search for advertisers by keyword or company name.

    Args:
        query: Search query (e.g. "Nike", "Coinbase", "crypto exchange")

    Returns:
        List of matching advertisers with advertiser_id, name, region, and ad_count.
    """
    return _get_client().search_advertisers(query)


@mcp.tool()
def get_ads(advertiser_name: str, count: int = 10) -> list[dict]:
    """Get ads for an advertiser with decoded content.

    Searches for the advertiser by name, fetches their ad creatives, and returns
    full details including decoded text ad content (headline, description, destination URL).

    Args:
        advertiser_name: The advertiser's name (e.g. "Nike, Inc.", "Coinbase")
        count: Number of ads to retrieve (default 10, max 100)

    Returns:
        List of ad details with format, date, and content fields.
    """
    count = max(1, min(count, 100))
    return _get_client().get_ads(advertiser_name, count)


@mcp.tool()
def get_ad_detail(advertiser_id: str, creative_id: str) -> dict:
    """Get full details for a specific ad creative.

    Args:
        advertiser_id: The advertiser's ID (e.g. "AR05099026886533578753")
        creative_id: The creative/ad ID (e.g. "CR10813648716908961793")

    Returns:
        Ad detail with format (text/image/video), last_shown date, and content.
        For text ads, content includes headline, description, and destination_url.
        For image ads, content includes image_url (a directly fetchable asset).
        For video ads, content includes video_id, video_url (YouTube), and the
        on-creative headline and button_label.
    """
    return _get_client().get_ad_detail(advertiser_id, creative_id)


@mcp.tool()
def compare_advertisers(domains: list[str]) -> list[dict]:
    """Compare active Google ad counts across a set of domains, one row each.

    The competitor paid-surface question in one call: who is running ads, and
    how many. Rows come back in input order; sort by ad_count yourself.

    Every row has a status. "ok" means an advertiser was found; "absent" means
    no advertiser is registered for that domain and IS a genuine zero;
    "blocked" means Google rate-limited the lookup and is NOT a zero; "error"
    is anything else. Rows flagged parent_entity resolved to a differently
    named advertiser (a parent company, a reseller, or a stranger whose ads
    mention the domain) — never cite those counts as the domain's own.

    Args:
        domains: Up to 50 domains or URLs (e.g. ["nike.com", "adidas.com"]).

    Returns:
        [{domain, status, advertiser_id, advertiser_name, ad_count,
          parent_entity, note}, ...]
    """
    return _get_client().compare_advertisers(domains[:50])


@mcp.tool()
def advertiser_summary(advertiser: str, sample: int = 50) -> dict:
    """Summarise one advertiser: format mix, copy sample, destinations.

    Fetches a sample of the advertiser's creatives and aggregates them:
    counts and share by format (text/image/video), the last-shown date range,
    de-duplicated headlines, descriptions and CTA labels, and the hosts the
    ads send people to. Pure aggregation — read strategy into it yourself.

    Args:
        advertiser: An advertiser id ("AR..."), a domain ("nike.com") or a
            name ("Nike Retail BV").
        sample: Creatives to sample (default 50, max 100). Roughly one to two
            requests per creative.

    Returns:
        {status, advertiser_id, advertiser_name, active_ads, region, sample:
         {sampled, by_format, format_share, last_shown, headlines,
          descriptions, cta_labels, destination_hosts, with_video, with_image}}
    """
    sample = max(1, min(sample, 100))
    return _get_client().summarize_advertiser(advertiser, sample)


@mcp.tool()
def fetch_ad_creative(
    advertiser_id: str,
    creative_id: str,
    out_dir: str = "",
    frames: int = DEFAULT_FRAMES,
    width: int = DEFAULT_WIDTH,
    full_quality: bool = False,
) -> dict:
    """Download an ad's actual creative to local files.

    Image ads are always saved at their original resolution, so the file you get
    back is the real creative — usable in a deck or a slide as-is. Video ads are
    downloaded and sampled into evenly spaced JPEG frames.

    Args:
        advertiser_id: The advertiser's ID (e.g. "AR04139428671737823233")
        creative_id: The creative/ad ID (e.g. "CR01542648288744833025")
        out_dir: Directory to write into. Defaults to a fresh temp directory.
        frames: How many frames to sample from a video (default 8).
        width: Frame width in pixels, height follows aspect (default 320).
            Ignored when full_quality is set; pass 0 for native resolution.
        full_quality: Keep the best video stream and write frames at native
            resolution. Use for presentation; leave off for vision analysis.

    Returns:
        {format, out_dir, files, ...}. Text ads carry no downloadable asset and
        return their decoded copy instead.
    """
    detail = _get_client().get_ad_detail(advertiser_id, creative_id)
    content = detail.get("content", {})
    target = Path(out_dir) if out_dir else Path(
        tempfile.mkdtemp(prefix=f"ad_{creative_id}_")
    )

    result: dict = {
        "format": detail.get("format", "unknown"),
        "out_dir": str(target),
        "last_shown": detail.get("last_shown", ""),
        "files": [],
    }

    video_url = content.get("video_url", "")
    image_url = content.get("image_url", "")

    if video_url and "youtube.com" in video_url:
        sampled = extract_video_frames(
            video_url,
            target,
            frames=frames,
            width=0 if full_quality and width == DEFAULT_WIDTH else width,
            full_quality=full_quality,
        )
        result["files"] = sampled["frames"]
        result["video_path"] = sampled["video_path"]
        result["duration"] = sampled["duration"]
        result["video_url"] = video_url
    elif image_url and "content.js" not in image_url:
        result["files"] = [download_image(image_url, target, name=creative_id)]
        result["image_url"] = image_url
    else:
        result["note"] = "No downloadable asset — this creative is text-only."

    for key in ("headline", "description", "destination_url", "button_label"):
        if content.get(key):
            result[key] = content[key]
    return result


@mcp.tool()
def download_ad_creatives(
    advertiser_name: str,
    out_dir: str,
    count: int = 10,
    full_quality: bool = True,
    frames: int = 4,
) -> dict:
    """Download a whole advertiser's creatives into one folder, with a manifest.

    This is the bulk path for collecting real ad examples — images at their
    original resolution, videos sampled to stills — so they can be dropped
    straight into a deck or a report. Each creative gets its own subfolder.

    Args:
        advertiser_name: The advertiser's name (e.g. "Buildkite", "Vercel Inc.")
        out_dir: Directory to write into. Created if missing.
        count: How many creatives to pull (default 10, max 100).
        full_quality: Native-resolution assets, suitable for presentation.
        frames: Frames to sample per video creative (default 4).

    Returns:
        {advertiser, out_dir, manifest_path, creatives: [...]} where each entry
        carries its format, local file paths, and any decoded ad copy.
    """
    count = max(1, min(count, 100))
    client = _get_client()
    ads = client.get_ads(advertiser_name, count)

    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    entries = []

    for ad in ads:
        creative_id = ad.get("creative_id", "")
        content = ad.get("content", {})
        entry: dict = {
            "creative_id": creative_id,
            "format": ad.get("format", "unknown"),
            "last_shown": ad.get("last_shown", ""),
            "files": [],
        }
        for key in ("headline", "description", "destination_url", "button_label"):
            if content.get(key):
                entry[key] = content[key]

        target = root / creative_id
        video_url = content.get("video_url", "")
        image_url = content.get("image_url", "")
        try:
            if video_url and "youtube.com" in video_url:
                sampled = extract_video_frames(
                    video_url, target, frames=frames,
                    width=0 if full_quality else DEFAULT_WIDTH,
                    full_quality=full_quality,
                )
                entry["files"] = sampled["frames"]
                entry["video_path"] = sampled["video_path"]
                entry["video_url"] = video_url
                entry["duration"] = sampled["duration"]
            elif image_url and "content.js" not in image_url:
                entry["files"] = [
                    download_image(image_url, target, name=creative_id)
                ]
                entry["image_url"] = image_url
            else:
                entry["note"] = "Text-only creative — no downloadable asset."
        except Exception as exc:
            # One dead creative must not sink the batch.
            entry["error"] = f"{type(exc).__name__}: {exc}"
        entries.append(entry)

    manifest = root / "manifest.json"
    payload = {
        "advertiser": advertiser_name,
        "out_dir": str(root),
        "creatives": entries,
    }
    manifest.write_text(json.dumps(payload, indent=2))
    return {**payload, "manifest_path": str(manifest)}
