#!/usr/bin/env python3
"""Пороги «денежной» школы и короткий список (без сети).

Вход:
  01-master/schools.csv        — школа → её страницы Meta, домены, аккаунты (склейка с доказательством)
  01-master/pages.csv          — сигналы по страницам (pages_aggregate.py)
  01-master/socials.csv        — подписчики (socials.py + ручной замер Instagram), если есть
  01-master/google_counts.csv  — креативы Google в регионе UZ, если есть
Выход: 01-master/master_list.csv; shortlist.csv — список, утверждённый на воротах 1 (APPROVED), со свежими сигналами;
       shortlist_auto.csv — автоматический отбор по порогам (для сравнения, этапы 2–8 его не читают).

Пороги — из утверждённого плана (основной / запасной). Общего балла нет: порядок — реклама Meta + Google,
долгие объявления, уникальные креативы, соцсети.
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = HERE / "01-master"

MAIN = {"meta": 30, "google": 30, "both": 40, "unique": 10, "evergreen": 5, "recent": 15, "uz_share": 0.5, "followers": 20_000}
FALLBACK = {"meta": 15, "google": 15, "both": 20, "unique": 6, "evergreen": 3, "recent": 8, "uz_share": 0.5, "followers": 5_000}
EARNING = {"маркетплейсы", "маркетинг и SMM", "монтаж и видео", "ИИ", "фриланс, IT, дизайн", "заработок в целом", "бизнес и финансы"}
SHORTLIST_EARNING = (5, 8)
SHORTLIST_LANGUAGES = 2
# Ворота 1, 16.09.2026: школы выбрал Вася. Домены дописаны по сайтам школ (в schools.csv их нет или не все).
APPROVED = ["najot-talim", "qadam", "logist-academy", "it-house", "shahlo-alikhanova", "bir-group",
            "inter-nation", "englify", "hbs-academy"]
EXTRA_DOMAINS = {
    "najot-talim": ["najottalim.uz"], "qadam": ["qadam.education", "qadam.online"], "logist-academy": ["logistacademy.uz"],
    "it-house": ["ithouseedu.uz"], "shahlo-alikhanova": ["alikhanova.aicreator.academy", "aicreator.academy"],
    "bir-group": ["bir-group-webinar.vercel.app"], "inter-nation": ["inter-nation.uz"],
    "englify": ["englify.uz", "instant.englify.uz"], "hbs-academy": ["hbstrading.net"],
}


def num(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def passes(s: dict, t: dict) -> dict[str, bool]:
    volume = s["meta_active"] >= t["meta"] or s["google_uz"] >= t["google"] or s["meta_active"] + s["google_uz"] >= t["both"]
    return {
        "объём": volume,
        "не тест": s["unique_creatives"] >= t["unique"],
        "платят": s["evergreen"] >= t["evergreen"] or s["recent"] >= t["recent"],
        "узбекский": s["uz_share"] is None or s["uz_share"] >= t["uz_share"],  # None — по текстам не определить, проверим по видео
        "соцсети": s["followers_max"] >= t["followers"],
    }


def classify_school(s: dict) -> str:
    if str(s.get("track", "")).startswith("исключить"):
        return s["track"].replace("исключить", "исключено", 1)
    if s["meta_active"] == 0 and s["google_uz"] == 0:
        return "реклама не найдена на дату замера"
    if all(passes(s, MAIN).values()):
        return "денежная (основной порог)"
    if all(passes(s, FALLBACK).values()):
        return "денежная (запасной порог)"
    return "мало рекламы или тест"


def school_signals(school: dict, pages: dict, socials: list[dict], google: dict) -> dict:
    page_ids = [p for p in school["page_ids"].split(";") if p.strip()]
    rows = [pages[p.strip()] for p in page_ids if p.strip() in pages]
    meta_active = sum(num(r["counter"]) or num(r["ads_seen"]) for r in rows)
    # Язык по текстам известен не у всех страниц (у видео текст часто пустой) — считаем по тем, где известен.
    known = [(num(r["uz_share"]), num(r.get("lang_known_ads", r["ads_seen"]))) for r in rows if r["uz_share"] not in ("", None)]
    uz_share = (sum(s * w for s, w in known) / (sum(w for _, w in known) or 1)) if known else None
    followers = [num(x["followers"]) for x in socials if x["school_id"] == school["school_id"]]
    g = google.get(school["school_id"], {})
    return {
        "school_id": school["school_id"], "name": school["name"], "track": school.get("track", "заработок"),
        "niche": school.get("niche") or (rows[0]["niche_top"] if rows else ""),
        "risk": any(num(r["risk_ads"]) > 0 for r in rows) or school.get("risk", "") == "да",
        "meta_active": meta_active,
        "google_uz": num(g.get("uz_creatives_30d")),
        "unique_creatives": sum(num(r["top30_unique_creatives"]) or num(r["unique_creatives_seen"]) for r in rows) + num(g.get("uz_unique")),
        "evergreen": sum(num(r["top30_evergreen"]) or num(r["evergreen_seen"]) for r in rows),
        "recent": sum(num(r["top30_recent"]) or num(r["recent_seen"]) for r in rows),
        "uz_share": round(uz_share, 2) if uz_share is not None else None,
        "followers_max": max(followers, default=0.0),
        "page_ids": school["page_ids"], "domains": school.get("domains", ""),
        "ad_library": " | ".join(f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=UZ"
                                 f"&is_targeted_country=false&media_type=all&search_type=page&view_all_page_id={p.strip()}"
                                 for p in page_ids if p.strip()),
    }


def order_key(s: dict) -> tuple:
    return (-(s["meta_active"] + s["google_uz"]), -s["evergreen"], -s["unique_creatives"], -s["followers_max"])


def pick_shortlist(schools: list[dict]) -> list[dict]:
    chosen = []
    for track, (min_n, max_n) in (("заработок", SHORTLIST_EARNING), ("английский", (SHORTLIST_LANGUAGES, SHORTLIST_LANGUAGES))):
        pool = sorted((s for s in schools if s["track"] == track and not s["risk"]), key=order_key)
        main = [s for s in pool if s["status"] == "денежная (основной порог)"][:max_n]
        if len(main) < min_n:
            main += [s for s in pool if s["status"] == "денежная (запасной порог)"][:min_n - len(main)]
        chosen += main
    return chosen


def approved_shortlist(schools: list[dict]) -> list[dict]:
    """Утверждённый список в порядке APPROVED; домены школы + EXTRA_DOMAINS без повторов."""
    by_id = {s["school_id"]: s for s in schools}
    missing = [i for i in APPROVED if i not in by_id]
    if missing:
        raise SystemExit(f"в мастер-списке нет утверждённых школ: {missing}")
    rows = []
    for school_id in APPROVED:
        s = by_id[school_id]
        domains = [d.strip() for d in str(s["domains"]).split(";") if d.strip()] + EXTRA_DOMAINS.get(school_id, [])
        rows.append({**s, "domains": "; ".join(dict.fromkeys(domains))})
    return rows


def main() -> None:
    pages = {p["page_id"]: p for p in read(M / "pages.csv")}
    socials = read(M / "socials.csv")
    google = {g["school_id"]: g for g in read(M / "google_counts.csv")}
    schools = []
    for school in read(M / "schools.csv"):
        s = school_signals(school, pages, socials, google)
        s["status"] = classify_school(s)
        checks_main, checks_fb = passes(s, MAIN), passes(s, FALLBACK)
        s["не прошёл (основной)"] = ", ".join(k for k, v in checks_main.items() if not v)
        s["не прошёл (запасной)"] = ", ".join(k for k, v in checks_fb.items() if not v)
        schools.append(s)
    schools.sort(key=order_key)
    shortlist = pick_shortlist(schools)
    for path, rows in ((M / "master_list.csv", schools), (M / "shortlist.csv", approved_shortlist(schools)),
                       (M / "shortlist_auto.csv", shortlist)):
        with path.open("w", encoding="utf-8", newline="") as fh:
            if rows:
                writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
    print(f"schools: {len(schools)}, shortlist: {len(shortlist)}; "
          f"основной порог: {sum(s['status'].endswith('(основной порог)') for s in schools)}, "
          f"запасной: {sum(s['status'].endswith('(запасной порог)') for s in schools)}, "
          f"риск среди денежных: {sum(s['risk'] and s['status'].startswith('денежная') for s in schools)}")


if __name__ == "__main__":
    main()
