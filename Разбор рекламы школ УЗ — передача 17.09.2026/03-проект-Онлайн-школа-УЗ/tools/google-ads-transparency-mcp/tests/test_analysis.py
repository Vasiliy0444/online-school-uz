from google_ads_transparency_mcp.analysis import (
    destination_host,
    is_parent_entity,
    looks_like_advertiser_id,
    normalize_domain,
    summarize_ads,
)


def test_normalize_domain_strips_scheme_www_and_path():
    assert normalize_domain("https://www.Nike.com/us/?x=1") == "nike.com"
    assert normalize_domain("adidas.com") == "adidas.com"
    assert normalize_domain("  http://Example.org:8080/  ") == "example.org"
    assert normalize_domain("") == ""


def test_looks_like_advertiser_id():
    assert looks_like_advertiser_id("AR18378488041124659201")
    assert not looks_like_advertiser_id("nike.com")
    assert not looks_like_advertiser_id("AR12")


def test_parent_entity_flags_unrelated_name_only():
    assert is_parent_entity("github.com", "Microsoft Corporation")
    assert not is_parent_entity("nike.com", "Nike Retail BV")
    assert not is_parent_entity("blacksmith.sh", "Blacksmith Software Inc")
    # A supplied company name can rescue a domain that shares no tokens.
    assert not is_parent_entity("gh.io", "GitHub, Inc.", company="GitHub")
    assert not is_parent_entity("", "Anyone")


def test_destination_host():
    assert destination_host("www.nike.com/launch") == "nike.com"
    assert destination_host("https://shop.adidas.co.uk/x") == "shop.adidas.co.uk"
    assert destination_host("") == ""


def _ad(fmt, **content):
    return {"format": fmt, "last_shown": content.pop("last_shown", ""), "content": content}


def test_summarize_ads_counts_shares_and_samples():
    ads = [
        _ad("text", headline="Run Faster", description="New shoes",
            destination_url="www.nike.com/a", last_shown="2026-08-01"),
        _ad("text", headline="run faster", description="New shoes", destination_url="nike.com/b",
            last_shown="2026-09-01"),
        _ad("image", image_url="https://tpc.googlesyndication.com/simgad/1"),
        _ad("video", video_url="https://www.youtube.com/watch?v=x", headline="Just Do It",
            button_label="Shop now", last_shown="2026-07-15"),
    ]
    s = summarize_ads(ads)
    assert s["sampled"] == 4
    assert s["by_format"] == {"image": 1, "text": 2, "video": 1}
    assert s["format_share"] == {"image": 0.25, "text": 0.5, "video": 0.25}
    assert s["last_shown"] == {"earliest": "2026-07-15", "latest": "2026-09-01"}
    assert s["headlines"] == ["Run Faster", "Just Do It"]  # case-insensitive de-dupe
    assert s["descriptions"] == ["New shoes"]
    assert s["cta_labels"] == [{"label": "Shop now", "count": 1}]
    assert s["destination_hosts"] == [{"host": "nike.com", "count": 2}]
    assert s["with_video"] == 1 and s["with_image"] == 1


def test_summarize_ads_empty():
    s = summarize_ads([])
    assert s["sampled"] == 0 and s["format_share"] == {} and s["headlines"] == []
