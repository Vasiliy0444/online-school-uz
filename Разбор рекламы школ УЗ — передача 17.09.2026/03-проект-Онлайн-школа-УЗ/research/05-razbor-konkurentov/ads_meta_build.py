#!/usr/bin/env python3
"""Этап 2, сборка данных Meta короткого списка (без сети).

Читает ~/Data/.../raw/meta/full/<page_id>/*.json (полные списки по курсору дат), raw/meta/gapfill/<page_id>/*.json
(добор пропущенного курсором) и загрузки этапа 1 (ad, page).
Пишет в 02-reklama/:
  ads_meta.csv            — одна строка на активное объявление: школа, страница, даты, формат, текст, ссылка, разметка,
                            top30_rank — место в первых 30 из загрузки страницы по умолчанию (сортировка Meta по показам);
  creatives_unique.csv    — одна строка на уникальный креатив (одинаковый медиафайл или текст): сколько объявлений, первый запуск, срок;
  coverage.csv            — полнота по страницам: собрано уникальных объявлений против счётчика Meta;
  stopped_since_0916.csv  — объявления этих страниц из скана 15–16.09.2026, которых нет в полном списке (слабый сигнал «выключили»).
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

import common as c
from pages_aggregate import creative_key

OUT = c.HERE / "02-reklama"
SCAN03 = c.PROJECT / "research" / "03-reklama-meta" / "ads.csv"
csv.field_size_limit(10**9)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        if rows:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    with (c.HERE / "01-master" / "shortlist.csv").open(encoding="utf-8") as fh:
        shortlist = list(csv.DictReader(fh))
    school_of = {p.strip(): s["school_id"] for s in shortlist for p in s["page_ids"].split(";") if p.strip()}

    # Место в выдаче по умолчанию (по показам) — из загрузок этапа 1: документ страницы или объявления, порядок в JSON.
    top_rank: dict[str, int] = {}
    for kind in ("page", "ad"):
        for load in c.load_raw(kind):
            ranked = [lid for lid, ad in load.get("ads", {}).items() if str(ad.get("page_id")) in school_of]
            for i, lid in enumerate(ranked, 1):
                top_rank.setdefault(lid, i)

    ads: dict[str, dict] = {}
    raw_ads: dict[str, dict] = {}
    coverage = []
    for page_id, school_id in school_of.items():
        folder = c.RAW_META / "full" / page_id
        cov_file = folder / "_coverage.json"
        cov = json.loads(cov_file.read_text(encoding="utf-8")) if cov_file.exists() else {}
        page_ads, with_copies = 0, 0
        loads = sorted(folder.glob("*.json")) + sorted((c.RAW_META / "gapfill" / page_id).glob("*.json"))  # добор после курсора
        for f in loads:
            if f.name.startswith("_"):
                continue
            load = json.loads(f.read_text(encoding="utf-8"))
            for lid, ad in load.get("ads", {}).items():
                if str(ad.get("page_id")) != page_id:
                    continue
                if lid not in ads:
                    page_ads += 1
                    with_copies += int(ad.get("collation_count") or 1)
                row = c.flat_ad(ad, load["fetched_at"])
                ads[lid] = {"school_id": school_id, **row, "top30_rank": top_rank.get(lid, "")}
                raw_ads[lid] = ad
        # Счётчик «~N results» = уникальные объявления (без копий collation_count): у 6 страниц недобор ровно равен сумме
        # превышений 30 по загрузкам курсора — Meta отдаёт в документе не больше 30 объявлений на загрузку.
        counter = cov.get("counter")
        coverage.append({"school_id": school_id, "page_id": page_id, "collected_ads": page_ads,
                         "collected_with_copies": with_copies, "meta_counter": counter or "",
                         "share": f"{min(page_ads / counter, 1):.0%}" if counter else "",
                         "notes": " | ".join(cov.get("notes", [])), "checked_at": cov.get("checked_at", "")})

    write_csv(OUT / "ads_meta.csv", list(ads.values()))
    write_csv(OUT / "coverage.csv", coverage)

    groups = defaultdict(list)
    for lid, row in ads.items():
        groups[(row["school_id"], creative_key(raw_ads[lid], row["text"]))].append(row)
    unique = []
    for (school_id, key), rows in groups.items():
        rows.sort(key=lambda r: (r["started"] or "9999", r["library_id"]))
        days = [r["days_running"] for r in rows if r["days_running"] != ""]
        starts = sorted({r["started"] for r in rows if r["started"]})
        unique.append({
            "school_id": school_id, "creative_key": key, "representative_id": rows[0]["library_id"],
            "ad_url": rows[0]["ad_url"], "ads": len(rows), "collation_max": max(int(r["collation_count"] or 1) for r in rows),
            "first_started": starts[0] if starts else "", "last_started": starts[-1] if starts else "",
            "relaunches": len(starts), "max_days_running": max(days) if days else "",
            "best_top30_rank": min((int(r["top30_rank"]) for r in rows if r["top30_rank"] != ""), default=""),
            "display_format": rows[0]["display_format"], "landing_domain": rows[0]["landing_domain"],
            "cta_text": rows[0]["cta_text"], "lang": rows[0]["lang"], "text_head": rows[0]["text"][:200],
            "library_ids": " ".join(r["library_id"] for r in rows),
        })
    unique.sort(key=lambda u: (u["school_id"], -(u["max_days_running"] or 0)))
    write_csv(OUT / "creatives_unique.csv", unique)

    stopped = []
    if SCAN03.exists():
        # В скане 03 нет page_id — сопоставляем школу по имени страницы (как в полных списках этапа 2).
        known_names = {}
        for lid, row in ads.items():
            known_names.setdefault(row["page_name"].strip().lower(), row["school_id"])
        with SCAN03.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                school_id = known_names.get((row["advertiser"] or "").strip().lower())
                if school_id and row["library_id"] not in ads:
                    stopped.append({"school_id": school_id, "library_id": row["library_id"], "ad_url": row["ad_url"],
                                    "started_03": row["started_running"], "days_running_03": row["days_running"],
                                    "text_head": (row["body"] or "")[:160]})
    write_csv(OUT / "stopped_since_0916.csv", stopped)
    print(f"ads: {len(ads)}, unique creatives: {len(unique)}, pages: {len(coverage)}, stopped since 16.09 scan: {len(stopped)}")


if __name__ == "__main__":
    main()
