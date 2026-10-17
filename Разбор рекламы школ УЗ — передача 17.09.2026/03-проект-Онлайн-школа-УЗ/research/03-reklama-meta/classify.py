#!/usr/bin/env python3
"""Чистка и разметка объявлений из raw/*.json.

Запуск из этой папки:
    python3 classify.py

Что делает:
  1. Собирает карточки всех запросов, убирает дубли по ID объявления (Library ID).
  2. Размечает каждое объявление: язык, инфопродукт или нет, ниши, тип воронки, цены, флаг риска,
     сколько дней идёт показ.
  3. Пишет ads.csv (все объявления), ads_uz_info.csv (узбекоязычные инфопродукты),
     advertisers.csv (сводка по рекламодателям), niches_x_funnels.csv и summary.json.

Разметка — правила по ключевым словам. Это черновая классификация для навигации по данным:
спорные случаи проверяются глазами, итоговые выводы — только со ссылкой на объявление.
"""
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
USD_TO_UZS = 11765  # курс ЦБ Узбекистана на 15.09.2026
EVERGREEN_DAYS = 30
TRIPWIRE_MAX_UZS = 300_000

APOSTROPHES = re.compile(r"[‘’ʻʼ`´]")
TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁўЎқҚғҒҳҲ']+")
UZ_LAT_APOSTROPHE = re.compile(r"\b\w*[og]'\w+", re.IGNORECASE)

UZ_LAT_WORDS = {
    "va", "uchun", "bilan", "bepul", "kurs", "kursi", "kursga", "kursda", "kurslar", "daromad", "qanday",
    "hozir", "kerak", "emas", "yoki", "ham", "mumkin", "qiling", "oling", "narxi", "chegirma", "joylar",
    "darslar", "dars", "ishlash", "pul", "haqida", "orqali", "yangi", "faqat", "siz", "sizga", "sizning",
    "biz", "bizning", "bu", "shu", "har", "kun", "kuni", "oyiga", "soat", "vebinar", "marafon", "sotuv",
    "savdo", "topish", "boshlang", "bosing", "yozing", "havola", "kanal", "kanalga", "obuna", "eng",
    "juda", "katta", "endi", "bugun", "ertaga", "hamma", "barcha", "mening", "men", "ular", "qilish",
    "olish", "berish", "dan", "gacha", "bor", "ushbu", "tez", "oson", "tilida", "uyda", "masofadan",
    "ish", "ishga", "kasb", "bilim", "tajriba", "natija", "natijalar", "mutaxassis", "ustoz", "sizni",
    "sentabr", "oktabr", "dekabr", "yanvar", "fevral", "iyun", "iyul", "avgust", "soatda", "ta",
}
UZ_CYR_LETTERS = set("ўЎқҚғҒҳҲ")
UZ_CYR_WORDS = {
    "ва", "учун", "билан", "бепул", "даромад", "сиз", "сизга", "ҳам", "керак", "эмас", "ёки", "мумкин",
    "қилиш", "орқали", "ҳақида", "янги", "фақат", "нархи", "сўм", "чегирма", "дарс", "дарслар", "бўлади",
    "қандай", "ҳозир", "пул", "ишлаш", "касб", "бугун", "жойлар", "устоз", "ўрганинг", "рўйхатдан",
}
RU_WORDS = {
    "и", "в", "на", "для", "что", "как", "вы", "это", "не", "с", "по", "от", "вас", "ваш", "если", "или",
    "уже", "чтобы", "только", "бесплатно", "узнайте", "получите", "обучение", "заработок", "сейчас",
    "мы", "наш", "при", "до", "за", "без", "из", "у", "к", "о", "так", "можно", "нужно", "будет", "есть",
}
EN_WORDS = {
    "the", "and", "for", "your", "with", "get", "free", "now", "our", "you", "to", "of", "in", "on",
    "this", "that", "is", "are", "learn", "shop", "new", "best", "more", "we",
}

INFO_PATTERNS = [
    r"\bkurs", r"\bdars", r"vebinar|webinar", r"marafon", r"intensiv", r"master[- ]?klass|masterklass",
    r"mentor", r"kurator", r"o'rgan", r"o'rgat", r"ta'lim", r"akademiya|academy", r"maktab|\bschool\b",
    r"bootcamp|praktikum", r"\befir\b", r"qo'llanma", r"o'quv", r"shogird", r"sertifikat", r"\bustoz",
    r"\bkasb", r"курс", r"дарс", r"вебинар", r"марафон", r"интенсив", r"мастер-?класс", r"ментор",
    r"ўрган", r"таълим", r"академия", r"мактаб", r"эфир", r"қўлланма", r"ўқув", r"шогирд", r"устоз",
    r"касб", r"обучени", r"урок",
]
INFO_NEGATIVE = re.compile(r"valyuta kurs|dollar kurs|kurs valyut|курс валют|курс доллар|валюта курс")
# Вакансии, доставка, такси, банковские карты и приложения выходят на запросы про «daromad»,
# но курсом не являются. Если признаков курса мало, такое объявление не считается инфопродуктом.
NON_INFO_RE = re.compile(
    r"kuryer|courier|haydovchisi|taksi|taxi|keshbek|cashback|kredit|mikroqarz|\bkarta(si|ngiz|lari)?\b|mastercard|"
    r"sovrin|xarid|iphone|smartfon|qaynoq aksiya|chegirmali aksiya|dostavka|yetkazib berish|ilovani yuklab|курьер|такси|кешбэк|кредит|"
    r"franshiza|франшиза|kvartira|turar joy|uy-joy|ipoteka|квартир|parazit|potensiya|prostata|gemorroy")
# Вакансии — не продажа обучения, даже если в тексте «dars» и «maktab».
VACANCY_RE = re.compile(r"qidirmoqda|ishga (qabul|taklif|olamiz)|vakansiya|rezyume|o'qituvchilarini|вакансия|ищем")

FUNNEL_RULES = [
    ("вебинар или бесплатный урок", re.compile(
        r"vebinar|webinar|bepul dars|ochiq dars|master[- ]?klass|masterklass|jonli efir|video ?dars|"
        r"бепул дарс|вебинар|мастер-?класс|жонли эфир|бесплатн\w* урок")),
    ("марафон или интенсив", re.compile(r"marafon|intensiv|challenge|марафон|интенсив|челлендж")),
    ("лид-магнит", re.compile(r"qo'llanma|\bpdf\b|chek-?list|checklist|\bgid\b|bepul kitob|қўлланма|чек-?лист|гайд")),
    ("слово в директ или комментарий", re.compile(
        r"direkt|\bdirect\b|izoh(ga|da)|komment|deb yozing|deb izoh|so'zini (qoldir|yoz)|xabar yuboring|"
        r"директ|изоҳ|деб ёзинг|напишите")),
    ("Telegram-бот или канал", re.compile(r"telegram|\bbot\b|телеграм|\bбот\b")),
    ("заявка или звонок", re.compile(
        r"ariza|raqam\w* qoldir|qo'ng'iroq|menejer|konsultatsiya|ариза|рақам\w* қолдир|қўнғироқ|менежер|консультац")),
    ("прямая продажа", re.compile(r"sotib oling|to'lov|chegirma|narxi|сотиб олинг|тўлов|нархи|чегирма|скидк")),
    ("офлайн", re.compile(r"oflayn|offline|filial|manzil|o'quv markaz|офлайн|филиал|манзил|ўқув маркази")),
]
DM_CTAS = {"send message", "message page", "send whatsapp message"}
DM_DOMAINS = {"fb.me", "m.me", "wa.me", "api.whatsapp.com", "ig.me", "instagram.com", "www.instagram.com"}
TG_DOMAINS = {"t.me", "telegram.me", "www.t.me"}
FORM_CTAS = {"sign up", "apply now", "get quote", "contact us", "call now", "request time"}

# Порядок важен только при равном числе совпадений: предмет курса (маркетплейсы, монтаж, SMM…)
# идёт раньше ИИ, потому что ИИ часто добавлен бонус-модулем к другому курсу.
NICHE_RULES = [
    ("маркетплейсы", re.compile(r"uzum|wildberries|\bozon\b|yandex ?market|marketpleys|marketplace|xitoydan|tovar biznes|маркетплейс|узум")),
    ("монтаж и видео", re.compile(r"mobilograf|montaj|capcut|reels|videograf|premiere|мобилограф|монтаж")),
    ("маркетинг и SMM", re.compile(r"\bsmm\b|target|marketing|marketolog|kopirayt|shaxsiy brend|bloger|смм|таргет|маркетинг|блогер")),
    ("фриланс, IT, дизайн", re.compile(
        r"frilans|freelanc|upwork|fiverr|dasturla|\bit\b|dizayn|design|figma|canva|\bux\b|\b3d\b|revit|autocad|arxitektur|"
        r"logist|dispetcher|фриланс|дастурла|дизайн")),
    ("ремёсла и бьюти", re.compile(
        r"manikyur|kosmetolog|konditer|qandolat|tikuv|tikish|moda akademiya|sartarosh|barber|vizaj|kiprik|oshpaz|pishiriq|"
        r"retsept|pekar|nit protsedur|маникюр|косметолог|кондитер|тикув|пекар|рецепт")),
    ("бухгалтерия и офис", re.compile(r"buxgalter|excel|\b1c\b|soliq hisobot|бухгалтер|эксель")),
    ("медицина и профобучение", re.compile(
        r"stomatolog|shifokor|tish shifokor|tishlash|elayner|implant|hamshira|farmatsevt|dorixona|стоматолог|шифокор|врач|фармацевт")),
    ("ИИ", re.compile(r"sun'iy intellekt|\bai\b|chatgpt|neyro|claude|prompt|vibe ?coding|midjourney|сунъий интеллект|нейро")),
    ("бизнес и финансы", re.compile(r"biznes|tadbirkor|investits|treyding|treyder|trading|kripto|crypto|forex|moliya|бизнес|тадбиркор|инвестиц|трейдинг|трейдер|крипто|форекс")),
    ("другие профессии", re.compile(r"tur ?agent|haydovchilik|avtomaktab|avto maktab|автошкол|турагент")),
    ("здоровье и похудение", re.compile(r"\bozish|ozmoqchi|qomat|dietolog|vazn|fitnes|fitness|intim salomatlik|похуде|диетолог")),
    ("психология и саморазвитие", re.compile(r"psixolog|motivats|shaxsiy rivoj|психолог|мотивац")),
    ("языки", re.compile(
        r"ingliz|ingiliz|english|ielts|cefr|nemis tili|xitoy tili|rus tili|arab tili|koreys|turk tili|speaking|razgovor|"
        r"инглиз|немис|араб тил|рус тил|хитой тил|английск")),
    ("школа, дети, поступление", re.compile(
        r"milliy sertifikat|abituriyent|\bdtm\b|kimyo|biologiya|matematika|fizika|huquq|sinf o'quvchi|farzand|bolalar|\bkids\b|"
        r"junior|абитуриент|математик|физик|химия|farzandingiz")),
    ("заработок в целом", re.compile(r"daromad|pul ishlash|pul topish|masofaviy|uydan turib|даромад|пул ишлаш|масофавий")),
]
# Хвост карточки, который разборщик иногда захватывает вместе с текстом объявления.
FOOTER_MARKERS = ("See more System status", "System status", "Ad Library API", "About ads and data use")
GROUP_TO_NICHE = {
    "voronki": "без явной ниши", "zarabotok": "заработок в целом", "marketpleysy": "маркетплейсы",
    "montazh": "монтаж и видео", "marketing": "маркетинг и SMM", "ii": "ИИ",
    "frilans-it-dizain": "фриланс, IT, дизайн", "remesla-byuti": "ремёсла и бьюти",
    "biznes-risk": "бизнес и финансы", "drugoe": "языки",
}
RISK_RE = re.compile(
    r"treyding|treyder|\btreyd\b|trading|kripto|crypto|forex|passiv daromad|kafolat\w* daromad|kuniga \$|"
    r"tarmoq marketing|network marketing|\bmlm\b|pul energiya|affirmats|transformatolog|stavka|kazino|"
    r"трейдинг|трейдер|крипто|форекс|пассив\w* доход|денежн\w* блок|казино")
# «Инвестиция» — риск только в финансовом смысле (акции, биржа, доходность), а не «инвестиция в себя/образование».
INVEST_RE = re.compile(r"investits|инвестиц")
INVEST_FINANCE_RE = re.compile(r"birja|aksiya|portfel|dividend|\bfoiz|депозит|depozit|биржа|акци|доходност")
INVEST_METAPHOR_RE = re.compile(r"o'zingizga investits|ta'limga investits|kelajakka investits|инвестици\w* в себя|в образование")
# «Trading» у логистов — это работа с грузами (load trading), а не финансовый трейдинг.
LOGISTICS_RE = re.compile(r"logist|dispetcher|yuk tashish|truck|broker|логист|диспетчер")

PRICE_UZS_RE = re.compile(
    r"(\d{1,3}(?:[ .,]\d{3})+|\d+(?:[.,]\d+)?)\s*(ming|mln|million|минг|млн)?\s*(so'm|som|sum|сўм|сум|uzs)",
    re.IGNORECASE)
PRICE_USD_RE = re.compile(r"\$\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*(?:\$|usd|dollar)", re.IGNORECASE)
# Сумма считается ценой курса только рядом со словами про цену, а обещанием дохода — рядом со словами про доход.
PRICE_CONTEXT = re.compile(r"narx|to'lov|chegirma|atigi|bor-yo'g'i|qiymati|narxda|price|нарх|тўлов|чегирма|стоимост|цена|скидк")
INCOME_CONTEXT = re.compile(r"daromad|oylik|oyiga|maosh|ishlab|topish|zarabot|даромад|ойлик|ойига|маош|доход|заработ")


def normalize(text: str) -> str:
    return APOSTROPHES.sub("'", text or "").lower()


def clean_body(text: str | None) -> str:
    cleaned = text or ""
    for marker in FOOTER_MARKERS:
        cut = cleaned.find(marker)
        if cut != -1:
            cleaned = cleaned[:cut]
    cleaned = re.sub(r"\[([^\]]*)\]\(https?://[^)]*\)", r"\1", cleaned)
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"\b\d{1,2}:\d{2} / \d{1,2}:\d{2}\b", " ", cleaned)
    cleaned = re.sub(r"​|\bActive\b", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def detect_lang(text: str) -> str:
    norm = normalize(text)
    tokens = TOKEN_RE.findall(norm)
    uz_lat = sum(t in UZ_LAT_WORDS for t in tokens) + 2 * len(UZ_LAT_APOSTROPHE.findall(norm))
    uz_cyr = 3 * min(5, sum(ch in UZ_CYR_LETTERS for ch in text or "")) + sum(t in UZ_CYR_WORDS for t in tokens)
    has_cyrillic = bool(re.search(r"[а-яё]", norm))
    ru = sum(t in RU_WORDS for t in tokens) if has_cyrillic else 0
    en = sum(t in EN_WORDS for t in tokens)
    uz = max(uz_lat, uz_cyr)
    if uz >= 2 and ru >= 3:
        return "uz+ru"
    if uz >= 2 and uz >= en:
        return "uz-lat" if uz_lat >= uz_cyr else "uz-cyr"
    if ru >= 2:
        return "ru"
    if en >= 3:
        return "en"
    return "unknown"


def info_score(text: str) -> int:
    norm = normalize(text)
    if INFO_NEGATIVE.search(norm) or VACANCY_RE.search(norm):
        return 0
    score = sum(1 for pattern in INFO_PATTERNS if re.search(pattern, norm))
    if NON_INFO_RE.search(norm) and score <= 1:
        return 0
    return score


def classify_funnel(text: str, cta: str | None, domain: str | None) -> list[str]:
    norm = normalize(text)
    domain = (domain or "").lower()
    cta = (cta or "").lower()
    found = [name for name, rx in FUNNEL_RULES if rx.search(norm)]
    if (cta in DM_CTAS or domain in DM_DOMAINS) and "слово в директ или комментарий" not in found:
        found.append("слово в директ или комментарий")
    if domain in TG_DOMAINS and "Telegram-бот или канал" not in found:
        found.append("Telegram-бот или канал")
    if cta in FORM_CTAS and "заявка или звонок" not in found:
        found.append("заявка или звонок")
    order = [name for name, _ in FUNNEL_RULES]
    return sorted(found, key=order.index)


def classify_niches(text: str, groups: list[str]) -> list[str]:
    norm = normalize(text)
    hits = [(len(rx.findall(norm)), -i, name) for i, (name, rx) in enumerate(NICHE_RULES) if rx.search(norm)]
    if not hits:
        return [GROUP_TO_NICHE.get(g, "без явной ниши") for g in groups[:1]] or ["без явной ниши"]
    return [name for _count, _order, name in sorted(hits, reverse=True)]


def _money_mentions(norm: str) -> list[tuple[int, int, int]]:
    """Все суммы в тексте: (сумма в сумах, начало, конец)."""
    found = []
    for m in PRICE_UZS_RE.finditer(norm):
        number, multiplier = m.group(1), (m.group(2) or "").lower()
        value = float(re.sub(r"[ .,](?=\d{3}\b)", "", number).replace(",", "."))
        if multiplier in ("ming", "минг"):
            value *= 1_000
        elif multiplier in ("mln", "million", "млн"):
            value *= 1_000_000
        if value >= 1_000:
            found.append((int(value), m.start(), m.end()))
    for m in PRICE_USD_RE.finditer(norm):
        amount = float((m.group(1) or m.group(2)).replace(",", "."))
        if 1 <= amount <= 50_000:
            found.append((int(amount * USD_TO_UZS), m.start(), m.end()))
    return found


def parse_money(text: str) -> tuple[list[int], list[int]]:
    """Делит суммы на цены курса и обещания дохода по словам рядом с суммой."""
    norm = normalize(text)
    prices, incomes = set(), set()
    for value, start, end in _money_mentions(norm):
        window = norm[max(0, start - 50):end + 50]
        if PRICE_CONTEXT.search(window):
            prices.add(value)
        elif INCOME_CONTEXT.search(window):
            incomes.add(value)
    return sorted(prices), sorted(incomes)


def parse_prices_uzs(text: str) -> list[int]:
    return parse_money(text)[0]


def is_risky(text: str) -> bool:
    """Трейдинг, крипта, форекс, гарантии дохода, сетевые схемы и «денежная» эзотерика.

    Поправки после ручного разбора 39 помеченных объявлений 16.09.2026: «trading» у логистов
    и «инвестиция в себя» у школ и вузов риском не считаются.
    """
    norm = normalize(text)
    match = RISK_RE.search(norm)
    if match and not (match.group(0) == "trading" and LOGISTICS_RE.search(norm)):
        return True
    return bool(INVEST_RE.search(norm) and INVEST_FINANCE_RE.search(norm) and not INVEST_METAPHOR_RE.search(norm))


def parse_started(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%b %d, %Y", "%d %b %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value.replace("Sept", "Sep"), fmt).date()
        except ValueError:
            continue
    return None


def load_raw(raw_dir: Path) -> tuple[dict, list[dict]]:
    ads: dict[str, dict] = {}
    per_query = []
    for path in sorted(raw_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        scan_day = datetime.fromisoformat(data["fetched_at"]).date()
        per_query.append({"query": data["query"], "group": data["group"], "cards": data["cards"],
                          "advertisers": len({a.get("advertiser") for a in data["ads"]}),
                          "blocked_suspected": data.get("blocked_suspected", False)})
        for card in data["ads"]:
            ad = ads.setdefault(card["library_id"], {**card, "queries": [], "groups": [], "scan_day": scan_day})
            ad["queries"].append(data["query"])
            if data["group"] not in ad["groups"]:
                ad["groups"].append(data["group"])
    return ads, per_query


def enrich(ad: dict) -> dict:
    body = clean_body(ad.get("body"))
    text = " ".join(filter(None, [body, clean_body(ad.get("link_text"))]))
    # Домен лендинга тоже подсказывает формат: vebinar.uznetix.com, aiochiqdars.aicreator.academy.
    text_with_domain = f"{text} {(ad.get('landing_domain') or '').replace('.', ' ')}"
    started = parse_started(ad.get("started_running"))
    days = (ad["scan_day"] - started).days if started else None
    prices, incomes = parse_money(text)
    funnels = classify_funnel(text_with_domain, ad.get("cta"), ad.get("landing_domain"))
    niches = classify_niches(text, ad["groups"])
    lang = detect_lang(text)
    score = info_score(text_with_domain)
    return {
        "library_id": ad["library_id"],
        "ad_url": ad["ad_details_url"],
        "advertiser": ad.get("advertiser", ""),
        "advertiser_handle": ad.get("advertiser_handle", ""),
        "started_running": started.isoformat() if started else "",
        "days_running": days if days is not None else "",
        "evergreen_30d": bool(days is not None and days >= EVERGREEN_DAYS),
        "ads_using_creative": ad.get("ads_using_creative", 1),
        "lang": lang,
        "is_uzbek": lang in ("uz-lat", "uz-cyr", "uz+ru"),
        "info_score": score,
        "is_info_product": score >= 1,
        "niche_primary": niches[0],
        "niches": "; ".join(niches),
        "funnel_primary": funnels[0] if funnels else "не определён",
        "funnels": "; ".join(funnels),
        "price_min_uzs": prices[0] if prices else "",
        "price_max_uzs": prices[-1] if prices else "",
        "tripwire_price": bool(prices and prices[0] <= TRIPWIRE_MAX_UZS),
        "income_claim_max_uzs": incomes[-1] if incomes else "",
        "risk_flag": is_risky(text),
        "cta": ad.get("cta") or "",
        "landing_domain": ad.get("landing_domain") or "",
        "landing_url": ad.get("landing_url") or "",
        "link_text": clean_body(ad.get("link_text")),
        "body": body[:1000],
        "queries": "; ".join(ad["queries"]),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarize_advertisers(rows: list[dict]) -> list[dict]:
    by_adv: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_adv[row["advertiser"]].append(row)
    summary = []
    for name, items in by_adv.items():
        starts = [r["started_running"] for r in items if r["started_running"]]
        summary.append({
            "advertiser": name,
            "handle": items[0]["advertiser_handle"],
            "active_ads": len(items),
            "creatives_sum": sum(int(r["ads_using_creative"]) for r in items),
            "earliest_start": min(starts) if starts else "",
            "max_days_running": max((int(r["days_running"]) for r in items if r["days_running"] != ""), default=""),
            "evergreen_ads": sum(r["evergreen_30d"] for r in items),
            "niches": "; ".join(n for n, _ in Counter(r["niche_primary"] for r in items).most_common(3)),
            "funnels": "; ".join(f for f, _ in Counter(r["funnel_primary"] for r in items).most_common(3)),
            "landing_domains": "; ".join(d for d, _ in Counter(r["landing_domain"] for r in items if r["landing_domain"]).most_common(3)),
            "price_min_uzs": min((r["price_min_uzs"] for r in items if r["price_min_uzs"] != ""), default=""),
            "risk_flag": any(r["risk_flag"] for r in items),
            "example_ad": items[0]["ad_url"],
        })
    return sorted(summary, key=lambda r: (-r["active_ads"], -r["creatives_sum"]))


def main() -> None:
    raw_ads, per_query = load_raw(HERE / "raw")
    rows = [enrich(ad) for ad in raw_ads.values()]
    # Рекламодатель считается продавцом обучения, если про обучение хотя бы половина его узбекоязычных объявлений.
    # Тогда в выборку попадают и его объявления без слов «курс» (например, «$500–2000 онлайн-продажами, звоните»).
    # У остальных (магазины, пиццерии, клиники с одним «мастер-классом») берутся только объявления про обучение.
    # Порог подобран после первого прогона 16.09.2026: без него в выборку попали 17 магазинов и сервисов, 49 объявлений.
    uz_rows = [r for r in rows if r["is_uzbek"]]
    per_advertiser = defaultdict(lambda: [0, 0])
    for r in uz_rows:
        per_advertiser[r["advertiser"]][0] += 1
        per_advertiser[r["advertiser"]][1] += r["is_info_product"]
    school_like = {name for name, (total, info) in per_advertiser.items() if name and info / total >= 0.5}
    uz_info = [r for r in uz_rows if r["advertiser"] in school_like or r["is_info_product"]]
    # Объявления без распознанного имени страницы остаются в выборке, но в сводку рекламодателей не идут:
    # под пустым именем склеиваются разные страницы.
    advertisers = summarize_advertisers([r for r in uz_info if r["advertiser"]])

    matrix = defaultdict(lambda: {"ads": 0, "advertisers": set()})
    for r in uz_info:
        cell = matrix[(r["niche_primary"], r["funnel_primary"])]
        cell["ads"] += 1
        cell["advertisers"].add(r["advertiser"])
    matrix_rows = sorted(
        ({"niche": n, "funnel": f, "ads": c["ads"], "advertisers": len(c["advertisers"])} for (n, f), c in matrix.items()),
        key=lambda r: (r["niche"], -r["advertisers"]))

    write_csv(HERE / "ads.csv", rows)
    write_csv(HERE / "ads_uz_info.csv", uz_info)
    write_csv(HERE / "advertisers.csv", advertisers)
    write_csv(HERE / "niches_x_funnels.csv", matrix_rows)
    summary = {
        "queries": len(per_query),
        "queries_blocked_suspected": sum(q["blocked_suspected"] for q in per_query),
        "cards_total": sum(q["cards"] for q in per_query),
        "unique_ads": len(rows),
        "lang": dict(Counter(r["lang"] for r in rows)),
        "uzbek_info_ads": len(uz_info),
        "uzbek_info_advertisers": len(advertisers),
        "risk_ads": sum(r["risk_flag"] for r in uz_info),
        "evergreen_ads": sum(r["evergreen_30d"] for r in uz_info),
        "per_query": per_query,
    }
    (HERE / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_query"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
