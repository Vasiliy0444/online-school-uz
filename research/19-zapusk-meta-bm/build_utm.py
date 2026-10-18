"""Реестр UTM-меток: какой креатив (с картинкой) и какая аудитория стоят за каждой меткой. Нужен, чтобы собирать аналитику.

У каждого из 60 объявлений своя метка utm_content. Она стоит в ссылке объявления, начинает его имя в Meta
и доходит до бота в параметре start. По ней склеиваются отчёт Meta, лендинг и бот.

Источники: launch.json и registry.json (их собирает build_launch.py), заголовки лендинга — websites/ii-na-zakaz-mini/js/hooks.js.
Пишет:
- thumbs/<код>.jpg — превью креатива: картинка 4:5, у карусели первая карточка, у видео кадр на 1-й секунде;
- utm_registry.csv — строка на объявление: метки, креатив, аудитория, кнопка, ID в Meta, метка бота;
- РЕЕСТР-UTM.md — креативы с картинками и метками, аудитории с метками и креативами;
- utm-registry.html — то же страницей: данные вставляются в блок <script id="utm-data">, остальное правится в самом файле.

Запуск после build_launch.py: python3 build_utm.py (превью пересобрать: --thumbs)
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
THUMBS = HERE / "thumbs"
HOOKS_JS = ROOT / "websites" / "ii-na-zakaz-mini" / "js" / "hooks.js"
PAGE = HERE / "utm-registry.html"
PAGE_URL = "https://claude.ai/artifact/NqF5z9W7dxN5GCYcW5TFEm"  # опубликованная страница; обновить — опубликовать utm-registry.html заново
THUMB_W = 320
VIDEO_FRAME_S = 1

AUD_SHORT = {"br": "широкая", "adv": "Advantage+", "biz": "бизнес", "ai": "ИИ", "fr": "фриланс"}
BUTTON = {"LEARN_MORE": "Подробнее", "SIGN_UP": "Зарегистрироваться"}
FORMAT = {"image": "картинка 4:5 на все места", "video": "видео 4:5 на все места", "carousel": "карусель 1:1, 6 карточек"}
CSV_FIELDS = ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "creative", "title_ru", "format",
              "hook", "landing_hook", "audience", "audience_title", "cta", "button", "meta_ad_name", "ad_id", "creative_id",
              "adset_id", "campaign_id", "state", "bot_start_tag", "link_url", "risk", "thumb"]


def landing_hook(utm_content: str) -> str | None:
    """Какой заголовок покажет лендинг — как pickHook в websites/ii-na-zakaz-mini/js/hooks.js."""
    words = [w for w in re.split(r"[^a-z0-9]+", utm_content.lower()) if w]
    if "math" in words:
        i = words.index("math")
        return "math_a" if words[i + 1:i + 2] == ["a"] else "math_b"
    return next((k for k in ("compare", "clients", "zero", "home", "now") if k in words), None)


def read_headlines() -> dict[str, str]:
    body = HOOKS_JS.read_text(encoding="utf-8").split("export const HOOKS = {", 1)[1].split("};", 1)[0]
    return {key: " ".join(re.findall(r"'((?:[^'\\]|\\.)*)'", arr)) for key, arr in re.findall(r"(\w+):\s*\[(.*?)\],", body)}


def state_kind(state: str) -> str:
    """Короткий вид состояния для страницы: опубликовано / черновик без Instagram / RISK."""
    if state.startswith("опубликовано"):
        return "live"
    if "RISK" in state:
        return "risk"
    return "draft"


def make_thumb(creative: dict, force: bool) -> str:
    out = THUMBS / f"{creative['code']}.jpg"
    if out.exists() and not force:
        return out.relative_to(HERE).as_posix()
    src = ROOT / creative["media"][0]["path"]  # 4:5 для лент или первая карточка карусели
    with tempfile.TemporaryDirectory() as tmp:
        if creative["kind"] == "video":
            frame = Path(tmp) / "frame.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(VIDEO_FRAME_S), "-i", str(src), "-frames:v", "1", str(frame)],
                           check=True)
            src = frame
        img = Image.open(src).convert("RGB")
        size = (THUMB_W, round(img.height * THUMB_W / img.width))
        THUMBS.mkdir(exist_ok=True)
        img.resize(size, Image.LANCZOS).save(out, "JPEG", quality=80, optimize=True, progressive=True)
    return out.relative_to(HERE).as_posix()


def targeting_text(adset: dict) -> str:
    t = adset["targeting"]
    age = f"{t['age_min']}–{t['age_max']}" if t.get("age_max") else f"от {t['age_min']}"
    auto = "Advantage+ включена: возраст — подсказка" if t["targeting_automation"]["advantage_audience"] else "Advantage+ выключена"
    parts = [f"Узбекистан, {age}", auto]
    if adset["interests_to_add"]:
        parts.append("интересы добавить в Ads Manager: " + ", ".join(adset["interests_to_add"]))
    return "; ".join(parts)


def adset_state(campaign: dict, adset: dict) -> str:
    if campaign["key"] == "RISK":
        return "в черновике до 4-го дня"
    if adset["paused_until_interests"]:
        return "на паузе до интересов"
    return "включена внутри выключенной кампании"


def collect(force_thumbs: bool) -> dict:
    launch = json.loads((HERE / "launch.json").read_text(encoding="utf-8"))
    registry = json.loads((HERE / "registry.json").read_text(encoding="utf-8"))
    headlines = read_headlines()
    creatives = [c for c in registry if c["placements"]]
    thumbs = {c["code"]: make_thumb(c, force_thumbs) for c in creatives}

    ads, adsets = [], []
    for camp in launch["campaigns"]:
        for s in camp["adsets"]:
            for ad in s["ads"]:
                meta, name = ad.get("meta") or {}, ad["name"]
                ads.append(dict(
                    campaign_key=camp["key"],
                    utm_source="meta", utm_medium="paid", utm_campaign=camp["name"], utm_term=s["name"], utm_content=name,
                    creative=ad["creative_code"], title_ru=ad["title_ru"], format=FORMAT[ad["format"]], hook=ad["hook"],
                    landing_hook=landing_hook(name) or "", audience=s["audience"], audience_title=s["audience_title"],
                    cta=ad["call_to_action"], button=BUTTON[ad["call_to_action"]], meta_ad_name=ad["display_name"],
                    ad_id=meta.get("ad_id", ""), creative_id=meta.get("creative_id", ""), adset_id=s["meta_id"],
                    campaign_id=camp["meta_id"], state=meta.get("state", ""), bot_start_tag=ad["bot_start_tag"],
                    link_url=ad["link_url"], risk=ad["risk"], thumb=thumbs[ad["creative_code"]]))
            adsets.append(dict(
                name=s["name"], campaign=camp["name"], campaign_key=camp["key"], audience=s["audience"],
                audience_title=s["audience_title"], targeting=targeting_text(s), budget_usd=s["daily_budget_usd"],
                state=adset_state(camp, s), adset_id=s["meta_id"], ads=[ad["name"] for ad in s["ads"]]))
    check(ads)
    first = {}  # креативы — в порядке групп, как в кабинете, а не по коду
    for i, a in enumerate(ads):
        first.setdefault(a["creative"], i)
    creatives.sort(key=lambda c: first[c["code"]])
    return dict(
        campaigns=[dict(key=c["key"], name=c["name"], id=c["meta_id"], spend_cap_usd=c["spend_cap_usd"]) for c in launch["campaigns"]],
        audiences={k: dict(short=v, title=next(s["audience_title"] for s in adsets if s["audience"] == k)) for k, v in AUD_SHORT.items()},
        hooks={k: dict(headline=headlines[k]) for k in sorted({a["landing_hook"] for a in ads if a["landing_hook"]})},
        creatives=[dict(code=c["code"], title=next(a["title_ru"] for a in ads if a["creative"] == c["code"]),
                        format=FORMAT[c["kind"]], hook=c["hook"], risk=c["risk"], thumb=thumbs[c["code"]],
                        ads=[a["utm_content"] for a in ads if a["creative"] == c["code"]]) for c in creatives],
        adsets=adsets,
        ads=[dict(a, state_kind=state_kind(a["state"])) for a in ads],
    )


def check(ads: list[dict]) -> None:
    errors = []
    names = [a["utm_content"] for a in ads]
    errors += [f"метка повторяется: {n}" for n in sorted({n for n in names if names.count(n) > 1})]
    for a in ads:
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(a["link_url"]).query))
        want = {k: a[k] for k in ("utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content")}
        if q != want:
            errors.append(f"{a['utm_content']}: метки в ссылке {q} не совпадают с реестром {want}")
        if not a["meta_ad_name"].startswith(a["utm_content"] + " · "):
            errors.append(f"{a['utm_content']}: имя в Meta не начинается с метки: {a['meta_ad_name']}")
        if not a["ad_id"]:
            errors.append(f"{a['utm_content']}: нет ID объявления в meta_ids.json")
    if errors:
        raise SystemExit("ошибки реестра UTM:\n" + "\n".join(errors))


def write_csv(data: dict) -> None:
    with (HERE / "utm_registry.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(data["ads"])


def md_state(a: dict) -> str:
    return {"live": "опубликовано", "risk": "черновик RISK", "draft": "черновик, нужен Instagram"}[a["state_kind"]]


def write_md(data: dict) -> None:
    by_name = {a["utm_content"]: a for a in data["ads"]}
    camps = {c["name"]: c for c in data["campaigns"]}
    lines = [
        "# Реестр UTM-меток запуска в Meta",
        "",
        "Собран `build_utm.py` из `launch.json` и `registry.json`, руками не править. ID объявлений — из кабинета Meta "
        "`2064860530825559`, состояние — на 18.10.2026. Та же таблица одной строкой на объявление — `utm_registry.csv`, "
        f"страницей с фильтрами — {PAGE_URL}.",
        "",
        "## Как собирать аналитику по меткам",
        "",
        "- **Ключ — `utm_content`.** Она своя у каждого из 60 объявлений и стоит в трёх местах:",
        "  - в ссылке объявления: `https://aibuyurtma.com/?utm_source=meta&utm_medium=paid&utm_campaign=<кампания>&utm_term=<группа>&utm_content=<метка>`;",
        "  - в начале имени объявления и креатива в Meta: `<метка> · <тема креатива> · <кнопка>`;",
        "  - в метке бота: `vm-meta-<кампания>-<метка>` в параметре `start` (маленькие буквы, `-` внутри метки → `_`).",
        "- **Метка читается по частям:** `I1-1_math_br_su` — креатив `I1-1`, хук `math`, аудитория `br`, `_su` — кнопка «Зарегистрироваться». Без `_su` кнопка «Подробнее».",
        "  - По креативу — первая часть, до первого `_`: обе аудитории креатива складываются.",
        "  - По аудитории — третья часть или `utm_term`, имя группы: `BR_LONG` → `br`.",
        "  - По кнопке — есть ли `_su` в конце.",
        "  - По хуку — вторая часть: от неё зависит заголовок лендинга.",
        "- **Где что считается:**",
        "  - Meta — показы, клики и `Lead`: пиксель шлёт его по нажатию кнопки «в бота» на лендинге. Отчёт по объявлениям склеивается с реестром по `ad_id` или по началу имени.",
        "  - Бот — старты по метке из `start`: это главный результат для оценки креативов (раздел 5 плана).",
        "  - Лендинг — события `page_view` и `cta_click` пишутся в `dataLayer`, но счётчика, который их забирает, на странице нет: в коде лендинга нет ни GTM, ни Метрики. Пиксель Meta заходы видит, но адрес страницы хранит без меток, поэтому визиты по `utm_content` из него не прочитать.",
        "",
        "Заголовки лендинга ниже — русская версия, узбекская показывает их перевод.",
        "",
        "| Часть метки | Значение | Что это |",
        "|---|---|---|",
    ]
    lines += [f"| `_{k}` | аудитория | {v['title']} |" for k, v in data["audiences"].items()]
    lines += [f"| `_{h}` | хук | лендинг покажет «{data['hooks'][h]['headline']}» |"
              for h in data["hooks"] if not h.startswith("math")]
    if "math_b" in data["hooks"]:
        lines.append(f"| `_math` | хук | лендинг покажет «{data['hooks']['math_b']['headline']}» |")
    lines += ["| `_su` | кнопка | «Зарегистрироваться»; без `_su` — «Подробнее» |", ""]

    lines += [f"## Креативы — {len(data['creatives'])}", "",
              "| Картинка | Креатив | Метка `utm_content` → группа `utm_term` · кнопка · ID объявления · состояние |", "|---|---|---|"]
    for c in data["creatives"]:
        ads = [by_name[n] for n in c["ads"]]
        cells = "<br>".join(f"`{a['utm_content']}` → `{a['utm_term']}` · {a['button']} · `{a['ad_id']}` · {md_state(a)}" for a in ads)
        risk = " · **RISK**" if ads[0]["campaign_key"] == "RISK" else ""
        lines.append(f"| <img src=\"{c['thumb']}\" width=\"96\" alt=\"{c['code']}\"> | **{c['code']}** {c['title']}<br>{c['format']} · хук `{c['hook']}`{risk} | {cells} |")

    lines += ["", f"## Аудитории — {len(data['adsets'])} групп", "",
              "`utm_campaign` — кампания, `utm_term` — группа. Аудитория группы — третья часть метки каждого её объявления.", "",
              "| `utm_term` | `utm_campaign` | Аудитория и настройки | В день | Состояние | ID группы | Креативы в группе |",
              "|---|---|---|---|---|---|---|"]
    for s in data["adsets"]:
        thumbs = " ".join(f"<img src=\"{by_name[n]['thumb']}\" width=\"40\" alt=\"{n}\" title=\"{n}\">" for n in s["ads"])
        names = "<br>".join(f"`{n}`" for n in s["ads"])
        cap = camps[s["campaign"]]["spend_cap_usd"]
        lines.append(f"| `{s['name']}` | `{s['campaign']}`<br>лимит ${cap} | **{s['audience_title']}**<br>{s['targeting']} | "
                     f"${s['budget_usd']:g} | {s['state']} | `{s['adset_id']}` | {thumbs}<br>{names} |")
    (HERE / "РЕЕСТР-UTM.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_page(data: dict) -> None:
    html = PAGE.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    new, n = re.subn(r'(<script type="application/json" id="utm-data">).*?(</script>)', lambda m: m.group(1) + payload + m.group(2),
                     html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f"{PAGE.name}: не найден блок <script id=\"utm-data\">")
    PAGE.write_text(new, encoding="utf-8")


def main() -> None:
    data = collect(force_thumbs="--thumbs" in sys.argv)
    write_csv(data)
    write_md(data)
    write_page(data)
    print(f"реестр UTM: {len(data['ads'])} объявлений, {len(data['creatives'])} креативов, {len(data['adsets'])} групп → "
          "utm_registry.csv, РЕЕСТР-UTM.md, utm-registry.html, thumbs/")


if __name__ == "__main__":
    main()
