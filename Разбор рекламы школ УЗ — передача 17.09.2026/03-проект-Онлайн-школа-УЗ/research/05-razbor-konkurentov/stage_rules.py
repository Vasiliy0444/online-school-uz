"""Этап воронки по адресу и тексту страницы. Правила проверяются по порядку, первое совпадение побеждает.

Слова — узбекский (латиница и кириллица) и русский. Если ничего не подошло или признаки противоречат друг другу,
этап решает агент по скриншоту и записывает причину.
"""
import re

TRIPWIRE_MAX_UZS = 300_000

URL_RULES = [
    ("оферта или оплата", r"oferta|offer|shartnoma|dogovor|tolov|to-lov|payment|checkout|oplata|paycom|payme|click\.uz|pay\b|invoice"),
    ("страница спасибо", r"thank|rahmat|spasibo|finish|success|tabrik"),
    ("квиз", r"quiz|kviz|test(?!imon)"),
    ("вебинар или мастер-класс", r"vebinar|webinar|web-|master-?klass|masterclass|jonli|efir|ochiq-?dars|bepul-?dars|intensiv|marafon"),
    ("лид-магнит", r"pdf|qollanma|qo-llanma|guide|gayd|chek-?list|checklist|lead|sovga|bonus|yuklab"),
    ("основной продукт", r"kurs|course|tarif|narx|price|program|oqim|potok|academy|/smm$|/dizayn$|/frontend$|/it$"),
]

TEXT_RULES = [
    ("оферта или оплата", r"ommaviy oferta|публичная оферта|оммавий оферта|to'lov qilish|to'lovni amalga|оплатить|shartnoma shartlari"),
    ("страница спасибо", r"rahmat|ro'yxatdan o'tdingiz|tabriklaymiz|спасибо за регистрацию|kanalga qo'shiling"),
    ("квиз", r"savolga javob bering|testdan o'ting|пройдите тест|qaysi kasb sizga mos"),
    ("вебинар или мастер-класс", r"vebinar|webinar|master-?klass|jonli efir|bepul dars|ochiq dars|мастер-класс|вебинар|эфир"),
    ("лид-магнит", r"bepul qo'llanma|chek-?list|pdf|yuklab oling|sovg'a|бесплатн\w* (гайд|чек-лист|pdf)"),
    ("основной продукт", r"tarif|paket|standart|premium|vip|modul|\d+ ta dars|kursga yozilish|oqim|тариф|модул"),
]

DATE_RE = re.compile(r"\b\d{1,2}[-–]?(sentabr|oktabr|noyabr|dekabr|yanvar|fevral|mart|aprel|may|iyun|iyul|avgust)|soat \d{1,2}[:.]\d{2}|\d{1,2}:\d{2}", re.I)
NORMALIZE = str.maketrans({"‘": "'", "’": "'", "ʻ": "'", "ʼ": "'", "`": "'"})


def stage_from_url(url: str) -> str | None:
    path = re.sub(r"^https?://[^/]+", "", url.lower())
    for stage, pattern in URL_RULES:
        if re.search(pattern, path):
            return stage
    return None


def stage_from_text(text: str, min_price_uzs: int | None = None) -> str | None:
    norm = (text or "").translate(NORMALIZE).lower()
    for stage, pattern in TEXT_RULES:
        if re.search(pattern, norm):
            if stage == "вебинар или мастер-класс" and not DATE_RE.search(norm) and min_price_uzs:
                continue  # «бесплатный урок» без даты, но с ценой — скорее курс
            if stage == "основной продукт" and min_price_uzs and min_price_uzs <= TRIPWIRE_MAX_UZS:
                return "мини-курс или трипвайер"
            return stage
    if min_price_uzs:
        return "мини-курс или трипвайер" if min_price_uzs <= TRIPWIRE_MAX_UZS else "основной продукт"
    return None


def classify(url: str, text: str = "", min_price_uzs: int | None = None) -> tuple[str, str]:
    """(этап, основание). Текст надёжнее адреса, адрес — запасной признак."""
    by_text = stage_from_text(text, min_price_uzs) if text else None
    by_url = stage_from_url(url)
    if by_text and by_url and by_text != by_url:
        return by_text, f"текст ({by_text}) против адреса ({by_url}) — проверить по скриншоту"
    if by_text:
        return by_text, "текст страницы"
    if by_url:
        return by_url, "адрес страницы"
    return "прочее", "признаков нет — решить по скриншоту"
