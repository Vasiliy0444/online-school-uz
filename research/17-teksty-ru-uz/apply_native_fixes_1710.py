#!/usr/bin/env python3
"""Правки носителя с креативов → тексты под постами (17.10.2026).

Силбек вычитал узбекский только на картинках (15.10 и 17.10). Те же формулировки стоят и в текстах
под постами, поэтому переносим его замены туда, чтобы подпись не спорила с картинкой:
- калька «$1000 ga chiqish» → «oyiga $1000 topish» / «ilk $1000 ni topish» (как на I2-1, I2-3, I3-1, I3-3);
- пул 9: «2 kechqurunda» → «2 kunda» (как на I1-3, I1-3B, I3-2), по-русски «за 2 вечера» → «за 2 дня».

Срочность, цены и счётчик мест не трогаем — решение Васи 17.10: «оставить как есть».
Скрипт идемпотентен: повторный запуск ничего не меняет. Подробности — pools_uz_final_pravki_1710.md.

    python3 apply_native_fixes_1710.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Порядок важен: частные замены идут раньше общих, в которые они входят.
FIXES_UZ = [
    ("ilk $1000 ga chiqish rejasi", "ilk $1000 ni topish rejasi", 1),        # P7 mid, как I3-3
    ("$1000 ga chiqish rejasi", "oyiga $1000 topish rejasi", 6),             # P1/P2/P3/P4/P7/P9 long, как I3-1
    ("noldan oyiga $1000 ga chiqish yo‘li", "noldan oyiga $1000 topish yo‘li", 1),  # P1 long
    ("oyiga $1000 ga qanday chiqiladi?", "oyiga $1000 qanday topiladi?", 1),  # P1 mid, как I2-1
    ("ilk $1000 ga qanday chiqishni", "ilk $1000 ni qanday topishni", 1),     # P3 short, как I2-3
    ("ilk $1000 ga qanday chiqish", "ilk $1000 ni qanday topish", 3),        # P3 mid, P4 mid, P6 mid
    ("2 kechqurunda yasadim", "2 kunda yasadim", 3),                         # P9 short/mid/long, как I3-2
]
FIXES_RU = [
    ("за 2 вечера", "за 2 дня", 3),                                          # P9 short/mid/long
]


def apply(texts, fixes, label):
    """texts — список строк; правит на месте, возвращает число замен."""
    total = 0
    for old, new, expected in fixes:
        found = sum(t.count(old) for t in texts)
        if found == 0 and any(new in t for t in texts):
            continue  # уже применено
        if found != expected:
            sys.exit(f"{label}: «{old}» найдено {found}, ожидалось {expected}")
        for i, t in enumerate(texts):
            texts[i] = t.replace(old, new)
        total += found
    return total


def fix_pools(path, fixes, label):
    data = json.loads(path.read_text(encoding="utf-8"))
    slots = [(pool, key) for pool in data["pools"] for key in pool["texts"]]
    texts = [pool["texts"][key] for pool, key in slots]
    n = apply(texts, fixes, label)
    for (pool, key), text in zip(slots, texts):
        pool["texts"][key] = text
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")  # формат исходника
    return n


def fix_md(path, fixes, label):
    texts = [path.read_text(encoding="utf-8")]
    n = apply(texts, fixes, label)
    path.write_text(texts[0], encoding="utf-8")
    return n


def main():
    done = {
        "pools_uz_final.json": fix_pools(HERE / "pools_uz_final.json", FIXES_UZ, "UZ"),
        "03-ТЕКСТЫ-ПУЛЫ-UZ.md": fix_md(HERE / "03-ТЕКСТЫ-ПУЛЫ-UZ.md", FIXES_UZ, "UZ md"),
        "pools_ru.json": fix_pools(HERE / "pools_ru.json", FIXES_RU, "RU"),
    }
    for name, n in done.items():
        print(f"{name}: замен {n}")
    print("Дальше: check_uz.py pools_uz_final.json, build_pools.py, build_pack_uz.py pools_uz_final.json, build_docx_silbek.py")


if __name__ == "__main__":
    main()
