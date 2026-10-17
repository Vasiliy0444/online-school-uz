"""Выводы отчёта берут числа только из facts.json.

Запуск из этой папки:  python3 -m pytest test_report_data.py -q -p no:cacheprovider
"""
import pytest

import report_data as rd

FACTS = {"qadam": {"days_max": 297.0, "ads_collected": 131},
         "shares": {"долгожитель (60+ дней)": {"тип хука": {"боль": 0.4}, "_n": 30}}}


def test_placeholders_are_filled_from_facts():
    text = "Qadam держит креатив {{qadam|days_max}} дней, {{int:qadam|ads_collected}} объявлений, боль — {{pct:shares|долгожитель (60+ дней)|тип хука|боль}}"
    assert rd.render_findings(text, FACTS, {}) == "Qadam держит креатив 297 дней, 131 объявлений, боль — 40%"


def test_unknown_fact_stops_the_build():
    with pytest.raises(SystemExit):
        rd.render_findings("{{qadam|days_median}}", FACTS, {})


def test_examples_must_exist():
    item = {"claim": "x", "examples": ["123"]}
    assert rd.render_findings(item, FACTS, {"123": "qadam"})["examples"] == ["123"]
    with pytest.raises(SystemExit):
        rd.render_findings(item, FACTS, {})


def test_destination_reads_lead_forms_and_messengers():
    base = {"landing_domain": "", "link_url": "", "cta_type": ""}
    assert rd.destination({**base, "landing_domain": "fb.me", "link_url": "http://fb.me/"}) == "мгновенная форма Meta"
    assert rd.destination({**base, "landing_domain": "t.me", "link_url": "https://t.me/x"}) == "Telegram"
    assert rd.destination({**base, "cta_type": "INSTAGRAM_MESSAGE"}) == "Instagram"
    assert rd.destination({**base, "landing_domain": "qadam.education", "link_url": "https://qadam.education/uzum"}) == "сайт"
    assert rd.destination(base) == "без ссылки"


def test_plural_and_date_formatting():
    facts = {"all": {"ads": 921, "pages": 63, "creatives": 82, "few": 12}, "google": {"last": "2026-03-28"}}
    text = "{{plural:all|ads:объявление/объявления/объявлений}}, {{plural:all|pages:страница/страницы/страниц}}, " \
           "{{plural:all|creatives:креатив/креатива/креативов}}, {{plural:all|few:креатив/креатива/креативов}}, {{date:google|last}}"
    assert rd.render_findings(text, facts, {}) == "921 объявление, 63 страницы, 82 креатива, 12 креативов, 28 марта 2026"
