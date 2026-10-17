"""Нормализация адресов и суммы из ссылок на оплату — без сети.

Запуск из этой папки:  python3 -m pytest test_landings_find.py -q -p no:cacheprovider
"""
import base64

import landings_find as lf


def test_normalize_strips_tracking_and_www():
    url = "http://www.Qadam.education/uzum-pdf/?utm_source=FB&utm_campaign=Uzum&fbclid=abc&step=2"
    assert lf.normalize(url) == "https://qadam.education/uzum-pdf?step=2"
    assert lf.normalize("tg://resolve?domain=x") == ""


def test_payme_amount_from_link_without_opening_it():
    token = base64.b64encode(b"m=5f1a2b;ac.order_id=12;a=99000000;c=https://x.uz").decode()
    assert lf.payment_amount(f"https://checkout.paycom.uz/{token}") == "990000 сум (Payme)"


def test_click_amount_from_query():
    assert lf.payment_amount("https://my.click.uz/services/pay?service_id=1&merchant_id=2&amount=1635000") == "1635000 сум (Click)"


def test_social_links_are_not_landings():
    col = lf.Collector()
    col.add("qadam", "https://www.instagram.com/qadam_education/", "ads:meta")
    col.add("qadam", "https://t.me/qadam_sharhlar", "ads:meta")
    col.add("qadam", "https://qadam.education/uzum-pdf?utm_source=FB", "ads:meta", "2026-04-11")
    col.add("qadam", "https://qadam.education/uzum-pdf", "wayback", "2025-01-02")
    assert list(col.urls) == [("qadam", "https://qadam.education/uzum-pdf")]
    row = col.urls[("qadam", "https://qadam.education/uzum-pdf")]
    assert row["sources"] == {"ads:meta", "wayback"} and row["first_seen"] == "2025-01-02"
