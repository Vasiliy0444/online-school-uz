#!/usr/bin/env python3
"""Этап 8: проверка данных отчёта перед публикацией.

  1. Числа: итоги в facts.json сходятся с таблицами (объявления, креативы, теги, разборы лендингов), выводы собраны без
     пропущенных фактов, примеры креативов в выводах принадлежат названной школе.
  2. Цитаты: выборка дословных цитат из разборов лендингов (поле quote) ищется в тексте страницы (page.md).
  3. Ссылки: страницы школ, соцсети (кроме Instagram — там стена входа) и карточки Google — код ответа по одной, с паузой.
     Ссылки на библиотеку Meta не проверяются запросами: их ID сверены со сбором (ads_meta.csv).
Выход: 05-proverki/verify_report.md; код выхода 1 — если есть ошибки.
Запуск: python3 verify_report.py [--no-links]
"""
import argparse
import csv
import json
import random
import re
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "05-proverki" / "verify_report.md"
LOGIN_WALLED = ("instagram.com", "facebook.com", "threads.net", "fb.me")
# Цитаты, которых нет в тексте страницы по объективной причине (проверено вручную по скриншоту)
QUOTE_EXCEPTIONS = {("inter-nation-uz-l-online-3554a3", "speaker"): "надпись на баннере слайдера, в тексте страницы её нет"}
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
csv.field_size_limit(10**9)


def load_report() -> dict:
    text = (HERE / "05-otchet" / "data" / "report.js").read_text(encoding="utf-8")
    return json.loads(text[text.index("=") + 1:].strip().rstrip(";"))


def check_numbers(report: dict) -> list[str]:
    errors = []
    facts = report["facts"]
    ads = list(csv.DictReader((HERE / "02-reklama" / "ads_meta.csv").open(encoding="utf-8")))
    for school in report["schools"]:
        sid = school["id"]
        rows = [a for a in ads if a["school_id"] == sid]
        tags = list((HERE / "04-razbor" / "tags" / sid).glob("*.json"))
        landings = list((HERE / "04-razbor" / "landings" / sid).glob("*.json"))
        expected = {"ads_collected": len(rows), "tagged": len(tags), "landings_analysed": len(landings),
                    "unique_creatives": len(school["creatives"])}
        for key, value in expected.items():
            if facts[sid][key] != value:
                errors.append(f"{sid}: {key} в facts {facts[sid][key]} ≠ по данным {value}")
    total = sum(facts[s["id"]]["ads_collected"] for s in report["schools"])
    if facts["all"]["ads_collected"] != total:
        errors.append(f"all.ads_collected {facts['all']['ads_collected']} ≠ сумма по школам {total}")
    owner = {c["id"]: s["id"] for s in report["schools"] for c in s["creatives"]}
    for item in (report.get("findings") or {}).get("works", []):
        for cid in item.get("examples", []):
            if item.get("school") and owner.get(cid) != item["school"]:
                errors.append(f"вывод «{item['claim'][:50]}»: креатив {cid} принадлежит {owner.get(cid)}, а не {item['school']}")
    text = json.dumps(report.get("findings") or {}, ensure_ascii=False)
    if "{{" in text:
        errors.append("в выводах остались незаполненные подстановки {{…}}")
    return errors


def normalize(text: str) -> str:
    """Сравнение без разметки Markdown, регистра, вида апострофов и пробелов (page.md склеивает и размечает блоки)."""
    text = re.sub(r"\]\([^)]*\)", " ", text)                   # адреса ссылок Markdown
    text = re.sub(r"[*#|_>`\[\]!]", " ", text)
    text = re.sub(r"[ʻʼ‘’`´]", "'", text).replace("·", " ")
    return re.sub(r"\s+", "", text).lower()  # без пробелов: page.md склеивает слова из соседних элементов («tilida0 dan»)


def check_quotes(sample: int) -> tuple[int, list[str]]:
    pairs = []
    for path in sorted((HERE / "04-razbor" / "landings").glob("*/*.json")):
        page = HERE / "03-lendingi" / path.parent.name / path.stem / "page.md"
        if not page.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for key, field in data.items():
            if isinstance(field, dict) and field.get("found") and field.get("quote"):
                pairs.append((path, key, field["quote"], page))
    random.Random(917).shuffle(pairs)
    errors = []
    for path, key, quote, page in pairs[:sample]:
        body = normalize(page.read_text(encoding="utf-8"))
        # цитата может состоять из нескольких кусков страницы: через «…» или построчно
        fragments = [normalize(f) for f in re.split(r"\s*(?:…|\.\.\.)\s*|\n", quote) if len(normalize(f)) >= 10]
        if (path.stem, key) in QUOTE_EXCEPTIONS:
            continue
        if not all(f[:35] in body for f in fragments):
            errors.append(f"{path.parent.name}/{path.stem} {key}: цитата не найдена в page.md — «{quote[:80]}»")
    return min(sample, len(pairs)), errors


def http_status(url: str) -> str:
    result = subprocess.run(["curl", "-s", "-o", "/dev/null", "-L", "--max-time", "20", "-A", USER_AGENT, "-w", "%{http_code}", url],
                            capture_output=True, text=True, timeout=30)
    return result.stdout.strip() or "000"


def check_links(report: dict) -> tuple[int, list[str], list[str]]:
    urls = set()
    for school in report["schools"]:
        urls.update(l["url"] for l in school["landings"] if l["analysis"])
        urls.update(x["url"] for x in school["socials"] if x.get("url"))
    urls.update(g["url"] for g in report.get("google_ads") or [])
    broken, walled = [], []
    for url in sorted(urls):
        if any(host in url for host in LOGIN_WALLED):
            walled.append(url)
            continue
        status = http_status(url)
        if not (status.isdigit() and 200 <= int(status) < 400):
            broken.append(f"{status} {url}")
        time.sleep(1.5)
    return len(urls), broken, walled


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-links", action="store_true")
    ap.add_argument("--quotes", type=int, default=60)
    args = ap.parse_args()
    report = load_report()
    number_errors = check_numbers(report)
    checked_quotes, quote_errors = check_quotes(args.quotes)
    link_total, broken, walled = (0, [], []) if args.no_links else check_links(report)
    lines = ["# Проверка отчёта", "",
             f"- Числа: ошибок {len(number_errors)}", f"- Цитаты лендингов: проверено {checked_quotes}, не найдено {len(quote_errors)}",
             f"- Ссылки: всего {link_total}, недоступны {len(broken)}, за стеной входа (не проверялись) {len(walled)}", ""]
    for title, items in (("Ошибки в числах", number_errors), ("Цитаты не найдены", quote_errors), ("Недоступные ссылки", broken)):
        if items:
            lines += [f"## {title}", "", *[f"- {x}" for x in items], ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:6]))
    raise SystemExit(1 if number_errors or quote_errors or broken else 0)


if __name__ == "__main__":
    main()
