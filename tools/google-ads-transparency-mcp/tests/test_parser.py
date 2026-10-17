from google_ads_transparency_mcp.scraper import GoogleAdsTransparency

parse = GoogleAdsTransparency._parse_preview_body


def test_text_ad_copy_from_renderer_body():
    body = (
        "<c-wiz jsrenderer\\x3d\\x22hCjESd\\x22 data-p\\x3d\\x22%.@.[1,[\\x26quot;Nike Sportswear"
        " dla mężczyzn\\x26quot;,\\x26quot;Odkryj {Keyword} online na Nike.com \\x26amp; more"
        "\\x26quot;,\\x26quot;nike.com\\x26quot;,null,[[\\x26quot;Nike\\x26quot;]]]\\x22>"
    )
    assert parse(body) == {
        "headline": "Nike Sportswear dla mężczyzn",
        "description": "Odkryj {Keyword} online na Nike.com & more",
        "destination_url": "nike.com",
    }


def test_video_renderer_body_still_parses():
    body = "var t = {'video_id': 'abc123', 'headline': 'Just Do It', 'button_label': 'Shop'};"
    out = parse(body)
    assert out["video_id"] == "abc123"
    assert out["video_url"] == "https://www.youtube.com/watch?v=abc123"
    assert out["headline"] == "Just Do It" and out["button_label"] == "Shop"


def test_unrelated_body_parses_to_nothing():
    assert parse("<html>nothing to see</html>") == {}
