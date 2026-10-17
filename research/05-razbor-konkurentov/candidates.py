#!/usr/bin/env python3
"""Черновой список кандидатов для мастер-списка (без сети).

Источники:
  - ../03-reklama-meta/advertisers.csv — рекламодатели прошлого скана: ниши заработка и бизнеса с 2+ объявлениями,
    языковые школы с 5+ (числа из скана по ключевым словам — нижняя граница);
  - ../01-brif-rynka/index.html — 19 игроков рынка;
  - ../02-blogery-zapuski/index.html — 19 блогеров, которые сами запускают курсы.
Выход: 01-master/candidates.csv (для каждого — пример объявления, если есть, чтобы найти ID страницы Ad Library).
"""
import csv
import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
OUT = HERE / "01-master" / "candidates.csv"
EARNING = {"маркетплейсы", "маркетинг и SMM", "монтаж и видео", "ИИ", "фриланс, IT, дизайн", "заработок в целом",
           "бизнес и финансы"}
MIN_ADS_EARNING = 2
MIN_ADS_LANGUAGES = 5
csv.field_size_limit(10**9)


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9а-яё]+", "", text.lower().replace("’", "'"))


def first_column(path: Path, section_id: str | None = None) -> list[str]:
    page = path.read_text(encoding="utf-8")
    if section_id:
        match = re.search(r'<section id="%s".*?</section>' % section_id, page, re.S)
        page = match.group(0) if match else page
    names = []
    for row in re.findall(r"<tr>(.*?)</tr>", page, re.S):
        cell = re.search(r'<td class="first">(.*?)</td>', row, re.S)
        if cell:
            text = html.unescape(re.sub(r"<[^>]+>", "", cell.group(1)))
            names.append(re.sub(r"\s+\d+$", "", re.sub(r"\s+", " ", text)).strip())
    return names


def main() -> None:
    advertisers = list(csv.DictReader((RESEARCH / "03-reklama-meta" / "advertisers.csv").open(encoding="utf-8")))
    by_norm = {norm(a["advertiser"]): a for a in advertisers if a["advertiser"]}
    rows: dict[str, dict] = {}

    for adv in advertisers:
        primary = adv["niches"].split("; ")[0] if adv["niches"] else ""
        ads = int(adv["active_ads"])
        if (primary in EARNING and ads >= MIN_ADS_EARNING) or (primary == "языки" and ads >= MIN_ADS_LANGUAGES):
            rows[adv["advertiser"]] = {
                "name": adv["advertiser"], "source": "скан 03", "niche_03": primary, "ads_03": ads,
                "example_ad": adv["example_ad"], "landing_domains": adv["landing_domains"], "risk_03": adv["risk_flag"],
                "search_hint": "",
            }

    external = [(n, "бриф 01") for n in first_column(RESEARCH / "01-brif-rynka" / "index.html", "players")]
    external += [(n, "блогеры 02") for n in first_column(RESEARCH / "02-blogery-zapuski" / "index.html")]
    for name, source in external:
        brand = re.sub(r"\s*\(.*?\)", "", name).strip()
        match = by_norm.get(norm(brand)) or next(
            (a for key, a in by_norm.items() if norm(brand) and (norm(brand) in key or key in norm(brand)) and len(key) > 4), None)
        if match and match["advertiser"] in rows:
            rows[match["advertiser"]]["source"] += f"; {source}"
            continue
        key = match["advertiser"] if match else brand
        rows[key] = {
            "name": key, "source": source, "niche_03": (match["niches"].split("; ")[0] if match and match["niches"] else ""),
            "ads_03": int(match["active_ads"]) if match else 0, "example_ad": match["example_ad"] if match else "",
            "landing_domains": match["landing_domains"] if match else "", "risk_03": match["risk_flag"] if match else "",
            "search_hint": "" if match else f"искать по названию: {brand}",
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows.values(), key=lambda r: (-r["ads_03"], r["name"]))
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(ordered[0].keys()))
        writer.writeheader()
        writer.writerows(ordered)
    print(f"candidates: {len(ordered)} (из скана 03: {sum(1 for r in ordered if r['source'].startswith('скан 03'))}, "
          f"только по названию: {sum(1 for r in ordered if r['search_hint'])})")


if __name__ == "__main__":
    main()
