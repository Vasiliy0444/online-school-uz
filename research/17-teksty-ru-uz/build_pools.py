#!/usr/bin/env python3
"""Собирает 02-ТЕКСТЫ-ПУЛЫ-RU.md из pools_ru.json. Правки текстов вносить в JSON."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LABELS = (("short", "Короткий"), ("mid", "Средний"), ("long", "Лонгрид"))


def quote(text):
    return "\n".join(f"> {line}" if line else ">" for line in text.split("\n"))


def render(pool):
    pain = f" Боль: {pool['pain']}." if pool.get("pain") else ""
    out = [f"## Пул {pool['n']}. {pool['title']}", "",
           f"*{pool['status']}. Креативы: {pool['creatives']}.{pain}*", ""]
    for key, label in LABELS:
        text = pool["texts"][key]
        out += [f"**{label}** ({len(text)} знаков)", "", quote(text), ""]
    return out


def main():
    pools = json.loads((HERE / "pools_ru.json").read_text(encoding="utf-8"))["pools"]
    lines = ["# Тексты под постами УЗ — по пулам (русский)", "",
             "Метод: скиллы `таргет-тексты` и `таргет-оптимизация` из базы таргетологов. "
             "На пул — по одному тексту трёх длин. Кнопка Meta везде «Подробнее». "
             "Старые 15 текстов отложены (`01-RU-на-согласование.md`).", ""]
    for pool in pools:
        lines += render(pool)
    data = json.loads((HERE / "pools_ru.json").read_text(encoding="utf-8"))
    lines += ["## Креативы без пула", ""]
    lines += [f"- **{u['ids']}**: {u['why']}" for u in data.get("unassigned", [])]
    lines.append("")
    out = HERE / "02-ТЕКСТЫ-ПУЛЫ-RU.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"записано: {out}")


if __name__ == "__main__":
    main()
