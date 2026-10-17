"""Этапы воронки на реальных адресах Qadam из Wayback (пилот 16.09.2026) и типовых текстах.

Запуск из этой папки:  python3 -m pytest test_stage_rules.py -q -p no:cacheprovider
"""
import stage_rules as s


def test_urls_from_qadam_archive():
    cases = {
        "https://qadam.education/oferta": "оферта или оплата",
        "https://qadam.education/dogovor-oferta": "оферта или оплата",
        "https://qadam.education/oplata": "оферта или оплата",
        "https://qadam.education/finish": "страница спасибо",
        "https://qadam.education/quiz-smm": "квиз",
        "https://qadam.education/smmvebinar": "вебинар или мастер-класс",
        "https://qadam.education/web-smm": "вебинар или мастер-класс",
        "https://qadam.education/uzum-pdf": "лид-магнит",
        "https://qadam.education/lead1": "лид-магнит",
        "https://qadam.education/smm": "основной продукт",
    }
    for url, stage in cases.items():
        assert s.stage_from_url(url) == stage, url


def test_text_beats_url_and_flags_conflict():
    stage, reason = s.classify("https://example.uz/kurs", "Bepul vebinar 17-sentabr soat 20:30, ro'yxatdan o'ting")
    assert stage == "вебинар или мастер-класс"
    assert "проверить по скриншоту" in reason


def test_price_decides_between_tripwire_and_main_product():
    assert s.stage_from_text("Kursga yozilish: Standart tarif", 99_000) == "мини-курс или трипвайер"
    assert s.stage_from_text("Kursga yozilish: Standart tarif", 1_635_000) == "основной продукт"


def test_thank_you_page_uzbek_apostrophes():
    assert s.stage_from_text("Tabriklaymiz! Siz ro‘yxatdan o‘tdingiz") == "страница спасибо"


def test_nothing_found():
    assert s.classify("https://example.uz/about", "Biz haqimizda") == ("прочее", "признаков нет — решить по скриншоту")
