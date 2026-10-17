"""Проверка разбора объявлений Meta: ссылки, соцсети, плоская строка.

Запуск из этой папки:  python3 -m pytest test_common.py -q -p no:cacheprovider
"""
import common as c

AD = {
    "ad_archive_id": "1366425478509152",
    "page_id": "111238895346791",
    "page_name": "Qadam.online",
    "start_date": 1763924400,  # 2025-11-24 00:00 по Ташкенту
    "is_active": True,
    "collation_id": "999",
    "collation_count": 2,
    "publisher_platform": ["FACEBOOK", "INSTAGRAM"],
    "snapshot": {
        "body": {"text": "Uzum’da savdo qilishni xohlaysiz, lekin qayerdan boshlashni bilmayapsizmi? UZUM bo‘yicha bepul darslar"},
        "display_format": "VIDEO",
        "cta_text": "Learn more",
        "link_url": "https://l.facebook.com/l.php?u=https%3A%2F%2Fqadam.education%2Fuzum-pdf%3Futm_source%3DFB&h=AT0",
        "videos": [{"video_hd_url": "https://video.fbcdn.net/v/abc_n.mp4?x=1"}],
        "cards": [],
        "page_like_count": 578,
        "page_profile_uri": "https://www.facebook.com/100093860176934/",
        "page_categories": ["Education"],
    },
}


def test_unwrap_link_and_domain():
    assert c.unwrap_link(AD["snapshot"]["link_url"]) == "https://qadam.education/uzum-pdf?utm_source=FB"
    assert c.domain_of(AD["snapshot"]["link_url"]) == "qadam.education"
    assert c.domain_of("https://www.instagram.com/qadam_education") == "instagram.com"


def test_social_handles_skip_posts_and_invites():
    found = c.social_handles("Kanal: t.me/+ESx_6g9iOMA1 va t.me/qadam_sharhlar",
                             ["https://www.instagram.com/p/C1234/", "https://www.instagram.com/qadam_education/"])
    assert found["telegram"] == ["qadam_sharhlar"]
    assert found["instagram"] == ["qadam_education"]


def test_dco_templates_are_removed_from_text():
    ad = {"snapshot": {"body": {"text": "{{product.brand}}"}, "cards": [{"body": "Bepul vebinar", "title": "{{product.name}}"}]}}
    assert c.ad_text(ad) == "Bepul vebinar"


def test_flat_ad_fields():
    row = c.flat_ad(AD, "2026-09-16T12:00:00+00:00")
    assert row["page_id"] == "111238895346791"
    assert row["started"] == "2025-11-24"
    assert row["days_running"] == 296
    assert row["landing_domain"] == "qadam.education"
    assert row["collation_count"] == 2
    assert row["n_videos"] == 1
    assert row["lang"] == "uz-lat"
    assert row["info_score"] >= 1
