"""compare_advertisers and summarize_advertiser against a stubbed client. No network."""

import os

import pytest

from google_ads_transparency_mcp.scraper import (
    AdsTransparencyBlocked,
    AdsTransparencyError,
    GoogleAdsTransparency,
)


def _client(lookup):
    """A GoogleAdsTransparency whose domain search is a dict lookup."""
    c = GoogleAdsTransparency.__new__(GoogleAdsTransparency)
    c._region = "anywhere"

    def search(domain):
        hit = lookup[domain]
        if isinstance(hit, Exception):
            raise hit
        return hit

    c.search_advertiser_by_domain = search
    return c


def test_compare_rows_in_input_order_with_statuses():
    c = _client({
        "nike.com": {"advertiser_id": "AR1", "name": "Nike Retail BV", "ad_count": 100000},
        "example.com": None,
        "github.com": {"advertiser_id": "AR2", "name": "Microsoft Corporation", "ad_count": 80000},
        "broken.io": AdsTransparencyError("unparseable body"),
    })
    rows = c.compare_advertisers(["https://www.nike.com/", "example.com", "github.com",
                                  "nike.com", "broken.io"])
    assert [r["domain"] for r in rows] == ["nike.com", "example.com", "github.com", "broken.io"]
    assert rows[0]["status"] == "ok" and rows[0]["ad_count"] == 100000
    assert rows[0]["parent_entity"] is False
    assert rows[1] == {
        "domain": "example.com", "status": "absent", "ad_count": 0,
        "note": "no Google advertiser is registered for this domain",
    }
    assert rows[2]["parent_entity"] is True and "Do not cite" in rows[2]["note"]
    assert rows[3]["status"] == "error" and "unparseable" in rows[3]["note"]


def test_compare_stops_requesting_once_every_route_is_blocked():
    calls = []
    c = _client({})

    def search(domain):
        calls.append(domain)
        raise AdsTransparencyBlocked("blocked everywhere")

    c.search_advertiser_by_domain = search
    rows = c.compare_advertisers(["a.com", "b.com", "c.com"])
    assert calls == ["a.com"]
    assert [r["status"] for r in rows] == ["blocked"] * 3
    assert rows[1]["note"].startswith("skipped")


def test_compare_uses_company_names_for_parent_check():
    c = _client({"gh.io": {"advertiser_id": "AR3", "name": "GitHub, Inc.", "ad_count": 5}})
    assert c.compare_advertisers(["gh.io"])[0]["parent_entity"] is True
    assert c.compare_advertisers(["gh.io"], {"gh.io": "GitHub"})[0]["parent_entity"] is False


def test_summarize_advertiser_absent():
    c = _client({"nothing.com": None})
    c.search_suggestions = lambda q: []
    out = c.summarize_advertiser("nothing.com", sample=5)
    assert out["status"] == "absent" and out["query"] == "nothing.com"


def test_summarize_advertiser_aggregates_sample():
    c = _client({"nike.com": {"advertiser_id": "AR1", "name": "Nike Retail BV", "ad_count": 9}})
    c.get_creative_ids = lambda aid, n: ["CR1", "CR2"][:n]
    c.get_ad_detail = lambda aid, cid: {
        "advertiser_id": aid, "creative_id": cid, "format": "text", "last_shown": "2026-09-01",
        "content": {"headline": f"H {cid}", "destination_url": "nike.com/x"},
    }
    out = c.summarize_advertiser("nike.com", sample=2)
    assert out["status"] == "ok" and out["active_ads"] == 9
    assert out["sample"]["sampled"] == 2 and out["sample"]["by_format"] == {"text": 2}
    assert out["sample"]["headlines"] == ["H CR1", "H CR2"]


def test_resolve_advertiser_passes_ids_through():
    c = _client({})
    assert c.resolve_advertiser("AR18378488041124659201") == {
        "advertiser_id": "AR18378488041124659201", "name": "", "ad_count": 0,
    }
    assert c.resolve_advertiser("   ") is None


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("ADS_LIVE"), reason="set ADS_LIVE=1 to hit Google")
def test_live_compare_and_summary():
    c = GoogleAdsTransparency()
    rows = c.compare_advertisers(["nike.com", "example.com"])
    assert rows[0]["status"] in ("ok", "blocked")
    out = c.summarize_advertiser("nike.com", sample=3)
    assert out["status"] in ("ok", "absent")
