#!/usr/bin/env python3
"""Сводка по страницам рекламодателей из всех загрузок Meta (без сети).

Читает ~/Data/online-shkola-uz/05-razbor-konkurentov/raw/meta/{discover,brands,ad,page}/*.json.
Пишет:
  01-master/ads_seen.csv — все увиденные объявления, одна строка на объявление (последняя загрузка побеждает);
  01-master/pages.csv    — одна строка на страницу Ad Library: сигналы для порогов «денежной» школы.
Числа из поиска — нижняя граница (до 30 объявлений на запрос). Полный счёт — из загрузки страницы (колонка counter).
"""
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

import common as c

OUT_DIR = c.HERE / "01-master"
EVERGREEN_DAYS = 30
RECENT_DAYS = 30
ENGLISH_RE = re.compile(r"ingliz|english|ielts|cefr|toefl|инглиз|англий|speaking", re.I)


def creative_key(ad: dict, text: str) -> str:
    snap = ad.get("snapshot") or {}
    blocks = (snap.get("videos") or []) + (snap.get("images") or []) + (snap.get("cards") or [])
    for block in blocks:
        url = block.get("video_hd_url") or block.get("video_sd_url") or block.get("original_image_url") or block.get("resized_image_url")
        if url:
            return Path(urlsplit(url).path).name
    return "text:" + text[:120]


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        if not rows:
            return
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def load_candidates() -> dict[str, dict]:
    """library_id примера объявления → строка кандидата (имя, источник, ниша из скана 03)."""
    path = OUT_DIR / "candidates.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = {}
    for row in rows:
        match = re.search(r"id=(\d+)", row.get("example_ad") or "")
        if match:
            out[match.group(1)] = row
    return out


def main() -> None:
    ads: dict[str, dict] = {}
    keys: dict[str, str] = {}
    hits = defaultdict(set)          # page_id -> метки загрузок поиска, где страница встретилась
    counters: dict[str, dict] = {}   # page_id -> данные загрузки страницы
    candidates = load_candidates()
    candidate_of: dict[str, dict] = {}  # page_id -> кандидат, чей пример объявления привёл к странице
    for kind in ("discover", "brands", "ad", "page"):
        for load in c.load_raw(kind):
            page_top = []
            for lib_id, ad in load.get("ads", {}).items():
                row = c.flat_ad(ad, load["fetched_at"]) | {"source": kind, "load": load["label"]}
                ads[lib_id] = row
                keys[lib_id] = creative_key(ad, row["text"])
                if kind in ("discover", "brands"):
                    hits[row["page_id"]].add(load["label"])
                page_top.append(row)
            # Страница рекламодателя или страница одного объявления: обе отдают список объявлений этой страницы и счётчик.
            owner = load["label"] if kind == "page" else None
            if kind == "ad":
                owner = load["ads"].get(load["label"], {}).get("page_id")
                if not owner and page_top:  # запрошенного объявления нет в первой порции — берём страницу большинства
                    top_page, count = Counter(r["page_id"] for r in page_top).most_common(1)[0]
                    owner = top_page if count >= 0.8 * len(page_top) else None
            if owner:
                owner = str(owner)
                if kind == "ad" and load["label"] in candidates:
                    candidate_of[owner] = candidates[load["label"]]
                previous = counters.get(owner)
                if not previous or load["fetched_at"] > previous["fetched_at"]:
                    counters[owner] = {"counter": load.get("counter"), "no_results": load.get("no_results"),
                                       "fetched_at": load["fetched_at"],
                                       "top": [r for r in page_top if r["page_id"] == owner]}

    write_csv(OUT_DIR / "ads_seen.csv", list(ads.values()))

    by_page = defaultdict(list)
    for lib_id, row in ads.items():
        by_page[row["page_id"]].append(row | {"creative_key": keys[lib_id]})

    pages = []
    for page_id, rows in by_page.items():
        # У видеообъявлений текст часто пустой — доли считаем только по объявлениям, где язык и текст есть.
        langs = Counter(r["lang"] for r in rows if r["lang"] != "unknown")
        text_rows = [r for r in rows if r["text"].strip()]
        niches = Counter(n for r in text_rows for n in r["niches"].split("; ")[:1] if n and n != "без явной ниши")
        cand = candidate_of.get(page_id, {})
        socials = defaultdict(set)
        for r in rows:
            for platform, handles in json.loads(r["socials"]).items():
                socials[platform].update(h.lower() for h in handles)
        days = [r["days_running"] for r in rows if r["days_running"] != ""]
        page = counters.get(page_id, {})
        top = page.get("top", [])
        top_days = [r["days_running"] for r in top if r["days_running"] != ""]
        pages.append({
            "page_id": page_id,
            "page_name": rows[0]["page_name"],
            "page_likes": max((r["page_likes"] for r in rows if r["page_likes"] != ""), default=""),
            "page_profile_uri": rows[0]["page_profile_uri"],
            "categories": rows[0]["page_categories"],
            "ads_seen": len(rows),
            "search_hits": len(hits.get(page_id, ())),
            "unique_creatives_seen": len({r["creative_key"] for r in rows}),
            "lang_known_ads": sum(langs.values()),
            "uz_share": round(sum(v for k, v in langs.items() if k.startswith("uz")) / sum(langs.values()), 2) if langs else "",
            "text_ads": len(text_rows),
            "info_share": round(sum(1 for r in text_rows if r["info_score"] >= 1) / len(text_rows), 2) if text_rows else "",
            "niche_top": niches.most_common(1)[0][0] if niches else "без явной ниши",
            "english_ads": sum(1 for r in text_rows if ENGLISH_RE.search(r["text"])),
            "candidate_name": cand.get("name", ""),
            "candidate_source": cand.get("source", ""),
            "candidate_niche": cand.get("niche_03", ""),
            "risk_ads": sum(1 for r in rows if r["risk_flag"]),
            "evergreen_seen": sum(1 for d in days if d >= EVERGREEN_DAYS),
            "recent_seen": sum(1 for d in days if d <= RECENT_DAYS),
            "max_days_running": max(days) if days else "",
            "landing_domains": "; ".join(sorted({r["landing_domain"] for r in rows if r["landing_domain"]})),
            "instagram": "; ".join(sorted(socials.get("instagram", ()))),
            "telegram": "; ".join(sorted(socials.get("telegram", ()))),
            "youtube": "; ".join(sorted(socials.get("youtube", ()))),
            "counter": page.get("counter", ""),
            "counter_fetched_at": page.get("fetched_at", ""),
            "top30_ads": len(top),
            "top30_unique_creatives": len({keys[r["library_id"]] for r in top}),
            "top30_evergreen": sum(1 for d in top_days if d >= EVERGREEN_DAYS),
            "top30_recent": sum(1 for d in top_days if d <= RECENT_DAYS),
            "top30_formats": "; ".join(f"{k}:{v}" for k, v in Counter(r["display_format"] for r in top).most_common()),
            "example_ad": rows[0]["ad_url"],
            "search_queries": "; ".join(sorted(hits.get(page_id, ())))[:500],
        })
    pages.sort(key=lambda p: (-(p["counter"] or 0), -p["ads_seen"]))
    write_csv(OUT_DIR / "pages.csv", pages)
    print(f"ads: {len(ads)}, pages: {len(pages)}, pages with counter: {sum(1 for p in pages if p['counter'] != '')}")


if __name__ == "__main__":
    main()
