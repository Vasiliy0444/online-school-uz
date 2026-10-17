"""Сборщик Meta без сети: окна по месяцам, разбор JSON из документа, адреса.

Запуск из этой папки:  ~/.venvs/fb-ads-library/bin/python -m pytest test_meta_collect.py -q -p no:cacheprovider
"""
import json
from datetime import date

import meta_collect as mc


def test_month_windows_cover_range_without_gaps():
    windows = mc.month_windows(date(2025, 11, 24), date(2026, 2, 10))
    assert windows == [(date(2025, 11, 1), date(2025, 11, 30)), (date(2025, 12, 1), date(2025, 12, 31)),
                       (date(2026, 1, 1), date(2026, 1, 31)), (date(2026, 2, 1), date(2026, 2, 10))]


def test_ads_are_found_inside_script_json_of_the_document():
    ad = {"ad_archive_id": "1366425478509152", "page_id": "111238895346791", "snapshot": {"body": {"text": "Bepul darslar"}}}
    payload = {"require": [["RelayPrefetchedStreamCache", "next", [], [{"__bbox": {"result": {"data": {
        "ad_library_main": {"search_results_connection": {"edges": [{"node": {"collated_results": [ad]}}]}}}}}}]]]}
    html = ('<!DOCTYPE html><html id="facebook"><head></head><body>'
            f'<script type="application/json" data-sjs>{json.dumps(payload)}</script></body></html>')
    sink: dict = {}
    for doc in mc.json_payloads(html):
        mc.collect_ads(doc, sink)
    assert list(sink) == ["1366425478509152"]


def test_graphql_lines_with_prefix_are_parsed():
    body = 'for (;;);{"data":{"x":[{"ad_archive_id":"1","snapshot":{}}]}}\n{"extensions":{"is_final":true}}'
    sink: dict = {}
    for doc in mc.json_payloads(body):
        mc.collect_ads(doc, sink)
    assert list(sink) == ["1"]


def _ad(day: str) -> dict:
    from datetime import datetime, timezone, timedelta
    ts = int(datetime.fromisoformat(day + "T12:00:00").replace(tzinfo=timezone(timedelta(hours=5))).timestamp())
    return {"start_date": ts, "snapshot": {}}


def test_cursor_moves_to_oldest_launch_in_batch():
    batch = {str(i): _ad("2026-05-24" if i < 11 else "2026-04-28") for i in range(30)}
    assert mc.next_cursor(batch, "2026-09-16") == ("2026-04-28", "")


def test_cursor_jumps_to_previous_month_when_month_group_is_not_full():
    # Meta отдаёт в документе одну группу-месяц: 15 сентябрьских объявлений при счётчике ~120 — это не конец списка
    batch = {str(i): _ad("2026-09-04" if i < 5 else "2026-09-15") for i in range(15)}
    assert mc.next_cursor(batch, "2026-09-16") == ("2026-08-31", "")


def test_cursor_ends_on_empty_batch():
    assert mc.next_cursor({}, "2025-01-31") == (None, "конец списка")


def test_cursor_steps_back_a_day_when_30_ads_share_one_day():
    batch = {str(i): _ad("2026-09-10") for i in range(30)}
    cursor, note = mc.next_cursor(batch, "2026-09-10")
    assert cursor == "2026-09-09" and "2026-09-10" in note


def test_page_url_uses_ad_library_page_id():
    url = mc.page_url("111238895346791")
    assert "view_all_page_id=111238895346791" in url and "country=UZ" in url and "is_targeted_country=false" in url


def test_overflow_windows_find_loads_where_counter_grew_by_more_than_30():
    loads = [("2026-09-16", 160), ("2026-08-27", 120), ("2026-07-27", 82), ("2026-05-24", 42), ("2026-04-13", 11)]
    assert mc.overflow_windows(loads) == [("2026-08-27", "2026-09-16", 120, 160), ("2026-07-27", "2026-08-27", 82, 120),
                                          ("2026-05-24", "2026-07-27", 42, 82), ("2026-04-13", "2026-05-24", 11, 42)]
    assert mc.overflow_windows([("2026-09-16", 25)]) == []


def test_midpoint_splits_window_or_gives_up_on_neighbour_days():
    assert mc.midpoint("2026-08-27", "2026-09-16") == "2026-09-06"
    assert mc.midpoint("2026-09-14", "2026-09-15") is None


def test_overflow_windows_use_page_batch_size():
    # у страницы, которой Meta отдаёт по 15 объявлений, окно в 20 объявлений тоже неполное
    assert mc.overflow_windows([("2026-09-16", 20)], cap=15) == [("2015-01-01", "2026-09-16", 0, 20)]
