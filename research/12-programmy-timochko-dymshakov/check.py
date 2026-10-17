#!/usr/bin/env python3
"""Проверяет программы курса по требованиям Васи.

Ошибки (скрипт завершится с кодом 1):
- модулей больше 9 или нумерация сбита; у модуля нет содержания, материалов или результата
  (у Дымшакова — ещё заданий);
- в «Карте болей» нет какой-то боли из 00-boli-ca.md или у неё пустое «Где закрываем»;
- карта ссылается на модуль, которого нет;
- в продающей части есть запрещённые слова;
- сноска [^n] без источника или источник без сноски.
Предупреждения — на ручную проверку: длина полей для слайда, цифры про деньги без сноски,
боли веры, которые закрыты только оффером.

Запуск:
    python3 check.py                                  # обе программы
    python3 check.py dymshakov/programma-dymshakov.md # одна
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

from render import DEFAULT_SOURCES, parse_md

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "00-boli-ca.md"
BANNED = ("пассивн", "процент в день", "процентов в день", "лёгкие деньги", "легкие деньги",
          "гарантируем доход", "гарантия дохода", "лучший", "уникальн", "роботы")
LIMITS = {"title": 55, "topic": 110, "task": 100, "material": 70, "result": 230}
MONEY_RE = re.compile(r"(\$\s?\d|\d\s?\$|\d[\d\s,.–-]*\s?(?:млн|тыс\.?)?\s?сум|\d+\s?%)")
PLACE_KINDS = (("М", r"\bМ\d"), ("лид-магнит", r"\bЛМ\b"), ("формат", r"Формат"),
               ("фишка/бонус", r"Фишк|Бонус"), ("для кого", r"Для кого"),
               ("путь/трансформация", r"Путь|Трансформац"), ("обложка", r"Обложк"),
               ("итог", r"Итог|Главные результаты|Результат результатов"),
               ("решения за Васей", r"Решения за Васей"), ("вне программы", r"[Вв]не программы"),
               ("тарифы", r"Тариф"))


def registry_ids(text: str) -> tuple[list, set]:
    ids = re.findall(r"^\| (Б\d\d) \|", text, flags=re.M)
    belief_part = text.split("## Боли веры", 1)[1].split("\n## ", 1)[0] if "## Боли веры" in text else ""
    belief = {pid for bold in re.findall(r"\*\*([^*]+)\*\*", belief_part) for pid in re.findall(r"Б\d\d", bold)}
    return ids, belief


def section(text: str, title_start: str) -> str:
    m = re.search(rf"^## {re.escape(title_start)}.*?$(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    return m.group(1) if m else ""


def pain_rows(appendix: str) -> dict:
    rows = {}
    for line in appendix.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and re.fullmatch(r"Б\d\d", cells[0]):
            rows.setdefault(cells[0], []).append(cells)
    return rows


def check_program(path: Path, ids: list, belief: set) -> tuple[list, list, Counter]:
    text = path.read_text(encoding="utf-8")
    data = parse_md(text)
    errors, warnings, kinds = [], [], Counter()
    is_d = "дымшаков" in data["cover"].get("label", "").lower()
    mods = data["modules"]

    if not 1 <= len(mods) <= 9:
        errors.append(f"модулей {len(mods)} — нужно от 1 до 9")
    first = mods[0]["n"] if mods else 1
    for i, mod in enumerate(mods, start=first):
        if first not in (0, 1) or mod["n"] != i:
            errors.append(f"нумерация модулей: ожидался {i}, стоит {mod['n']}")
        parts = [("topics", "содержание модуля"), ("materials", "материалы"), ("result", "результат после модуля")]
        if is_d:
            parts.append(("tasks", "задания"))
        for key, name in parts:
            if not mod[key]:
                errors.append(f"Модуль {mod['n']}: нет «{name}»")
        if not is_d and not mod["week"]:
            warnings.append(f"Модуль {mod['n']}: нет строки «Неделя»")
        if len(mod["title"]) > LIMITS["title"]:
            warnings.append(f"Модуль {mod['n']}: название {len(mod['title'])} знаков (> {LIMITS['title']})")
        for key, limit_key in (("topics", "topic"), ("tasks", "task"), ("materials", "material")):
            for item in mod[key]:
                if len(item) > LIMITS[limit_key]:
                    warnings.append(f"Модуль {mod['n']}: {limit_key} {len(item)} знаков — «{item[:50]}…»")
        if len(mod["result"]) > LIMITS["result"]:
            warnings.append(f"Модуль {mod['n']}: результат {len(mod['result'])} знаков (> {LIMITS['result']})")

    appendix = section(text, "Приложение")
    if not appendix:
        errors.append("нет раздела «## Приложение. Карта болей → где закрываем»")
    rows = pain_rows(appendix)
    for pid in ids:
        if pid not in rows:
            errors.append(f"{pid}: нет в карте болей")
            continue
        if len(rows[pid]) > 1:
            warnings.append(f"{pid}: встречается в карте {len(rows[pid])} раза")
        cells = rows[pid][0]
        where = cells[2] if len(cells) > 2 else ""
        if not where or where in ("—", "-", "–"):
            errors.append(f"{pid}: пустое «Где закрываем»")
            continue
        for mref in re.findall(r"\bМ(\d)", where):
            if int(mref) > len(mods):
                errors.append(f"{pid}: ссылка на М{mref}, а модулей {len(mods)}")
        found = [kind for kind, rx in PLACE_KINDS if re.search(rx, where)]
        kinds.update(found or ["другое"])
        if pid in belief and found == ["решения за Васей"]:
            warnings.append(f"{pid} — боль веры, но закрыта только решением за Васей")
    extra = sorted(set(rows) - set(ids))
    if extra:
        warnings.append(f"в карте есть номера, которых нет в реестре: {', '.join(extra)}")

    sales = text.split("## Приложение", 1)[0]
    sales_plain = re.sub(r"<!--.*?-->", "", sales, flags=re.S)
    low = sales_plain.lower()
    for word in BANNED:
        if word in low:
            line = next(ln for ln in sales_plain.splitlines() if word in ln.lower())
            errors.append(f"запрещённое слово «{word}»: «{line.strip()[:90]}»")

    used = set(re.findall(r"\[\^(\d+)\](?!:)", text))
    defined = set(re.findall(r"^\[\^(\d+)\]:", text, flags=re.M))
    for n in sorted(used - defined, key=int):
        errors.append(f"сноска [^{n}] без источника")
    for n in sorted(defined - used, key=int):
        errors.append(f"источник [^{n}] не упомянут в тексте")

    for ln in sales_plain.splitlines():
        s = ln.strip()
        if not s or s.startswith(("[^", "#", "|")):
            continue
        if MONEY_RE.search(s) and "[^" not in s and "не проверено" not in s.lower():
            warnings.append(f"цифра про деньги без сноски: «{s[:90]}»")
    return errors, warnings, kinds


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", nargs="*", type=Path)
    args = parser.parse_args()
    ids, belief = registry_ids(REGISTRY.read_text(encoding="utf-8"))
    sources = [s if s.is_absolute() else Path.cwd() / s for s in args.sources] or DEFAULT_SOURCES
    total_errors = 0
    print(f"Реестр болей: {len(ids)} (боли веры: {', '.join(sorted(belief))})")
    for src in sources:
        if not src.exists():
            print(f"\n{src.name}: файла нет")
            total_errors += 1
            continue
        errors, warnings, kinds = check_program(src, ids, belief)
        total_errors += len(errors)
        print(f"\n{src.parent.name}/{src.name}: ошибок {len(errors)}, предупреждений {len(warnings)}")
        print("  где закрыты боли: " + ", ".join(f"{k} — {v}" for k, v in kinds.most_common()))
        for e in errors:
            print(f"  ОШИБКА: {e}")
        for w in warnings:
            print(f"  проверить: {w}")
    sys.exit(1 if total_errors else 0)


if __name__ == "__main__":
    main()
