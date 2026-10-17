#!/usr/bin/env python3
"""Собирает дизайн-PDF программы курса из MD: слайды 16:9 (1280×720).

Источник правды — MD (схема — в README.md этой папки). Правишь текст там и запускаешь скрипт заново.
Порядок слайдов: обложка → для кого → бесплатный вход → путь на курсе или трансформация →
модули → формат и фишки (бонусы) → итог → откуда цифры. Приложения MD (карта болей,
решения за Васей, проверки) в PDF не идут.

Две темы: «timochko» — светлая с коралловым акцентом, «dymshakov» — тёмная с лаймовым.
Тема выбирается по строке «по методике …» в MD или ключом --theme.

Запуск:
    python3 render.py                                   # обе программы
    python3 render.py timochko/programma-timochko.md    # одна
    python3 render.py --previews <папка>                # плюс PNG каждого слайда
"""
import argparse
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCES = [HERE / "timochko" / "programma-timochko.md", HERE / "dymshakov" / "programma-dymshakov.md",
                   HERE / "edinaya" / "programma-edinaya.md"]
SLIDE_W, SLIDE_H = 1280, 720
MAX_MODULES = 9

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
    "list": '<path d="M9.5 6.5h10M9.5 12h10M9.5 17.5h10"/><path d="M4.8 6.5h.01M4.8 12h.01M4.8 17.5h.01" stroke-width="2.6"/>',
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
    "phone": '<rect x="6.5" y="2.8" width="11" height="18.4" rx="2.6"/><path d="M10.5 17.8h3"/>',
    "arrow": '<path d="M4 12h15M13.5 6.5L19 12l-5.5 5.5"/>',
    "book": '<path d="M4.5 5.5A2 2 0 0 1 6.5 3.5H19v14H6.5a2 2 0 0 0-2 2z"/><path d="M4.5 19.5a2 2 0 0 0 2 2H19v-4"/>',
    "task": '<rect x="3.5" y="3.5" width="17" height="17" rx="3.5"/><path d="M7.5 12h9M12 7.5v9"/>',
}

# Значок материала: первое совпадение по ключу в тексте (без учёта регистра).
MATERIAL_ICONS = [
    ("репозитор", "folder"), ("скилл", "spark"), ("референс", "eye"), ("пайплайн", "layers"),
    ("юридическ", "pen"), ("скрипт диагност", "chat"),
    ("видео", "video"), ("скринкаст", "video"), ("мини-урок", "video"), ("запись эфир", "video"),
    ("калькулятор", "calc"), ("упражнен", "target"), ("конспект", "book"), ("красн", "flag"), ("чек-лист", "check"), ("таблиц", "table"), ("crm", "table"),
    ("трекер", "table"), ("промпт", "spark"), ("скрипт", "chat"), ("договор", "pen"), ("прайс", "tag"),
    ("план на", "calendar"), ("карта 30", "calendar"), ("календар", "calendar"), ("расписани", "clock"),
    ("гайд", "book"), ("инструкц", "book"), ("памятк", "book"), ("структур", "layers"), ("сценари", "layers"),
    ("нейросет", "spark"), ("карт", "map"), ("список", "list"), ("база", "list"), ("переписк", "chat"),
    ("сообщени", "chat"), ("возражен", "shield"), ("акт", "pen"), ("оплат", "card"), ("счёт", "card"),
    ("отзыв", "star"), ("кейс", "award"), ("сертификат", "award"), ("цен", "tag"), ("английск", "globe"),
    ("портфолио", "folder"), ("бот", "bot"), ("кп", "doc"), ("шаблон", "doc"),
]
FORMAT_ICONS = [
    ("узбек", "lang"), ("язык", "lang"), ("минут", "clock"), ("урок", "clock"), ("телефон", "phone"),
    ("куратор", "eye"), ("провер", "eye"), ("эфир", "live"), ("разбор", "live"), ("чат", "users"),
    ("сертификат", "award"), ("диплом", "award"), ("защит", "award"), ("практик", "map"),
    ("доступ", "video"), ("запис", "video"), ("задани", "check"), ("домашк", "check"),
]
PERK_ICONS = [
    ("ии-", "bot"), ("бот", "bot"), ("наставник", "bot"), ("эфир", "live"), ("разбор", "live"),
    ("банк", "folder"), ("шаблон", "folder"), ("чат", "users"), ("сообществ", "users"),
    ("выпускник", "users"), ("сертификат", "award"), ("челлендж", "flag"), ("заказ", "tag"),
    ("карт", "map"), ("калькулятор", "calc"), ("друг", "users"), ("интервью", "chat"),
]


def icon(name: str, size: int = 20) -> str:
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


def pick_icon(text: str, table: list, default: str = "doc") -> str:
    """Ключ ищется с начала слова: «бот» не должен находиться в «работаешь»."""
    low = text.lower()
    return next((name for key, name in table if re.search(r"(?<![а-яёa-z])" + re.escape(key), low)), default)


# ---------------------------------------------------------------- разбор MD
LABEL_RE = re.compile(r"^\*\*([^*]+?):\*\*\s*(.*)$")
BOLD_LEAD_RE = re.compile(r"^\*\*(.+?)\*\*\s*(.*)$")
LIST_RE = re.compile(r"^(?:[-*•]|\d+[.)])\s+(.+)$")
FOOTNOTE_RE = re.compile(r"^\[\^(\d+)\]:\s*(.+)$")
MODULE_RE = re.compile(r"^Модуль\s+(\d+)\.\s*(.+)$")
SKIP_TITLES = ("Приложение", "Решения за", "Проверить до", "Вопросы аудитории", "Слабые места", "Что изменено")


def classify(title: str, started: bool) -> str:
    if MODULE_RE.match(title):
        return "module"
    for prefix, section in (("Для кого", "for_whom"), ("Бесплатный вход", "lead"), ("Путь на курсе", "path"),
                            ("Трансформация", "transform"), ("Как проходит обучение", "format"),
                            ("Фишки", "perks"), ("Бонусы", "perks"), ("Главные результаты", "results"),
                            ("Результат результатов", "results"), ("Итог", "results"), ("Через", "results"),
                            ("Тарифы", "tariffs")):
        if title.startswith(prefix):
            return section
    if title.startswith(SKIP_TITLES):
        return "skip"
    return "skip" if started else "cover"


def join(a: str, b: str) -> str:
    return f"{a} {b}".strip() if a else b.strip()


def parse_md(text: str) -> dict:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    data = {"cover": {"chips": []}, "segments": [], "segments_intro": "", "leads": [], "leads_intro": "",
            "path": [], "path_intro": "", "transform": {"steps": []}, "modules": [], "format": [],
            "perks": [], "perks_title": "", "results": {"items": [], "labels": {}}, "footnotes": {}, "used_fn": set(),
            "tariffs": {"cards": [], "intro": "", "note": ""},
            "warnings": []}
    section, item, mode, started = "head", None, None, False

    for raw in text.splitlines():
        line = raw.strip()
        fn = FOOTNOTE_RE.match(line)
        if fn:
            data["footnotes"][fn.group(1)] = fn.group(2).strip()
            continue
        if not line or line in ("---", "***"):
            continue
        if line.startswith("# "):
            data["cover"]["name"] = line[2:].strip()
            continue
        if line.startswith("## "):
            title = line[3:].strip()
            section = classify(title, started)
            started = started or section != "cover"
            item, mode = None, None
            if section == "cover":
                data["cover"]["promise"] = title
            elif section == "module":
                m = MODULE_RE.match(title)
                item = {"n": int(m.group(1)), "title": m.group(2).strip(), "week": "", "lead": "", "price": "",
                        "tariff": "", "topics": [], "tasks": [], "materials": [], "result": ""}
                data["modules"].append(item)
            elif section == "perks":
                data["perks_title"] = title
            elif section == "results":
                data["results"]["title"] = title
            elif section == "skip" and not title.startswith(SKIP_TITLES):
                data["warnings"].append(f"раздел «{title}» не знаком сборщику — в PDF не попадёт")
            continue
        if section in ("skip",):
            continue
        if section == "head":
            data["cover"]["label"] = re.sub(r"\*\*", "", line)
            continue
        handler = HANDLERS.get(section)
        data["used_fn"].update(re.findall(r"\[\^(\d+)\]", line))
        if handler:
            item, mode = handler(data, line, item, mode)

    data["modules"].sort(key=lambda m: m["n"])
    return data


def h_cover(data: dict, line: str, item, mode):
    c = data["cover"]
    lab = LABEL_RE.match(line)
    if lab and lab.group(1).startswith("Коротко"):
        c["meta"] = lab.group(2)
    elif lab and lab.group(1).startswith("Плашки"):
        c["chips"] = [p.strip() for p in lab.group(2).split("·") if p.strip()]
    elif lab and lab.group(1).startswith("Оффер"):
        c["offer"] = [x.strip() for x in lab.group(2).split("|") if x.strip()]
    elif line.startswith(">"):
        c["tagline"] = join(c.get("tagline", ""), line.lstrip("> ").strip())
    else:
        c["sub"] = join(c.get("sub", ""), line)
    return item, mode


def h_segments(data: dict, line: str, item, mode):
    if line.startswith("### "):
        item = {"title": line[4:].strip(), "text": "", "result": ""}
        data["segments"].append(item)
        return item, "text"
    lab = LABEL_RE.match(line)
    if item is None:
        data["segments_intro"] = join(data["segments_intro"], line)
    elif lab and "результат" in lab.group(1).lower():
        item["result"], mode = lab.group(2), "result"
    else:
        item[mode or "text"] = join(item[mode or "text"], re.sub(r"^[-*]\s+", "", line))
    return item, mode


LEAD_KEYS = {"закрывает": "closes", "внутри": "inside", "уносишь": "takes", "получаешь": "takes"}


def h_leads(data: dict, line: str, item, mode):
    if line.startswith("### "):
        item = {"name": line[4:].strip(), "closes": "", "inside": "", "takes": "", "extra": ""}
        data["leads"].append(item)
        return item, "extra"
    lab = LABEL_RE.match(line)
    if item is None:
        data["leads_intro"] = join(data["leads_intro"], line)
        return item, mode
    key = LEAD_KEYS.get(lab.group(1).strip().lower()) if lab else None
    if key:
        item[key], mode = lab.group(2), key
    else:
        item[mode or "extra"] = join(item[mode or "extra"], re.sub(r"^[-*]\s+", "", line))
    return item, mode


def split_step(text: str) -> dict:
    m = re.match(r"^\*\*(.+?)\*\*\s*[—–:-]?\s*(.*)$", text)
    if m:
        return {"label": m.group(1).strip().rstrip(":"), "text": m.group(2).strip()}
    return {"label": "", "text": text.strip()}


def h_path(data: dict, line: str, item, mode):
    li = LIST_RE.match(line)
    if li:
        data["path"].append(split_step(li.group(1)))
    elif data["path"]:
        data["path"][-1]["text"] = join(data["path"][-1]["text"], line)
    else:
        data["path_intro"] = join(data["path_intro"], line)
    return item, mode


TRANSFORM_KEYS = {"точка а": "a", "точка б": "b", "уровень трансформации": "level", "уровень": "level"}


def h_transform(data: dict, line: str, item, mode):
    t = data["transform"]
    lab = LABEL_RE.match(line)
    key = TRANSFORM_KEYS.get(lab.group(1).strip().lower()) if lab else None
    li = LIST_RE.match(line)
    if key:
        t[key], mode = lab.group(2), key
    elif li:
        t["steps"].append(split_step(li.group(1)))
        mode = "steps"
    elif mode and mode != "steps":
        t[mode] = join(t.get(mode, ""), line)
    else:
        t["intro"] = join(t.get("intro", ""), line)
    return item, mode


MODULE_KEYS = {"неделя": "week", "содержание модуля": "topics", "содержание": "topics", "темы": "topics",
               "задания": "tasks", "материалы": "materials", "результат после модуля": "result",
               "результат": "result", "сколько платят": "price", "тариф": "tariff"}


def h_module(data: dict, line: str, item, mode):
    lab = LABEL_RE.match(line)
    key = MODULE_KEYS.get(lab.group(1).strip().lower()) if lab else None
    li = LIST_RE.match(line)
    if key in ("week", "result", "price", "tariff"):
        item[key], mode = lab.group(2).strip(), key
    elif key:
        mode = key
        if lab.group(2).strip():
            item[key].append(lab.group(2).strip())
    elif li and mode in ("topics", "tasks", "materials"):
        item[mode].append(li.group(1).strip())
    elif mode == "result":
        item["result"] = join(item["result"], line)
    elif mode is None:
        item["lead"] = join(item["lead"], line.strip("*_ "))
    else:
        data["warnings"].append(f"Модуль {item['n']}: строка вне блоков — «{line[:60]}»")
    return item, mode


def h_format(data: dict, line: str, item, mode):
    li = LIST_RE.match(line)
    if li:
        data["format"].append(li.group(1).strip())
    elif data["format"]:
        data["format"][-1] = join(data["format"][-1], line)
    return item, mode


def h_perks(data: dict, line: str, item, mode):
    if line.startswith("### "):
        item = {"name": line[4:].strip(), "text": ""}
        data["perks"].append(item)
        return item, mode
    li = LIST_RE.match(line)
    if li and item is None:
        step = split_step(li.group(1))
        data["perks"].append({"name": step["label"] or step["text"], "text": step["text"] if step["label"] else ""})
    elif item is not None:
        item["text"] = join(item["text"], re.sub(r"^[-*]\s+", "", line))
    return item, mode


def h_results(data: dict, line: str, item, mode):
    r = data["results"]
    lab = LABEL_RE.match(line)
    li = LIST_RE.match(line)
    if lab:
        r["labels"][lab.group(1).strip()] = lab.group(2).strip()
    elif li:
        r["items"].append(li.group(1).strip())
    elif re.fullmatch(r"\*(?!\*)(.+)\*", line) or line.startswith("_"):
        r["honest"] = line.strip("*_ ")
    elif BOLD_LEAD_RE.match(line):
        m = BOLD_LEAD_RE.match(line)
        r["money_head"], r["money"] = m.group(1).strip(), m.group(2).strip()
    else:
        r["extra"] = join(r.get("extra", ""), line)
    return item, mode


TARIFF_KEYS = {"метка": "flag", "для кого": "who", "обычная цена": "regular", "цена для зрителей эфира": "viewers",
               "спеццена": "special", "спеццена на 24 часа": "special"}


def h_tariffs(data: dict, line: str, item, mode):
    t = data["tariffs"]
    if line.startswith("### "):
        item = {"name": line[4:].strip(), "flag": "", "who": "", "items": [], "regular": "", "viewers": "", "special": ""}
        t["cards"].append(item)
        return item, None
    if line.startswith(">"):
        t["note"] = join(t["note"], line.lstrip("> ").strip())
        return item, mode
    lab = LABEL_RE.match(line)
    key = TARIFF_KEYS.get(lab.group(1).strip().lower()) if lab else None
    li = LIST_RE.match(line)
    if item is None:
        t["intro"] = join(t["intro"], line)
    elif key:
        item[key] = lab.group(2).strip()
    elif li:
        item["items"].append(li.group(1).strip())
    else:
        data["warnings"].append(f"Тариф «{item['name']}»: строка вне блоков — «{line[:60]}»")
    return item, mode


HANDLERS = {"cover": h_cover, "for_whom": h_segments, "lead": h_leads, "path": h_path,
            "transform": h_transform, "module": h_module, "format": h_format, "perks": h_perks,
            "results": h_results, "tariffs": h_tariffs}


def validate(data: dict, src: Path) -> list:
    problems = []
    mods = data["modules"]
    if not 1 <= len(mods) <= MAX_MODULES:
        problems.append(f"модулей {len(mods)}, а нужно от 1 до {MAX_MODULES}")
    first = mods[0]["n"] if mods else 1
    for i, mod in enumerate(mods, start=first):
        if first not in (0, 1) or mod["n"] != i:
            problems.append(f"нумерация модулей сбита: ожидался {i}, стоит {mod['n']}")
        for part, name in (("topics", "содержание"), ("materials", "материалы"), ("result", "результат")):
            if not mod[part]:
                problems.append(f"Модуль {mod['n']}: пусто — {name}")
    for key in ("name", "promise"):
        if not data["cover"].get(key):
            problems.append(f"обложка: нет «{key}»")
    if problems:
        sys.exit(f"Ошибка в {src.name}:\n- " + "\n- ".join(problems))
    return data["warnings"]


# ---------------------------------------------------------------- форматирование строк
NUM_RE = re.compile(
    r"(?<![\w/:.$])(\d{1,2}:\d{2}|\$?\d+(?:[.,]\d+)?(?:\s?[–-]\s?\$?\d+(?:[.,]\d+)?)?(?:\+|%)?)(?![\w/]|-[а-яё])")
CAPS_KEEP = {"ИИ", "КП", "CRM", "ЦА", "ИП", "AI", "OLX", "ЦБ", "PDF", "IT", "СНГ", "ДЗ", "FAQ"}


def fmt(text: str, numbers: bool = False, footnotes: bool = True) -> str:
    text = re.sub(r"\[([^\]]+)\]\((?:[^)]+)\)", r"\1", text)  # ссылки — только текст
    text = text.replace("`", "")
    marks = re.findall(r"\[\^(\d+)\]", text)
    text = re.sub(r"\s*\[\^\d+\]", "\u0000", text)
    out = html.escape(text, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", out)
    if numbers:
        out = NUM_RE.sub(r'<b class="num">\1</b>', out)
    for n in marks:
        out = out.replace("\u0000", f'<sup class="fn">{n}</sup>' if footnotes else "", 1)
    return out.replace("\u0000", "")


def plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    return few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many


def upper_first(text: str) -> str:
    return text[:1].upper() + text[1:]


def top_bar(pill: str, note: str, brand: str, page: int, total: int, tag: str = "") -> str:
    note_html = f'<span class="pill-note">{html.escape(note)}</span>' if note else ""
    tag_html = f'<span class="pill tag">★ {html.escape(tag)}</span>' if tag else ""
    return (f'<div class="top"><div class="week"><span class="pill">{html.escape(pill)}</span>{note_html}{tag_html}</div>'
            f'<div class="brand">{html.escape(brand)} · программа <b>{page:02d} / {total:02d}</b></div></div>')


# ---------------------------------------------------------------- слайды
def cover_slide(data: dict, theme: str, total: int) -> str:
    c = data["cover"]
    name = html.escape(c["name"])
    chips = "".join(f'<span class="chip">{html.escape(ch)}</span>' for ch in c.get("chips", []))
    stats = []
    for part in (c.get("meta") or "").split("·"):
        part = part.strip()
        m = re.match(r"^(\d+)\s+(.+)$", part)
        if m:
            stats.append(f'<div class="stat"><span class="big">{m.group(1)}</span><span>{html.escape(m.group(2))}</span></div>')
        elif part:
            stats.append(f'<div class="stat stat-text"><span>{html.escape(part)}</span></div>')
    method = html.escape(c.get("label", "Программа курса"))
    big = re.search(r"(\d+)\s*(дн|недел|вечер)", c["promise"] + " " + (c.get("meta") or ""))
    badge = ""
    if big:
        n = int(big.group(1))
        forms = {"дн": ("день", "дня", "дней"), "недел": ("неделя", "недели", "недель"),
                 "вечер": ("вечер", "вечера", "вечеров")}[big.group(2)]
        unit = plural(n, *forms)
        badge = (f'<div class="badge"><span class="badge-num">{big.group(1)}</span>'
                 f'<span class="badge-cap">{unit}</span></div>')
    offers_html = ""
    if c.get("offer"):
        cells = "".join(f'<div class="offer">{icon("gift", 24)}<span>{fmt(o, numbers=True)}</span></div>' for o in c["offer"])
        offers_html = f'<div class="offers">{cells}</div>'
    return f"""
<section class="slide cover{" has-offer" if offers_html else ""}">
  <div class="deco"></div>
  <div class="cover-label">{method}</div>
  <h1 class="cover-name" data-fit data-min="44" data-max="{'118' if theme == 'dymshakov' else '92'}">{name}</h1>
  <div class="cover-promise" data-fit data-min="28" data-max="44">{fmt(c['promise'])}</div>
  <div class="cover-sub" data-fit data-min="16" data-max="22">{fmt(c.get('sub', ''))}</div>
  <div class="chips">{chips}</div>
  {offers_html}
  {badge}
  <div class="cover-bottom{'' if c.get('tagline') else ' no-tagline'}">
    <div class="tagline">{fmt(c.get('tagline', ''))}</div>
    <div class="stats">{''.join(stats)}</div>
  </div>
</section>"""


def segments_slide(data: dict, brand: str, page: int, total: int) -> str:
    cards = "".join(
        f'<div class="seg" data-fit data-min="11.5" data-max="19"><div class="seg-num">{i:02d}</div>'
        f'<h3>{fmt(s["title"])}</h3><p class="seg-text">{fmt(s["text"])}</p>'
        f'<div class="seg-res"><span class="lbl">Твой результат</span><p>{fmt(upper_first(s["result"]))}</p></div></div>'
        for i, s in enumerate(data["segments"], start=1))
    intro = f'<p class="s-intro">{fmt(data["segments_intro"])}</p>' if data["segments_intro"] else ""
    return f"""
<section class="slide segments{' has-intro' if data['segments_intro'] else ''}">
  <div class="deco faint"></div>
  {top_bar("Для кого", "узнай себя", brand, page, total)}
  <h2 class="s-title">Для кого эта программа</h2>{intro}
  <div class="seg-row n{len(data['segments'])}">{cards}</div>
</section>"""


def leads_slide(data: dict, brand: str, page: int, total: int) -> str:
    rows = (("closes", "Закрывает сомнения", "shield"), ("inside", "Внутри", "layers"), ("takes", "Уносишь", "gift"))
    cards = []
    for i, lm in enumerate(data["leads"], start=1):
        blocks = "".join(
            f'<div class="lm-row"><span class="ic">{icon(ic, 18)}</span><div><span class="lbl">{lbl}</span>'
            f'<p>{fmt(upper_first(lm[key]))}</p></div></div>'
            for key, lbl, ic in rows if lm.get(key))
        extra = f'<p class="lm-extra">{fmt(lm["extra"])}</p>' if lm.get("extra") else ""
        big = "24" if len(data["leads"]) == 1 else "19"
        cards.append(f'<div class="lm" data-fit data-min="11.5" data-max="{big}"><div class="lm-head"><span class="lm-step">'
                     f'{"Бесплатно" if len(data["leads"]) == 1 else f"Шаг {i}"}</span>'
                     f'<h3>{fmt(lm["name"])}</h3></div>{extra}{blocks}</div>')
    intro = f'<p class="s-intro">{fmt(data["leads_intro"])}</p>' if data["leads_intro"] else ""
    return f"""
<section class="slide leads{' has-intro' if data['leads_intro'] else ''}">
  <div class="deco faint"></div>
  {top_bar("До покупки", "бесплатный вход", brand, page, total)}
  <h2 class="s-title">Бесплатный вход — проверь нас до оплаты</h2>{intro}
  <div class="lm-row-wrap n{len(data['leads'])}">{''.join(cards)}</div>
</section>"""


def path_slide(data: dict, brand: str, page: int, total: int) -> str:
    steps = data["path"]
    half = (len(steps) + 1) // 2
    cols = []
    for part, offset in ((steps[:half], 0), (steps[half:], half)):
        items = "".join(
            f'<div class="step{" last" if offset + i == len(steps) - 1 else ""}"><span class="dot">{offset + i + 1}</span>'
            f'<div><span class="step-label">{fmt(st["label"])}</span><p>{fmt(upper_first(st["text"]))}</p></div></div>'
            for i, st in enumerate(part))
        cols.append(f'<div class="path-col" data-fit data-min="12" data-max="20">{items}</div>')
    intro = f'<p class="s-intro">{fmt(data["path_intro"])}</p>' if data["path_intro"] else ""
    return f"""
<section class="slide path{' has-intro' if data['path_intro'] else ''}">
  <div class="deco faint"></div>
  {top_bar("Путь", "что будет с тобой по неделям", brand, page, total)}
  <h2 class="s-title">Путь на курсе</h2>{intro}
  <div class="path-grid">{''.join(cols)}</div>
</section>"""


def transform_step(i: int, st: dict) -> str:
    label = f"<b>{fmt(st['label'])}</b>" if st["label"] else ""
    return (f'<div class="t-step" data-fit data-min="11.5" data-max="19"><span class="t-num">{i:02d}</span>'
            f'{label}<p>{fmt(upper_first(st["text"]))}</p></div>')


def transform_slide(data: dict, brand: str, page: int, total: int) -> str:
    t = data["transform"]
    steps = "".join(transform_step(i, st) for i, st in enumerate(t["steps"], start=1))
    level = f'<div class="t-level">{icon("layers", 20)}<span>{fmt(t.get("level", ""))}</span></div>' if t.get("level") else ""
    return f"""
<section class="slide transform">
  <div class="deco faint"></div>
  {top_bar("Трансформация", "точка А → точка Б", brand, page, total)}
  <h2 class="s-title">Из точки А в точку Б</h2>
  <div class="ab">
    <div class="pt a" data-fit data-min="13" data-max="22"><span class="pt-lbl">Точка А · сейчас</span><p>{fmt(upper_first(t.get('a', '')))}</p></div>
    <div class="ab-arrow">{icon('arrow', 44)}</div>
    <div class="pt b" data-fit data-min="13" data-max="22"><span class="pt-lbl">Точка Б · после курса</span><p>{fmt(upper_first(t.get('b', '')))}</p></div>
  </div>
  {level}
  <div class="t-steps n{len(t['steps'])}">{steps}</div>
</section>"""


def module_slide(mod: dict, theme: str, brand: str, page: int, total: int, n_mod: int, pos: int = 0) -> str:
    topics = "".join(f"<li>{fmt(t, numbers=True)}</li>" for t in mod["topics"])
    mats = "".join(
        f'<div class="mat"><span class="ic">{icon(pick_icon(t, MATERIAL_ICONS), 18)}</span>'
        f'<span class="t">{fmt(t)}</span></div>' for t in mod["materials"])
    tasks = "".join(f'<li><span class="ic">{icon("check_square", 17)}</span><span>{fmt(t, numbers=True)}</span></li>'
                    for t in mod["tasks"])
    pos = pos or mod["n"]
    progress = "".join(f'<i class="{"on" if i == pos else ("done" if i < pos else "")}"></i>'
                       for i in range(1, n_mod + 1))
    week = mod["week"]
    pill, note = (week.split("—", 1)[0].strip(), week.split("—", 1)[1].strip()) if "—" in week else (
        (week, "") if week else (f"Модуль {mod['n']}", "программа курса"))
    lead = f'<p class="m-lead">{fmt(mod["lead"])}</p>' if mod["lead"] else ""
    if mod["price"]:
        lead += (f'<div class="m-price">{icon("tag", 18)}<span class="m-price-lbl">Сколько платят</span>'
                 f'<span class="m-price-val">{fmt(mod["price"], numbers=True)}</span></div>')
    result = fmt(upper_first(mod["result"]), numbers=True)
    if theme == "dymshakov":
        tasks_block = (f'<div class="lbl">Задания</div><ul class="tasks">{tasks}</ul>' if tasks else "")
        return f"""
<section class="slide module d">
  <div class="deco faint"></div>
  {top_bar(pill, note, brand, page, total, mod["tariff"])}
  <div class="dcard">
    <div class="d-head"><span class="d-num">{mod['n']:02d}</span><div class="d-titles"><span class="d-kicker">Модуль {mod['n']}</span>
      <h2 class="m-title" data-fit data-min="30" data-max="46">{fmt(mod['title'])}</h2>{lead}</div></div>
    <div class="d-grid">
      <div class="d-col" data-fit data-min="12.5" data-max="17.5" data-spread="li"><div class="lbl">Содержание модуля</div><ul class="topics">{topics}</ul></div>
      <div class="d-col side" data-fit data-min="11.5" data-max="15">{tasks_block}<div class="lbl">Материалы</div>{mats}</div>
    </div>
    <div class="d-result" data-fit data-min="13" data-max="17"><div class="d-res-lbl">{icon('target', 22)}<span>Результат после модуля</span></div><p>{result}</p></div>
  </div>
  <div class="progress"><span>{pos} из {n_mod}</span><div class="bar">{progress}</div></div>
</section>"""
    tasks_block = (f'<div class="aside-label">Задания</div><ul class="tasks">{tasks}</ul>' if tasks else "")
    return f"""
<section class="slide module t">
  <div class="deco faint"></div>
  {top_bar(pill, note, brand, page, total, mod["tariff"])}
  <div class="stack">
    <div class="back"></div>
    <div class="card">
      <div class="tab"><span>Модуль {mod['n']}</span></div>
      <h2 class="m-title" data-fit data-min="30" data-max="42">{fmt(mod['title'])}</h2>{lead}
      <div class="grid">
        <div class="topics-box" data-fit data-min="12.5" data-max="18" data-spread="li"><ul class="topics">{topics}</ul></div>
        <div class="aside" data-fit data-min="11.5" data-max="14.5">{tasks_block}<div class="aside-label">Материалы</div>{mats}</div>
      </div>
      <div class="result" data-fit data-min="12.5" data-max="15.5"><div class="h"><span>Результат</span>{icon('check_square', 28)}</div><p>{result}</p></div>
    </div>
  </div>
  <div class="progress"><span>{pos} из {n_mod}</span><div class="bar">{progress}</div></div>
</section>"""


def format_slide(data: dict, brand: str, page: int, total: int) -> str:
    rows = "".join(
        f'<div class="frow"><span class="ic">{icon(pick_icon(t, FORMAT_ICONS, "check"), 19)}</span><span>{fmt(t, numbers=True)}</span></div>'
        for t in data["format"])
    tiles = "".join(
        f'<div class="perk{" hero" if i == 0 else ""}" data-fit data-min="11" data-max="15">'
        f'<div class="p-head"><span class="ic">{icon(pick_icon(p["name"] + " " + p["text"], PERK_ICONS, "gift"), 19)}</span>'
        f'<span class="p-name">{fmt(p["name"])}</span></div><p>{fmt(upper_first(p["text"]))}</p></div>'
        for i, p in enumerate(data["perks"]))
    perks_label = "Фишки" if data["perks_title"].startswith("Фишки") else "Бонусы и усилители"
    return f"""
<section class="slide format">
  <div class="deco faint"></div>
  {top_bar("Формат", "что входит в курс", brand, page, total)}
  <h2 class="s-title">Как проходит обучение</h2>
  <div class="format-grid">
    <div class="panel"><div class="panel-label">Формат</div><div class="frows" data-fit data-min="11.5" data-max="16.5">{rows}</div></div>
    <div class="perks"><div class="panel-label accent">{perks_label}</div><div class="perk-grid n{len(data['perks'])}">{tiles}</div></div>
  </div>
</section>"""


def results_slide(data: dict, brand: str, page: int, total: int) -> str:
    r = data["results"]
    tiles = "".join(
        f'<div class="res-tile" data-fit data-min="12.5" data-max="21"><span class="res-num">{i:02d}</span><p>{fmt(t, numbers=True)}</p></div>'
        for i, t in enumerate(r["items"], start=1))
    labels = "".join(f'<div class="res-label"><span class="lbl">{html.escape(k)}</span><p>{fmt(upper_first(v))}</p></div>'
                     for k, v in r["labels"].items())
    money = (f'<div class="money"><b>{fmt(r["money_head"])}</b> {fmt(r.get("money", ""))}</div>'
             if r.get("money_head") else "")
    honest = f'<div class="honest">{fmt(r["honest"])}</div>' if r.get("honest") else ""
    title = r.get("title", "Главные результаты")
    return f"""
<section class="slide results">
  <div class="deco"></div>
  {top_bar("Итог", "что будет после программы", brand, page, total)}
  <h2 class="s-title">{fmt(title)}</h2>
  <div class="res-body">
    {f'<div class="res-labels">{labels}</div>' if labels else ''}
    <div class="res-grid n{len(r['items'])}">{tiles}</div>
    {money}
    {honest}
  </div>
</section>"""


def tariff_card(card: dict) -> str:
    items = "".join(f"<li>{fmt(it, numbers=True)}</li>" for it in card["items"])
    flag = f'<span class="t-flag">{html.escape(card["flag"])}</span>' if card["flag"] else ""
    who = f'<p class="t-who">{fmt(upper_first(card["who"]))}</p>' if card["who"] else ""
    rows = "".join(f'<div class="t-row"><span>{lbl}</span><s>{fmt(card[key])}</s></div>'
                   for key, lbl in (("regular", "Обычная цена"), ("viewers", "Зрителям эфира")) if card[key])
    special = (f'<div class="t-special-lbl">Спеццена · 24 часа после эфира</div>'
               f'<div class="t-special">{fmt(card["special"])}</div>') if card["special"] else ""
    return (f'<div class="tariff{" hero" if card["flag"] else ""}">{flag}<div class="t-name">{fmt(card["name"])}</div>{who}'
            f'<ul class="t-items" data-fit data-min="11" data-max="15.5">{items}</ul>'
            f'<div class="t-price">{rows}{special}</div></div>')


def tariffs_slide(data: dict, brand: str, page: int, total: int) -> str:
    t = data["tariffs"]
    intro = f'<p class="s-intro">{fmt(t["intro"], numbers=True)}</p>' if t["intro"] else ""
    note = f'<div class="t-note">{fmt(t["note"])}</div>' if t["note"] else ""
    return f"""
<section class="slide tariffs">
  <div class="deco"></div>
  {top_bar("Тарифы", "цена растёт в 3 этапа", brand, page, total)}
  <h2 class="s-title">Выбери свой тариф</h2>{intro}
  <div class="tariff-grid n{len(t['cards'])}">{''.join(tariff_card(c) for c in t['cards'])}</div>
  {note}
</section>"""


def sources_slide(data: dict, brand: str, page: int, total: int) -> str:
    items = "".join(f'<li><sup class="fn">{n}</sup>{fmt(t, footnotes=False)}</li>'
                    for n, t in sorted(data["footnotes"].items(), key=lambda kv: int(kv[0]))
                    if n in data["used_fn"])
    return f"""
<section class="slide sources">
  <div class="deco faint"></div>
  {top_bar("Источники", "откуда цифры", brand, page, total)}
  <h2 class="s-title">Откуда цифры</h2>
  <p class="s-intro">Цены на рынке и расчёты — из исследования проекта. Где первоисточник не перепроверен, так и написано.</p>
  <ol class="src-list" data-fit data-min="10" data-max="14">{items}</ol>
</section>"""


# ---------------------------------------------------------------- стили
BASE_CSS = """
@page { size: 1280px 720px; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: var(--bg); }
body { font-family: var(--f-body); color: var(--ink); -webkit-font-smoothing: antialiased; }
.slide { position: relative; width: 1280px; height: 720px; overflow: hidden; break-after: page; background: var(--slide-bg); }
.slide:last-child { break-after: auto; }
.deco { position: absolute; inset: 0; background-image: var(--pattern); background-size: var(--pattern-size); opacity: var(--pattern-op); pointer-events: none; }
.deco.faint { opacity: calc(var(--pattern-op) * .6); }
[data-fit] { overflow: hidden; }
b.num { font-weight: 700; color: var(--num); }
sup.fn { font-size: .62em; font-weight: 700; color: var(--accent-text); margin-left: 1px; vertical-align: super; line-height: 0; }
.lbl { display: block; font-family: var(--f-label); font-weight: 800; font-size: 13px; letter-spacing: .16em; text-transform: uppercase; color: var(--accent-text); margin-bottom: 8px; }

/* шапка */
.top { position: absolute; left: 64px; right: 64px; top: 28px; display: flex; align-items: center; justify-content: space-between; z-index: 3; }
.week { display: flex; align-items: center; gap: 14px; }
.pill { font-family: var(--f-label); font-weight: 800; font-size: 15px; letter-spacing: .14em; text-transform: uppercase;
        color: var(--pill-ink); background: var(--accent); padding: 6px 13px 5px; border-radius: 999px; }
.pill-note { font-family: var(--f-label); font-weight: 700; font-size: 16px; letter-spacing: .08em; text-transform: uppercase; color: var(--accent-text); }
.brand { font-family: var(--f-label); font-weight: 700; font-size: 13.5px; letter-spacing: .16em; text-transform: uppercase; color: var(--faint); }
.brand b { color: var(--muted); margin-left: 8px; }
.s-title { position: absolute; left: 72px; top: 74px; right: 72px; font-family: var(--f-title); font-weight: var(--title-w); font-size: var(--s-title-size);
           line-height: 1; letter-spacing: var(--title-ls); text-transform: var(--title-tt); color: var(--ink); }
.s-intro { position: absolute; left: 72px; right: 72px; top: 136px; font-size: 17px; line-height: 1.35; color: var(--muted); }

/* обложка */
.cover-label { position: absolute; left: 72px; top: 62px; font-family: var(--f-label); font-weight: 800; font-size: 16px; letter-spacing: .26em;
               text-transform: uppercase; color: var(--accent-text); display: flex; align-items: center; gap: 16px; }
.cover-label::after { content: ""; width: 110px; height: 1.5px; background: var(--accent); opacity: .7; }
.cover-name { position: absolute; left: 68px; top: 96px; width: 770px; height: 150px; line-height: 150px; white-space: nowrap;
              font-family: var(--f-display); font-weight: 900; letter-spacing: var(--name-ls); text-transform: var(--title-tt); color: var(--name-color); }
.cover-promise { position: absolute; left: 72px; top: 262px; width: 770px; height: 128px; font-family: var(--f-title); font-weight: var(--title-w);
                 line-height: 1.06; letter-spacing: var(--title-ls); text-transform: var(--promise-tt); color: var(--ink); }
.cover-sub { position: absolute; left: 72px; top: 400px; width: 740px; height: 84px; line-height: 1.35; color: var(--soft); }
.chips { position: absolute; left: 72px; top: 500px; display: flex; gap: 12px; flex-wrap: wrap; width: 760px; }
.chip { font-size: 16px; font-weight: 600; color: var(--chip-ink); padding: 8px 17px; border-radius: 999px; border: 1.5px solid var(--chip-line); background: var(--chip-bg); }
.badge { position: absolute; right: 90px; top: 150px; width: 300px; height: 300px; border-radius: 50%; display: flex; flex-direction: column;
         align-items: center; justify-content: center; background: var(--badge-bg); border: 2px solid var(--badge-line); box-shadow: var(--badge-shadow); }
.badge::before { content: ""; position: absolute; inset: -20px; border-radius: 50%; border: 1.5px dashed var(--badge-line); opacity: .6; }
.badge-num { font-family: var(--f-display); font-weight: 900; font-size: 128px; line-height: .9; color: var(--badge-ink); }
.badge-cap { margin-top: 8px; font-family: var(--f-label); font-weight: 800; font-size: 20px; letter-spacing: .16em; text-transform: uppercase; color: var(--badge-cap); }
.cover-bottom { position: absolute; left: 72px; right: 72px; bottom: 40px; display: flex; align-items: flex-end; justify-content: space-between; gap: 40px;
                border-top: 1px solid var(--line); padding-top: 20px; }
.tagline { flex: 1; font-size: 18px; line-height: 1.35; color: var(--muted); }
.cover-bottom.no-tagline { justify-content: flex-start; }
.cover-bottom.no-tagline .tagline { display: none; }
.stats { display: flex; gap: 30px; align-items: flex-end; }
.stat { display: flex; align-items: baseline; gap: 9px; font-family: var(--f-label); font-weight: 700; font-size: 17px; letter-spacing: .06em; text-transform: uppercase; color: var(--soft); }
.stat .big { font-family: var(--f-display); font-weight: 900; font-size: 40px; letter-spacing: 0; color: var(--accent-text); }
.stat-text { max-width: 230px; font-size: 14px; line-height: 1.25; }

/* для кого */
.seg-row { position: absolute; left: 72px; right: 72px; top: 150px; bottom: 44px; display: grid; grid-auto-rows: minmax(0, 1fr); gap: 16px; }
.seg-row.n3 { grid-template-columns: repeat(3, 1fr); } .seg-row.n4 { grid-template-columns: repeat(4, 1fr); }
.seg-row.n5 { grid-template-columns: repeat(5, 1fr); } .seg-row.n2 { grid-template-columns: repeat(2, 1fr); }
.seg-row.n6 { grid-template-columns: repeat(3, 1fr); grid-template-rows: 1fr 1fr; }
.seg { display: flex; flex-direction: column; border-radius: 20px; padding: 1.2em 1.1em 1.1em; background: var(--card-bg); border: 1.5px solid var(--card-line); box-shadow: var(--card-shadow); }
.seg-num { font-family: var(--f-display); font-weight: 900; font-size: 1.7em; line-height: 1; color: var(--accent-text); margin-bottom: .45em; }
.seg h3 { font-family: var(--f-title); font-weight: var(--title-w); font-size: 1.42em; line-height: 1.05; letter-spacing: var(--title-ls); text-transform: var(--h3-tt); color: var(--ink); margin-bottom: .55em; }
.seg-text { font-size: .94em; line-height: 1.38; color: var(--soft); margin-bottom: .8em; }
.seg-res { margin-top: auto; border-top: 1.5px solid var(--accent-soft); padding-top: .7em; }
.seg-res .lbl { font-size: .78em; margin-bottom: .35em; }
.seg-res p { font-size: .98em; line-height: 1.36; color: var(--ink); font-weight: 600; }

/* бесплатный вход */
.lm-row-wrap { position: absolute; left: 72px; right: 72px; top: 150px; bottom: 44px; display: grid; grid-auto-rows: minmax(0, 1fr); gap: 18px; }
.lm-row-wrap.n1 { grid-template-columns: 1fr; } .lm-row-wrap.n2 { grid-template-columns: repeat(2, 1fr); }
.lm-row-wrap.n3 { grid-template-columns: repeat(3, 1fr); } .lm-row-wrap.n4 { grid-template-columns: repeat(4, 1fr); }
.lm { display: flex; flex-direction: column; gap: .9em; border-radius: 22px; padding: 1.3em 1.3em 1.2em; background: var(--card-bg); border: 1.5px solid var(--card-line); box-shadow: var(--card-shadow); }
.lm-row-wrap.n1 .lm { display: grid; grid-template-columns: 1fr 1fr 1fr; grid-template-rows: auto auto; align-content: center; column-gap: 1.6em; row-gap: 1.4em; }
.lm-row-wrap.n1 .lm-head, .lm-row-wrap.n1 .lm-extra { grid-column: 1 / -1; }
.lm-step { display: inline-block; font-family: var(--f-label); font-weight: 800; font-size: .78em; letter-spacing: .16em; text-transform: uppercase; color: var(--pill-ink); background: var(--accent); padding: .3em .7em .25em; border-radius: 999px; margin-bottom: .6em; }
.lm h3 { font-family: var(--f-title); font-weight: var(--title-w); font-size: 1.45em; line-height: 1.06; letter-spacing: var(--title-ls); text-transform: var(--h3-tt); color: var(--ink); }
.lm-row-wrap.n1 .lm h3 { font-size: 2em; }
.lm-extra { font-size: .95em; line-height: 1.38; color: var(--soft); }
.lm-row { display: flex; gap: .7em; align-items: flex-start; }
.lm-row .ic, .mat .ic, .frow .ic, .p-head .ic { flex: 0 0 auto; width: 2.1em; height: 2.1em; min-width: 30px; min-height: 30px; border-radius: 10px; display: flex; align-items: center; justify-content: center;
            background: var(--ic-bg); border: 1px solid var(--ic-line); color: var(--ic-ink); }
.lm-row .lbl { font-size: .74em; margin-bottom: .25em; }
.lm-row p { font-size: .95em; line-height: 1.38; color: var(--soft); }

/* путь */
.path-grid { position: absolute; left: 72px; right: 72px; top: 146px; bottom: 40px; display: grid; grid-template-columns: 1fr 1fr; gap: 36px; }
.path-col { position: relative; display: flex; flex-direction: column; justify-content: space-between; }
.path-col::before { content: ""; position: absolute; left: 1.03em; top: 1.2em; bottom: 1.6em; width: 2px; background: var(--accent-soft); }
.step { position: relative; display: flex; gap: 1em; align-items: flex-start; padding-bottom: .3em; }
.dot { flex: 0 0 2.15em; height: 2.15em; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-family: var(--f-label); font-weight: 800; font-size: 1em;
       color: var(--pill-ink); background: var(--accent); position: relative; z-index: 1; }
.step.last .dot { background: var(--ink); color: var(--bg); }
.step-label { display: block; font-family: var(--f-label); font-weight: 800; font-size: .86em; letter-spacing: .12em; text-transform: uppercase; color: var(--accent-text); margin: .15em 0 .2em; }
.step p { font-size: 1em; line-height: 1.34; color: var(--ink); }

/* трансформация */
.ab { position: absolute; left: 72px; right: 72px; top: 150px; height: 236px; display: grid; grid-template-columns: 1fr 70px 1fr; align-items: stretch; }
.pt { border-radius: 22px; padding: 1.1em 1.2em; }
.pt.a { background: var(--card-bg); border: 1.5px solid var(--card-line); }
.pt.b { background: var(--accent); color: var(--pill-ink); }
.pt-lbl { display: block; font-family: var(--f-label); font-weight: 800; font-size: .72em; letter-spacing: .16em; text-transform: uppercase; margin-bottom: .5em; opacity: .85; }
.pt p { font-size: 1em; line-height: 1.34; }
.pt.a p { color: var(--soft); }
.ab-arrow { display: flex; align-items: center; justify-content: center; color: var(--accent-text); }
.t-level { position: absolute; left: 72px; right: 72px; top: 402px; display: flex; gap: 12px; align-items: center; font-size: 16px; line-height: 1.35; color: var(--soft); }
.t-level svg { flex: 0 0 auto; color: var(--accent-text); }
.t-steps { position: absolute; left: 72px; right: 72px; top: 452px; height: 206px; display: grid; grid-auto-rows: minmax(0, 1fr); gap: 14px; }
.t-steps.n3 { grid-template-columns: repeat(3, 1fr); } .t-steps.n4 { grid-template-columns: repeat(4, 1fr); }
.t-steps.n5 { grid-template-columns: repeat(5, 1fr); } .t-steps.n6 { grid-template-columns: repeat(6, 1fr); }
.t-steps.n2 { grid-template-columns: repeat(2, 1fr); } .t-steps.n1 { grid-template-columns: 1fr; }
.t-step { display: flex; flex-direction: column; border-radius: 18px; padding: .9em 1em; background: var(--card-bg); border: 1.5px solid var(--card-line); }
.t-step p { margin-top: auto; }
.t-num { display: block; font-family: var(--f-display); font-weight: 900; font-size: 1.6em; line-height: 1; color: var(--accent-text); margin-bottom: .35em; }
.t-step b { color: var(--ink); }
.t-step p { font-size: .98em; line-height: 1.34; color: var(--soft); }

/* модуль — общие части */
ul.topics { list-style: none; }
ul.topics li { position: relative; padding-left: 1.45em; line-height: 1.34; color: var(--soft); margin-bottom: .5em; }
ul.topics li::before { content: ""; position: absolute; left: .25em; top: .5em; width: .42em; height: .42em; transform: rotate(45deg); background: var(--accent); border-radius: 1.5px; }
ul.tasks { list-style: none; margin-bottom: 1em; }
ul.tasks li { display: flex; gap: .55em; align-items: flex-start; line-height: 1.32; color: var(--soft); margin-bottom: .5em; }
ul.tasks li .ic { flex: 0 0 auto; color: var(--accent-text); margin-top: .05em; }
.mat { display: flex; gap: .7em; align-items: center; margin-bottom: .6em; }
.mat .t { line-height: 1.28; color: var(--soft); }
.m-lead { font-size: 16px; line-height: 1.35; color: var(--muted); margin: -6px 0 12px; }
.progress { position: absolute; left: 116px; bottom: 20px; display: flex; align-items: center; gap: 14px; z-index: 3;
            font-family: var(--f-label); font-weight: 700; font-size: 13px; letter-spacing: .14em; text-transform: uppercase; color: var(--faint); }
.progress .bar { display: flex; gap: 6px; }
.progress i { display: block; width: 26px; height: 5px; border-radius: 3px; background: var(--bar-off); }
.progress i.done { background: var(--bar-done); } .progress i.on { background: var(--accent); }

/* модуль — Тимочко: карточка-стопка как в «Программе» */
.module.t .stack { position: absolute; left: 116px; top: 92px; width: 1076px; height: 566px; }
.module.t .back { position: absolute; inset: 0; transform: translate(16px, -14px); border-radius: 26px; background: var(--back-bg); border: 1.5px solid var(--back-line); }
.module.t .card { position: absolute; inset: 0; display: flex; flex-direction: column; border-radius: 26px; padding: 30px 40px 34px 62px;
                  background: var(--card-bg); border: 1.5px solid var(--card-line-strong); box-shadow: var(--card-shadow); }
.module.t .tab { position: absolute; left: -27px; top: 50px; width: 54px; height: 206px; border-radius: 14px; background: var(--accent);
                 display: flex; align-items: center; justify-content: center; box-shadow: 0 12px 28px var(--tab-shadow); }
.module.t .tab span { writing-mode: vertical-rl; transform: rotate(180deg); font-family: var(--f-label); font-weight: 900; font-size: 21px; letter-spacing: .16em; text-transform: uppercase; color: var(--pill-ink); }
.module.t .m-title { flex: 0 0 auto; max-height: 104px; padding-bottom: .08em; font-family: var(--f-title); font-weight: var(--title-w); line-height: 1.06; letter-spacing: var(--title-ls);
                     text-transform: var(--h3-tt); color: var(--ink); margin-bottom: 16px; max-width: 960px; }
.module.t .grid { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 330px; column-gap: 40px; }
.module.t .topics-box { height: 100%; }
.module.t .aside { align-self: start; }
.aside-label { font-family: var(--f-label); font-weight: 800; font-size: 13px; letter-spacing: .18em; text-transform: uppercase; color: var(--accent-text); margin-bottom: 10px; }
.module.t .result { position: absolute; right: 34px; bottom: -30px; width: 372px; border-radius: 20px; padding: 15px 22px 17px; max-height: 214px;
                    background: var(--res-bg); border: 1.5px solid var(--res-line); box-shadow: var(--res-shadow); }
.module.t .result .h { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; font-family: var(--f-label); font-weight: 800; font-size: 1.4em; color: var(--res-head); }
.module.t .result p { line-height: 1.38; color: var(--res-ink); }
.module.t .result b.num { color: var(--res-num); }

/* модуль — Дымшаков: результат полосой, задания отдельной колонкой */
.module.d .dcard { position: absolute; left: 64px; right: 64px; top: 80px; bottom: 50px; display: flex; flex-direction: column; border-radius: 26px;
                   padding: 26px 34px 24px; background: var(--card-bg); border: 1.5px solid var(--card-line); box-shadow: var(--card-shadow); }
.d-head { display: flex; gap: 22px; align-items: center; margin-bottom: 16px; }
.d-num { font-family: var(--f-display); font-weight: 900; font-size: 92px; line-height: .82; color: var(--accent-text); }
.d-titles { flex: 1; min-width: 0; }
.d-kicker { display: block; font-family: var(--f-label); font-weight: 800; font-size: 13px; letter-spacing: .2em; text-transform: uppercase; color: var(--muted); margin-bottom: 4px; }
.module.d .m-title { max-height: 104px; padding-bottom: .06em; font-family: var(--f-title); font-weight: var(--title-w); line-height: 1; letter-spacing: var(--title-ls); text-transform: var(--h3-tt); color: var(--ink); }
.module.d .m-lead { margin: 6px 0 0; }
.d-grid { flex: 1; min-height: 0; display: grid; grid-template-columns: 1.35fr 1fr; gap: 32px; margin-bottom: 16px; }
.d-col { height: 100%; }
.d-col.side { border-left: 1.5px solid var(--line); padding-left: 28px; }
.d-col .lbl { font-size: 12.5px; }
.d-result { flex: 0 0 auto; max-height: 118px; display: grid; grid-template-columns: 250px 1fr; gap: 20px; align-items: center; border-radius: 18px; padding: 14px 22px;
            background: var(--res-bg); border: 1.5px solid var(--res-line); }
.d-res-lbl { display: flex; gap: 10px; align-items: center; font-family: var(--f-label); font-weight: 800; font-size: 15px; letter-spacing: .14em; text-transform: uppercase; color: var(--res-head); }
.d-result p { line-height: 1.36; color: var(--res-ink); font-weight: 600; }
.d-result b.num { color: var(--res-num); }

/* формат */
.format-grid { position: absolute; left: 72px; right: 72px; top: 148px; bottom: 42px; display: grid; grid-template-columns: 540px 1fr; grid-template-rows: minmax(0, 1fr); gap: 24px; }
.panel { display: flex; flex-direction: column; border-radius: 22px; padding: 22px 24px 18px; background: var(--card-bg); border: 1.5px solid var(--card-line-strong); box-shadow: var(--card-shadow); }
.panel-label { font-family: var(--f-label); font-weight: 800; font-size: 14px; letter-spacing: .18em; text-transform: uppercase; color: var(--accent-text); margin-bottom: 14px; }
.frows { flex: 1; min-height: 0; display: flex; flex-direction: column; justify-content: space-between; gap: .45em; }
.frow { display: flex; gap: .8em; align-items: center; line-height: 1.3; color: var(--soft); }
.perks { display: flex; flex-direction: column; min-height: 0; }
.perk-grid { flex: 1; min-height: 0; display: grid; grid-template-columns: 1fr 1fr; grid-auto-rows: minmax(0, 1fr); gap: 13px; }
.perk-grid.n4 { grid-template-rows: repeat(2, minmax(0, 1fr)); } .perk-grid.n5, .perk-grid.n6 { grid-template-rows: repeat(3, minmax(0, 1fr)); }
.perk-grid.n3 { grid-template-columns: 1fr; grid-template-rows: repeat(3, minmax(0, 1fr)); }
.perk { border-radius: 18px; padding: .95em 1.1em 1em; background: var(--perk-bg); border: 1.5px solid var(--perk-line); }
.perk.hero { background: var(--perk-hero-bg); border-color: var(--accent); }
.p-head { display: flex; align-items: center; gap: .7em; margin-bottom: .5em; }
.p-name { font-family: var(--f-title); font-weight: var(--title-w); font-size: 1.3em; line-height: 1.05; letter-spacing: var(--title-ls); text-transform: var(--h3-tt); color: var(--ink); }
.perk p { font-size: .96em; line-height: 1.35; color: var(--soft); }

/* итог */
.res-body { position: absolute; left: 72px; right: 72px; top: 150px; bottom: 32px; display: flex; flex-direction: column; gap: 16px; }
.res-labels { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.res-label { border-radius: 18px; padding: 14px 18px; background: var(--card-bg); border: 1.5px solid var(--card-line); }
.res-label:first-child { background: var(--accent); border-color: var(--accent); }
.res-label:first-child .lbl, .res-label:first-child p { color: var(--pill-ink); }
.res-label p { font-size: 16.5px; line-height: 1.35; color: var(--ink); font-weight: 600; }
.res-grid { flex: 1; min-height: 0; display: grid; grid-template-columns: repeat(3, 1fr); grid-auto-rows: minmax(0, 1fr); gap: 16px; }
.res-grid.n4 { grid-template-columns: repeat(4, 1fr); } .res-grid.n2 { grid-template-columns: repeat(2, 1fr); }
.res-grid.n5 { grid-template-columns: repeat(6, 1fr); } .res-grid.n5 .res-tile { grid-column: span 2; }
.res-grid.n5 .res-tile:nth-child(n+4) { grid-column: span 3; }
.res-tile { border-radius: 20px; padding: 18px 20px; background: var(--card-bg); border: 1.5px solid var(--card-line-strong); box-shadow: var(--card-shadow); }
.res-num { display: block; font-family: var(--f-display); font-weight: 900; font-size: 1.6em; line-height: 1; color: var(--accent-text); margin-bottom: .45em; }
.res-tile p { line-height: 1.32; color: var(--ink); }
.money { font-size: 20px; line-height: 1.4; color: var(--soft); }
.money b { font-family: var(--f-title); font-weight: var(--title-w); font-size: 28px; letter-spacing: var(--title-ls); text-transform: var(--h3-tt); color: var(--accent-text); margin-right: 6px; }
.honest { flex: 0 0 auto; padding-top: 12px; border-top: 1px solid var(--line); font-size: 14.5px; line-height: 1.4; color: var(--muted); font-style: italic; }

.has-intro .seg-row, .has-intro .lm-row-wrap, .has-intro .path-grid { top: 178px; }

.pt.b sup.fn, .d-result sup.fn, .res-label:first-child sup.fn, .lm-step sup.fn { color: inherit; }

/* цена услуги и тариф на слайде модуля, оффер на обложке */
.pill.tag { background: transparent; color: var(--accent-text); border: 1.5px solid var(--accent); font-size: 13px; letter-spacing: .1em; padding: 5px 12px 4px; }
.m-price { display: inline-flex; align-self: flex-start; align-items: center; gap: 10px; margin: -6px 0 14px; padding: 7px 16px 7px 12px;
           border-radius: 12px; background: var(--ic-bg); border: 1px solid var(--ic-line); max-width: 960px; }
.m-price svg { flex: 0 0 auto; color: var(--ic-ink); }
.m-price-lbl { font-family: var(--f-label); font-weight: 800; font-size: 12.5px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent-text); white-space: nowrap; }
.m-price-val { font-size: 15.5px; line-height: 1.3; color: var(--ink); }
.m-price-val b.num { color: var(--ink); }
.module.d .m-price { margin: 8px 0 0; }
.cover.has-offer .cover-bottom { bottom: 26px; }
.offers { position: absolute; left: 72px; right: 72px; top: 550px; display: flex; gap: 14px; align-items: stretch; }
.offer { flex: 1 1 0; display: flex; gap: 12px; align-items: center; padding: 9px 16px 9px 13px;
         border-radius: 14px; border: 1.5px solid var(--accent); background: var(--chip-bg); font-size: 16px; line-height: 1.28; color: var(--ink); }
.offer svg { flex: 0 0 auto; color: var(--accent-text); }

/* тарифы */
.tariffs .s-intro { top: 132px; }
.tariff-grid { position: absolute; left: 72px; right: 72px; top: 182px; bottom: 56px; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
               grid-template-rows: minmax(0, 1fr); gap: 18px; }
.tariff-grid.n2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.tariff { position: relative; display: flex; flex-direction: column; min-height: 0; border-radius: 22px; padding: 22px 22px 18px;
          background: var(--card-bg); border: 1.5px solid var(--card-line-strong); box-shadow: var(--card-shadow); }
.tariff.hero { border-color: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft), var(--card-shadow); }
.t-flag { position: absolute; top: -13px; left: 22px; font-family: var(--f-label); font-weight: 800; font-size: 13px; letter-spacing: .16em;
          text-transform: uppercase; color: var(--pill-ink); background: var(--accent); padding: 5px 12px 4px; border-radius: 999px; }
.t-name { font-family: var(--f-title); font-weight: var(--title-w); font-size: 34px; line-height: 1; letter-spacing: var(--title-ls);
          text-transform: var(--h3-tt); color: var(--ink); }
.t-who { margin-top: 6px; font-size: 14px; line-height: 1.3; color: var(--muted); }
.t-items { flex: 1; min-height: 0; list-style: none; margin-top: 14px; }
.t-items li { position: relative; padding-left: 1.35em; margin-bottom: .5em; line-height: 1.3; color: var(--soft); }
.t-items li::before { content: "✓"; position: absolute; left: 0; top: 0; font-weight: 700; color: var(--accent-text); }
.t-price { flex: 0 0 auto; margin-top: 10px; padding-top: 12px; border-top: 1px solid var(--line); }
.t-row { display: flex; justify-content: space-between; gap: 10px; font-size: 13.5px; line-height: 1.5; color: var(--muted); }
.t-row s { color: var(--muted); text-decoration-thickness: 1.5px; }
.t-special-lbl { margin-top: 8px; font-family: var(--f-label); font-weight: 800; font-size: 12px; letter-spacing: .14em; text-transform: uppercase; color: var(--accent-text); }
.t-special { font-family: var(--f-display); font-weight: 900; font-size: 27px; line-height: 1.1; color: var(--ink); white-space: nowrap; }
.tariff.hero .t-special { color: var(--accent-text); }
.t-note { position: absolute; left: 72px; right: 72px; bottom: 20px; font-size: 13.5px; line-height: 1.35; color: var(--muted); font-style: italic; }

/* источники */
.src-list { position: absolute; left: 72px; right: 72px; top: 186px; bottom: 40px; list-style: none; columns: 2; column-gap: 40px; }
.src-list li { break-inside: avoid; line-height: 1.38; color: var(--soft); margin-bottom: .7em; }
.src-list sup.fn { font-size: .8em; margin-right: .4em; }
"""

THEMES = {
    "timochko": {
        "brand_method": "по методике Михаила Тимочко",
        "vars": """
:root {
  --bg: #F5F0E8; --slide-bg: radial-gradient(760px 520px at 104% -8%, rgba(255,90,54,.13), transparent 62%), radial-gradient(640px 480px at -6% 112%, rgba(23,22,27,.06), transparent 60%), #F5F0E8;
  --ink: #17161B; --soft: #3A3841; --muted: #6E6875; --faint: #A69D92; --line: #E2D7C7;
  --accent: #FF5A36; --accent-text: #E4431F; --accent-soft: rgba(255,90,54,.28); --pill-ink: #FFFFFF; --num: #17161B;
  --card-bg: #FFFFFF; --card-line: #EADFD0; --card-line-strong: #E4D6C4; --card-shadow: 0 18px 40px rgba(60,40,20,.08);
  --back-bg: #EFE4D4; --back-line: #E4D6C4; --tab-shadow: rgba(255,90,54,.30);
  --res-bg: #17161B; --res-line: #17161B; --res-head: #FF7A5C; --res-ink: #F6F3EE; --res-num: #FFB39F; --res-shadow: 0 18px 40px rgba(23,22,27,.28);
  --ic-bg: #FFF0EA; --ic-line: #FFC9B8; --ic-ink: #E4431F;
  --chip-ink: #17161B; --chip-line: #17161B; --chip-bg: transparent;
  --badge-bg: #FFFFFF; --badge-line: #FF5A36; --badge-ink: #FF5A36; --badge-cap: #17161B; --badge-shadow: 0 30px 70px rgba(255,90,54,.18);
  --perk-bg: #FFFFFF; --perk-line: #EADFD0; --perk-hero-bg: #FFF4EF;
  --bar-off: #E6DCCD; --bar-done: #FFB39F;
  --name-color: #17161B; --name-size: 92px; --name-ls: -.01em; --s-title-size: 50px;
  --pattern: radial-gradient(circle, rgba(23,22,27,.16) 1.2px, transparent 1.4px); --pattern-size: 22px 22px; --pattern-op: .55;
  --f-display: 'RF Dewi Expanded', 'Avenir Next', sans-serif; --f-title: 'Akrobat', 'Avenir Next Condensed', sans-serif; --f-label: 'Akrobat', sans-serif;
  --f-body: 'Avenir Next', 'Helvetica Neue', Arial, sans-serif; --title-w: 800; --title-ls: 0; --title-tt: none; --h3-tt: none; --promise-tt: none;
}""",
    },
    "dymshakov": {
        "brand_method": "по методике Олега Дымшакова",
        "vars": """
:root {
  --bg: #0C0E11; --slide-bg: radial-gradient(820px 520px at 108% -10%, rgba(200,241,53,.13), transparent 62%), radial-gradient(700px 520px at -8% 112%, rgba(200,241,53,.06), transparent 60%), #0C0E11;
  --ink: #F4F6F8; --soft: #C9CFD8; --muted: #8C94A1; --faint: #5E6572; --line: #262B33;
  --accent: #C8F135; --accent-text: #C8F135; --accent-soft: rgba(200,241,53,.30); --pill-ink: #0C0E11; --num: #FFFFFF;
  --card-bg: #14171C; --card-line: #252A32; --card-line-strong: #2E343D; --card-shadow: 0 24px 60px rgba(0,0,0,.45);
  --back-bg: #111418; --back-line: #252A32; --tab-shadow: rgba(200,241,53,.25);
  --res-bg: #C8F135; --res-line: #C8F135; --res-head: #0C0E11; --res-ink: #0C0E11; --res-num: #0C0E11; --res-shadow: none;
  --ic-bg: rgba(200,241,53,.10); --ic-line: rgba(200,241,53,.40); --ic-ink: #C8F135;
  --chip-ink: #C8F135; --chip-line: rgba(200,241,53,.6); --chip-bg: rgba(200,241,53,.07);
  --badge-bg: #14171C; --badge-line: #C8F135; --badge-ink: #C8F135; --badge-cap: #F4F6F8; --badge-shadow: 0 0 110px rgba(200,241,53,.18);
  --perk-bg: #14171C; --perk-line: #252A32; --perk-hero-bg: rgba(200,241,53,.08);
  --bar-off: #262B33; --bar-done: rgba(200,241,53,.45);
  --name-color: #F4F6F8; --name-size: 118px; --name-ls: .01em; --s-title-size: 62px;
  --pattern: linear-gradient(rgba(255,255,255,.05) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.05) 1px, transparent 1px); --pattern-size: 40px 40px; --pattern-op: .8;
  --f-display: 'Bebas Neue Cyrillic', 'Bebas Neue', 'Akrobat', sans-serif; --f-title: 'Bebas Neue Cyrillic', 'Bebas Neue', 'Akrobat', sans-serif; --f-label: 'Akrobat', sans-serif;
  --f-body: 'Avenir Next', 'Helvetica Neue', Arial, sans-serif; --title-w: 400; --title-ls: .01em; --title-tt: uppercase; --h3-tt: uppercase; --promise-tt: none;
}
.cover-promise { font-family: 'Akrobat', sans-serif; font-weight: 800; letter-spacing: 0; }
.module.d .m-title { line-height: .98; }""",
    },
    "edinaya": {
        "brand_method": "единая программа",
        "vars": """
:root {
  --bg: #0F1115; --slide-bg: radial-gradient(820px 520px at 108% -10%, rgba(255,107,61,.16), transparent 62%), radial-gradient(700px 520px at -8% 112%, rgba(255,107,61,.07), transparent 60%), #0F1115;
  --ink: #F5F6F8; --soft: #CDD2DA; --muted: #8E96A3; --faint: #5E6572; --line: #262A31;
  --accent: #FF6B3D; --accent-text: #FF8A63; --accent-soft: rgba(255,107,61,.32); --pill-ink: #14161A; --num: #FFFFFF;
  --card-bg: #171A20; --card-line: #262B33; --card-line-strong: #30363F; --card-shadow: 0 24px 60px rgba(0,0,0,.45);
  --back-bg: #13161B; --back-line: #2A2F37; --tab-shadow: rgba(255,107,61,.28);
  --res-bg: #FF6B3D; --res-line: #FF6B3D; --res-head: #14161A; --res-ink: #14161A; --res-num: #14161A; --res-shadow: 0 18px 44px rgba(255,107,61,.22);
  --ic-bg: rgba(255,107,61,.12); --ic-line: rgba(255,107,61,.42); --ic-ink: #FF8A63;
  --chip-ink: #FF8A63; --chip-line: rgba(255,107,61,.6); --chip-bg: rgba(255,107,61,.08);
  --badge-bg: #171A20; --badge-line: #FF6B3D; --badge-ink: #FF6B3D; --badge-cap: #F5F6F8; --badge-shadow: 0 0 110px rgba(255,107,61,.20);
  --perk-bg: #171A20; --perk-line: #262B33; --perk-hero-bg: rgba(255,107,61,.10);
  --bar-off: #262A31; --bar-done: rgba(255,107,61,.5);
  --name-color: #F5F6F8; --name-size: 92px; --name-ls: -.01em; --s-title-size: 52px;
  --pattern: radial-gradient(circle, rgba(255,255,255,.10) 1.1px, transparent 1.3px); --pattern-size: 24px 24px; --pattern-op: .6;
  --f-display: 'RF Dewi Expanded', 'Avenir Next', sans-serif; --f-title: 'Akrobat', 'Avenir Next Condensed', sans-serif; --f-label: 'Akrobat', sans-serif;
  --f-body: 'Avenir Next', 'Helvetica Neue', Arial, sans-serif; --title-w: 800; --title-ls: 0; --title-tt: none; --h3-tt: none; --promise-tt: none;
}""",
    },
}


FIT_JS = """
// Каждый блок с data-fit уменьшает шрифт, пока текст не влезет. Блоки с data-spread
// потом раздают лишнее место промежуткам между пунктами.
function overflowing(el) { return el.scrollHeight > el.clientHeight + 2 || el.scrollWidth > el.clientWidth + 2; }
function fit(el, fromCurrent) {
  const min = parseFloat(el.dataset.min || '11'), max = parseFloat(el.dataset.max || '16');
  let size = fromCurrent ? parseFloat(el.style.fontSize) || max : max; el.style.fontSize = size + 'px';
  while (overflowing(el) && size > min) { size -= 0.25; el.style.fontSize = size + 'px'; }
  if (el.dataset.spread) {
    const items = [...el.querySelectorAll(el.dataset.spread)];
    let gap = 0.5;
    while (gap < 1.3 && !overflowing(el)) { gap += 0.05; items.forEach(i => { i.style.marginBottom = gap + 'em'; }); }
    if (overflowing(el)) { gap -= 0.05; items.forEach(i => { i.style.marginBottom = gap + 'em'; }); }
  }
}
document.fonts.ready.then(() => {
  // «Материалы» у Тимочко не должны заходить под рамку «Результат».
  document.querySelectorAll('.module.t').forEach(s => {
    const aside = s.querySelector('.aside'), res = s.querySelector('.result');
    fit(res);
    const room = res.getBoundingClientRect().top - aside.getBoundingClientRect().top - 12;
    aside.style.maxHeight = room + 'px';
  });
  document.querySelectorAll('[data-fit]').forEach(el => { if (!el.classList.contains('result')) fit(el, false); });
  // второй проход: соседние блоки могли поменять высоту строк сетки
  document.querySelectorAll('[data-fit]').forEach(el => { if (overflowing(el)) fit(el, true); });
  document.body.dataset.fitted = '1';
});
"""

LAYOUT_CHECK_JS = """
() => {
  const issues = [];
  document.querySelectorAll('section.slide').forEach((s, i) => {
    s.querySelectorAll('[data-fit]').forEach(el => {
      if (el.scrollHeight > el.clientHeight + 2 || el.scrollWidth > el.clientWidth + 2)
        issues.push(`слайд ${i + 1}: текст не влез в .${el.className.split(' ')[0]} (${el.scrollHeight - el.clientHeight} px) даже на минимальном шрифте`);
    });
    const sr = s.getBoundingClientRect();
    s.querySelectorAll('h1, h2, p, li, .chip, .stat, .res-tile, .seg, .lm, .perk').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width && (r.right > sr.right + 1 || r.bottom > sr.bottom + 1)) issues.push(`слайд ${i + 1}: <${el.tagName.toLowerCase()}> выходит за край слайда`);
    });
    s.querySelectorAll('.format-grid, .seg-row, .lm-row-wrap, .res-grid, .perk-grid, .t-steps, .path-grid, .res-body, .tariff-grid').forEach(g => {
      const gr = g.getBoundingClientRect();
      [...g.children].forEach(ch => { const r = ch.getBoundingClientRect(); if (r.height && r.bottom > gr.bottom + 2) issues.push(`слайд ${i + 1}: блок вылезает из .${g.className.split(' ')[0]} (${Math.round(r.bottom - gr.bottom)} px)`); });
    });
    const res = s.querySelector('.module.t .result');
    if (res) {
      const rr = res.getBoundingClientRect();
      s.querySelectorAll('.aside .mat, .aside li').forEach(m => { if (m.getBoundingClientRect().bottom > rr.top - 4) issues.push(`слайд ${i + 1}: материалы заходят под «Результат»`); });
      s.querySelectorAll('.topics-box li').forEach(li => { const r = li.getBoundingClientRect(); if (r.right > rr.left && r.bottom > rr.top) issues.push(`слайд ${i + 1}: тема под «Результатом»`); });
    }
  });
  return issues;
}
"""


def detect_theme(data: dict, forced: str | None) -> str:
    if forced:
        return forced
    label = data["cover"].get("label", "").lower()
    return "dymshakov" if "дымшаков" in label else "timochko"


def build_html(data: dict, theme: str) -> str:
    brand = data["cover"]["name"]
    parts = [("segments", data["segments"]), ("leads", data["leads"]),
             ("path", data["path"]), ("transform", data["transform"].get("a") or data["transform"]["steps"])]
    optional = [kind for kind, present in parts if present]
    tail = [kind for kind, present in (("format", data["format"] or data["perks"]),
                                       ("results", data["results"]["items"] or data["results"]["labels"]),
                                       ("tariffs", data["tariffs"]["cards"]),
                                       ("sources", data["used_fn"] & set(data["footnotes"]))) if present]
    total = 1 + len(optional) + len(data["modules"]) + len(tail)
    builders = {"segments": segments_slide, "leads": leads_slide, "path": path_slide, "transform": transform_slide,
                "format": format_slide, "results": results_slide, "tariffs": tariffs_slide,
                "sources": sources_slide}
    slides, page = [cover_slide(data, theme, total)], 1
    for kind in optional:
        page += 1
        slides.append(builders[kind](data, brand, page, total))
    for pos, mod in enumerate(data["modules"], start=1):
        page += 1
        slides.append(module_slide(mod, theme, brand, page, total, len(data["modules"]), pos))
    for kind in tail:
        page += 1
        slides.append(builders[kind](data, brand, page, total))
    css = BASE_CSS + THEMES[theme]["vars"]  # тематические правки идут после базовых правил
    title = html.escape(f"{data['cover']['name']} — программа курса")
    return (f'<!doctype html>\n<html lang="ru"><head><meta charset="utf-8"><title>{title}</title>'
            f"<style>{css}</style></head><body>{''.join(slides)}\n<script>{FIT_JS}</script></body></html>\n")


def render(html_path: Path, pdf_path: Path, previews: Path | None) -> list:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H}, device_scale_factor=2)
        page.goto(html_path.as_uri())
        page.wait_for_function("document.body.dataset.fitted === '1'", timeout=30000)
        missing = page.evaluate("""() => {
            const ctx = document.createElement('canvas').getContext('2d');
            const width = font => { ctx.font = font; return ctx.measureText('Программа курса 2026').width; };
            return ['Akrobat', 'RF Dewi Expanded', 'Avenir Next', 'Bebas Neue Cyrillic']
                .filter(f => width(`32px "${f}", monospace`) === width('32px monospace'));
        }""")
        if missing:
            print("ВНИМАНИЕ: не найдены шрифты:", ", ".join(missing))
        issues = page.evaluate(LAYOUT_CHECK_JS)
        if previews:
            previews.mkdir(parents=True, exist_ok=True)
            for i, el in enumerate(page.query_selector_all("section.slide"), start=1):
                el.screenshot(path=str(previews / f"{pdf_path.stem}-{i:02d}.png"))
        page.pdf(path=str(pdf_path), width=f"{SLIDE_W}px", height=f"{SLIDE_H}px",
                 print_background=True, prefer_css_page_size=True)
        browser.close()
    return issues


NO_FOOTNOTES_RE = re.compile(r"<!--\s*pdf:\s*без сносок\s*-->")


def strip_footnotes(text: str) -> str:
    """Для PDF без сносок: убрать значки [^n] из текста и строки с источниками. В MD они остаются."""
    text = re.sub(r"\s?\[\^\d+\](?!:)", "", text)
    return re.sub(r"^\[\^\d+\]:.*$", "", text, flags=re.M)


def build(src: Path, theme: str | None, previews: Path | None) -> int:
    text = src.read_text(encoding="utf-8")
    forced = re.search(r"<!--\s*pdf:\s*тема\s+(\w+)\s*-->", text)
    theme = theme or (forced.group(1) if forced and forced.group(1) in THEMES else None)
    if NO_FOOTNOTES_RE.search(text):
        text = strip_footnotes(text)
    data = parse_md(text)
    warnings = validate(data, src)
    chosen = detect_theme(data, theme)
    html_path, pdf_path = src.with_suffix(".html"), src.with_suffix(".pdf")
    html_path.write_text(build_html(data, chosen), encoding="utf-8")
    issues = render(html_path, pdf_path, previews)
    for w in warnings:
        print(f"  предупреждение: {w}")
    for issue in issues:
        print(f"  ВЁРСТКА: {issue}")
    print(f"{src.parent.name}/{pdf_path.name}: тема {chosen}, модулей {len(data['modules'])}, "
          f"сносок {len(data['footnotes'])}, проблем вёрстки {len(issues)}")
    return len(issues)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", nargs="*", type=Path, help="MD-файлы программ (по умолчанию обе)")
    parser.add_argument("--theme", choices=sorted(THEMES), help="принудительно выбрать тему")
    parser.add_argument("--previews", type=Path, help="папка для PNG каждого слайда")
    args = parser.parse_args()
    sources = [s if s.is_absolute() else (Path.cwd() / s) for s in args.sources] or DEFAULT_SOURCES
    problems = sum(build(src.resolve(), args.theme, args.previews) for src in sources if src.exists())
    missing = [s.name for s in sources if not s.exists()]
    if missing:
        print("Нет файлов:", ", ".join(missing))
    sys.exit(1 if problems or missing else 0)


if __name__ == "__main__":
    main()
