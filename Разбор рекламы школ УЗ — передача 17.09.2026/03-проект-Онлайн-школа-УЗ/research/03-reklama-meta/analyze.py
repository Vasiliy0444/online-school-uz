#!/usr/bin/env python3
"""Сводные таблицы по размеченным объявлениям для ИТОГ.md и страницы-отчёта.

Запуск из этой папки после classify.py:
    python3 analyze.py

Читает ads_uz_info.csv и advertisers.csv, пишет в папку analysis/:
  niche_funnel_advertisers.csv — сколько рекламодателей в каждой нише использует каждый тип воронки
  funnel_share.csv             — доля рекламодателей по типу воронки
  top_advertisers_by_niche.csv — топ-8 рекламодателей каждой ниши по числу активных объявлений
  evergreen_ads.csv            — объявления, которые идут 30+ дней (по одному на рекламодателя, самое долгое)
  prices_by_niche.csv          — видимые цены курсов по нишам (медиана, минимум, максимум)
  income_claims_by_niche.csv   — обещания дохода по нишам
  landing_types.csv            — куда ведёт клик: Instagram, Telegram, Messenger, свой сайт
  cta.csv                      — кнопки объявлений
  facts.json                   — ключевые числа для текста отчёта
"""
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "analysis"
USD_TO_UZS = 11765


def read_csv(name: str) -> list[dict]:
    with (HERE / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(name: str, rows: list[dict]) -> None:
    OUT.mkdir(exist_ok=True)
    with (OUT / name).open("w", encoding="utf-8", newline="") as fh:
        if not rows:
            return
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def landing_type(domain: str) -> str:
    d = (domain or "").lower()
    if not d:
        return "нет ссылки (сообщение или форма в Meta)"
    if "instagram.com" in d or d == "ig.me":
        return "Instagram"
    if d in ("t.me", "telegram.me", "www.t.me"):
        return "Telegram"
    if d in ("fb.me", "m.me", "facebook.com", "www.facebook.com"):
        return "Facebook / Messenger"
    if d in ("wa.me", "api.whatsapp.com"):
        return "WhatsApp"
    if "play.google.com" in d or "apps.apple.com" in d:
        return "приложение"
    return "свой сайт или лендинг"


def usd(value: float) -> int:
    return round(value / USD_TO_UZS)


def main() -> None:
    ads = read_csv("ads_uz_info.csv")
    named = [row for row in ads if row["advertiser"]]  # без имени страницы — не считаем рекламодателем
    advertisers = read_csv("advertisers.csv")
    summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
    for row in ads:
        row["_landing"] = landing_type(row["landing_domain"])

    # Ниша × тип воронки: считаем рекламодателей, а не объявления — один активный школа-рекламодатель
    # с 12 копиями объявления не должен перевешивать 12 разных игроков.
    cell = defaultdict(set)
    for row in named:
        cell[(row["niche_primary"], row["funnel_primary"])].add(row["advertiser"])
    niches = sorted({n for n, _ in cell}, key=lambda n: -len({a for (nn, _), s in cell.items() if nn == n for a in s}))
    funnels = sorted({f for _, f in cell})
    matrix = []
    for niche in niches:
        line = {"niche": niche, "advertisers_total": len({a for (n, _), s in cell.items() if n == niche for a in s})}
        for funnel in funnels:
            line[funnel] = len(cell.get((niche, funnel), set()))
        matrix.append(line)
    write_csv("niche_funnel_advertisers.csv", matrix)

    adv_funnel = defaultdict(set)
    for row in named:
        for funnel in filter(None, row["funnels"].split("; ")):
            adv_funnel[funnel].add(row["advertiser"])
    total_adv = len({row["advertiser"] for row in named})
    funnel_share = sorted(({"funnel": f, "advertisers": len(s), "share_pct": round(100 * len(s) / total_adv, 1)}
                           for f, s in adv_funnel.items()), key=lambda r: -r["advertisers"])
    write_csv("funnel_share.csv", funnel_share)

    by_niche = defaultdict(list)
    for adv in advertisers:
        primary = adv["niches"].split("; ")[0] if adv["niches"] else "без явной ниши"
        by_niche[primary].append(adv)
    top_rows = []
    for niche, items in sorted(by_niche.items(), key=lambda kv: -len(kv[1])):
        for adv in sorted(items, key=lambda a: (-int(a["active_ads"]), -int(a["creatives_sum"])))[:8]:
            top_rows.append({"niche": niche, **adv})
    write_csv("top_advertisers_by_niche.csv", top_rows)

    evergreen_best = {}
    for row in named:
        if row["evergreen_30d"] != "True":
            continue
        best = evergreen_best.get(row["advertiser"])
        if best is None or int(row["days_running"]) > int(best["days_running"]):
            evergreen_best[row["advertiser"]] = row
    evergreen = sorted(evergreen_best.values(), key=lambda r: -int(r["days_running"]))
    write_csv("evergreen_ads.csv", [
        {k: r[k] for k in ("advertiser", "days_running", "started_running", "niche_primary", "funnel_primary",
                           "cta", "landing_domain", "risk_flag", "ad_url", "body")} for r in evergreen])

    prices = defaultdict(list)
    incomes = defaultdict(list)
    for row in ads:
        if row["price_min_uzs"]:
            prices[row["niche_primary"]].append(int(row["price_min_uzs"]))
        if row["income_claim_max_uzs"]:
            incomes[row["niche_primary"]].append(int(row["income_claim_max_uzs"]))
    write_csv("prices_by_niche.csv", sorted(({
        "niche": n, "ads_with_price": len(v), "median_uzs": int(statistics.median(v)), "median_usd": usd(statistics.median(v)),
        "min_uzs": min(v), "max_uzs": max(v)} for n, v in prices.items()), key=lambda r: -r["ads_with_price"]))
    write_csv("income_claims_by_niche.csv", sorted(({
        "niche": n, "ads_with_income_claim": len(v), "median_uzs": int(statistics.median(v)),
        "median_usd": usd(statistics.median(v)), "max_uzs": max(v), "max_usd": usd(max(v))}
        for n, v in incomes.items()), key=lambda r: -r["ads_with_income_claim"]))

    landing_adv = defaultdict(set)
    for row in named:
        landing_adv[row["_landing"]].add(row["advertiser"])
    write_csv("landing_types.csv", sorted(({"landing": k, "advertisers": len(v), "share_pct": round(100 * len(v) / total_adv, 1)}
                                           for k, v in landing_adv.items()), key=lambda r: -r["advertisers"]))
    # Основной канал рекламодателя — самый частый тип посадки среди его объявлений. В landing_types.csv
    # рекламодатель с объявлениями в Instagram и на сайт считается в обеих строках; здесь — один раз.
    per_adv_landing = defaultdict(Counter)
    for row in named:
        per_adv_landing[row["advertiser"]][row["_landing"]] += 1
    main_landing = Counter(counter.most_common(1)[0][0] for counter in per_adv_landing.values())
    write_csv("landing_main_by_advertiser.csv", [
        {"landing": k, "advertisers": v, "share_pct": round(100 * v / total_adv, 1)} for k, v in main_landing.most_common()])
    # «Learn More» и «Learn more» — одна и та же кнопка в разных версиях интерфейса
    cta_counts = Counter((row["cta"] or "без кнопки").capitalize() for row in ads)
    write_csv("cta.csv", [{"cta": k, "ads": v} for k, v in cta_counts.most_common()])

    facts = {
        "queries_scanned": summary["queries"],
        "cards_total": summary["cards_total"],
        "unique_ads": summary["unique_ads"],
        "uzbek_info_ads": len(ads),
        "uzbek_info_advertisers": total_adv,
        "evergreen_advertisers": len(evergreen),
        "risk_advertisers": len({r["advertiser"] for r in named if r["risk_flag"] == "True"}),
        "ads_without_advertiser_name": len(ads) - len(named),
        "ads_with_visible_price": sum(1 for r in ads if r["price_min_uzs"]),
        "ads_with_income_claim": sum(1 for r in ads if r["income_claim_max_uzs"]),
        "lang_split": dict(Counter(r["lang"] for r in ads)),
        "top_funnels": funnel_share[:6],
        "landing_types": sorted(({"landing": k, "advertisers": len(v)} for k, v in landing_adv.items()),
                                key=lambda r: -r["advertisers"]),
        "landing_main_by_advertiser": [{"landing": k, "advertisers": v} for k, v in main_landing.most_common()],
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(facts, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
