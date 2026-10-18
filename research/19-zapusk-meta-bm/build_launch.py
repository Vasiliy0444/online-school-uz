#!/usr/bin/env python3
"""Собирает launch.json и реестр креативов и текстов для запуска в кабинете БМ «Uzbekustan RK».

Структура утверждена 17.10.2026 (01-ПЛАН-ЗАПУСКА.md): неделя 1 до $150, событие Lead.
C1 uz_lead_broad_2610 — 5 групп низкого риска с дня 1. RISK uz_lead_risk_2610 — 3 группы, публикуется с 4-го дня.

Откуда что:
- каталог креативов, хуки, общие настройки, поиск файлов — research/18…/build_structure.py (план 15.10);
- тексты под постами — research/17-teksty-ru-uz/pools_uz_final.json;
- ID кабинета, страницы, Instagram, пикселя — ids.json;
- ID созданных в Meta объектов — meta_ids.json (заполняется при заливке).

    python3 build_launch.py   → launch.json, registry.json, РЕЕСТР-КРЕАТИВОВ-И-ТЕКСТОВ.md
    python3 check_launch.py   → проверка; с --online — ещё и ссылки raw
"""
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "research" / "18-struktura-kampaniy-i-piksel"))
import build_structure as B  # noqa: E402  план 15.10

VERSION = "2026-10-17"
RAW_BASE = "https://raw.githubusercontent.com/Vasiliy0444/online-school-uz"
POOLS_RU = B.POOLS_FILE.with_name("pools_ru.json")
IDS_FILE = HERE / "ids.json"
META_IDS_FILE = HERE / "meta_ids.json"
OUT_LAUNCH = HERE / "launch.json"
OUT_REGISTRY = HERE / "registry.json"
OUT_MD = HERE / "РЕЕСТР-КРЕАТИВОВ-И-ТЕКСТОВ.md"
WEEK_CAP_USD = 150

# Этих креативов нет в каталоге 15.10. I1-3, I1-3B, I3-2 носитель проверил 17.10 — волна 2. V4 — для полноты реестра.
EXTRA_CREATIVES = {
    "I1-3":  dict(disk="I1-3",  kind="image", pool=9, risk="medium", note="«продал за 3 млн сум» — нужен настоящий проданный сайт и скрин оплаты"),
    "I1-3B": dict(disk="I1-3B", kind="image", pool=9, risk="medium", note="только если $1 040 на скрине — оплата именно за этот сайт"),
    "I3-2":  dict(disk="I3-2",  kind="video", pool=9, risk="medium", note="«продал за 3 млн сум» — нужен настоящий проданный сайт и скрин оплаты"),
    "V4":    dict(disk="V4",    kind="video", pool=2, risk="never", note="карточка fbstore.shop — магазин FB-аккаунтов"),
}
CREATIVES = {**B.CREATIVES, **EXTRA_CREATIVES}
RESERVE = {"V3"}
WAVE2 = {"K2-4", "I1-3", "I1-3B", "I3-2"}
NEVER = {"V4"}

# --- Кампании недели 1 (решения Васи 17.10: Lead, риск отдельной кампанией с 4-го дня, неделя до $150) -----
PLAN_FILE = HERE / "v2_plan.json"
TYPE_TEST = {
    "LONG": "длинный текст на картинке", "SHORT": "те же 5 концептов с коротким текстом — зеркало LONG",
    "MEME": "мемы-раздача", "MIX": "остальная статика низкого риска",
    "CAR": "карусели; K2-1 с цифрами против K2-1b без",
    "RSTAT": "статика и мемы среднего риска", "RVID": "ролики среднего и высокого риска; V2 — выключить при первом отказе",
}
# Пересборка 17.10 по голосовому Васи: группы по аудиториям, каждый креатив минимум в 2 аудиториях (v2_plan.json).
CAMPAIGN_META = {
    "uz_lead_main_2610": dict(key="C1", start="день 1", spend_cap_usd=120, labels=[],
                              purpose="креативы низкого риска на 5 аудиториях: широкая, Advantage+, три по интересам"),
    "uz_lead_risk_2610": dict(key="RISK", start="день 4", spend_cap_usd=100, labels=["RISK"],
                              purpose="креативы среднего и высокого риска на широкой и Advantage+; включаем с 4-го дня"),
}


def load_plan() -> tuple[list[dict], dict]:
    plan = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    campaigns = []
    for name, camp in plan["campaigns"].items():
        adsets = [dict(key=a["aud"], name=adset_name, aud=a["aud"], type=a["type"], budget=plan["daily_budget_cents"] / 100,
                       ads=plan["types"][a["type"]], test=TYPE_TEST[a["type"]])
                  for adset_name, a in camp["adsets"].items()]
        campaigns.append(dict(CAMPAIGN_META[name], name=name, adsets=adsets))
    return campaigns, plan


CAMPAIGNS, PLAN = load_plan()
DAYS_IN_WEEK = {"день 1": 7, "день 4": 4}

# Свои аудитории сайта: event=None — все посетители лендинга.
AUDIENCES = [
    dict(name="CA_REG_180D", event="CompleteRegistration", days=180,
         why="исключение во всех холодных; наполнится, когда заработает CAPI"),
    dict(name="CA_BUY_180D", event="Purchase", days=180, why="исключение во всех холодных"),
    dict(name="CA_REG_30D", event="CompleteRegistration", days=30, why="источник LAL, неделя 2+"),
    dict(name="CA_LP_14D", event=None, days=14, why="посетители лендинга — ретаргет W1"),
    dict(name="CA_LP_30D", event=None, days=30, why="посетители лендинга"),
    dict(name="CA_LEAD_7D", event="Lead", days=7, why="нажал кнопку «в бота», но не стартовал"),
]

KIND_RU = {"image": "картинка", "video": "видео", "carousel": "карусель"}
RISK_RU = {"low": "низкий", "medium": "средний", "high": "высокий", "never": "не для Meta"}
START_LIMITS = {"source": 10, "campaign": 18, "content": 20}  # как в websites/ii-na-zakaz-mini/js/attribution.js


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def last_commit(rel: str) -> str | None:
    """Последний коммит, где менялся файл. None — файл не закоммичен или изменён в рабочей копии."""
    if git("status", "--porcelain", "--", rel):
        return None
    return git("log", "-1", "--format=%H", "--", rel) or None


def probe(path: Path) -> dict:
    if path.suffix.lower() == ".png":
        with Image.open(path) as im:
            return dict(width=im.width, height=im.height)
    if not shutil.which("ffprobe"):
        return dict(width=None, height=None, duration_s=None, audio=None)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True).stdout
    info = json.loads(out or "{}")
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    duration = info.get("format", {}).get("duration")
    return dict(width=video.get("width"), height=video.get("height"),
                duration_s=round(float(duration), 1) if duration else None,
                audio=any(s.get("codec_type") == "audio" for s in streams))


def media_entry(role: str, abs_path: str | None, meta_media: dict) -> dict:
    if not abs_path:
        return dict(role=role, path=None)
    path = Path(abs_path)
    rel = path.relative_to(ROOT).as_posix()
    sha = last_commit(rel)
    return dict(role=role, path=rel, bytes=path.stat().st_size, commit=sha,
                url=f"{RAW_BASE}/{sha}/{urllib.parse.quote(rel)}" if sha else None,
                **probe(path), meta=meta_media.get(rel, {}))


def media_list(code: str, index: dict, meta_media: dict) -> list[dict]:
    found = B.find_media(CREATIVES[code], index)
    if "cards_1x1" in found:
        return [media_entry(f"card{i}_1x1", p, meta_media) for i, p in enumerate(found["cards_1x1"], 1)]
    return [media_entry(role, found[role], meta_media) for role in ("feed_4x5", "stories_reels_9x16")]


def sanitize(value: str, limit: int) -> str:
    """Часть метки для параметра start бота — как sanitizePart в attribution.js."""
    cleaned = re.sub(r"_+", "_", re.sub(r"[^a-z0-9_]+", "_", value.lower())).strip("_")
    return cleaned[:limit].rstrip("_")


def start_tag(campaign: str, ad_name: str) -> str:
    parts = ("meta", campaign, ad_name)
    return "vm-" + "-".join(sanitize(v, START_LIMITS[k]) for k, v in zip(("source", "campaign", "content"), parts))


def audience_rule(aud: dict, pixel_id: str) -> str:
    """Правило для ads_create_custom_audience (subtype WEBSITE) — строка JSON, как требует MCP."""
    if aud["event"] is None:
        template, flt = "ALL_VISITORS", {"field": "url", "operator": "i_contains", "value": ""}
    else:
        template, flt = "VISITORS_BY_URL", {"field": "event", "operator": "eq", "value": aud["event"]}
    rule = {"inclusions": {"operator": "or", "rules": [{
        "event_sources": [{"type": "pixel", "id": pixel_id}],
        "retention_seconds": aud["days"] * 86400,
        "filter": {"operator": "and", "filters": [flt]},
        "template": template,
    }]}}
    return json.dumps(rule, ensure_ascii=False)


def ad_link(landing: str, campaign: str, adset: str, name: str) -> str:
    """Ссылка объявления — как в креативе: готовые метки, без макросов (у инструмента создания креатива нет url_tags)."""
    q = urllib.parse.urlencode(dict(utm_source="meta", utm_medium="paid", utm_campaign=campaign, utm_term=adset, utm_content=name))
    return f"{landing}?{q}"


def signup_text(text: str) -> str:
    """Текст под кнопку «Зарегистрироваться»: ссылки на кнопку «Batafsil» в таком объявлении быть не должно."""
    return text.replace("«Batafsil» tugmasini", "Tugmani")


def build_ad(code: str, adset: dict, camp: dict, pools: dict, ids: dict, index: dict, meta: dict) -> dict:
    creo = CREATIVES[code]
    pool = creo["pool"]
    hook = B.HOOK_BY_POOL[pool]
    base = f"{code}_{hook}_{adset['aud']}"
    cta_plan = PLAN["cta"]
    sign_up = base in cta_plan["sign_up_ads"]
    cta = "SIGN_UP" if sign_up else cta_plan["default"]
    name = base + cta_plan["sign_up_suffix"] if sign_up else base  # он же utm_content в ссылке
    title_ru = PLAN["titles"][code]
    text = signup_text if sign_up else (lambda t: t)
    video = creo["kind"] == "video"
    landing = PLAN["landing"]
    ad_defaults = dict(B.AD_DEFAULTS,
                       call_to_action=cta,
                       link_url=ad_link(landing, camp["name"], adset["name"], name),
                       url_tags="",
                       conversion_domain=urllib.parse.urlparse(landing).netloc,
                       page_id=ids.get("page_id") or "{{PAGE_ID}}",
                       instagram_user_id=ids.get("instagram_user_id"))
    return dict(
        name=name,
        display_name=f"{name} · {title_ru} · {cta_plan['button_ru'][cta]}",  # имя объявления и креатива в Meta
        title_ru=title_ru,
        replaces=base if sign_up else None,
        creative_code=code,
        format=creo["kind"],
        media=media_list(code, index, meta["media"]),
        text_pool=pool,
        hook=hook,
        body_keys=["short"] if video else ["mid"],
        body_options=[text(t) for t in B.bodies(pools[pool], creo["kind"])],
        body_fallback=text(pools[pool]["short" if video else "mid"]),  # один текст: при медиа по плейсментам API принимает только его
        bot_start_tag=start_tag(camp["name"], name),
        risk=creo["risk"],
        risk_note=creo.get("note", ""),
        labels=camp["labels"],
        meta=meta["ads"].get(name, {}),
        **ad_defaults,
    )


def build_adset(adset: dict, camp: dict, pools: dict, ids: dict, index: dict, meta: dict) -> dict:
    aud = PLAN["audiences"][adset["aud"]]
    defaults = dict(B.ADSET_DEFAULTS,
                    promoted_object={"pixel_id": ids.get("pixel_id") or "{{PIXEL_ID}}", "custom_event_type": "LEAD"})
    return dict(
        name=adset["name"],
        key=adset["key"],
        audience=adset["aud"],
        audience_title=aud["title"],
        interests_to_add=aud.get("interests_to_add", []),
        paused_until_interests=bool(aud.get("interests_to_add")),
        creative_type=adset["type"],
        start=camp["start"],
        daily_budget_usd=adset["budget"],
        daily_budget_minor=round(adset["budget"] * 100),
        test=adset["test"],
        targeting=aud["targeting"],
        audience_note=aud["title"],
        labels=camp["labels"],
        meta_id=meta["adsets"].get(f"{camp['name']}/{adset['name']}"),
        ads=[build_ad(code, adset, camp, pools, ids, index, meta) for code in adset["ads"]],
        **defaults,
    )


def build_campaigns(pools: dict, ids: dict, index: dict, meta: dict) -> list[dict]:
    out = []
    for camp in CAMPAIGNS:
        out.append(dict(
            key=camp["key"], name=camp["name"], start=camp["start"], purpose=camp["purpose"],
            spend_cap_usd=camp["spend_cap_usd"], spend_cap_minor=camp["spend_cap_usd"] * 100,
            labels=camp["labels"], meta_id=meta["campaigns"].get(camp["name"]),
            adsets=[build_adset(a, camp, pools, ids, index, meta) for a in camp["adsets"]],
            **B.CAMPAIGN_DEFAULTS,
        ))
    return out


def status_of(code: str, placed: dict) -> str:
    if code in placed:
        return "волна 1 · RISK с 4-го дня" if placed[code][0]["campaign"].startswith("uz_lead_risk") else "волна 1 · C1 с дня 1"
    if code in NEVER:
        return "не для Meta"
    if code in RESERVE:
        return "резерв"
    if code in WAVE2:
        return "волна 2"
    return "не распределён"


def build_registry(campaigns: list[dict], pools_uz: dict, pools_ru: dict, index: dict, meta: dict) -> list[dict]:
    placed: dict[str, list] = {}
    for camp in campaigns:
        for adset in camp["adsets"]:
            for ad in adset["ads"]:
                placed.setdefault(ad["creative_code"], []).append(dict(
                    campaign=camp["name"], adset=adset["name"], audience=adset["audience"], ad_name=ad["name"],
                    display_name=ad["display_name"], cta=ad["call_to_action"],
                    bot_start_tag=ad["bot_start_tag"], meta=ad["meta"]))
    registry = []
    for code, creo in CREATIVES.items():
        hits = placed.get(code, [])
        media = media_list(code, index, meta["media"])
        folders = sorted({str(Path(m["path"]).parent.relative_to(B.CREO_DIR.relative_to(ROOT)))
                          for m in media if m.get("path")})
        video = creo["kind"] == "video"
        registry.append(dict(
            code=code,
            kind=creo["kind"],
            folder=folders[0] if len(folders) == 1 else folders,
            status=status_of(code, placed),
            placements=hits,
            pool=creo["pool"],
            pool_title_ru=pools_ru[creo["pool"]]["title"],
            pool_title_uz=pools_uz[creo["pool"]]["title_uz"],
            hook=B.HOOK_BY_POOL[creo["pool"]],
            texts_used=(["short"] if video else ["mid"]) if hits else None,
            risk=creo["risk"],
            risk_note=creo.get("note", ""),
            media=media,
        ))
    return registry


def md_link(rel: str | None, label: str) -> str:
    if not rel:
        return f"{label}: нет файла"
    return f"[{label}]({urllib.parse.quote('../../' + rel)})"


def md_files(item: dict) -> str:
    media = item["media"]
    if item["kind"] == "carousel":
        return f"{len(media)} карточек 1:1: " + " ".join(md_link(m["path"], str(i)) for i, m in enumerate(media, 1))
    parts = []
    for m in media:
        label = "4:5" if m["role"] == "feed_4x5" else "9:16"
        if m.get("duration_s"):
            label += f", {m['duration_s']:g} с"
        parts.append(md_link(m["path"], label))
    return " · ".join(parts)


def md_meta(item: dict) -> str:
    bits = [f"`{h['ad_name']}`: ad `{h['meta'].get('ad_id', '—')}`, creative `{h['meta'].get('creative_id', '—')}`"
            + (f" — {h['meta']['state']}" if h['meta'].get('state') else "")
            for h in item["placements"]]
    uploaded = sum(1 for m in item["media"] if m.get("meta"))
    if uploaded:
        bits.append(f"медиа загружено {uploaded}/{len(item['media'])}")
    return "; ".join(bits) or "—"


def build_md(campaigns: list[dict], registry: list[dict], pools_uz: dict, pools_ru: dict, ids: dict) -> str:
    lines = [
        "# Реестр креативов и текстов — запуск Meta в кабинете БМ",
        "",
        f"Собирает `build_launch.py` ({VERSION}) из `v2_plan.json` (структура по аудиториям), каталога креативов "
        "`research/18-struktura-kampaniy-i-piksel/build_structure.py`, текстов `research/17-teksty-ru-uz/pools_uz_final.json`, "
        "`ids.json` и `meta_ids.json`. Руками не править: правки — в источниках, потом `python3 build_launch.py`. "
        "Почему так — `01-ПЛАН-ЗАПУСКА.md`, раздел 10.",
        "",
        f"Кабинет `{ids['ad_account_id']}` «{ids['ad_account_name']}», БМ {ids['business']}. "
        f"Страница: {ids.get('page_id') or 'не задана'}. Instagram: {ids.get('instagram_user_id') or 'нет — решение Васи'}. "
        f"Пиксель: {ids.get('pixel_id') or 'не задан'}. Лендинг: {PLAN['landing']}",
        "",
        "## Аудитории",
        "",
        "Везде Узбекистан (живут или недавно были), мужчины и женщины, Facebook и Instagram, "
        "исключены `CA_REG_180D` и `CA_BUY_180D`.",
        "",
        "| Код | Аудитория | Возраст | Advantage+ аудитория | Что добавить |",
        "|---|---|---|---|---|",
    ]
    for key, aud in PLAN["audiences"].items():
        if aud.get("later"):
            lines.append(f"| `{key}` | {aud['title']} | — | — | группа появится позже |")
            continue
        t = aud["targeting"]
        age = f"{t['age_min']}–{t['age_max']}" if t.get("age_max") else f"от {t['age_min']}, дальше решает Meta"
        adv = "включена" if t["targeting_automation"]["advantage_audience"] else "выключена"
        todo = ("интересы вручную в Ads Manager: " + ", ".join(aud["interests_to_add"]) +
                " (у инструмента нет поиска ID интересов); до этого группы на паузе") if aud.get("interests_to_add") else "—"
        lines.append(f"| `{key}` | {aud['title']} | {age} | {adv} | {todo} |")
    lines += [
        "",
        "## Кампании и группы — неделя 1",
        "",
        "| Кампания | Группа | Аудитория | В день | С какого дня | Объявления | Что проверяем |",
        "|---|---|---|---|---|---|---|",
    ]
    for camp in campaigns:
        for adset in camp["adsets"]:
            ads = ", ".join(f"`{ad['name']}`" + (" (рег.)" if ad["call_to_action"] == "SIGN_UP" else "") for ad in adset["ads"])
            paused = " · на паузе до интересов" if adset["paused_until_interests"] else ""
            lines.append(f"| `{camp['name']}` | `{adset['name']}` | `{adset['audience']}`{paused} | ${adset['daily_budget_usd']:g} | "
                         f"{camp['start']} | {ads} | {adset['test']} |")
    lines.append("")
    planned = 0
    for camp in campaigns:
        per_day = sum(a["daily_budget_usd"] for a in camp["adsets"])
        days = DAYS_IN_WEEK[camp["start"]]
        planned += per_day * days
        lines.append(f"- `{camp['name']}`: ${per_day:g} в день × {days} дн. ≈ ${per_day * days:g}, "
                     f"лимит трат кампании ${camp['spend_cap_usd']}." + (" Метка RISK, включаем с 4-го дня." if camp["labels"] else ""))
    lines += [f"- План недели ≈ ${planned:g}. Потолок ${WEEK_CAP_USD} держит лимит расходов кабинета: лимиты кампаний "
              f"в сумме ${sum(c['spend_cap_usd'] for c in campaigns)}, меньше $100 на кампанию Meta не принимает.", ""]

    lines += [
        "## Креативы — все из папки «АКТУАЛЬНЫЕ креативы УЗ — Meta»",
        "",
        "| Код | Тип | Статус | Где стоит: группа → объявление | Пул · хук | Текст | Риск | Файлы | ID в Meta |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in registry:
        where = "<br>".join(f"`{h['adset']}` → `{h['ad_name']}` · {PLAN['cta']['button_ru'][h['cta']]}" for h in item["placements"]) or "—"
        texts = "/".join({"short": "S", "mid": "M", "long": "L"}[k] for k in item["texts_used"]) if item["texts_used"] else "—"
        risk = RISK_RU[item["risk"]] + (f": {item['risk_note']}" if item["risk_note"] else "")
        title = f" — {PLAN['titles'][item['code']]}" if item["code"] in PLAN["titles"] else ""
        lines.append(f"| {item['code']}{title} | {KIND_RU[item['kind']]} | {item['status']} | {where} | "
                     f"{item['pool']} · {item['hook']} | {texts} | {risk} | {md_files(item)} | {md_meta(item)} |")
    lines += ["", "Текст: один на объявление — M (средний) у картинок и каруселей, S (короткий) у видео: при разных медиа "
              "для лент и для Stories/Reels API принимает только один основной текст.", ""]

    lines += [
        "## Тексты под постами",
        "",
        "Полные тексты: узбекский — [`03-ТЕКСТЫ-ПУЛЫ-UZ.md`](../17-teksty-ru-uz/03-ТЕКСТЫ-ПУЛЫ-UZ.md), "
        "русский — [`02-ТЕКСТЫ-ПУЛЫ-RU.md`](../17-teksty-ru-uz/02-ТЕКСТЫ-ПУЛЫ-RU.md). "
        "Заголовок у всех объявлений — «Bepul mini-kurs». Кнопка — «Подробнее», у 27 объявлений с `_su` в имени — "
        "«Зарегистрироваться», и в их тексте ««Batafsil» tugmasini» заменено на «Tugmani» (план, раздел 11).",
        "",
        "| Пул | Тема | Креативы волны 1 | Знаков UZ: S / M / L | Начало текста (UZ) |",
        "|---|---|---|---|---|",
    ]
    for n, pool in pools_uz.items():
        wave1 = ", ".join(i["code"] for i in registry if i["pool"] == n and i["placements"]) or "—"
        texts = pool["texts"]
        first = texts["short"].split("\n")[0]
        lines.append(f"| {n} | {pools_ru[n]['title']} / {pool['title_uz']} | {wave1} | "
                     f"{len(texts['short'])} / {len(texts['mid'])} / {len(texts['long'])} | {first} |")
    lines += [
        "",
        "## Метка в боте",
        "",
        "Кнопка лендинга передаёт боту метку `start`: кампания и объявление, а в имени объявления — код аудитории. "
        "По ней видно, какое объявление и какая аудитория привели человека. Метки объявлений:",
        "",
    ]
    lines += [f"- `{h['ad_name']}` → `{h['bot_start_tag']}`" for i in registry for h in i["placements"]]
    lines += ["", "## Как добавить креатив или текст", "",
              "1. Файл — в «АКТУАЛЬНЫЕ креативы УЗ — Meta/<папка>» под именем «<код> <название> — 4x5.png» и «— 9x16.png» "
              "(видео — .mp4, карусель — «<код>_card<N>_1x1.png»).",
              "2. Код креатива — в `EXTRA_CREATIVES` в `build_launch.py`: тип, пул, риск. В группу — в `v2_plan.json` (`types`, `adsets`).",
              "3. Новый текст — новым пулом в `pools_ru.json` и `pools_uz_final.json`, проверка `check_uz.py`.",
              "4. `python3 build_launch.py && python3 check_launch.py`, коммит и пуш.", ""]
    return "\n".join(lines)


def build_all() -> tuple[dict, list[dict], str]:
    """launch.json, registry.json и текст реестра — без записи на диск (check_launch.py сверяет с файлами)."""
    ids = json.loads(IDS_FILE.read_text(encoding="utf-8"))
    meta = json.loads(META_IDS_FILE.read_text(encoding="utf-8"))
    pools_uz = {p["n"]: p for p in json.loads(B.POOLS_FILE.read_text(encoding="utf-8"))["pools"]}
    pools_ru = {p["n"]: p for p in json.loads(POOLS_RU.read_text(encoding="utf-8"))["pools"]}
    texts = {n: p["texts"] for n, p in pools_uz.items()}
    index = B.media_index()

    campaigns = build_campaigns(texts, ids, index, meta)
    pixel = ids.get("pixel_id") or "{{PIXEL_ID}}"
    launch = dict(
        version=VERSION,
        source="research/19-zapusk-meta-bm/build_launch.py",
        plan="research/19-zapusk-meta-bm/01-ПЛАН-ЗАПУСКА.md",
        structure="research/19-zapusk-meta-bm/v2_plan.json",
        based_on="research/18-struktura-kampaniy-i-piksel (план 15.10)",
        kpi_usd=B.KPI_USD,
        week_cap_usd=WEEK_CAP_USD,
        account=ids,
        rules_for_executor=[
            "Создаётся в черновике Ads Manager. Публикуем выключенным: кампании на паузе, публикация без включения (решение Васи 17.10).",
            "Включает Вася или Claude по его прямой команде. RISK uz_lead_risk_2610 — с 4-го дня.",
            "Группы по интересам (biz, ai, fr) на паузе, пока Вася не добавит интересы в Ads Manager.",
            "V4 не загружать никогда.",
            "Картинки и видео — медиа по плейсментам: 4x5 — ленты, 9x16 — Stories и Reels. Карусели — карточки 1x1.",
            "Один основной текст на объявление (body_fallback): M у картинок и каруселей, S у видео.",
            "Улучшения Advantage+ creative — все OPT_OUT; standard_enhancements в API не передавать.",
            "Ссылка — готовые метки в link_url, conversion_domain — домен лендинга.",
            "После ошибки записи сначала читать кабинет, повтор вслепую запрещён.",
            "ID созданных объектов — в meta_ids.json, затем python3 build_launch.py.",
        ],
        custom_audiences=[dict(aud, subtype="WEBSITE", rule=audience_rule(aud, pixel),
                               meta_id=meta["audiences"].get(aud["name"])) for aud in AUDIENCES],
        campaigns=campaigns,
        reserve=sorted(RESERVE),
        wave2=sorted(WAVE2),
        not_for_meta=sorted(NEVER),
    )
    registry = build_registry(campaigns, pools_uz, pools_ru, index, meta)
    return launch, registry, build_md(campaigns, registry, pools_uz, pools_ru, ids)


def dump(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main() -> None:
    launch, registry, md = build_all()
    OUT_LAUNCH.write_text(dump(launch), encoding="utf-8")
    OUT_REGISTRY.write_text(dump(registry), encoding="utf-8")
    OUT_MD.write_text(md, encoding="utf-8")
    campaigns = launch["campaigns"]
    n_adsets = sum(len(c["adsets"]) for c in campaigns)
    n_ads = sum(len(a["ads"]) for c in campaigns for a in c["adsets"])
    print(f"launch.json: {len(campaigns)} кампании, {n_adsets} групп, {n_ads} объявлений; "
          f"реестр: {len(registry)} креативов → {OUT_MD.name}")


if __name__ == "__main__":
    main()
