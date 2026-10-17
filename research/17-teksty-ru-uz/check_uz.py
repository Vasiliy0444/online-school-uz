#!/usr/bin/env python3
"""Механическая проверка узбекского перевода текстов по пулам против русского оригинала.

    python3 check_uz.py pools_uz_v1.json

Проверяет: структуру (6 пулов × 3 текста), кириллицу, апострофы, обращение «siz»,
абзацы и строки, эмодзи, числа и суммы, кнопку «Batafsil», разрастание длины.
Выход: 0 — ошибок нет (предупреждения возможны), 1 — есть ошибки.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEYS = ("short", "mid", "long")
EMOJI = re.compile("[⌀-⏿☀-➿\U0001f300-\U0001faff️⃣]")
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
BAD_APOSTROPHES = ("'", "`", "ʻ", "ʼ", "′")
SEN_FORMS = re.compile(r"\b(sen|senga|seni|sening|bosgin|qilgin|kelgin|ol|ko‘r)\b", re.IGNORECASE)
MAX_GROWTH = 1.45


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))["pools"]


def norm_numbers(text):
    return Counter(n.replace(",", ".") for n in NUMBER.findall(text))


def check_text(label, ru, uz, errors, warnings):
    if re.search("[А-Яа-яЁё]", uz):
        errors.append(f"{label}: кириллица в узбекском тексте")
    for ch in BAD_APOSTROPHES:
        if ch in uz:
            errors.append(f"{label}: запрещённый апостроф {ch!r}")
    if re.search("[oOgG]’", uz):
        warnings.append(f"{label}: после o/g стоит ’ (тутук) вместо ‘ — проверить: o‘/g‘")
    if SEN_FORMS.search(uz):
        warnings.append(f"{label}: возможное обращение на «sen»: {SEN_FORMS.search(uz).group(0)!r}")
    if ru.count("\n\n") != uz.count("\n\n"):
        errors.append(f"{label}: абзацев {ru.count(chr(10) * 2) + 1} → {uz.count(chr(10) * 2) + 1}")
    if ru.count("\n") != uz.count("\n"):
        errors.append(f"{label}: строк {ru.count(chr(10)) + 1} → {uz.count(chr(10)) + 1}")
    if EMOJI.findall(ru) != EMOJI.findall(uz):
        errors.append(f"{label}: эмодзи не совпадают: {''.join(EMOJI.findall(ru))} → {''.join(EMOJI.findall(uz))}")
    ru_nums, uz_nums = norm_numbers(ru), norm_numbers(uz)
    if ru_nums != uz_nums:
        errors.append(f"{label}: числа не совпадают: нет {dict(ru_nums - uz_nums)}, лишние {dict(uz_nums - ru_nums)}")
    if ru.count("«Подробнее»") != uz.count("«Batafsil»"):
        errors.append(f"{label}: кнопка «Подробнее» ×{ru.count('«Подробнее»')} → «Batafsil» ×{uz.count('«Batafsil»')}")
    growth = len(uz) / len(ru)
    if growth > MAX_GROWTH:
        warnings.append(f"{label}: узбекский длиннее русского в {growth:.2f} раза ({len(ru)} → {len(uz)})")
    return growth


def main(uz_path):
    ru_pools = load(HERE / "pools_ru.json")
    uz_pools = load(uz_path)
    errors, warnings, growths = [], [], []
    if len(ru_pools) != len(uz_pools):
        errors.append(f"пулов: русских {len(ru_pools)}, узбекских {len(uz_pools)}")
    for ru_pool, uz_pool in zip(ru_pools, uz_pools):
        for key in KEYS:
            label = f"пул {ru_pool['n']} · {key}"
            if key not in uz_pool.get("texts", {}):
                errors.append(f"{label}: нет перевода")
                continue
            growths.append(check_text(label, ru_pool["texts"][key], uz_pool["texts"][key], errors, warnings))
    for line in errors:
        print("ОШИБКА  ", line)
    for line in warnings:
        print("ВНИМАНИЕ", line)
    if growths:
        print(f"Рост длины: средний {sum(growths) / len(growths):.2f}, максимум {max(growths):.2f}")
    print(f"Итог: ошибок {len(errors)}, предупреждений {len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else HERE / "pools_uz_v1.json"))
