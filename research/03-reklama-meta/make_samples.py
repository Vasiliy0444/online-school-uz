#!/usr/bin/env python3
"""Выборки объявлений для качественного разбора (хуки, офферы, лендинги).

Запуск из этой папки после classify.py и analyze.py:
    python3 make_samples.py

Пишет в analysis/:
  sample_earning.csv    — ниши заработка: топ-15 рекламодателей ниши, до 3 разных объявлений у каждого
  sample_other.csv      — остальные ниши: топ-10 рекламодателей ниши, до 2 объявлений у каждого
  landings_to_check.csv — 20 рекламодателей со своими сайтами (не Instagram, Messenger, Telegram), по одному лендингу
"""
import csv
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "analysis"
EARNING_NICHES = ["маркетплейсы", "монтаж и видео", "маркетинг и SMM", "ИИ", "фриланс, IT, дизайн", "заработок в целом"]
NOT_OWN_SITE = ("instagram.com", "fb.me", "m.me", "facebook.com", "t.me", "telegram.me", "wa.me", "whatsapp.com",
                "play.google.com", "apps.apple.com", "ig.me")
FIELDS = ["niche", "advertiser", "advertiser_active_ads", "evergreen_30d", "days_running", "funnel_primary", "funnels",
          "cta", "landing_domain", "price_min_uzs", "income_claim_max_uzs", "risk_flag", "ad_url", "body"]


def read(name: str) -> list[dict]:
    with (HERE / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def pick(ads: list[dict], niches: list[str] | None, top_advertisers: int, per_advertiser: int) -> list[dict]:
    by_niche = defaultdict(lambda: defaultdict(list))
    for row in ads:
        by_niche[row["niche_primary"]][row["advertiser"]].append(row)
    chosen = []
    for niche in niches or sorted(by_niche):
        advertisers = sorted(by_niche[niche].items(), key=lambda kv: -len(kv[1]))[:top_advertisers]
        for name, rows in advertisers:
            seen_bodies = set()
            # Сначала самые долгие показы: они ближе всего к «рабочему» креативу.
            for row in sorted(rows, key=lambda r: -int(r["days_running"] or 0)):
                key = row["body"][:120]
                if key in seen_bodies:
                    continue
                seen_bodies.add(key)
                chosen.append({"niche": niche, "advertiser": name, "advertiser_active_ads": len(rows),
                               **{f: row[f] for f in FIELDS if f in row}})
                if len(seen_bodies) >= per_advertiser:
                    break
    return chosen


def write(name: str, rows: list[dict]) -> None:
    OUT.mkdir(exist_ok=True)
    with (OUT / name).open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ads = read("ads_uz_info.csv")
    earning = pick(ads, EARNING_NICHES, top_advertisers=15, per_advertiser=3)
    other_niches = sorted({r["niche_primary"] for r in ads} - set(EARNING_NICHES))
    other = pick(ads, other_niches, top_advertisers=10, per_advertiser=2)
    write("sample_earning.csv", earning)
    write("sample_other.csv", other)

    counts = defaultdict(int)
    for row in ads:
        counts[row["advertiser"]] += 1
    landings, seen_domains = [], set()
    for row in sorted(ads, key=lambda r: (-counts[r["advertiser"]], -int(r["days_running"] or 0))):
        domain = row["landing_domain"].lower()
        if not domain or any(bad in domain for bad in NOT_OWN_SITE) or domain in seen_domains:
            continue
        if row["advertiser"] in {l["advertiser"] for l in landings}:
            continue
        seen_domains.add(domain)
        landings.append({"niche": row["niche_primary"], "advertiser": row["advertiser"],
                         "advertiser_active_ads": counts[row["advertiser"]], "landing_url": row["landing_url"],
                         "ad_url": row["ad_url"], "funnel_primary": row["funnel_primary"], "cta": row["cta"],
                         "body": row["body"]})
        if len(landings) >= 20:
            break
    with (OUT / "landings_to_check.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(landings[0].keys()))
        writer.writeheader()
        writer.writerows(landings)
    print(f"sample_earning: {len(earning)} объявлений, sample_other: {len(other)}, landings_to_check: {len(landings)}")


if __name__ == "__main__":
    main()
