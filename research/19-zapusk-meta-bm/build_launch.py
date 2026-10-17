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
CAMPAIGNS = [
    dict(key="C1", name="uz_lead_broad_2610", start="день 1", spend_cap_usd=105, labels=[],
         purpose="тест креативов низкого риска на широкой аудитории",
         adsets=[
             dict(key="lg", name="BR_LONG", budget=3, ads=["I1-1", "I1-2", "I2-1", "I2-2", "I2-3"],
                  test="длинный текст на картинке"),
             dict(key="sh", name="BR_SHORT", budget=3, ads=["I1-1S", "I1-2S", "I2-1S", "I2-2S", "I2-3S"],
                  test="те же 5 концептов с коротким текстом — зеркало BR_LONG"),
             dict(key="me", name="BR_MEME", budget=3, ads=["M2", "M3", "M4", "M5", "M7"], test="мемы-раздача"),
             dict(key="mx", name="BR_MIX", budget=3, ads=["I1-4", "I3-1", "I3-1S", "I3-3S", "I2-4S"],
                  test="остальная статика низкого риска"),
             dict(key="ca", name="BR_CAR", budget=3, ads=["K2-1", "K2-1b", "K2-3"],
                  test="карусели; K2-1 с цифрами против K2-1b без"),
         ]),
    dict(key="RISK", name="uz_lead_risk_2610", start="день 4", spend_cap_usd=45, labels=["RISK"],
         purpose="креативы среднего и высокого риска модерации; в черновике до 4-го дня",
         adsets=[
             dict(key="rs", name="RK_STAT", budget=3, ads=["I2-4", "I3-3", "M1", "M6"],
                  test="статика и мемы среднего риска"),
             dict(key="rv", name="RK_VID", budget=3, ads=["V4b", "V1"],
                  test="ролики среднего риска: монтаж против моушна, текст пула 2"),
             dict(key="r2", name="RK_V2", budget=3, ads=["V2"],
                  test="V2 высокого риска отдельно: при первом отказе выключить и не перезаливать"),
         ]),
]
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


def build_ad(code: str, adset_key: str, camp: dict, pools: dict, ids: dict, index: dict, meta: dict) -> dict:
    creo = CREATIVES[code]
    pool = creo["pool"]
    hook = B.HOOK_BY_POOL[pool]
    name = f"{code}_{adset_key}_{hook}"
    video = creo["kind"] == "video"
    ad_defaults = dict(B.AD_DEFAULTS,
                       link_url=ids.get("landing_url") or "{{LANDING_URL}}",
                       page_id=ids.get("page_id") or "{{PAGE_ID}}",
                       instagram_user_id=ids.get("instagram_user_id") or "{{IG_USER_ID}}")
    return dict(
        name=name,
        creative_code=code,
        format=creo["kind"],
        media=media_list(code, index, meta["media"]),
        text_pool=pool,
        hook=hook,
        body_keys=["short"] if video else ["short", "mid", "long"],
        body_options=B.bodies(pools[pool], creo["kind"]),
        body_fallback=pools[pool]["short" if video else "mid"],  # если API не примет варианты текста с медиа по плейсментам
        bot_start_tag=start_tag(camp["name"], name),
        risk=creo["risk"],
        risk_note=creo.get("note", ""),
        labels=camp["labels"],
        meta=meta["ads"].get(name, {}),
        **ad_defaults,
    )


def build_adset(adset: dict, camp: dict, pools: dict, ids: dict, index: dict, meta: dict) -> dict:
    targeting = dict(B.TARGETING_BASE)
    targeting.update({k: v for k, v in B.BROAD_AUDIENCE.items() if k != "note"})
    defaults = dict(B.ADSET_DEFAULTS,
                    promoted_object={"pixel_id": ids.get("pixel_id") or "{{PIXEL_ID}}", "custom_event_type": "LEAD"})
    return dict(
        name=adset["name"],
        key=adset["key"],
        start=camp["start"],
        daily_budget_usd=adset["budget"],
        daily_budget_minor=round(adset["budget"] * 100),
        test=adset["test"],
        targeting=targeting,
        audience_note=B.BROAD_AUDIENCE["note"],
        labels=camp["labels"],
        meta_id=meta["adsets"].get(f"{camp['name']}/{adset['name']}"),
        ads=[build_ad(code, adset["key"], camp, pools, ids, index, meta) for code in adset["ads"]],
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
        return "волна 1 · RISK с 4-го дня" if placed[code]["campaign"].startswith("uz_lead_risk") else "волна 1 · C1 с дня 1"
    if code in NEVER:
        return "не для Meta"
    if code in RESERVE:
        return "резерв"
    if code in WAVE2:
        return "волна 2"
    return "не распределён"


def build_registry(campaigns: list[dict], pools_uz: dict, pools_ru: dict, index: dict, meta: dict) -> list[dict]:
    placed = {}
    for camp in campaigns:
        for adset in camp["adsets"]:
            for ad in adset["ads"]:
                placed[ad["creative_code"]] = dict(campaign=camp["name"], adset=adset["name"], ad=ad)
    registry = []
    for code, creo in CREATIVES.items():
        hit = placed.get(code)
        media = hit["ad"]["media"] if hit else media_list(code, index, meta["media"])
        folders = sorted({str(Path(m["path"]).parent.relative_to(B.CREO_DIR.relative_to(ROOT)))
                          for m in media if m.get("path")})
        registry.append(dict(
            code=code,
            kind=creo["kind"],
            folder=folders[0] if len(folders) == 1 else folders,
            status=status_of(code, placed),
            campaign=hit["campaign"] if hit else None,
            adset=hit["adset"] if hit else None,
            ad_name=hit["ad"]["name"] if hit else None,
            bot_start_tag=hit["ad"]["bot_start_tag"] if hit else None,
            pool=creo["pool"],
            pool_title_ru=pools_ru[creo["pool"]]["title"],
            pool_title_uz=pools_uz[creo["pool"]]["title_uz"],
            hook=B.HOOK_BY_POOL[creo["pool"]],
            texts_used=(hit["ad"]["body_keys"] if hit else None),
            risk=creo["risk"],
            risk_note=creo.get("note", ""),
            media=media,
            meta=hit["ad"]["meta"] if hit else {},
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
    bits = [f"{k}: `{v}`" for k, v in item["meta"].items()]
    uploaded = sum(1 for m in item["media"] if m.get("meta"))
    if uploaded:
        bits.append(f"медиа загружено {uploaded}/{len(item['media'])}")
    return "; ".join(bits) or "—"


def build_md(campaigns: list[dict], registry: list[dict], pools_uz: dict, pools_ru: dict, ids: dict) -> str:
    lines = [
        "# Реестр креативов и текстов — запуск Meta в кабинете БМ",
        "",
        f"Собирает `build_launch.py` ({VERSION}) из каталога креативов `research/18-struktura-kampaniy-i-piksel/build_structure.py`, "
        "текстов `research/17-teksty-ru-uz/pools_uz_final.json`, `ids.json` и `meta_ids.json`. "
        "Руками не править: правки — в источниках, потом `python3 build_launch.py`. Почему так — `01-ПЛАН-ЗАПУСКА.md`.",
        "",
        f"Кабинет `{ids['ad_account_id']}` «{ids['ad_account_name']}», БМ {ids['business']}. "
        f"Страница: {ids.get('page_id') or 'не задана'}. Instagram: {ids.get('instagram_user_id') or 'не задан'}. "
        f"Пиксель: {ids.get('pixel_id') or 'не задан'}. Лендинг: {ids['landing_url']}",
        "",
        "## Кампании и группы — неделя 1",
        "",
        "| Кампания | Группа | В день | С какого дня | Объявления | Что проверяем |",
        "|---|---|---|---|---|---|",
    ]
    for camp in campaigns:
        for adset in camp["adsets"]:
            ads = ", ".join(f"`{ad['name']}`" for ad in adset["ads"])
            lines.append(f"| `{camp['name']}` | `{adset['name']}` | ${adset['daily_budget_usd']:g} | {camp['start']} | {ads} | {adset['test']} |")
    lines.append("")
    for camp in campaigns:
        per_day = sum(a["daily_budget_usd"] for a in camp["adsets"])
        days = DAYS_IN_WEEK[camp["start"]]
        lines.append(f"- `{camp['name']}`: ${per_day:g} в день × {days} дн. ≈ ${per_day * days:g}, "
                     f"лимит трат кампании ${camp['spend_cap_usd']}." + (" Метка RISK, в черновике до 4-го дня." if camp["labels"] else ""))
    lines += [f"- Неделя не больше ${WEEK_CAP_USD}: лимиты трат кампаний в сумме ${sum(c['spend_cap_usd'] for c in campaigns)}.", ""]

    lines += [
        "## Креативы — все из папки «АКТУАЛЬНЫЕ креативы УЗ — Meta»",
        "",
        "| Код | Тип | Статус | Группа → объявление | Пул · хук | Тексты | Риск | Файлы | ID в Meta |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in registry:
        where = f"`{item['adset']}` → `{item['ad_name']}`" if item["ad_name"] else "—"
        texts = "/".join({"short": "S", "mid": "M", "long": "L"}[k] for k in item["texts_used"]) if item["texts_used"] else "—"
        risk = RISK_RU[item["risk"]] + (f": {item['risk_note']}" if item["risk_note"] else "")
        lines.append(f"| {item['code']} | {KIND_RU[item['kind']]} | {item['status']} | {where} | "
                     f"{item['pool']} · {item['hook']} | {texts} | {risk} | {md_files(item)} | {md_meta(item)} |")
    lines += ["", "Тексты: S — короткий, M — средний, L — лонгрид. У картинок и каруселей S, M и L идут вариантами основного текста "
              "в одном объявлении; если API не примет их вместе с медиа по плейсментам — только M. У видео только S.", ""]

    lines += [
        "## Тексты под постами",
        "",
        "Полные тексты: узбекский — [`03-ТЕКСТЫ-ПУЛЫ-UZ.md`](../17-teksty-ru-uz/03-ТЕКСТЫ-ПУЛЫ-UZ.md), "
        "русский — [`02-ТЕКСТЫ-ПУЛЫ-RU.md`](../17-teksty-ru-uz/02-ТЕКСТЫ-ПУЛЫ-RU.md). "
        "Заголовок у всех объявлений — «Bepul mini-kurs», описание пустое, кнопка — «Подробнее».",
        "",
        "| Пул | Тема | Креативы волны 1 | Знаков UZ: S / M / L | Начало текста (UZ) |",
        "|---|---|---|---|---|",
    ]
    for n, pool in pools_uz.items():
        wave1 = ", ".join(i["code"] for i in registry if i["pool"] == n and i["ad_name"]) or "—"
        texts = pool["texts"]
        first = texts["short"].split("\n")[0]
        lines.append(f"| {n} | {pools_ru[n]['title']} / {pool['title_uz']} | {wave1} | "
                     f"{len(texts['short'])} / {len(texts['mid'])} / {len(texts['long'])} | {first} |")
    lines += [
        "",
        "## Метка в боте",
        "",
        "Кнопка лендинга передаёт боту метку `start`. По ней видно, какое объявление привело человека. "
        "Решения по креативам принимаем по стартам бота с этой меткой. Метки объявлений:",
        "",
    ]
    lines += [f"- `{i['ad_name']}` → `{i['bot_start_tag']}`" for i in registry if i["ad_name"]]
    lines += ["", "## Как добавить креатив или текст", "",
              "1. Файл — в «АКТУАЛЬНЫЕ креативы УЗ — Meta/<папка>» под именем «<код> <название> — 4x5.png» и «— 9x16.png» "
              "(видео — .mp4, карусель — «<код>_card<N>_1x1.png»).",
              "2. Код креатива — в `EXTRA_CREATIVES` в `build_launch.py`: тип, пул, риск. В группу — в `CAMPAIGNS`.",
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
        based_on="research/18-struktura-kampaniy-i-piksel (план 15.10)",
        kpi_usd=B.KPI_USD,
        week_cap_usd=WEEK_CAP_USD,
        account=ids,
        rules_for_executor=[
            "Всё создаётся только в черновике Ads Manager. Публикует Вася или Claude по его прямой команде.",
            "RISK uz_lead_risk_2610 не публиковать до 4-го дня. При публикации C1 выбирать только объекты C1.",
            "V4 не загружать никогда.",
            "Плейсхолдеры {{...}} заменить реальными ID из ids.json до записи; пустое поле не заменять догадкой.",
            "Картинки и видео — медиа по плейсментам: 4x5 — ленты, 9x16 — Stories и Reels. Карусели — карточки 1x1.",
            "body_options — варианты основного текста в одном объявлении; не принимает API — body_fallback.",
            "Улучшения Advantage+ creative — все OPT_OUT; standard_enhancements в API не передавать.",
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
