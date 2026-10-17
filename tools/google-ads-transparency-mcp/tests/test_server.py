import asyncio

from google_ads_transparency_mcp.server import mcp

EXPECTED = {
    "search_advertiser_by_domain", "search_advertisers", "get_ads", "get_ad_detail",
    "compare_advertisers", "advertiser_summary", "fetch_ad_creative", "download_ad_creatives",
}


def test_all_tools_register():
    tools = asyncio.run(mcp.list_tools())
    assert {t.name for t in tools} == EXPECTED
    for t in tools:
        assert t.description, f"{t.name} has no description"
