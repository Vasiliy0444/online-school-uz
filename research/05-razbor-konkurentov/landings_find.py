#!/usr/bin/env python3
"""Все публичные адреса лендингов школ из короткого списка — 8 источников, каждая попытка в журнале.

Источники:
  1 ads        — ссылки из объявлений Meta (01-master/ads_seen.csv, 02-reklama/ads_meta.csv) и Google (02-reklama/ads_google.csv)
  2 profiles   — ссылки из профилей (Instagram, мультиссылки) — ручной файл 03-lendingi/manual_links.csv
  3 telegram   — внешние ссылки каналов через t.me/s/<канал>, до 6 месяцев назад
  4 site       — robots.txt, sitemap.xml и типовые адреса (/oferta, /tolov, /narxlar, …): только GET и код ответа
  5 crtsh      — поддомены из журнала сертификатов crt.sh (один повтор при сбое)
  6 wayback    — история адресов домена, скилл web-archive-scraper (CDX, --collapse none)
  7 search     — site:-запросы в поисковике — ручной файл 03-lendingi/search_hits.csv (ищет агент через WebSearch)
  8 payment    — ссылки на оплату Payme/Click: не открываем, сумму читаем из самой ссылки
Не открываем: формы, ботов (t.me/<bot>?start=…), закрытые каналы (t.me/+…), страницы оплаты.
Запуск: python3 landings_find.py [--schools id1,id2] [--skip wayback,crtsh]
Выход: 03-lendingi/urls.csv, 03-lendingi/sources_log.csv
"""
import argparse
import base64
import csv
import json
import random
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import requests

import stage_rules

HERE = Path(__file__).resolve().parent
M, R, L = HERE / "01-master", HERE / "02-reklama", HERE / "03-lendingi"
WAYBACK = Path.home() / ".claude" / "skills" / "web-archive-scraper" / "scripts" / "search_archive.py"
UA = "Mozilla/5.0 (research; online-shkola-uz)"
SOCIAL_HOSTS = ("instagram.com", "facebook.com", "fb.me", "m.me", "wa.me", "youtube.com", "youtu.be", "tiktok.com",
                "t.me", "telegram.me", "apps.apple.com", "play.google.com", "itunes.apple.com", "l.facebook.com")
TRACKING = re.compile(r"^(utm_|fbclid|gclid|yclid|_gl$|mc_|ref$)")
TYPICAL_PATHS = ["/robots.txt", "/sitemap.xml", "/oferta", "/ommaviy-oferta", "/offer", "/public-offer", "/shartnoma",
                 "/dogovor", "/tolov", "/payment", "/narxlar", "/tariflar", "/kurslar", "/courses"]
TG_MONTHS_BACK = 6


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def normalize(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return ""
    query = urlencode([(k, v) for k, vs in parse_qs(parts.query).items() for v in vs if not TRACKING.match(k)])
    host = parts.netloc.lower().removeprefix("www.")
    return urlunsplit(("https", host, parts.path.rstrip("/") or "/", query, ""))


def payment_amount(url: str) -> str:
    """Сумма из ссылки на оплату без перехода: Payme — base64 с a=<тийины>, Click — amount=."""
    parts = urlsplit(url)
    if "paycom.uz" in parts.netloc or "payme.uz" in parts.netloc:
        token = parts.path.strip("/").split("/")[-1]
        try:
            decoded = base64.b64decode(token + "=" * (-len(token) % 4)).decode("utf-8", "replace")
            match = re.search(r"(?:^|;)a=(\d+)", decoded)
            return f"{int(match.group(1)) // 100} сум (Payme)" if match else ""
        except (ValueError, UnicodeDecodeError):
            return ""
    if "click.uz" in parts.netloc:
        amount = parse_qs(parts.query).get("amount", [""])[0]
        return f"{amount} сум (Click)" if amount else ""
    return ""


class Collector:
    def __init__(self) -> None:
        self.urls: dict[tuple[str, str], dict] = {}
        self.log: list[dict] = []

    def add(self, school: str, url: str, source: str, first_seen: str = "", last_seen: str = "") -> None:
        norm = normalize(url)
        if not norm or any(h in urlsplit(norm).netloc for h in SOCIAL_HOSTS):
            return
        key = (school, norm)
        row = self.urls.setdefault(key, {"school_id": school, "url": norm, "host": urlsplit(norm).netloc, "sources": set(),
                                         "first_seen": first_seen, "last_seen": last_seen, "payment_amount": payment_amount(norm)})
        row["sources"].add(source)
        if first_seen and (not row["first_seen"] or first_seen < row["first_seen"]):
            row["first_seen"] = first_seen
        if last_seen and last_seen > row["last_seen"]:
            row["last_seen"] = last_seen

    def note(self, school: str, method: str, query: str, found: int, comment: str = "") -> None:
        self.log.append({"school_id": school, "method": method, "query": query, "found": found, "comment": comment,
                         "at": datetime.now(timezone.utc).isoformat(timespec="seconds")})


def from_ads(col: Collector, school: dict) -> None:
    page_ids = {p.strip() for p in school["page_ids"].split(";") if p.strip()}
    rows = [r for r in read(M / "ads_seen.csv") + read(R / "ads_meta.csv") if r.get("page_id") in page_ids]
    before = len(col.urls)
    for r in rows:
        for link in (r.get("all_links") or r.get("link_url") or "").split(" | "):
            if link:
                col.add(school["school_id"], link, "ads:meta", r.get("started", ""), r.get("fetched_at", "")[:10])
    for g in read(R / "ads_google.csv"):
        if g.get("school_id") == school["school_id"] and g.get("destination_url"):
            col.add(school["school_id"], g["destination_url"], "ads:google", g.get("first_shown", ""), g.get("last_shown", ""))
    col.note(school["school_id"], "ads", f"{len(rows)} объявлений Meta", len(col.urls) - before)


def from_manual(col: Collector, school: dict, filename: str, method: str) -> None:
    rows = [r for r in read(L / filename) if r.get("school_id") == school["school_id"]]
    before = len(col.urls)
    for r in rows:
        col.add(school["school_id"], r["url"], f"{method}:{r.get('found_via') or r.get('query', '')}")
    col.note(school["school_id"], method, filename, len(col.urls) - before, "" if rows else "файла или строк нет")


def from_telegram(col: Collector, school: dict) -> None:
    handles = [s["handle"].lstrip("@") for s in read(M / "socials.csv")
               if s["school_id"] == school["school_id"] and s["platform"] == "telegram" and s["account_type"] == "канал"]
    horizon = (datetime.now(timezone.utc) - timedelta(days=30 * TG_MONTHS_BACK)).isoformat()
    for handle in handles:
        before, url, pages = len(col.urls), f"https://t.me/s/{handle}", 0
        while url and pages < 40:
            html = requests.get(url, headers={"User-Agent": UA}, timeout=30).text
            pages += 1
            dates = re.findall(r'<time datetime="([^"]+)"', html)
            for link in re.findall(r'href="(https?://[^"]+)"', html):
                if not re.match(r"https?://(t\.me|telegram\.org)", link):
                    col.add(school["school_id"], link, f"telegram:{handle}", dates[0][:10] if dates else "")
            ids = [int(x) for x in re.findall(r'data-post="[^/]+/(\d+)"', html)]
            if not ids or not dates or min(dates) < horizon:
                break
            url = f"https://t.me/s/{handle}?before={min(ids)}"
            time.sleep(random.uniform(2, 3))
        col.note(school["school_id"], "telegram", handle, len(col.urls) - before, f"страниц ленты: {pages}")


def from_site(col: Collector, school: dict, domain: str) -> None:
    before = len(col.urls)
    for path in TYPICAL_PATHS:
        try:
            resp = requests.get(f"https://{domain}{path}", headers={"User-Agent": UA}, timeout=20, allow_redirects=True)
        except requests.RequestException:
            continue
        if resp.status_code == 200:
            if path == "/robots.txt":
                for sitemap in re.findall(r"(?im)^sitemap:\s*(\S+)", resp.text):
                    col.add(school["school_id"], sitemap, "site:robots")
            elif path == "/sitemap.xml" or path.endswith(".xml"):
                for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", resp.text)[:2000]:
                    col.add(school["school_id"], loc, "site:sitemap")
            else:
                col.add(school["school_id"], resp.url, f"site:{path}")
        time.sleep(random.uniform(1, 2))
    col.note(school["school_id"], "site", domain, len(col.urls) - before)


def from_crtsh(col: Collector, school: dict, domain: str) -> None:
    rows = None
    for attempt in range(2):
        try:
            resp = requests.get("https://crt.sh/", params={"q": f"%.{domain}", "output": "json"}, headers={"User-Agent": UA}, timeout=90)
            rows = resp.json()
            break
        except (requests.RequestException, ValueError):
            time.sleep(10)
    if rows is None:
        col.note(school["school_id"], "crtsh", domain, 0, "crt.sh не ответил дважды")
        return
    hosts = {n.strip().lower() for r in rows for n in r.get("name_value", "").split("\n") if n.strip() and "*" not in n}
    before = len(col.urls)
    for host in hosts:
        col.add(school["school_id"], f"https://{host}/", "crtsh")
    col.note(school["school_id"], "crtsh", domain, len(col.urls) - before, f"сертификатов: {len(rows)}")
    time.sleep(10)


def from_wayback(col: Collector, school: dict, domain: str) -> None:
    result = subprocess.run(["python3", str(WAYBACK), "--url", domain, "--match", "domain", "--status", "200",
                             "--collapse", "none", "--limit", "5000", "--output", "json"], capture_output=True, text=True, timeout=300)
    try:
        snaps = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        col.note(school["school_id"], "wayback", domain, 0, f"ошибка: {result.stderr.strip()[-120:]}")
        return
    before = len(col.urls)
    for snap in snaps:
        if "html" in (snap.get("mime_type") or ""):
            ts = snap["timestamp"]
            col.add(school["school_id"], snap["url"], "wayback", f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}", f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}")
    col.note(school["school_id"], "wayback", domain, len(col.urls) - before, f"снимков: {len(snaps)}")
    time.sleep(5)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schools", default="")
    ap.add_argument("--skip", default="")
    ap.add_argument("--merge", action="store_true",
                    help="начать с готовых urls.csv и sources_log.csv: пропущенные через --skip источники не теряются")
    args = ap.parse_args()
    only = {s for s in args.schools.split(",") if s}
    skip = {s for s in args.skip.split(",") if s}
    col = Collector()
    if args.merge:
        for row in read(L / "urls.csv"):
            for source in row["sources"].split(" | "):
                col.add(row["school_id"], row["url"], source, row["first_seen"], row["last_seen"])
        col.log = [r for r in read(L / "sources_log.csv") if not (r["method"] == "ads" and (not only or r["school_id"] in only))]
    for school in read(M / "shortlist.csv"):
        if only and school["school_id"] not in only:
            continue
        from_ads(col, school)
        from_manual(col, school, "manual_links.csv", "profiles")
        from_manual(col, school, "search_hits.csv", "search")
        if "telegram" not in skip:
            from_telegram(col, school)
        for domain in [d.strip() for d in school.get("domains", "").split(";") if d.strip()]:
            if "site" not in skip:
                from_site(col, school, domain)
            if "crtsh" not in skip:
                from_crtsh(col, school, domain)
            if "wayback" not in skip:
                from_wayback(col, school, domain)
    L.mkdir(parents=True, exist_ok=True)
    rows = []
    for row in col.urls.values():
        stage = stage_rules.stage_from_url(row["url"]) or ""
        rows.append({**row, "sources": " | ".join(sorted(row["sources"])), "stage_auto": stage, "stage_final": "",
                     "live_status": "", "closed": "", "closed_reason": "", "snapshot_dir": ""})
    for path, data in ((L / "urls.csv", rows), (L / "sources_log.csv", col.log)):
        with path.open("w", encoding="utf-8", newline="") as fh:
            if data:
                writer = csv.DictWriter(fh, fieldnames=list(data[0].keys()))
                writer.writeheader()
                writer.writerows(data)
    print(f"urls: {len(rows)}, log entries: {len(col.log)}")


if __name__ == "__main__":
    main()
