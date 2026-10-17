"""Google Ads Transparency MCP Server — look up any advertiser's Google ads."""

from .analysis import is_parent_entity, normalize_domain, summarize_ads
from .scraper import AdsTransparencyBlocked, AdsTransparencyError, GoogleAdsTransparency

__all__ = [
    "AdsTransparencyBlocked",
    "AdsTransparencyError",
    "GoogleAdsTransparency",
    "is_parent_entity",
    "normalize_domain",
    "summarize_ads",
]
