#!/usr/bin/env python3
"""Собирает structure.json — manifest кампаний Meta для заливки через MCP (шаг G в
research/15-meta-ads-avtomatizatsiya/ПЛАН-ПОДКЛЮЧЕНИЯ.md).

Источник правды по структуре — словари CREATIVES и CAMPAIGNS ниже.
Файлы креативов ищутся по id в папке research/16-kreativy-meta/«АКТУАЛЬНЫЕ креативы УЗ — Meta»,
тексты под постом — по номеру пула в research/17-teksty-ru-uz/pools_uz_final.json.

Запуск:  python3 build_structure.py   → пишет structure.json рядом
Проверка: python3 check_structure.py
"""
import json
import pathlib
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
CREO_DIR = PROJECT / "research" / "16-kreativy-meta" / "АКТУАЛЬНЫЕ креативы УЗ — Meta"
POOLS_FILE = PROJECT / "research" / "17-teksty-ru-uz" / "pools_uz_final.json"
OUT = HERE / "structure.json"

KPI_USD = 0.30
HEADLINE = "Bepul mini-kurs"  # один заголовок на все объявления; вычитать носителем
CTA = "LEARN_MORE"  # тексты пулов зовут нажать «Batafsil»
URL_TAGS = (
    "utm_source=meta&utm_medium=paid&utm_campaign={{campaign.name}}"
    "&utm_term={{adset.name}}&utm_content={{ad.name}}"
    "&cid={{campaign.id}}&asid={{adset.id}}&aid={{ad.id}}&pl={{placement}}"
)
# Слово-хук в имени объявления меняет заголовок лендинга (websites/ii-na-zakaz-mini/js/hooks.js).
HOOK_BY_POOL = {1: "math", 2: "now", 3: "compare", 4: "zero", 5: "clients",
                6: "compare", 7: "clients", 8: "home", 9: "math"}

# id в кабинете (только латиница) → как креатив назван на диске, формат, пул текста, риск.
CREATIVES = {
    "I1-1":  dict(disk="I1-1",  kind="image", pool=1, risk="low"),
    "I1-2":  dict(disk="I1-2",  kind="image", pool=1, risk="low"),
    "I1-4":  dict(disk="I1-4",  kind="image", pool=5, risk="low"),
    "I2-1":  dict(disk="I2-1",  kind="image", pool=1, risk="low"),
    "I2-2":  dict(disk="I2-2",  kind="image", pool=3, risk="low"),
    "I2-3":  dict(disk="I2-3",  kind="image", pool=3, risk="low"),
    "I2-4":  dict(disk="I2-4",  kind="image", pool=3, risk="medium", note="«$1000 через 2–3 месяца» — риск «нереалистичный результат»"),
    "I3-1":  dict(disk="I3-1",  kind="image", pool=1, risk="low"),
    "I3-3":  dict(disk="I3-3",  kind="image", pool=7, risk="medium", note="«$1000 через 2–3 месяца»"),
    "I1-1S": dict(disk="I1-1S", kind="image", pool=1, risk="low"),
    "I1-2S": dict(disk="I1-2S", kind="image", pool=1, risk="low"),
    "I2-1S": dict(disk="I2-1S", kind="image", pool=1, risk="low"),
    "I2-2S": dict(disk="I2-2S", kind="image", pool=3, risk="low"),
    "I2-3S": dict(disk="I2-3S", kind="image", pool=3, risk="low"),
    "I2-4S": dict(disk="I2-4S", kind="image", pool=3, risk="low"),
    "I3-1S": dict(disk="I3-1S", kind="image", pool=1, risk="low"),
    "I3-3S": dict(disk="I3-3S", kind="image", pool=7, risk="low"),
    "M1":    dict(disk="M1",    kind="image", pool=5, risk="medium", note="пародия на логотип сайта для взрослых"),
    "M2":    dict(disk="M2",    kind="video", pool=4, risk="low"),
    "M3":    dict(disk="M3",    kind="image", pool=4, risk="low"),
    "M4":    dict(disk="M4",    kind="image", pool=4, risk="low", note="«бесплатно до 23:59» должно быть правдой"),
    "M5":    dict(disk="M5",    kind="image", pool=4, risk="low"),
    "M6":    dict(disk="M6",    kind="image", pool=3, risk="medium", note="кадры «Рика и Морти», авторские права"),
    "M7":    dict(disk="M7",    kind="image", pool=4, risk="low"),
    "V1":    dict(disk="V1",    kind="video", pool=2, risk="medium", note="нарисованная кнопка «Bepul ko‘rish»"),
    "V2":    dict(disk="V2",    kind="video", pool=1, risk="high", note="выдуманные уведомления и зачисления; отдельная группа с 4–5 дня, при первом отказе — выключить"),
    "V3":    dict(disk="V3",    kind="video", pool=4, risk="high", note="тот же монтаж, что V4б, но с нарисованным нажатием кнопки — резерв"),
    "V4b":   dict(disk="V4б",   kind="video", pool=2, risk="medium", note="основное видео; V4 с fbstore.shop не льём"),
    "K2-1":  dict(disk="K2-1",  kind="carousel", pool=6, risk="low", note="цифру «такси ~8 млн сум» подтвердить"),
    "K2-1b": dict(disk="K2-1b", kind="carousel", pool=6, risk="low"),
    "K2-3":  dict(disk="K2-3",  kind="carousel", pool=5, risk="low", note="нужен бонус «Топ-10 каналов»"),
    "K2-4":  dict(disk="K2-4",  kind="carousel", pool=8, risk="low", note="J4, волна 2"),
}
WAVE1_RESERVE = {"V3"}
WAVE2_CREATIVES = {"K2-4"}
PENDING_TRANSLATION = ["I1-3", "I1-3B", "I3-2"]  # лежат в «На перевод — I1-3, I1-3B, I3-2»

# --- Общие настройки -----------------------------------------------------------------
CAMPAIGN_DEFAULTS = dict(
    objective="OUTCOME_LEADS",
    buying_type="AUCTION",
    special_ad_categories=[],
    budget_level="ADSET",  # ABO
    is_adset_budget_sharing_enabled=False,
    status="PAUSED",
)
ADSET_DEFAULTS = dict(
    destination_type="WEBSITE",
    optimization_goal="OFFSITE_CONVERSIONS",
    promoted_object={"pixel_id": "{{PIXEL_ID}}", "custom_event_type": "COMPLETE_REGISTRATION"},
    billing_event="IMPRESSIONS",
    bid_strategy="LOWEST_COST_WITHOUT_CAP",
    attribution_spec=[
        {"event_type": "CLICK_THROUGH", "window_days": 7},
        {"event_type": "ENGAGED_VIDEO_VIEW", "window_days": 1},
    ],
    attribution_note="7 дн после клика + 1 день engage-through, без просмотра. Имя типа engage-through сверить через ads_get_field_context.",
    status="PAUSED",
)
TARGETING_BASE = dict(
    geo_locations={"countries": ["UZ"], "location_types": ["home", "recent"]},
    publisher_platforms=["facebook", "instagram"],  # без audience_network и messenger; места внутри — все
    excluded_custom_audiences=["{{CA_REG_180D}}", "{{CA_BUY_180D}}"],
    locales=[],
)
BROAD_AUDIENCE = dict(
    targeting_automation={"advantage_audience": 1},
    age_min=18, age_max=35, genders=[1],
    note="Advantage+ аудитория: жёстко только гео, 18+ и исключения; мужчины 18–35 — подсказка. Галочку «расширить за пределы гео» не ставить.",
)
MANUAL_AUDIENCE = dict(
    targeting_automation={"advantage_audience": 0},
    age_min=18, age_max=35, genders=[1],
    note="Ручная аудитория: мужчины 18–35 жёстко. Расширение интересов Meta включает сама.",
)
AD_DEFAULTS = dict(
    title=HEADLINE, description="", call_to_action=CTA,
    link_url="{{LANDING_URL}}", url_tags=URL_TAGS,
    advantage_creative="все улучшения OPT_OUT (перечислить через ads_get_field_context)",
    multi_advertiser_ads=False,
    page_id="{{PAGE_ID}}", instagram_user_id="{{IG_USER_ID}}",
    status="PAUSED",
)
TOP4_DEFAULT = ["V4b", "I1-1", "K2-1", "M5"]
TOP4_RULE = ("4 креатива с самой низкой ценой старта бота в C1 после ≥48 ч и ≥5 × KPI; при равенстве — выше CTR; "
             "из пары длинный/короткий — только лучший. Если к дню 3 данных мало — пакет по умолчанию.")

# --- Кампании -------------------------------------------------------------------------
CAMPAIGNS = [
    dict(
        key="C1", name="uz_reg_broad_2610", wave=1, start="день 1",
        purpose="тест креативов на широкой аудитории: каждый креатив волны 1 стоит один раз",
        audience=BROAD_AUDIENCE,
        adsets=[
            dict(key="l1", name="BR_L1", budget=4, ads=["I1-1", "I2-1", "I3-3", "I2-4"], test="длинный текст на картинке, пара A"),
            dict(key="s1", name="BR_S1", budget=4, ads=["I1-1S", "I2-1S", "I3-3S", "I2-4S"], test="короткий текст — зеркало BR_L1"),
            dict(key="l2", name="BR_L2", budget=4, ads=["I1-2", "I2-2", "I3-1", "I2-3"], test="длинный текст, пара B"),
            dict(key="s2", name="BR_S2", budget=4, ads=["I1-2S", "I2-2S", "I3-1S", "I2-3S"], test="короткий текст — зеркало BR_L2"),
            dict(key="m1", name="BR_M1", budget=4, ads=["M2", "M3", "I1-4"], test="мемы и «5 способов»"),
            dict(key="m2", name="BR_M2", budget=4, ads=["M4", "M5", "K2-3"], test="мемы-раздача и карусель про клиентов"),
            dict(key="m3", name="BR_M3", budget=4, ads=["M7", "M1", "M6"], test="мемы"),
            dict(key="ak", name="AB_K21", budget=2.5, ads=["K2-1"], test="A/B: карусель-сравнение с цифрами"),
            dict(key="akb", name="AB_K21b", budget=2.5, ads=["K2-1b"], test="A/B: то же без цифр"),
            dict(key="av4", name="AB_V4b", budget=2.5, ads=["V4b"], pool_override=2, test="A/B: монтаж HyperFrames; текст пула 2, как у V1"),
            dict(key="av1", name="AB_V1", budget=2.5, ads=["V1"], pool_override=2, test="A/B: моушн-ролик"),
            dict(key="rv2", name="RISK_V2", budget=2.5, ads=["V2"], start="день 4–5", test="рискованный V2 отдельно; при первом отказе выключить"),
        ],
    ),
    dict(
        key="C2", name="uz_reg_int_2610", wave=1, start="день 3–4",
        purpose="тест интересов: во всех группах одни и те же 4 креатива, контроль — без интересов",
        audience=MANUAL_AUDIENCE, ads_rule=TOP4_RULE, ads_default=TOP4_DEFAULT,
        ab_test_note="Лучше одним A/B-тестом Meta (до 5 групп): тогда аудитории не пересекаются. Создаёт Вася в Ads Manager — у MCP такого инструмента нет.",
        adsets=[
            dict(key="ctl", name="CTRL_M1835", budget=4, interests=[], test="контроль: мужчины 18–35 без интересов"),
            dict(key="ai", name="INT_AI", budget=4, interests=["Artificial intelligence", "ChatGPT"],
                 interests_check=["OpenAI", "Generative artificial intelligence"]),
            dict(key="earn", name="INT_EARN", budget=4, interests=["Freelancer", "Upwork", "Fiverr"],
                 interests_check=["Remote work", "Work from home", "Make money online"]),
            dict(key="srv", name="INT_SERVICES", budget=4, interests=["Web design", "Graphic design", "Telegram (software)"]),
            dict(key="biz", name="INT_BUSINESS", budget=4, interests=["Entrepreneurship", "Small business"],
                 interests_check=["Uzum", "Payme", "Click"]),
        ],
        reserve=dict(name="INT_BLOGERS", interests_check=["Asror Iskandarov", "Alima Oybekovna", "seva_ravshanovna_",
                                                          "Ikhtiyar Dosmetov", "avrangzeb.si"],
                     note="блогеры-конкуренты как интересы, если Meta их находит"),
        never=["Forex", "Trading", "Cryptocurrency", "Passive income"],
    ),
    dict(
        key="C3", name="uz_reg_beh_2610", wave=1, start="день 3–4",
        purpose="тест поведений и демографии; сравнение с CTRL_M1835 из C2 на тех же 4 креативах",
        audience=MANUAL_AUDIENCE, ads_rule=TOP4_RULE, ads_default=TOP4_DEFAULT,
        adsets=[
            dict(key="tech", name="BEH_TECH", budget=4, behaviors=["Technology early adopters"]),
            dict(key="stu", name="DEM_STUDENT", budget=4, demographics=["Education level: In college / Undergrad"],
                 test="J1 студент"),
            dict(key="fam", name="DEM_FAMILY", budget=4, age_min=23,
                 demographics=["Life events: Newly engaged (1 year)", "Life events: Newlywed (1 year)",
                               "Parents: Parents with toddlers (01-02 years)"],
                 test="J2 кормилец, от 23 лет"),
        ],
        merge_rule="Если аудитория группы меньше ~50 тыс., склеить DEM_STUDENT и DEM_FAMILY.",
    ),
]
WAVE2 = [
    dict(key="C4", name="uz_reg_lal_2611", start="от 100 стартов бота, лучше 500",
         adsets=["LAL 1% UZ по CA_REG_30D", "LAL 1–3% UZ по CA_REG_30D",
                 "потом LAL по Lesson3Done, PracticeAttend, Purchase — когда в каждом 100+"],
         ads="топ-4 по цене старта бота из C1–C3"),
    dict(key="C5", name="uz_warm_2611", start="со 2-й недели, $3–5 в день",
         adsets=["W1: лендинг 14 дн без старта бота — «Лиды» → CompleteRegistration",
                 "W2: в боте, не записался на практику — «Охват», частота ≤2 за 7 дн",
                 "W3: был на практике, не купил — «Охват», частота ≤2 за 7 дн"],
         ads="для W2 и W3 нужны креативы-приглашения — их нет"),
    dict(key="C6", name="uz_scale_2611", start="когда есть победители",
         adsets=["3 лучшие аудитории × 3–4 лучших креатива, бюджет на кампанию (CBO)"],
         ads="+20% бюджета раз в 3–4 дня, если старт бота 3–5 дней подряд ≤ KPI"),
    dict(key="C7", name="uz_book_2611", start="когда PracticeBooked ≥50 в неделю на группу",
         adsets=["новая группа с оптимизацией на «записался на практику»"], ads="лучшие из C1–C3"),
]


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def media_index() -> dict[str, pathlib.Path]:
    """Имя файла (NFC) → путь. На macOS имена бывают в NFD, поэтому сравниваем в NFC."""
    return {nfc(p.name): p for p in CREO_DIR.rglob("*") if p.is_file()}


def find_media(creo: dict, index: dict[str, pathlib.Path]) -> dict:
    disk = nfc(creo["disk"])
    if creo["kind"] == "carousel":
        cards = sorted(
            (p for name, p in index.items() if name.startswith(f"{disk}_card") and name.endswith("_1x1.png")),
            key=lambda p: int(nfc(p.name).split("_card")[1].split("_")[0]),
        )
        return {"cards_1x1": [str(p) for p in cards]}
    ext = ".mp4" if creo["kind"] == "video" else ".png"
    found = {}
    for fmt, key in (("4x5", "feed_4x5"), ("9x16", "stories_reels_9x16")):
        hits = [p for name, p in index.items() if name.startswith(f"{disk} ") and name.endswith(f"— {fmt}{ext}")]
        found[key] = str(hits[0]) if len(hits) == 1 else None
    return found


def bodies(pool_texts: dict[str, str], kind: str) -> list[str]:
    if kind == "video":
        return [pool_texts["short"]]  # в Reels видно ~72 знака — под видео только короткий
    return [pool_texts["short"], pool_texts["mid"], pool_texts["long"]]


def build_ad(creo_id: str, adset_key: str, pool_override: int | None,
             pools: dict[int, dict[str, str]], index: dict[str, pathlib.Path]) -> dict:
    creo = CREATIVES[creo_id]
    pool = pool_override or creo["pool"]
    hook = HOOK_BY_POOL[pool]
    return dict(
        name=f"{creo_id}_{adset_key}_{hook}",
        creative_id=creo_id,
        format=creo["kind"],
        media=find_media(creo, index),
        text_pool=pool,
        hook=hook,
        body_options=bodies(pools[pool], creo["kind"]),
        risk=creo["risk"],
        risk_note=creo.get("note", ""),
        **AD_DEFAULTS,
    )


def build_targeting(audience: dict, adset: dict) -> dict:
    targeting = dict(TARGETING_BASE)
    targeting.update({k: v for k, v in audience.items() if k != "note"})
    if adset.get("age_min"):
        targeting["age_min"] = adset["age_min"]
    detailed = {k: adset[k] for k in ("interests", "behaviors", "demographics") if adset.get(k)}
    if detailed:
        targeting["flexible_spec_names"] = detailed
        targeting["flexible_spec_note"] = "ID найти через Graph API /search (adinterest, adTargetingCategory); чего нет — не ставить"
    if adset.get("interests_check"):
        targeting["interests_check"] = adset["interests_check"]
    return targeting


def main() -> None:
    pools = {p["n"]: p["texts"] for p in json.loads(POOLS_FILE.read_text())["pools"]}
    index = media_index()
    campaigns = []
    for camp in CAMPAIGNS:
        adsets = []
        for adset in camp["adsets"]:
            creos = adset.get("ads", camp.get("ads_default", []))
            adsets.append(dict(
                name=adset["name"],
                start=adset.get("start", camp["start"]),
                daily_budget_usd=adset["budget"],
                daily_budget_minor=int(round(adset["budget"] * 100)),
                test=adset.get("test", ""),
                targeting=build_targeting(camp["audience"], adset),
                audience_note=camp["audience"]["note"],
                ads=[build_ad(c, adset["key"], adset.get("pool_override"), pools, index) for c in creos],
                ads_rule=camp.get("ads_rule", ""),
                **ADSET_DEFAULTS,
            ))
        extra = {k: camp[k] for k in ("ab_test_note", "reserve", "never", "merge_rule") if k in camp}
        campaigns.append(dict(key=camp["key"], name=camp["name"], wave=camp["wave"], start=camp["start"],
                              purpose=camp["purpose"], adsets=adsets, **extra, **CAMPAIGN_DEFAULTS))
    manifest = dict(
        version="2026-10-15",
        source="research/18-struktura-kampaniy-i-piksel/build_structure.py",
        kpi_usd=KPI_USD,
        account=dict(ad_account_id="{{AD_ACCOUNT_ID}}", currency="USD", timezone="Asia/Tashkent",
                     page_id="{{PAGE_ID}}", instagram_user_id="{{IG_USER_ID}}",
                     pixel_id="{{PIXEL_ID}}", landing_url="{{LANDING_URL}}"),
        custom_audiences_needed=["CA_REG_180D", "CA_BUY_180D", "CA_REG_30D", "CA_LP_14D", "CA_LP_30D",
                                 "CA_LEAD_7D", "CA_L3_30D", "CA_BOOK_14D", "CA_ATT_30D", "CA_IG_365D",
                                 "CA_VID50_90D"],
        rules_for_executor=[
            "Все объекты — только новые и только PAUSED. Запуск — Вася в Ads Manager.",
            "После ошибки записи сначала читать кабинет, повтор вслепую запрещён.",
            "Плейсхолдеры {{...}} заменить реальными ID до записи; пустое поле не заменять догадкой.",
            "Креатив с двумя форматами (4x5 + 9x16) — через настройку медиа по плейсментам; если MCP не умеет — Meta CLI или Graph API.",
            "Несколько body_options — варианты основного текста в одном объявлении.",
        ],
        campaigns=campaigns,
        wave2=WAVE2,
        reserve_creatives=sorted(WAVE1_RESERVE),
        wave2_creatives=sorted(WAVE2_CREATIVES),
        pending_translation=PENDING_TRANSLATION,
        not_for_meta=["V4 (карточка fbstore.shop — магазин FB-аккаунтов)"],
    )
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    n_ads = sum(len(a["ads"]) for c in campaigns for a in c["adsets"])
    print(f"structure.json: {len(campaigns)} кампании волны 1, "
          f"{sum(len(c['adsets']) for c in campaigns)} групп, {n_ads} объявлений")


if __name__ == "__main__":
    main()
