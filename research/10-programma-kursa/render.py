#!/usr/bin/env python3
"""Собирает programma.html и programma.pdf из programma-kursa.md.

Источник правды — MD: правишь текст там и запускаешь скрипт заново.
Слайды 16:9 (1280×720): обложка → 9 модулей → «Формат и бонусы» → итог.
Шрифты — локальные (Akrobat, RF Dewi Expanded, Avenir Next), PDF их встраивает.

Запуск:
    python3 render.py                      # HTML + PDF
    python3 render.py --previews <папка>   # плюс PNG каждого слайда для проверки
"""
import argparse
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MD_PATH = HERE / "programma-kursa.md"
HTML_PATH = HERE / "programma.html"
PDF_PATH = HERE / "programma.pdf"

SLIDE_W, SLIDE_H = 1280, 720
ABBREVIATIONS = {"КП", "ИИ", "CRM", "OLX", "ЦА", "ИП", "AI"}

# ---------------------------------------------------------------- иконки (24×24, контур)
ICONS = {
    "video": '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M10 9.3v5.4l4.6-2.7z" fill="currentColor" stroke="none"/>',
    "calc": '<rect x="5" y="3" width="14" height="18" rx="2.5"/><rect x="8" y="6" width="8" height="3.5" rx="1"/><path d="M8.6 13.2h.01M12 13.2h.01M15.4 13.2h.01M8.6 16.8h.01M12 16.8h.01M15.4 16.8h.01" stroke-width="2.4"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4M8 14h3M8 17h6"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "spark": '<path d="M11 3.5l1.9 5 5.1 1.9-5.1 1.9-1.9 5-1.9-5L4 10.4l5.1-1.9z"/><path d="M18.5 15l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z"/>',
    "layers": '<path d="M12 3.5l8.5 4.3-8.5 4.3-8.5-4.3z"/><path d="M3.5 12.2l8.5 4.3 8.5-4.3M3.5 16.4l8.5 4.3 8.5-4.3"/>',
    "check": '<rect x="4" y="3.5" width="16" height="17" rx="2.5"/><path d="M8 9.2l1.8 1.8 3.4-3.4M8 14.5h8M8 17.5h5"/>',
    "doc": '<path d="M14 3.5H7.5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2V8z"/><path d="M14 3.5V8h4.5M9 13h6M9 16.5h4"/>',
    "table": '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M3.5 9.5h17M3.5 14.5h17M9.5 4.5v15"/>',
    "map": '<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.4"/>',
    "list": '<path d="M9.5 6.5h10M9.5 12h10M9.5 17.5h10M4.8 6.5h.01M4.8 12h.01M4.8 17.5h.01" /><path d="M4.8 6.5h.01M4.8 12h.01M4.8 17.5h.01" stroke-width="2.6"/>',
    "chat": '<path d="M20 12a7.5 7.5 0 0 1-11 6.6L4.2 20l1.2-4.4A7.5 7.5 0 1 1 20 12z"/><path d="M9 12h.01M12.5 12h.01M16 12h.01" stroke-width="2.4"/>',
    "shield": '<path d="M12 3.5l7 2.8v5.2c0 4.4-3 7.8-7 9-4-1.2-7-4.6-7-9V6.3z"/><path d="M9 12l2.1 2.1L15.2 10"/>',
    "users": '<circle cx="9" cy="8.5" r="3"/><path d="M3.5 19c.6-3 2.9-5 5.5-5s4.9 2 5.5 5"/><circle cx="17" cy="9.5" r="2.4"/><path d="M16.6 14.2c2.1.3 3.6 2 3.9 4.3"/>',
    "pen": '<path d="M4.5 19.5l1-4.4L15.6 5a2.1 2.1 0 0 1 3 3L8.5 18.1z"/><path d="M13.6 7l3 3M13.5 20h6"/>',
    "card": '<rect x="3" y="5.5" width="18" height="13" rx="2.5"/><path d="M3 10h18M7 15h3"/>',
    "flag": '<path d="M5.5 21V4"/><path d="M5.5 4.5h11.5l-2 4 2 4H5.5"/>',
    "star": '<path d="M12 3.8l2.5 5.1 5.6.8-4.1 4 1 5.6-5-2.6-5 2.6 1-5.6-4.1-4 5.6-.8z"/>',
    "award": '<circle cx="12" cy="9" r="5.5"/><path d="M8.8 13.4L7.6 21l4.4-2.5 4.4 2.5-1.2-7.6"/>',
    "tag": '<path d="M3.5 12.4V4.5a1 1 0 0 1 1-1h7.9l8.1 8.1a1.5 1.5 0 0 1 0 2.1l-7.4 7.4a1.5 1.5 0 0 1-2.1 0z"/><circle cx="8" cy="8" r="1.4"/>',
    "globe": '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.3 2.4 3.4 5.2 3.4 8.5s-1.1 6.1-3.4 8.5c-2.3-2.4-3.4-5.2-3.4-8.5S9.7 5.9 12 3.5z"/>',
    "bot": '<rect x="4.5" y="8" width="15" height="11" rx="3"/><path d="M12 4.5V8M9.5 16h5"/><circle cx="12" cy="3.8" r="1"/><path d="M9 12.6h.01M15 12.6h.01" stroke-width="2.6"/>',
    "live": '<circle cx="12" cy="12" r="2.2"/><path d="M8.2 8.2a5.4 5.4 0 0 0 0 7.6M15.8 8.2a5.4 5.4 0 0 1 0 7.6M5.3 5.3a9.5 9.5 0 0 0 0 13.4M18.7 5.3a9.5 9.5 0 0 1 0 13.4"/>',
    "lang": '<path d="M4 5.5h9M8.5 3.5v2M6 5.5c.6 3.3 2.6 5.9 5.5 7.4M11 5.5c-.6 3.3-2.6 5.9-5.5 7.4"/><path d="M13 20.5l3.5-8.5 3.5 8.5M14.3 17.6h4.4"/>',
    "gift": '<rect x="4" y="9.5" width="16" height="10.5" rx="1.5"/><path d="M3.2 9.5h17.6M12 9.5V20"/><path d="M12 9.5S10.6 5 8.3 5.6C6.6 6.1 7.4 9.5 12 9.5zM12 9.5S13.4 5 15.7 5.6c1.7.5.9 3.9-3.7 3.9z"/>',
    "folder": '<path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2.5h7a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/>',
    "eye": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>',
    "check_square": '<rect x="3.5" y="3.5" width="17" height="17" rx="3.5"/><path d="M8 12.3l3 3 5.4-6.3"/>',
    "target": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/>',
}

# Какой значок у материала: первое совпадение по ключу в тексте (без учёта регистра).
MATERIAL_ICONS = [
    ("видео", "video"), ("мини-урок", "video"), ("калькулятор", "calc"),
    ("карта 30", "calendar"), ("план на 90", "calendar"), ("расписани", "clock"),
    ("нейросет", "spark"), ("промпт", "spark"), ("структур", "layers"),
    ("встреч", "users"), ("сценари", "layers"), ("чек-лист «красн", "flag"), ("чек-лист", "check"),
    ("таблиц", "table"), ("crm", "table"), ("яндекс", "map"), ("список 50", "list"),
    ("скрипт", "chat"), ("переписк", "chat"), ("возражен", "shield"),
    ("договор", "pen"), ("оплат", "card"), ("счёт", "doc"), ("отзыв", "star"),
    ("кейс", "award"), ("прайс", "tag"), ("английск", "globe"), ("портфолио", "folder"),
    ("кп", "doc"),
]
FORMAT_ICONS = [
    ("узбекском", "lang"), ("урок", "clock"), ("практика", "map"), ("куратор", "eye"),
    ("живые", "live"), ("чат", "users"),
]
BONUS_ICONS = [
    ("ustoz", "bot"), ("эфир", "live"), ("банк", "folder"), ("чат", "users"),
    ("сертификат", "award"), ("оплату", "gift"),
]


def icon(name: str, size: int = 20) -> str:
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


def pick_icon(text: str, table: list, default: str = "doc") -> str:
    low = text.lower()
    for key, name in table:
        if key in low:
            return name
    return default


# ---------------------------------------------------------------- разбор MD
def parse_md(text: str) -> dict:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    data = {"cover": {}, "modules": [], "format": [], "bonuses": [], "final": {"items": []}}
    section, week, module, mode, sub = "cover", None, None, None, None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line == "---":
            continue
        if line.startswith("[^"):
            break  # дальше только сноски с источниками — в PDF не идут
        if line.startswith("# "):
            data["cover"]["name"] = line[2:].strip()
            continue
        m = re.match(r"^## Неделя (\d+)\.\s+(.+)$", line)
        if m:
            section, week = "modules", {"n": int(m.group(1)), "name": m.group(2)}
            continue
        m = re.match(r"^### Модуль (\d+)\.\s+(.+)$", line)
        if m:
            module = {"n": int(m.group(1)), "title": m.group(2), "week": week,
                      "topics": [], "materials": [], "result": ""}
            data["modules"].append(module)
            mode = "topics"
            continue
        if line.startswith("## Формат"):
            section = "format"
            continue
        if line.startswith("## Через"):
            section = "final"
            data["final"]["title"] = line[3:].strip()
            continue

        if section == "cover":
            if line.startswith("## "):
                data["cover"]["promise"] = line[3:].strip()
            elif line.startswith("> "):
                data["cover"]["tagline"] = line[2:].strip()
            elif re.fullmatch(r"\*\*(.+)\*\*", line):
                key = "label" if "label" not in data["cover"] else "meta"
                data["cover"][key] = line[2:-2]
            else:
                data["cover"]["sub"] = line
        elif section == "modules":
            if line.startswith("**Материалы"):
                mode = "materials"
                continue
            m = re.match(r"^\*\*Результат:\*\*\s*(.+)$", line)
            if m:
                module["result"], mode = m.group(1), None
                continue
            if line.startswith("- ") and mode:
                module[mode].append(line[2:].strip())
        elif section == "format":
            if line.startswith("### Как"):
                sub = "format"
            elif line.startswith("### Бонус"):
                sub = "bonuses"
            elif line.startswith("- "):
                item = line[2:].strip()
                if sub == "format":
                    data["format"].append(item)
                else:
                    m = re.match(r"^\*\*(.+?)\*\*\s*—\s*(.+)$", item)
                    data["bonuses"].append({"name": m.group(1), "desc": m.group(2)} if m
                                           else {"name": item, "desc": ""})
        elif section == "final":
            m = re.match(r"^\d+\.\s+(.+)$", line)
            if m:
                data["final"]["items"].append(m.group(1))
            elif line.startswith("**"):
                m = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", line)
                data["final"]["money_head"], data["final"]["money"] = m.group(1), m.group(2)
            elif line.startswith("*"):
                data["final"]["honest"] = line.strip("*").strip()

    validate(data)
    return data


def validate(data: dict) -> None:
    """Шаблон Васи: не больше 9 модулей, у каждого темы, материалы и результат."""
    problems = []
    if not 1 <= len(data["modules"]) <= 9:
        problems.append(f"модулей {len(data['modules'])}, а нужно от 1 до 9")
    for mod in data["modules"]:
        for part in ("topics", "materials", "result"):
            if not mod[part]:
                problems.append(f"Модуль {mod['n']}: пусто — {part}")
    for key in ("name", "promise", "sub", "meta", "tagline"):
        if not data["cover"].get(key):
            problems.append(f"обложка: нет «{key}»")
    if problems:
        sys.exit("Ошибка в programma-kursa.md:\n- " + "\n- ".join(problems))


# ---------------------------------------------------------------- форматирование строк
NUM_RE = re.compile(
    r"(?<![\w/:])(\d{1,2}:\d{2}|\$?\d+(?:[.,]\d+)?(?:[–-]\$?\d+(?:[.,]\d+)?)?(?:\+|%)?)(?![\w/])")
CAPS_RE = re.compile(r"\b([А-ЯЁ]{2,})\b")


def fmt(text: str, numbers: bool = True) -> str:
    text = re.sub(r"\[\^\d+\]", "", text)
    out = html.escape(text, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    if numbers:
        out = NUM_RE.sub(r'<b class="num">\1</b>', out)
    out = CAPS_RE.sub(lambda m: m.group(1) if m.group(1) in ABBREVIATIONS
                      else f'<span class="caps">{m.group(1)}</span>', out)
    return out


def upper_first(text: str) -> str:
    return text[:1].upper() + text[1:]


def slide_top(week_label: str, week_name: str, page: int, total: int) -> str:
    return f"""
  <div class="top">
    <div class="week"><span class="week-pill">{week_label}</span><span class="week-name">{html.escape(week_name)}</span></div>
    <div class="brand">ИИ на заказ · программа <b>{page:02d} / {total:02d}</b></div>
  </div>"""


# ---------------------------------------------------------------- слайды
def cover_slide(c: dict) -> str:
    name = html.escape(c["name"])
    first, _, rest = name.partition(" ")
    promise_head, _, promise_tail = c["promise"].partition(":")
    days = re.search(r"(\d+)\s+дн", promise_head)
    first_sentence, _, plan = c["sub"].partition(". ")
    plan = re.sub(r"^И\s+", "", plan.strip())
    plan = plan[:1].upper() + plan[1:]
    tail = promise_tail.strip()
    tail = tail[:1].upper() + tail[1:]
    chips = [p.strip() for p in re.split(r",\s*|\s+и\s+", first_sentence) if p.strip()]
    chips_html = "".join(f'<span class="chip">{html.escape(ch.lower())}</span>' for ch in chips)
    stats = []
    for item in c["meta"].split("·"):
        item = item.strip()
        m = re.match(r"^(\d+)\s+(.+)$", item)
        if m:
            stats.append(f'<div class="stat"><span class="big">{m.group(1)}</span><span>{html.escape(m.group(2))}</span></div>')
        else:
            stats.append(f'<div class="stat stat-text"><span>{html.escape(item)}</span></div>')
    return f"""
<section class="slide cover">
  <div class="pattern"></div>
  <div class="cover-label">{html.escape(c['label']).upper()}</div>
  <h1 class="cover-name"><span class="accent">{first}</span> {rest}</h1>
  <div class="cover-promise">{fmt(promise_head, numbers=False)}</div>
  <div class="cover-promise-tail">{fmt(tail, numbers=False)}</div>
  <div class="chips">{chips_html}</div>
  <div class="plan">{icon('target', 22)}<span>{fmt(plan.rstrip('.'))}</span></div>
  <div class="ring"><span class="ring-num">{days.group(1) if days else ''}</span><span class="ring-cap">дней до первого<br>оплаченного заказа</span></div>
  <div class="cover-bottom">
    <div class="tagline">{fmt(c['tagline'], numbers=False)}</div>
    <div class="stats">{''.join(stats)}</div>
  </div>
</section>"""


def module_slide(mod: dict, page: int, total: int, n_modules: int) -> str:
    week = mod["week"]
    topics = "".join(f"<li>{fmt(t)}</li>" for t in mod["topics"])
    mats = "".join(
        f'<div class="mat"><span class="ic">{icon(pick_icon(t, MATERIAL_ICONS), 19)}</span>'
        f'<span class="t">{fmt(t, numbers=False)}</span></div>'
        for t in mod["materials"])
    progress = "".join(f'<i class="{"on" if i + 1 == mod["n"] else ("done" if i + 1 < mod["n"] else "")}"></i>'
                       for i in range(n_modules))
    return f"""
<section class="slide module">
  <div class="pattern faint"></div>
  {slide_top(f"Неделя {week['n']}", week["name"], page, total)}
  <div class="stack">
    <div class="back"></div>
    <div class="card">
      <div class="tab"><span>Модуль {mod['n']}</span></div>
      <h2 class="m-title">{fmt(mod['title'], numbers=False)}</h2>
      <div class="grid">
        <ul class="topics">{topics}</ul>
        <div class="aside">
          <div class="aside-label">Материалы</div>
          {mats}
        </div>
      </div>
      <div class="result">
        <div class="h"><span>Результат</span>{icon('check_square', 30)}</div>
        <p>{fmt(upper_first(mod['result']))}</p>
      </div>
    </div>
  </div>
  <div class="progress"><span>Модуль {mod['n']} из {n_modules}</span><div class="bar">{progress}</div></div>
</section>"""


def format_slide(items: list, bonuses: list, page: int, total: int) -> str:
    rows = "".join(
        f'<div class="frow"><span class="ic">{icon(pick_icon(t, FORMAT_ICONS), 20)}</span><span>{fmt(t)}</span></div>'
        for t in items)
    tiles = "".join(
        f'<div class="bonus{" hero" if i == 0 else ""}"><div class="b-head"><span class="ic">{icon(pick_icon(b["name"] + " " + b["desc"], BONUS_ICONS, "gift"), 20)}</span>'
        f'<span class="b-name">{fmt(b["name"], numbers=False)}</span></div><p>{fmt(upper_first(b["desc"]))}</p></div>'
        for i, b in enumerate(bonuses))
    return f"""
<section class="slide format">
  <div class="pattern faint"></div>
  {slide_top("Формат", "что входит в курс", page, total)}
  <h2 class="s-title">Формат и бонусы</h2>
  <div class="format-grid">
    <div class="panel">
      <div class="panel-label">Как проходит обучение</div>
      <div class="frows">{rows}</div>
    </div>
    <div class="bonuses">
      <div class="panel-label gold">Бонусы</div>
      <div class="bonus-grid">{tiles}</div>
    </div>
  </div>
</section>"""


def final_slide(f: dict, page: int, total: int) -> str:
    tiles = "".join(
        f'<div class="res-tile"><span class="res-num">{i + 1:02d}</span><p>{fmt(t)}</p></div>'
        for i, t in enumerate(f["items"]))
    return f"""
<section class="slide final">
  <div class="pattern"></div>
  {slide_top("Итог", "что будет после программы", page, total)}
  <h2 class="s-title">{fmt(f['title'], numbers=False)}</h2>
  <div class="res-grid">{tiles}</div>
  <div class="money"><b>{fmt(f.get('money_head', ''), numbers=False)}</b> {fmt(f.get('money', ''), numbers=False)}</div>
  <div class="honest">{fmt(f.get('honest', ''), numbers=False)}</div>
</section>"""


# ---------------------------------------------------------------- стили
PATTERN_SVG = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='96' height='96' viewBox='0 0 96 96'>"
    "<g fill='none' stroke='%232BC6D4' stroke-width='1'>"
    "<rect x='31' y='31' width='34' height='34'/>"
    "<rect x='31' y='31' width='34' height='34' transform='rotate(45 48 48)'/>"
    "<circle cx='48' cy='48' r='7'/>"
    "<path d='M0 48h17M79 48h17M48 0v17M48 79v17'/></g></svg>"
)

CSS = """
@page { size: 1280px 720px; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #07101F; --turq: #2BC6D4; --turq-l: #72E4EC; --gold: #F2C14E; --gold-l: #F9DC92; --gold-d: #CF962F;
  --text: #EAF2FF; --soft: #D5E0F2; --muted: #9DB0CE; --faint: #5F7597;
}
html, body { background: var(--bg); }
body { font-family: 'Avenir Next', 'Helvetica Neue', Arial, sans-serif; color: var(--text);
       -webkit-font-smoothing: antialiased; }
.slide { position: relative; width: 1280px; height: 720px; overflow: hidden; break-after: page;
  background:
    radial-gradient(880px 520px at 6% -12%, rgba(43,198,212,.20), transparent 62%),
    radial-gradient(760px 520px at 104% 112%, rgba(242,193,78,.11), transparent 60%),
    var(--bg); }
.slide:last-child { break-after: auto; }
.pattern { position: absolute; inset: 0; background-image: url("PATTERN"); background-size: 96px 96px; opacity: .06; }
.pattern.faint { opacity: .035; }
b.num { font-weight: 700; color: #FFFFFF; }
.caps { color: var(--gold); font-weight: 700; letter-spacing: .02em; }

/* ---------- шапка слайда */
.top { position: absolute; left: 64px; right: 64px; top: 30px; display: flex; align-items: center; justify-content: space-between; }
.week { display: flex; align-items: center; gap: 14px; }
.week-pill { font-family: 'Akrobat'; font-weight: 800; font-size: 15px; letter-spacing: .14em; text-transform: uppercase;
             color: #06101D; background: var(--turq); padding: 6px 13px 5px; border-radius: 999px; }
.week-name { font-family: 'Akrobat'; font-weight: 700; font-size: 17px; letter-spacing: .08em; text-transform: uppercase; color: var(--turq-l); }
.brand { font-family: 'Akrobat'; font-weight: 700; font-size: 14px; letter-spacing: .16em; text-transform: uppercase; color: var(--faint); }
.brand b { color: var(--muted); margin-left: 10px; }

/* ---------- модуль: карточка-стопка как в «Программе» */
.stack { position: absolute; left: 116px; top: 96px; width: 1076px; height: 560px; }
.stack .back { position: absolute; inset: 0; transform: translate(16px, -15px); border: 1.5px solid rgba(43,198,212,.30); border-radius: 26px; }
.card { position: absolute; inset: 0; border-radius: 26px; padding: 32px 40px 36px 60px;
        background: linear-gradient(180deg, rgba(16,31,53,.97), rgba(9,20,36,.97));
        border: 1.5px solid rgba(43,198,212,.70); box-shadow: 0 30px 80px rgba(0,0,0,.45); }
.tab { position: absolute; left: -27px; top: 54px; width: 54px; height: 206px; border-radius: 14px;
       background: linear-gradient(180deg, var(--gold-l), var(--gold-d)); display: flex; align-items: center; justify-content: center;
       box-shadow: 0 12px 30px rgba(242,193,78,.22); }
.tab span { writing-mode: vertical-rl; transform: rotate(180deg); font-family: 'Akrobat'; font-weight: 900; font-size: 21px;
            letter-spacing: .16em; text-transform: uppercase; color: #1C1406; }
.m-title { font-family: 'Akrobat'; font-weight: 800; font-size: 42px; line-height: 1.04; color: var(--turq-l);
           margin-bottom: 20px; max-width: 930px; }
.grid { display: grid; grid-template-columns: 1fr 336px; column-gap: 44px; }
ul.topics { list-style: none; }
ul.topics li { position: relative; padding-left: 26px; font-size: 16.6px; line-height: 1.34; color: var(--soft); margin-bottom: 8.5px; }
ul.topics li::before { content: ""; position: absolute; left: 4px; top: 8px; width: 7.5px; height: 7.5px; transform: rotate(45deg);
                       background: var(--turq); border-radius: 1.5px; }
.aside-label { font-family: 'Akrobat'; font-weight: 800; font-size: 14px; letter-spacing: .18em; text-transform: uppercase;
               color: var(--turq-l); margin-bottom: 12px; }
.mat { display: flex; gap: 12px; align-items: center; margin-bottom: 10px; }
.mat .ic, .frow .ic, .b-head .ic { flex: 0 0 34px; height: 34px; border-radius: 10px; display: flex; align-items: center; justify-content: center;
                    background: rgba(43,198,212,.12); border: 1px solid rgba(43,198,212,.38); color: var(--turq-l); }
.mat .t { font-size: 14.2px; line-height: 1.28; color: #C6D3EA; }
.result { position: absolute; right: 36px; bottom: -32px; width: 368px; border-radius: 20px; padding: 16px 22px 18px;
          background: linear-gradient(180deg, #14243D, #0E1B30); border: 1.5px solid var(--gold);
          box-shadow: 0 18px 44px rgba(0,0,0,.55), 0 0 0 6px rgba(242,193,78,.07); }
.result .h { display: flex; align-items: center; justify-content: space-between; margin-bottom: 7px;
             font-family: 'Akrobat'; font-weight: 800; font-size: 22px; letter-spacing: .02em; color: var(--gold); }
.result .h svg { color: var(--gold); }
.result p { font-size: 15px; line-height: 1.38; color: #F3F6FF; }
.result b.num { color: var(--gold-l); }
.progress { position: absolute; left: 116px; bottom: 22px; display: flex; align-items: center; gap: 14px;
            font-family: 'Akrobat'; font-weight: 700; font-size: 13px; letter-spacing: .14em; text-transform: uppercase; color: var(--faint); }
.progress .bar { display: flex; gap: 6px; }
.progress i { display: block; width: 26px; height: 5px; border-radius: 3px; background: rgba(157,176,206,.20); }
.progress i.done { background: rgba(43,198,212,.45); }
.progress i.on { background: var(--gold); }

/* ---------- обложка */
.cover-label { position: absolute; left: 72px; top: 64px; font-family: 'Akrobat'; font-weight: 800; font-size: 17px; letter-spacing: .3em;
               color: var(--turq-l); display: flex; align-items: center; gap: 16px; }
.cover-label::after { content: ""; width: 120px; height: 1.5px; background: rgba(114,228,236,.6); }
.cover-name { position: absolute; left: 68px; top: 104px; font-family: 'RF Dewi Expanded'; font-weight: 900; font-size: 88px;
              line-height: 1; letter-spacing: -.01em; color: #FFFFFF; }
.cover-name .accent { color: var(--turq); }
.cover-promise { position: absolute; left: 72px; top: 238px; width: 740px; font-family: 'Akrobat'; font-weight: 800; font-size: 46px;
                 line-height: 1.02; color: #FFFFFF; }
.cover-promise-tail { position: absolute; left: 72px; top: 292px; width: 720px; font-size: 25px; line-height: 1.3; color: var(--soft); }
.chips { position: absolute; left: 72px; top: 382px; display: flex; gap: 12px; }
.chip { font-size: 17px; font-weight: 600; color: var(--turq-l); padding: 9px 18px; border-radius: 999px;
        border: 1.5px solid rgba(114,228,236,.55); background: rgba(43,198,212,.08); }
.plan { position: absolute; left: 72px; top: 452px; display: flex; align-items: center; gap: 12px; padding: 12px 20px 12px 16px;
        border-radius: 14px; border: 1.5px solid var(--gold); background: rgba(242,193,78,.07); font-size: 20px; font-weight: 600; color: #FFF6DE; }
.plan svg { color: var(--gold); }
.plan b.num { color: var(--gold-l); }
.ring { position: absolute; right: 86px; top: 150px; width: 330px; height: 330px; border-radius: 50%;
        border: 2px solid rgba(43,198,212,.55); box-shadow: inset 0 0 0 14px rgba(43,198,212,.06), 0 0 120px rgba(43,198,212,.18);
        display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
.ring::before { content: ""; position: absolute; inset: -22px; border-radius: 50%; border: 1px dashed rgba(242,193,78,.45); }
.ring-num { font-family: 'RF Dewi Expanded'; font-weight: 900; font-size: 150px; line-height: .9; color: var(--turq); }
.ring-cap { margin-top: 14px; font-family: 'Akrobat'; font-weight: 700; font-size: 19px; letter-spacing: .1em; text-transform: uppercase;
            line-height: 1.25; color: var(--soft); }
.cover-bottom { position: absolute; left: 72px; right: 72px; bottom: 44px; display: flex; align-items: flex-end; justify-content: space-between;
                border-top: 1px solid rgba(157,176,206,.22); padding-top: 22px; }
.tagline { width: 520px; font-size: 19px; line-height: 1.35; color: var(--muted); }
.stats { display: flex; gap: 34px; align-items: flex-end; }
.stat { display: flex; align-items: baseline; gap: 10px; font-family: 'Akrobat'; font-weight: 700; font-size: 18px; letter-spacing: .06em;
        text-transform: uppercase; color: var(--soft); }
.stat .big { font-family: 'RF Dewi Expanded'; font-weight: 900; font-size: 40px; letter-spacing: 0; color: var(--gold); }
.stat-text { max-width: 210px; font-size: 15px; line-height: 1.25; letter-spacing: .05em; }

/* ---------- формат и бонусы */
.s-title { position: absolute; left: 72px; top: 78px; font-family: 'Akrobat'; font-weight: 800; font-size: 52px; line-height: 1; color: #FFFFFF; }
.format-grid { position: absolute; left: 72px; right: 72px; top: 158px; bottom: 44px; display: grid; grid-template-columns: 468px 1fr; gap: 28px; }
.panel { display: flex; flex-direction: column; border: 1.5px solid rgba(43,198,212,.55); border-radius: 24px; padding: 24px 26px 18px;
         background: linear-gradient(180deg, rgba(16,31,53,.9), rgba(9,20,36,.9)); }
.panel-label { font-family: 'Akrobat'; font-weight: 800; font-size: 15px; letter-spacing: .18em; text-transform: uppercase; color: var(--turq-l); margin-bottom: 16px; }
.panel-label.gold { color: var(--gold); }
.frows { flex: 1; display: flex; flex-direction: column; justify-content: space-between; padding-bottom: 6px; }
.frow { display: flex; gap: 14px; align-items: center; font-size: 17px; line-height: 1.3; color: var(--soft); }
.bonuses { display: flex; flex-direction: column; }
.bonus-grid { flex: 1; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: repeat(3, 1fr); gap: 14px; }
.bonus { border: 1.5px solid rgba(242,193,78,.45); border-radius: 18px; padding: 15px 18px 16px; background: rgba(242,193,78,.05); }
.bonus.hero { border-color: var(--gold); background: rgba(242,193,78,.10); }
.b-head { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.b-head .ic { flex-basis: 32px; height: 32px; color: var(--gold); background: rgba(242,193,78,.12); border-color: rgba(242,193,78,.45); }
.b-name { font-family: 'Akrobat'; font-weight: 800; font-size: 20px; line-height: 1.05; color: var(--gold-l); }
.bonus p { font-size: 15px; line-height: 1.35; color: var(--soft); }

/* ---------- итог */
.final .s-title { font-size: 56px; top: 80px; }
.res-grid { position: absolute; left: 72px; right: 72px; top: 170px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.res-tile { border: 1.5px solid rgba(43,198,212,.55); border-radius: 20px; padding: 20px 22px 22px; min-height: 142px;
            background: linear-gradient(180deg, rgba(16,31,53,.92), rgba(9,20,36,.92)); }
.res-num { display: block; font-family: 'RF Dewi Expanded'; font-weight: 900; font-size: 30px; color: var(--turq); margin-bottom: 10px; }
.res-tile p { font-size: 18px; line-height: 1.32; color: #F1F5FF; }
.money { position: absolute; left: 72px; right: 72px; top: 520px; font-size: 22px; line-height: 1.4; color: var(--soft); }
.money b { font-family: 'Akrobat'; font-weight: 800; font-size: 30px; color: var(--gold); margin-right: 6px; }
.honest { position: absolute; left: 72px; right: 72px; bottom: 40px; padding-top: 16px; border-top: 1px solid rgba(157,176,206,.22);
          font-size: 15px; line-height: 1.4; color: var(--muted); font-style: italic; }
"""


FIT_JS = """
// Один размер шрифта тем на всех модулях (18.6px), уменьшаем только если не влезает;
// оставшееся место по высоте раздаём промежуткам между темами.
document.fonts.ready.then(() => {
  document.querySelectorAll('section.module').forEach(s => {
    const card = s.querySelector('.card'), ul = s.querySelector('ul.topics');
    const lis = [...ul.querySelectorAll('li')];
    const limit = card.getBoundingClientRect().bottom - 40;
    const bottom = () => lis[lis.length - 1].getBoundingClientRect().bottom;
    let size = 18.6, gap = 10;
    const apply = () => {
      ul.style.fontSize = size.toFixed(1) + 'px';
      lis.forEach(li => { li.style.marginBottom = gap.toFixed(1) + 'px'; });
    };
    apply();
    while (bottom() > limit && size > 15.4) { size -= 0.2; apply(); }
    while (gap < 30 && bottom() < limit - 6) { gap += 0.5; apply(); }
    if (bottom() > limit) { gap -= 0.5; apply(); }
  });
  document.body.dataset.fitted = '1';
});
"""


def build_html(data: dict) -> str:
    n_mod = len(data["modules"])
    total = 1 + n_mod + 2
    slides = [cover_slide(data["cover"])]
    for i, mod in enumerate(data["modules"]):
        slides.append(module_slide(mod, page=2 + i, total=total, n_modules=n_mod))
    slides.append(format_slide(data["format"], data["bonuses"], page=total - 1, total=total))
    slides.append(final_slide(data["final"], page=total, total=total))
    css = CSS.replace("PATTERN", PATTERN_SVG)
    title = html.escape(f"{data['cover']['name']} — программа курса")
    return (f'<!doctype html>\n<html lang="ru"><head><meta charset="utf-8"><title>{title}</title>'
            f"<style>{css}</style></head><body>{''.join(slides)}\n<script>{FIT_JS}</script></body></html>\n")


# ---------------------------------------------------------------- проверка вёрстки и печать
LAYOUT_CHECK_JS = """
() => {
  const issues = [];
  document.querySelectorAll('section.slide').forEach((s, i) => {
    const sr = s.getBoundingClientRect();
    s.querySelectorAll('*').forEach(el => {
      if (el.classList.contains('pattern') || el.closest('.pattern')) return;
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return;
      if (r.right > sr.right + 1 || r.bottom > sr.bottom + 1 || r.left < sr.left - 1 || r.top < sr.top - 1) {
        if (!el.classList.contains('back') && !el.classList.contains('tab') && !el.closest('.ring'))
          issues.push(`слайд ${i + 1}: <${el.tagName.toLowerCase()} class="${el.className}"> выходит за край`);
      }
    });
    s.querySelectorAll('.panel, .bonus, .res-tile').forEach(box => {
      const br = box.getBoundingClientRect();
      box.querySelectorAll('*').forEach(ch => {
        const r = ch.getBoundingClientRect();
        if (r.height > 0 && r.bottom > br.bottom + 1) issues.push(`слайд ${i + 1}: текст вылезает из блока .${box.className.split(' ')[0]}`);
      });
    });
    const card = s.querySelector('.card');
    if (card) {
      const cr = card.getBoundingClientRect();
      const lis = s.querySelectorAll('ul.topics li');
      const last = lis[lis.length - 1].getBoundingClientRect();
      if (last.bottom > cr.bottom - 22) issues.push(`слайд ${i + 1}: темы упираются в низ карточки (${Math.round(last.bottom - cr.bottom)} px)`);
      const res = s.querySelector('.result').getBoundingClientRect();
      const mats = s.querySelectorAll('.mat');
      const lastMat = mats[mats.length - 1].getBoundingClientRect();
      if (lastMat.bottom > res.top - 10) issues.push(`слайд ${i + 1}: материалы наезжают на «Результат» (${Math.round(lastMat.bottom - res.top)} px)`);
      lis.forEach(li => { const r = li.getBoundingClientRect(); if (r.right > res.left - 8 && r.bottom > res.top) issues.push(`слайд ${i + 1}: тема под «Результатом»`); });
    }
  });
  return issues;
}
"""


def render(previews: Path | None) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H}, device_scale_factor=2)
        page.goto(HTML_PATH.as_uri())
        page.evaluate("() => document.fonts.ready.then(() => true)")
        page.wait_for_function("document.body.dataset.fitted === '1'")
        # Шрифт есть в системе, если текст им шире или уже, чем запасным моноширинным.
        missing = page.evaluate("""() => {
            const ctx = document.createElement('canvas').getContext('2d');
            const width = font => { ctx.font = font; return ctx.measureText('Программа курса 2026').width; };
            return ['Akrobat', 'RF Dewi Expanded', 'Avenir Next']
                .filter(f => width(`32px "${f}", monospace`) === width('32px monospace'));
        }""")
        if missing:
            print("ВНИМАНИЕ: не найдены шрифты:", ", ".join(missing))
        issues = page.evaluate(LAYOUT_CHECK_JS)
        for issue in issues:
            print("ВЁРСТКА:", issue)
        if previews:
            previews.mkdir(parents=True, exist_ok=True)
            for i, el in enumerate(page.query_selector_all("section.slide"), start=1):
                el.screenshot(path=str(previews / f"slide-{i:02d}.png"))
        page.pdf(path=str(PDF_PATH), width=f"{SLIDE_W}px", height=f"{SLIDE_H}px",
                 print_background=True, prefer_css_page_size=True)
        browser.close()
    print(f"Готово: {PDF_PATH.name}, проблем вёрстки: {len(issues)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--previews", type=Path, help="папка для PNG каждого слайда")
    args = parser.parse_args()
    data = parse_md(MD_PATH.read_text(encoding="utf-8"))
    HTML_PATH.write_text(build_html(data), encoding="utf-8")
    print(f"{HTML_PATH.name}: обложка, {len(data['modules'])} модулей, формат и бонусы, итог")
    render(args.previews)


if __name__ == "__main__":
    main()
