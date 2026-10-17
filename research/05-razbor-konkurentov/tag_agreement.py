#!/usr/bin/env python3
"""Согласие двух разметок креативов: основная (04-razbor/tags) против слепой повторной (04-razbor/tags_check).

Одиночные поля — точное совпадение; списки — коэффициент Жаккара ≥ 0.5 считается согласием.
Порог приёмки плана — 80% по каждому полю. Выход: 04-razbor/tag_agreement.csv и таблица в консоли.
Запуск: python3 tag_agreement.py --make-batch 3   — порция для слепой разметки: по 3 размеченных креатива из каждой школы
        python3 tag_agreement.py                  — сравнение после того, как агент записал tags_check/
"""
import argparse
import csv
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE / "04-razbor"
SINGLE = {
    "формат": lambda t: t["format"]["type"],
    "длительность": lambda t: t["format"].get("duration_bucket", ""),
    "призыв в креативе": lambda t: t["cta"]["in_creative"],
    "куда ведёт": lambda t: t["cta"]["destination"],
    "этап воронки": lambda t: t["cta"].get("funnel_stage", ""),
    "спикер": lambda t: t["speaker"]["role"],
    "язык": lambda t: t["language"],
}
MULTI = {
    "стиль": lambda t: t["style"],
    "тип хука": lambda t: t["hook"]["types"],
    "визуал хука": lambda t: t["hook"].get("visual", []),
    "смысл": lambda t: t["meaning"]["main"],
    "оффер": lambda t: t["offer"]["items"],
}
THRESHOLD = 0.8


def jaccard(a: list, b: list) -> float:
    sa, sb = set(a), set(b)
    return 1.0 if not sa and not sb else len(sa & sb) / len(sa | sb)


def compare(main: dict, check: dict) -> dict[str, bool]:
    result = {name: get(main) == get(check) for name, get in SINGLE.items()}
    result.update({name: jaccard(get(main), get(check)) >= 0.5 for name, get in MULTI.items()})
    return result


def make_batch(per_school: int) -> None:
    """Случайные размеченные креативы (зерно 917) с теми же входными данными, что видел основной разметчик."""
    items = {}
    for path in sorted((R / "batches").glob("*.json")):
        if path.name.startswith("qc_"):
            continue
        for item in json.loads(path.read_text(encoding="utf-8")):
            items[(item["school_id"], item["creative_id"])] = item
    rng = random.Random(917)
    sample = []
    for school in sorted({s for s, _ in items}):
        tagged = [items[(school, p.stem)] for p in sorted((R / "tags" / school).glob("*.json")) if (school, p.stem) in items]
        sample += rng.sample(tagged, min(per_school, len(tagged)))
    (R / "batches" / "qc_01.json").write_text(json.dumps(sample, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"qc_01.json: {len(sample)} креативов")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-batch", type=int, default=0, help="сделать порцию для слепой разметки: креативов на школу")
    args = ap.parse_args()
    if args.make_batch:
        make_batch(args.make_batch)
        return
    pairs = []
    for check_path in sorted((R / "tags_check").glob("*/*.json")):
        main_path = R / "tags" / check_path.parent.name / check_path.name
        if main_path.exists():
            pairs.append(compare(json.loads(main_path.read_text(encoding="utf-8")), json.loads(check_path.read_text(encoding="utf-8"))))
    rows = []
    for name in [*SINGLE, *MULTI]:
        agree = sum(p[name] for p in pairs)
        share = agree / len(pairs) if pairs else 0.0
        rows.append({"field": name, "pairs": len(pairs), "agree": agree, "share": round(share, 3), "passes_80": share >= THRESHOLD})
    with (R / "tag_agreement.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        print(f"{r['field']:20} {r['agree']:>3}/{r['pairs']:<3} {r['share']:.0%} {'ок' if r['passes_80'] else 'ниже 80%'}")


if __name__ == "__main__":
    main()
