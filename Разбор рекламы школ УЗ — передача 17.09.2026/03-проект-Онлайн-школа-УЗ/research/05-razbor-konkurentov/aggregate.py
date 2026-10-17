#!/usr/bin/env python3
"""Этап 6–7: сводные числа по разметке агентов — считает скрипт, а не агенты (без сети).

Читает: 04-razbor/tags/<school>/*.json (теги креативов), 02-reklama/creatives_unique.csv, 02-reklama/ads_meta.csv,
        04-razbor/landings/<school>/*.json (разборы лендингов), если есть.
Группы по «работает ли» (косвенные сигналы при одном снимке):
  долгожитель — идёт 60+ дней; держат — 30–59; рано судить — до 14; середина — 15–29;
  топ-10 — среди 10 первых в выдаче Meta по показам у страницы.
Пишет в 04-razbor/: shares_by_group.csv (доля тега в группе), hooks_library.csv (хуки с доказательствами и сроками),
        offers_prices.csv (цены, рассрочки, гарантии с лендингов), facts.json (числа для отчёта).
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = HERE / "04-razbor"
csv.field_size_limit(10**9)


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def tier(days: float) -> str:
    if days >= 60:
        return "долгожитель (60+ дней)"
    if days >= 30:
        return "держат (30–59 дней)"
    if days <= 14:
        return "рано судить (до 14 дней)"
    return "середина (15–29 дней)"


def tag_values(tag: dict) -> dict[str, list[str]]:
    """Плоский набор значений тегов по полям — для подсчёта долей."""
    return {
        "формат": [tag["format"]["type"]],
        "длительность": [tag["format"].get("duration_bucket", "")] if tag["format"].get("duration_bucket") else [],
        "стиль": tag.get("style", []),
        "тип хука": tag["hook"].get("types", []),
        "визуал хука": tag["hook"].get("visual", []),
        "смысл": tag["meaning"].get("main", []),
        "оффер": tag["offer"].get("items", []),
        "призыв": [tag["cta"].get("in_creative", "")],
        "куда ведёт": [tag["cta"].get("destination", "")],
        "этап воронки": [tag["cta"].get("funnel_stage", "")] if tag["cta"].get("funnel_stage") else [],
        "спикер": [tag["speaker"].get("role", "")],
        "язык": [tag.get("language", "")],
    }


LIFT_MIN_GROUP = 4  # в школе нужно хотя бы 4 размеченных креатива из топ-10 и 4 — вне его


def top10_lift(tags: list[dict]) -> list[dict]:
    """Чем креативы из топ-10 по показам отличаются от остальных размеченных — внутри каждой школы, потом среднее по школам.

    Сравнение внутри школы убирает эффект стратегии: у одних школ все креативы долгие, у других — все свежие.
    Вес школы — размер меньшей из двух групп. Сигнал слабый: групп мало, креативов в них по 4–30.
    """
    by_school = defaultdict(list)
    for tag in tags:
        by_school[tag["school_id"]].append(tag)
    acc = defaultdict(lambda: {"diff": 0.0, "weight": 0, "top": 0, "top_n": 0, "rest": 0, "rest_n": 0, "schools": 0})
    for items in by_school.values():
        top = [t for t in items if t["_rank"] <= 10]
        rest = [t for t in items if t["_rank"] > 10]
        if len(top) < LIFT_MIN_GROUP or len(rest) < LIFT_MIN_GROUP:
            continue
        weight = min(len(top), len(rest))
        values = defaultdict(set)
        for t in items:
            for field, vals in tag_values(t).items():
                values[field].update(v for v in vals if v)
        for field, vals in values.items():
            for value in vals:
                has = lambda t: value in tag_values(t)[field]  # noqa: E731
                a, b = sum(map(has, top)), sum(map(has, rest))
                row = acc[(field, value)]
                row["diff"] += (a / len(top) - b / len(rest)) * weight
                row["weight"] += weight
                row.update(top=row["top"] + a, top_n=row["top_n"] + len(top), rest=row["rest"] + b,
                           rest_n=row["rest_n"] + len(rest), schools=row["schools"] + 1)
    rows = [{"field": f, "value": v, "lift": round(r["diff"] / r["weight"], 3), "top_count": r["top"], "top_n": r["top_n"],
             "rest_count": r["rest"], "rest_n": r["rest_n"], "schools": r["schools"]} for (f, v), r in acc.items() if r["weight"]]
    return sorted(rows, key=lambda r: -abs(r["lift"]))


def main() -> None:
    creatives = {(c["school_id"], c["representative_id"]): c for c in read(HERE / "02-reklama" / "creatives_unique.csv")}
    tags, not_course = [], []
    for path in sorted((R / "tags").glob("*/*.json")):
        tag = json.loads(path.read_text(encoding="utf-8"))
        if tag.get("ad_goal") in ("найм сотрудников", "другое"):  # вакансии и прочее — не реклама обучения, в доли не входят
            not_course.append(tag["creative_id"])
            continue
        meta = creatives.get((tag["school_id"], tag["creative_id"]), {})
        tag["_days"] = num(meta.get("max_days_running"))
        tag["_rank"] = num(meta.get("best_top30_rank"), 99.0)
        tag["_ads"] = int(num(meta.get("ads"), 1))
        tags.append(tag)

    groups = defaultdict(list)
    for tag in tags:
        groups["все размеченные"].append(tag)
        groups[tier(tag["_days"])].append(tag)
        if tag["_rank"] <= 10:
            groups["топ-10 по показам"].append(tag)
        groups[f"школа: {tag['school_id']}"].append(tag)

    shares = []
    for group, items in groups.items():
        counters = defaultdict(Counter)
        for tag in items:
            for field, values in tag_values(tag).items():
                for v in set(values):
                    if v:
                        counters[field][v] += 1
        for field, counter in counters.items():
            for value, n in counter.most_common():
                shares.append({"group": group, "creatives_in_group": len(items), "field": field, "value": value,
                               "count": n, "share": round(n / len(items), 3)})
    R.mkdir(parents=True, exist_ok=True)
    with (R / "shares_by_group.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["group", "creatives_in_group", "field", "value", "count", "share"])
        writer.writeheader()
        writer.writerows(shares)

    lift = top10_lift(tags)
    with (R / "lift_top10.csv").open("w", encoding="utf-8", newline="") as fh:
        if lift:
            writer = csv.DictWriter(fh, fieldnames=list(lift[0].keys()))
            writer.writeheader()
            writer.writerows(lift)

    hooks = [{"school_id": t["school_id"], "creative_id": t["creative_id"], "days_running": int(t["_days"]),
              "top30_rank": "" if t["_rank"] == 99 else int(t["_rank"]), "ads_with_creative": t["_ads"],
              "hook": t["hook"]["verbatim"], "hook_types": "; ".join(t["hook"].get("types", [])),
              "format": t["format"]["type"], "meaning": "; ".join(t["meaning"].get("main", [])),
              "income_claim": t["meaning"].get("income_claim", ""), "revenue_claim": t["meaning"].get("revenue_claim", ""),
              "offer": "; ".join(t["offer"].get("items", [])),
              "confidence": t.get("confidence", ""),
              "ad_url": f"https://www.facebook.com/ads/library/?id={t['creative_id']}"} for t in tags]
    hooks.sort(key=lambda h: (-h["days_running"], h["top30_rank"] if h["top30_rank"] != "" else 99))
    with (R / "hooks_library.csv").open("w", encoding="utf-8", newline="") as fh:
        if hooks:
            writer = csv.DictWriter(fh, fieldnames=list(hooks[0].keys()))
            writer.writeheader()
            writer.writerows(hooks)

    offers = []
    for path in sorted((R / "landings").glob("*/*.json")):
        land = json.loads(path.read_text(encoding="utf-8"))
        for tariff in (land.get("price") or {}).get("tariffs", []) or [None]:
            offers.append({
                "school_id": land["school_id"], "url": land["url"], "stage": land["stage"], "is_archive": land.get("is_archive", False),
                "snapshot_date": land.get("snapshot_date", ""),
                "tariff": tariff["name"] if tariff else "", "price_uzs": tariff["price_uzs"] if tariff else "",
                "old_price_uzs": (tariff or {}).get("old_price_uzs", ""), "period": (tariff or {}).get("period", ""),
                "price_hidden_reason": (land.get("price") or {}).get("hidden_reason", ""),
                "installments": (land.get("installments") or {}).get("value", "") if (land.get("installments") or {}).get("found") else "",
                "guarantee": (land.get("guarantee") or {}).get("value", "") if (land.get("guarantee") or {}).get("found") else "",
                "bonuses": (land.get("bonuses") or {}).get("value", "") if (land.get("bonuses") or {}).get("found") else "",
                "deadline": (land.get("deadline") or {}).get("value", "") if (land.get("deadline") or {}).get("found") else "",
                "next_step": land.get("next_step", ""),
            })
    with (R / "offers_prices.csv").open("w", encoding="utf-8", newline="") as fh:
        if offers:
            writer = csv.DictWriter(fh, fieldnames=list(offers[0].keys()))
            writer.writeheader()
            writer.writerows(offers)

    facts = {
        "tagged_creatives": len(tags), "tagged_not_course_ads": len(not_course),
        "groups": {g: len(v) for g, v in groups.items()},
        "landings_analysed": len({(o["school_id"], o["url"]) for o in offers}),
        "landings_with_price": len({(o["school_id"], o["url"]) for o in offers if o["price_uzs"] != ""}),
        "landings_with_installments": len({(o["school_id"], o["url"]) for o in offers if o["installments"]}),
        "landings_with_guarantee": len({(o["school_id"], o["url"]) for o in offers if o["guarantee"]}),
    }
    (R / "facts_tags.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(facts, ensure_ascii=False))


if __name__ == "__main__":
    main()
