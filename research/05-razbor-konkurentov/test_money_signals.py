"""Пограничные случаи порогов «денежной» школы.

Запуск из этой папки:  python3 -m pytest test_money_signals.py -q -p no:cacheprovider
"""
import money_signals as ms


def school(**over):
    base = {"school_id": "x", "name": "X", "track": "заработок", "niche": "ИИ", "risk": False, "meta_active": 30.0,
            "google_uz": 0.0, "unique_creatives": 10.0, "evergreen": 5.0, "recent": 0.0, "uz_share": 0.9,
            "followers_max": 20_000.0, "page_ids": "1", "domains": "", "ad_library": ""}
    base.update(over)
    return base


def test_boundary_29_vs_30_active_ads():
    assert ms.classify_school(school(meta_active=30.0)) == "денежная (основной порог)"
    assert ms.classify_school(school(meta_active=29.0)) == "денежная (запасной порог)"


def test_meta_plus_google_counts_together():
    assert ms.classify_school(school(meta_active=25.0, google_uz=15.0)) == "денежная (основной порог)"


def test_two_creatives_is_a_test_not_a_school():
    assert ms.classify_school(school(meta_active=40.0, unique_creatives=2.0)) == "мало рекламы или тест"


def test_no_ads_anywhere():
    assert ms.classify_school(school(meta_active=0.0, google_uz=0.0)) == "реклама не найдена на дату замера"


def test_shortlist_fills_with_fallback_when_fewer_than_five_pass_main():
    schools = [school(school_id=f"m{i}", meta_active=100.0 - i) for i in range(3)]
    schools += [school(school_id=f"f{i}", meta_active=20.0 - i) for i in range(4)]
    for s in schools:
        s["status"] = ms.classify_school(s)
    picked = ms.pick_shortlist(schools)
    assert [s["school_id"] for s in picked] == ["m0", "m1", "m2", "f0", "f1"]


def test_risky_schools_are_not_auto_shortlisted():
    risky = school(school_id="trade", meta_active=200.0, risk=True)
    clean = [school(school_id=f"c{i}", meta_active=50.0 - i) for i in range(5)]
    for s in [risky, *clean]:
        s["status"] = ms.classify_school(s)
    picked = [s["school_id"] for s in ms.pick_shortlist([risky, *clean])]
    assert "trade" not in picked and len(picked) == 5


def test_unknown_language_from_texts_does_not_fail_the_school():
    assert ms.classify_school(school(uz_share=None)) == "денежная (основной порог)"
    assert ms.classify_school(school(uz_share=0.3)) == "мало рекламы или тест"


def test_english_track_takes_two():
    eng = [school(school_id=f"e{i}", track="английский", meta_active=60.0 - i) for i in range(4)]
    for s in eng:
        s["status"] = ms.classify_school(s)
    assert [s["school_id"] for s in ms.pick_shortlist(eng)] == ["e0", "e1"]


def test_approved_shortlist_keeps_gate_order_and_merges_domains():
    schools = [school(school_id=i, domains="qadam.online" if i == "qadam" else "") for i in reversed(ms.APPROVED)]
    rows = ms.approved_shortlist(schools)
    assert [r["school_id"] for r in rows] == ms.APPROVED
    assert next(r for r in rows if r["school_id"] == "qadam")["domains"] == "qadam.online; qadam.education"


def test_approved_shortlist_fails_loudly_when_school_missing():
    import pytest
    with pytest.raises(SystemExit):
        ms.approved_shortlist([school(school_id="qadam")])
