#!/usr/bin/env python3
"""Этап 4: снимки лендингов школ — текст, скриншот в ширину телефона, техника (landing-page-intel), этап воронки.

Берёт адреса из 03-lendingi/urls.csv и отбирает по школе не больше --per-school:
  1) все адреса из объявлений (источник ads:*) — они получают трафик прямо сейчас;
  2) адреса из Telegram-каналов, sitemap, типовых путей и поддомены (crt.sh);
  3) архивные адреса Wayback с признаками этапа воронки (вебинар, лид-магнит, квиз, оплата, оферта, спасибо, курс) — сначала свежие.
Живую страницу открывает headless Chromium (crawl4ai, окно 390×844, без stealth). Если страница не открывается — берёт
последний снимок из Wayback и помечает is_archive. Формы не заполняет, по ссылкам оплаты и ботов не переходит.
Выход: 03-lendingi/<school>/<slug>/{page.md, intel.json, meta.json}; скриншоты — ~/Data/.../lendingi/<school>/<slug>/.
Запуск: ~/.venvs/fb-ads-library/bin/python landings_snapshot.py [--schools qadam] [--per-school 40]
"""
import argparse
import asyncio
import base64
import csv
import hashlib
import io
import json
import random
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from PIL import Image

import stage_rules

HERE = Path(__file__).resolve().parent
L = HERE / "03-lendingi"
DATA = Path.home() / "Data" / "online-shkola-uz" / "05-razbor-konkurentov" / "lendingi"
INTEL = Path.home() / ".claude" / "skills" / "landing-page-intel" / "scripts" / "scrape_landing_page.py"
CDX = "https://web.archive.org/cdx/search/cdx"
UA = "Mozilla/5.0 (research; online-shkola-uz)"
MAX_SCREENSHOT_H = 14000
SKIP_URL = re.compile(
    r"\.(png|jpe?g|gif|svg|webp|css|js|ico|pdf|mp4|woff2?|txt|xml|json)(\?|$)|/wp-(content|includes|json|admin)/|/feed/?$|/tag/|/author/"
    r"|/_next/|%0A|/auth/|/login|/sign-?in|/hr(/|\?|$)|zoom\.us|forms\.gle|docs\.google|maps\.google|google\.com/maps"
    r"|apps\.apple\.com|play\.google\.com|wa\.me|/cart|/checkout|[?&]_rsc=", re.I)
SHORTENERS = re.compile(r"^https?://(bit\.ly|t\.co|clck\.ru|goo\.gl|tinyurl\.com|cutt\.ly|is\.gd|rb\.gy)/", re.I)
BUILDER_HOSTS = re.compile(r"(vercel\.app|tilda\.ws|netlify\.app|taplink\.(cc|ws)|lovable\.app|notion\.site|framer\.(website|ai)|"
                           r"webflow\.io|wixsite\.com|carrd\.co|linktr\.ee|hipolink\.(me|net)|mssg\.me|getcourse\.ru|"
                           r"aicreator\.academy|github\.io|pages\.dev|onrender\.com)$", re.I)
PRIORITY_STAGES = {"вебинар или мастер-класс", "лид-магнит", "квиз", "оферта или оплата", "страница спасибо", "основной продукт"}


def slug(url: str) -> str:
    parts = urlsplit(url)
    base = re.sub(r"[^a-z0-9]+", "-", (parts.netloc + parts.path).lower()).strip("-")[:60]
    return f"{base}-{hashlib.md5(url.encode()).hexdigest()[:6]}"


TECH_HOST = re.compile(r"^(api|mail|webmail|smtp|mx|ftp|cdn|static|assets|media|img|files|admin|dev|test|staging|stage|crm|cpanel|"
                       r"whm|webdisk|cpcalendars|cpcontacts|autodiscover|ns\d*|vpn|git|gitlab|jenkins|grafana|sentry|minio|s3|"
                       r"storage|db|monitor|status|auth|sso|id|accounts?|pay|payment|billing|bot|ws|socket|panel|backend|back|"
                       r"server|proxy|metrics|logs?|lms|lms-backend|mock|mock-backend|feed)[.-]", re.I)


def pick(rows: list[dict], per_school: int, school_domains: set[str] | None = None) -> list[dict]:
    """Приоритет: адреса из рекламы → страницы с этапом воронки → остальные страницы сайтов и Telegram → поддомены.

    Поддомены из crt.sh берём, только если это действительно поддомены доменов школы.
    """
    def rank(r: dict) -> tuple:
        src, stage = r["sources"], r["stage_auto"]
        is_subdomain_only = src == "crtsh"
        tier = 0 if "ads:" in src else 1 if stage in PRIORITY_STAGES else 3 if is_subdomain_only else 2
        return (tier, -(int((r["last_seen"] or "0").replace("-", "")[:8] or 0)))
    seen_paths, chosen = set(), []
    for r in sorted(rows, key=rank):
        parts = urlsplit(r["url"])
        host = parts.netloc.split(":")[0]
        key = (host, parts.path.rstrip("/"))
        own = bool(school_domains) and any(host == d or host.endswith("." + d) for d in school_domains)
        builder = bool(BUILDER_HOSTS.search(host))
        foreign_subdomain = r["sources"] == "crtsh" and bool(school_domains) and not own
        telegram_only = "telegram:" in r["sources"] and "ads:" not in r["sources"] and "site:" not in r["sources"]
        if telegram_only and not (own or builder):
            continue
        if (SKIP_URL.search(r["url"]) or r.get("payment_amount") or key in seen_paths or foreign_subdomain
                or TECH_HOST.match(host) or re.search(r"/(blog|news|yangiliklar|maqola|article)s?(/|$)", parts.path, re.I)):
            continue
        seen_paths.add(key)
        chosen.append(r)
        if len(chosen) >= per_school:
            break
    return chosen


async def render(url: str) -> dict:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

    browser = BrowserConfig(headless=True, browser_type="chromium", viewport_width=390, viewport_height=844,
                            headers={"Accept-Language": "uz,ru;q=0.8,en;q=0.6"})
    # Без прокрутки: после прокрутки вниз и обратно часть сайтов снималась подвалом. Текст страниц от этого не меняется
    # (проверено на najottalim.uz и qadam.education: та же длина page.md).
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, wait_until="load", delay_before_return_html=6, page_timeout=60000,
                           screenshot=True, force_viewport_screenshot=True, screenshot_wait_for=1.0)
    async with AsyncWebCrawler(config=browser) as crawler:
        result = await crawler.arun(url=url, config=run)
    md = result.markdown.raw_markdown if hasattr(result.markdown, "raw_markdown") else str(result.markdown or "")
    return {"status": result.status_code, "final_url": result.url, "markdown": md, "screenshot": result.screenshot,
            "title": (result.metadata or {}).get("title", ""), "success": result.success}


def latest_archive(url: str) -> str | None:
    try:
        resp = requests.get(CDX, params={"url": url, "output": "json", "filter": "statuscode:200", "limit": "-1",
                                         "fl": "timestamp,original"}, headers={"User-Agent": UA}, timeout=40)
        rows = resp.json()[1:]
    except (requests.RequestException, ValueError):
        return None
    if not rows:
        return None
    ts, original = rows[-1]
    return f"https://web.archive.org/web/{ts}id_/{original}"


def save_screenshot(b64: str | None, target: Path) -> str:
    if not b64:
        return ""
    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    if img.height > MAX_SCREENSHOT_H:
        img = img.crop((0, 0, img.width, MAX_SCREENSHOT_H))
    target.parent.mkdir(parents=True, exist_ok=True)
    img.save(target, "JPEG", quality=70)
    return str(target)


def intel(url: str) -> dict:
    parts = urlsplit(url)
    result = subprocess.run(["python3", str(INTEL), "--url", f"{parts.scheme}://{parts.netloc}", "--pages", parts.path or "/",
                             "--output", "json", "--timeout", "20"], capture_output=True, text=True, timeout=120)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": result.stderr.strip()[-200:]}


def text_digest(markdown: str) -> str:
    return hashlib.md5(re.sub(r"\s+", " ", markdown)[:8000].encode("utf-8")).hexdigest()


def reshoot(schools: set[str]) -> None:
    """Скриншот первого экрана заново — для разобранных живых снимков без дублей (page.md не трогаем)."""
    for meta_path in sorted(L.glob("*/*/meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        analysed = (HERE / "04-razbor" / "landings" / meta["school_id"] / f"{meta_path.parent.name}.json").exists()
        if ((schools and meta["school_id"] not in schools) or not analysed or meta.get("is_archive") or meta.get("duplicate_of")
                or meta.get("reshot_at") or not meta.get("screenshot")):
            continue
        try:
            page = asyncio.run(render(meta["url"]))
        except Exception as exc:
            print(f"{meta['school_id']} | ошибка {type(exc).__name__} | {meta['url'][:90]}", flush=True)
            continue
        meta.update(screenshot=save_screenshot(page["screenshot"], DATA / meta["school_id"] / meta_path.parent.name / "screenshot-mobile.jpg"),
                    reshot_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{meta['school_id']} | переснят | {meta['url'][:90]}", flush=True)
        time.sleep(random.uniform(3, 6))


def write_index() -> None:
    """Индекс строится из всех meta.json на диске (в том числе оферт), с именем папки снимка в колонке dir."""
    index = [{**json.loads(p.read_text(encoding="utf-8")), "dir": p.parent.name} for p in sorted(L.glob("*/*/meta.json"))]
    with (L / "snapshots_index.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=sorted({k for m in index for k in m}))
        writer.writeheader()
        writer.writerows(index)
    print(f"snapshots: {len(index)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schools", default="")
    ap.add_argument("--per-school", type=int, default=40)
    ap.add_argument("--index-only", action="store_true", help="без сети: собрать snapshots_index.csv из готовых meta.json")
    ap.add_argument("--reshoot", action="store_true", help="переснять только скриншоты первого экрана у готовых живых снимков")
    args = ap.parse_args()
    if args.index_only:
        write_index()
        return
    if args.reshoot:
        reshoot({s for s in args.schools.split(",") if s})
        return
    only = {s for s in args.schools.split(",") if s}
    with (L / "urls.csv").open(encoding="utf-8") as fh:
        urls = list(csv.DictReader(fh))
    with (HERE / "01-master" / "shortlist.csv").open(encoding="utf-8") as fh:
        domains = {r["school_id"]: {d.strip() for d in r["domains"].split(";") if d.strip()} for r in csv.DictReader(fh)}
    by_school: dict[str, list[dict]] = {}
    for r in urls:
        if not only or r["school_id"] in only:
            if SHORTENERS.match(r["url"]):  # короткая ссылка из Telegram: узнаём адрес назначения без перехода на него
                try:
                    location = requests.head(r["url"], headers={"User-Agent": UA}, timeout=15, allow_redirects=False).headers.get("location")
                except requests.RequestException:
                    location = None
                if not location:
                    continue
                r = {**r, "url": location, "sources": r["sources"] + f" | через {urlsplit(r['url']).netloc}"}
                time.sleep(1)
            by_school.setdefault(r["school_id"], []).append(r)
    for school, rows in by_school.items():
        text_seen: dict[str, str] = {}
        for r in pick(rows, args.per_school, domains.get(school)):
            folder = L / school / slug(r["url"])
            meta_path = folder / "meta.json"
            if meta_path.exists():
                if (folder / "page.md").exists():  # дубли ищем и среди страниц прошлых запусков
                    text_seen.setdefault(text_digest((folder / "page.md").read_text(encoding="utf-8")), r["url"])
                continue
            folder.mkdir(parents=True, exist_ok=True)
            meta = {"school_id": school, "url": r["url"], "sources": r["sources"], "first_seen": r["first_seen"],
                    "last_seen": r["last_seen"], "stage_auto_url": r["stage_auto"], "is_archive": False,
                    "snapshot_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            page = None
            try:
                page = asyncio.run(render(r["url"]))
            except Exception as exc:
                meta["render_error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
            if not page or not page["success"] or (page["status"] or 0) >= 400 or len(page["markdown"]) < 200:
                archived = latest_archive(r["url"])
                meta["live_status"] = page["status"] if page else None
                if archived:
                    try:
                        page = asyncio.run(render(archived))
                        meta.update(is_archive=True, archive_url=archived)
                    except Exception as exc:
                        meta["archive_error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
            else:
                meta["live_status"] = page["status"]
            if page:
                # Одностраничные сайты отдают главную на любой путь — одинаковый текст внутри школы считаем дублем.
                digest = text_digest(page["markdown"])
                if digest in text_seen and not meta.get("is_archive"):
                    meta.update(duplicate_of=text_seen[digest], stage_auto="дубль (тот же текст)")
                    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
                    print(f"{school} | дубль текста {text_seen[digest][:60]} | {r['url'][:80]}", flush=True)
                    time.sleep(random.uniform(2, 4))
                    continue
                text_seen.setdefault(digest, r["url"])
                (folder / "page.md").write_text(page["markdown"], encoding="utf-8")
                meta.update(final_url=page["final_url"], title=page["title"],
                            screenshot=save_screenshot(page["screenshot"], DATA / school / folder.name / "screenshot-mobile.jpg"))
                raw_prices = re.findall(r"(\d[\d\s]{4,9})\s*(?:so['‘’ʻ]?m|сум|uzs)", page["markdown"] or "", re.I)
                prices = [int(p) for p in (re.sub(r"\s", "", x) for x in raw_prices) if p.isdigit()]
                stage, reason = stage_rules.classify(r["url"], page["markdown"][:20000], min(prices) if prices else None)
                meta.update(stage_auto=stage, stage_reason=reason, text_chars=len(page["markdown"]))
            if not meta.get("is_archive"):
                (folder / "intel.json").write_text(json.dumps(intel(r["url"]), ensure_ascii=False, indent=1), encoding="utf-8")
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{school} | {meta.get('stage_auto', '—'):26} | archive={meta['is_archive']} | {r['url'][:90]}", flush=True)
            time.sleep(random.uniform(3, 6))
    write_index()


if __name__ == "__main__":
    main()
