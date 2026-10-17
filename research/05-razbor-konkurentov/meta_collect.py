#!/usr/bin/env python3
"""Сбор объявлений из Meta Ad Library настоящим браузером — без прокрутки и без обхода защиты.

Как работает (проверено на пилоте 16.09.2026, см. 00-pilot/):
  - headless Chromium через crawl4ai, как в прошлом скане; stealth, подмена navigator, куки и прокси не используются;
  - Meta отдаёт первые 30 объявлений прямо в документе страницы (JSON внутри <script type="application/json">)
    вместе с page_id, датами, числом копий креатива, платформами и ссылками на картинки и видео;
  - счётчик «~N results» читается из текста страницы;
  - прокрутку не делаем: догрузка через /api/graphql/ при быстрой прокрутке упёрлась в «Rate limit exceeded».
    Если в ответах страницы встречается этот лимит — скрипт сразу останавливается.

Режимы:
  discover  — поиск по ключевым словам (keywords из ../03-reklama-meta/keywords.csv): кто рекламируется, ID страниц Ad Library
  brands    — поиск по названиям школ, которых нет в прошлом скане (01-master/candidates.csv, колонка search_hint)
  ad        — страница одного объявления: page_id рекламодателя, если его не дал поиск
  page      — страница рекламодателя: счётчик активных объявлений и 30 самых показываемых (сортировка Meta по показам)

Запуск (окружение прошлого скана):
  ~/.venvs/fb-ads-library/bin/python meta_collect.py discover --limit 3
  ~/.venvs/fb-ads-library/bin/python meta_collect.py page --page-ids 111238895346791,...
Результат: сырые файлы в ~/Data/online-shkola-uz/05-razbor-konkurentov/raw/meta/<режим>/, журнал — logs/meta_collect.log.
Скрипт продолжает с места остановки: уже собранные файлы пропускаются.
"""
import argparse
import asyncio
import csv
import hashlib
import json
import random
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
KEYWORDS = PROJECT / "research" / "03-reklama-meta" / "keywords.csv"
DATA = Path.home() / "Data" / "online-shkola-uz" / "05-razbor-konkurentov"
RAW = DATA / "raw" / "meta"
LOG = DATA / "logs" / "meta_collect.log"

ACCEPT_LANGUAGE = "en-US,en;q=0.9"
COUNTRY = "UZ"
SKIP_GROUPS = {"remesla-byuti", "drugoe"}          # не ниши заработка
PAUSE_RANGE = (25, 45)                             # секунд между загрузками страниц
RATE_LIMIT_MARK = "Rate limit exceeded"
MAX_EMPTY_STREAK = 3                               # столько пустых ответов подряд → стоп
SCRIPT_JSON_RE = re.compile(r'<script type="application/json"[^>]*>(.*?)</script>', re.S)
RESULTS_RE = re.compile(r"~?\s?([\d,]+)\s+results?\b")
NO_RESULTS = "No ads match your search criteria"


class RateLimited(RuntimeError):
    """Meta ответила «Rate limit exceeded» — дальше не идём."""


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def library_url(**params: str) -> str:
    base = {"active_status": "active", "ad_type": "all", "country": COUNTRY,
            "is_targeted_country": "false", "media_type": "all"}
    return "https://www.facebook.com/ads/library/?" + urlencode({**base, **params})


def keyword_url(query: str) -> str:
    return library_url(q=query, search_type="keyword_unordered")


def page_url(page_id: str) -> str:
    return library_url(search_type="page", view_all_page_id=page_id)


def slug(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "q"
    return f"{base}-{hashlib.md5(text.encode('utf-8')).hexdigest()[:6]}"


def json_payloads(text: str) -> list:
    """JSON-документы из HTML (<script type=application/json>) или из построчного ответа graphql."""
    blocks = SCRIPT_JSON_RE.findall(text) if "<html" in text[:2000].lower() else [text]
    found = []
    for block in blocks:
        for line in block.splitlines() or [block]:
            line = line.strip().removeprefix("for (;;);")
            if not line or line[0] not in "[{":
                continue
            try:
                found.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return found


def collect_ads(node, sink: dict) -> None:
    """Все объекты объявлений (у них есть ad_archive_id и snapshot) — рекурсивно."""
    if isinstance(node, dict):
        if "ad_archive_id" in node and isinstance(node.get("snapshot"), dict):
            sink.setdefault(str(node["ad_archive_id"]), node)
        for value in node.values():
            collect_ads(value, sink)
    elif isinstance(node, list):
        for value in node:
            collect_ads(value, sink)


async def render(url: str) -> dict:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

    browser = BrowserConfig(headless=True, browser_type="chromium", viewport_width=1400, viewport_height=1600,
                            headers={"Accept-Language": ACCEPT_LANGUAGE})
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, delay_before_return_html=6, page_timeout=90000,
                           js_code=["await new Promise(r=>setTimeout(r,8000));"], locale="en-US",
                           timezone_id="Asia/Tashkent", capture_network_requests=True)
    async with AsyncWebCrawler(config=browser) as crawler:
        result = await crawler.arun(url=url, config=run)
    md = result.markdown.raw_markdown if hasattr(result.markdown, "raw_markdown") else str(result.markdown or "")
    return {"status_code": result.status_code, "markdown": md, "network": result.network_requests or []}


def fetch(url: str) -> dict:
    """Одна загрузка страницы: объявления из документа, счётчик, признаки лимита."""
    data = asyncio.run(render(url))
    ads: dict = {}
    graphql_errors = []
    for event in data["network"]:
        if event.get("event_type") != "response":
            continue
        body = ((event.get("body") or {}).get("text")) or ""
        if RATE_LIMIT_MARK in body:
            graphql_errors.append(body[:200])
        if "ad_archive_id" in body and ("<html" in body[:2000].lower() or "/api/graphql" in event.get("url", "")):
            for payload in json_payloads(body):
                collect_ads(payload, ads)
    counter = RESULTS_RE.search(data["markdown"])
    return {
        "url": url, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status_code": data["status_code"], "counter_text": counter.group(0) if counter else None,
        "counter": int(counter.group(1).replace(",", "")) if counter else None,
        "no_results": NO_RESULTS in data["markdown"], "rate_limited": bool(graphql_errors),
        "ads": ads,
    }


def load_keywords(limit: int | None) -> list[dict]:
    with KEYWORDS.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["group"] not in SKIP_GROUPS]
    return rows[:limit] if limit else rows


def run_jobs(jobs: list[tuple[str, str, Path]]) -> None:
    """jobs: (метка, url, файл). Пропускает готовые файлы, делает паузы, стоп на лимите и серии пустых ответов."""
    empty_streak = 0
    todo = [j for j in jobs if not j[2].exists()]
    log(f"start: {len(jobs)} jobs, {len(jobs) - len(todo)} already done, {len(todo)} to fetch")
    for i, (label, url, target) in enumerate(todo, 1):
        started = time.time()
        try:
            result = fetch(url)
        except Exception as exc:  # сеть, таймаут браузера — записываем и идём дальше
            log(f"[{i}/{len(todo)}] {label}: error {type(exc).__name__}: {str(exc)[:200]}")
            empty_streak += 1
        else:
            if result["rate_limited"]:
                log(f"[{i}/{len(todo)}] {label}: RATE LIMIT — stop, nothing saved for this job")
                raise RateLimited(label)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"label": label, **result}, ensure_ascii=False), encoding="utf-8")
            n = len(result["ads"])
            log(f"[{i}/{len(todo)}] {label}: status={result['status_code']} ads={n} counter={result['counter_text']} "
                f"no_results={result['no_results']} {round(time.time() - started)}s")
            empty_streak = 0 if (n or result["no_results"]) else empty_streak + 1
        if empty_streak >= MAX_EMPTY_STREAK:
            log(f"stop: {MAX_EMPTY_STREAK} empty or failed responses in a row")
            sys.exit(2)
        if i < len(todo):
            time.sleep(random.uniform(*PAUSE_RANGE))
    log("done")


PAGE_CAP = 30  # столько объявлений приходит в документе без прокрутки


def month_windows(first: date, last: date) -> list[tuple[date, date]]:
    windows, cursor = [], first.replace(day=1)
    while cursor <= last:
        nxt = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
        windows.append((cursor, min(nxt - timedelta(days=1), last)))
        cursor = nxt
    return windows


def run_windows(page_id: str, first_month: str) -> None:
    """Все активные объявления страницы окнами по датам: окно со счётчиком > 30 делится пополам.

    Фильтр Meta start_date[min]/[max] не делит строго по дате запуска (пилот 16.09.2026), поэтому
    в конце — сверка объединения окон с общим счётчиком страницы (raw/meta/page/<page_id>.json).
    """
    folder = RAW / "windows" / page_id
    queue = month_windows(date.fromisoformat(first_month + "-01"), date.today())
    empty_streak, fetched = 0, 0
    union: dict = {}
    log(f"windows {page_id}: {len(queue)} month windows from {first_month}")
    while queue:
        lo, hi = queue.pop(0)
        target = folder / f"{lo.isoformat()}_{hi.isoformat()}.json"
        if target.exists():
            result = json.loads(target.read_text(encoding="utf-8"))
        else:
            if fetched:
                time.sleep(random.uniform(*PAUSE_RANGE))
            url = library_url(search_type="page", view_all_page_id=page_id,
                              **{"start_date[min]": lo.isoformat(), "start_date[max]": hi.isoformat()})
            try:
                result = fetch(url)
            except Exception as exc:
                log(f"windows {page_id} {lo}..{hi}: error {type(exc).__name__}: {str(exc)[:200]}")
                empty_streak += 1
                if empty_streak >= MAX_EMPTY_STREAK:
                    log("stop: too many errors in a row")
                    sys.exit(2)
                continue
            fetched += 1
            if result["rate_limited"]:
                log(f"windows {page_id} {lo}..{hi}: RATE LIMIT — stop")
                raise RateLimited(page_id)
            folder.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({"label": f"{page_id} {lo}..{hi}", **result}, ensure_ascii=False), encoding="utf-8")
            n = len(result["ads"])
            empty_streak = 0 if (n or result["no_results"]) else empty_streak + 1
            log(f"windows {page_id} {lo}..{hi}: ads={n} counter={result['counter_text']} no_results={result['no_results']}")
        union.update(result["ads"])
        if (result.get("counter") or 0) > PAGE_CAP and hi > lo:
            mid = lo + (hi - lo) // 2
            queue[:0] = [(lo, mid), (mid + timedelta(days=1), hi)]
    page_file = RAW / "page" / f"{page_id}.json"
    total = json.loads(page_file.read_text(encoding="utf-8")).get("counter") if page_file.exists() else None
    if total is None and (HERE / "01-master" / "pages.csv").exists():
        with (HERE / "01-master" / "pages.csv").open(encoding="utf-8") as fh:
            row = next((r for r in csv.DictReader(fh) if r["page_id"] == page_id), None)
        total = int(float(row["counter"])) if row and row.get("counter") else None
    (folder / "_coverage.json").write_text(json.dumps({"page_id": page_id, "unique_ads": len(union), "counter": total,
                                                       "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}),
                                          encoding="utf-8")
    coverage = f"{len(union)}/{total} = {len(union) / total:.0%}" if total else f"{len(union)} (общего счётчика нет)"
    log(f"windows {page_id}: done, unique ads {coverage}")


GROUPED_SORT = {"sort_data[mode]": "relevancy_monthly_grouped", "sort_data[direction]": "desc"}
EARLIEST = "2015-01-01"


def start_day(ad: dict) -> str:
    return datetime.fromtimestamp(ad["start_date"], timezone(timedelta(hours=5))).date().isoformat()


def next_cursor(batch: dict, cursor: str) -> tuple[str | None, str]:
    """Следующая верхняя граница даты запуска после порции (или None — список закончился) и пометка.

    С сортировкой relevancy_monthly_grouped и фильтром start_date[max] Meta отдаёт объявления, запущенные не позже
    границы, от новых к старым — но в документе только одну группу-месяц, не больше 30 объявлений (16.09.2026:
    у Shahlo Alikhanova 15 сентябрьских объявлений при счётчике ~120). Поэтому:
      - порция из 30 — месяц мог обрезаться: следующая граница = дата самого старого в порции;
        если все 30 запущены в один день — на день раньше, с пометкой о возможном пропуске;
      - порция меньше 30 — месяц пришёл целиком: следующая граница = последний день предыдущего месяца;
      - пустая порция — объявлений раньше границы нет, список закончился.
    """
    dated = [start_day(a) for a in batch.values() if a.get("start_date")]
    if not dated:
        return None, "конец списка"
    oldest = min(dated)
    if len(batch) < PAGE_CAP:
        first_of_month = date.fromisoformat(oldest).replace(day=1)
        previous = (first_of_month - timedelta(days=1)).isoformat()
        return (previous, "") if previous >= EARLIEST else (None, "конец списка")
    if oldest < cursor:
        return oldest, ""
    earlier = (date.fromisoformat(oldest) - timedelta(days=1)).isoformat()
    return earlier, f"больше {PAGE_CAP} объявлений запущены {oldest} — часть могла не попасть"


def run_full(page_id: str) -> None:
    """Все активные объявления страницы: курсор по дате запуска, по 30 объявлений за загрузку, без прокрутки."""
    folder = RAW / "full" / page_id
    folder.mkdir(parents=True, exist_ok=True)
    cursor = date.today().isoformat()
    union: dict = {}
    total = None
    notes = []
    fetched = 0
    empty_streak = 0
    while cursor:
        target = folder / f"{cursor}.json"
        if target.exists():
            result = json.loads(target.read_text(encoding="utf-8"))
        else:
            if fetched:
                time.sleep(random.uniform(*PAUSE_RANGE))
            url = library_url(search_type="page", view_all_page_id=page_id,
                              **{"start_date[min]": EARLIEST, "start_date[max]": cursor}, **GROUPED_SORT)
            try:
                result = fetch(url)
            except Exception as exc:
                log(f"full {page_id} ≤{cursor}: error {type(exc).__name__}: {str(exc)[:160]}")
                empty_streak += 1
                if empty_streak >= MAX_EMPTY_STREAK:
                    log("stop: too many errors in a row")
                    sys.exit(2)
                continue
            fetched += 1
            if result["rate_limited"]:
                log(f"full {page_id} ≤{cursor}: RATE LIMIT — stop")
                raise RateLimited(page_id)
            if not result["ads"] and not result["no_results"]:
                empty_streak += 1
                log(f"full {page_id} ≤{cursor}: empty response ({empty_streak}/{MAX_EMPTY_STREAK})")
                if empty_streak >= MAX_EMPTY_STREAK:
                    log("stop: empty responses in a row")
                    sys.exit(2)
                continue
            empty_streak = 0
            target.write_text(json.dumps({"label": f"{page_id} ≤{cursor}", **result}, ensure_ascii=False), encoding="utf-8")
            log(f"full {page_id} ≤{cursor}: ads={len(result['ads'])} counter={result['counter_text']}")
        if total is None:
            total = result.get("counter")
        before = len(union)
        union.update(result["ads"])
        cursor_next, note = next_cursor(result["ads"], cursor)
        if note and cursor_next:
            notes.append(note)
        if cursor_next and len(union) == before:
            notes.append(f"порция ≤{cursor} не добавила новых объявлений — остановка")
            break
        cursor = cursor_next
    coverage = {"page_id": page_id, "unique_ads": len(union), "counter": total, "notes": notes,
                "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (folder / "_coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=1), encoding="utf-8")
    share = f"{len(union) / total:.0%}" if total else "—"
    log(f"full {page_id}: done, unique ads {len(union)} of ~{total} ({share}); notes: {len(notes)}")


def cached_full(page_id: str) -> tuple[dict, dict[str, int], int]:
    """Все объявления страницы (курсор и добор), счётчик «~N results» по каждой границе даты и размер порции.

    Размер порции — сколько объявлений Meta отдаёт в документе этой страницы (обычно 30, у Shahlo Alikhanova 15).
    """
    union, counters, sizes = {}, {}, []
    paths = [p for p in (RAW / "full" / page_id).glob("*.json") if not p.name.startswith("_")]
    for path in paths + sorted((RAW / "gapfill" / page_id).glob("*.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        ads = result.get("ads") or {}
        union.update(ads)
        counters[path.stem] = result.get("counter") or 0
        sizes.append(len(ads))
    return union, counters, min(PAGE_CAP, max(sizes, default=PAGE_CAP)) or PAGE_CAP


def overflow_windows(loads: list[tuple[str, int]], cap: int = PAGE_CAP) -> list[tuple[str, str, int, int]]:
    """Окна между соседними границами дат, где счётчик вырос больше размера порции — там часть объявлений не пришла.

    loads — (граница, счётчик «~N results») от новых к старым; последняя граница без следующей сравнивается с нулём.
    Возвращает (нижняя граница, верхняя, счётчик нижней, счётчик верхней).
    """
    windows = []
    for i, (hi, n_hi) in enumerate(loads):
        lo, n_lo = loads[i + 1] if i + 1 < len(loads) else (EARLIEST, 0)
        if n_hi - n_lo > cap:
            windows.append((lo, hi, n_lo, n_hi))
    return windows


def midpoint(lo: str, hi: str) -> str | None:
    """Дата посередине окна (lo, hi]; None — окно не делится (соседние дни)."""
    a, b = date.fromisoformat(lo), date.fromisoformat(hi)
    if (b - a).days < 2:
        return None
    return (a + timedelta(days=(b - a).days // 2)).isoformat()


def run_gapfill(page_id: str, max_loads: int) -> None:
    """Добор пропущенных курсором объявлений: окна со счётчиком больше 30 делим пополам по дате, пока окно не станет ≤30.

    Каждая загрузка «≤ середина окна» отдаёт 30 самых новых объявлений до этой даты (проверено пробами) и свой счётчик.
    Загрузки сохраняются в raw/meta/gapfill/<page_id>/<дата>.json — media_download.py и ads_meta_build.py их подхватывают.
    """
    folder = RAW / "gapfill" / page_id
    folder.mkdir(parents=True, exist_ok=True)
    union, counters, cap = cached_full(page_id)
    queue = [(lo, hi) for lo, hi, _, _ in overflow_windows(sorted(counters.items(), reverse=True), cap)]
    fetched, unsplittable = 0, []
    while queue and fetched < max_loads:
        lo, hi = queue.pop(0)
        mid = midpoint(lo, hi)
        if mid is None:
            unsplittable.append(f"{lo}..{hi}")
            continue
        target = folder / f"{mid}.json"
        if target.exists():
            result = json.loads(target.read_text(encoding="utf-8"))
        else:
            if fetched:
                time.sleep(random.uniform(*PAUSE_RANGE))
            url = library_url(search_type="page", view_all_page_id=page_id,
                              **{"start_date[min]": EARLIEST, "start_date[max]": mid}, **GROUPED_SORT)
            result = fetch(url)
            fetched += 1
            if result["rate_limited"]:
                log(f"gapfill {page_id} ≤{mid}: RATE LIMIT — stop")
                raise RateLimited(page_id)
            target.write_text(json.dumps({"label": f"{page_id} ≤{mid} gapfill", **result}, ensure_ascii=False), encoding="utf-8")
        before = len(union)
        union.update(result["ads"])
        counters[mid] = result.get("counter") or 0
        log(f"gapfill {page_id} ≤{mid}: ads={len(result['ads'])} counter={result.get('counter_text')} new={len(union) - before}")
        queue += [(a, b) for a, b in ((lo, mid), (mid, hi)) if counters.get(b, 0) - counters.get(a, 0) > cap]
    total = max(counters.values(), default=0)
    log(f"gapfill {page_id}: unique ads {len(union)} of ~{total}; loads {fetched}; left in queue {len(queue)}; "
        f"unsplittable {unsplittable}")


def run_probe(page_id: str, max_date: str, mode: str) -> None:
    """Проверочная загрузка: сколько новых объявлений даёт граница max_date (и другая сортировка) против полного списка."""
    sort = GROUPED_SORT if mode == "grouped" else {"sort_data[mode]": "total_impressions", "sort_data[direction]": mode}
    url = library_url(search_type="page", view_all_page_id=page_id, **{"start_date[min]": EARLIEST, "start_date[max]": max_date}, **sort)
    union, _, _ = cached_full(page_id)
    result = fetch(url)
    folder = RAW / "probe" / page_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{max_date}-{mode}.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    new = [lid for lid in result["ads"] if lid not in union]
    days = sorted(start_day(a) for a in result["ads"].values() if a.get("start_date"))
    log(f"probe {page_id} ≤{max_date} {mode}: ads={len(result['ads'])} counter={result['counter_text']} new={len(new)} "
        f"days={days[0] if days else '-'}..{days[-1] if days else '-'} rate_limited={result['rate_limited']}")
    if result["rate_limited"]:
        raise RateLimited(page_id)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    d = sub.add_parser("discover")
    d.add_argument("--limit", type=int, default=None)
    b = sub.add_parser("brands", help="поиск по названиям школ из 01-master/candidates.csv (колонка search_hint)")
    b.add_argument("--limit", type=int, default=None)
    a = sub.add_parser("ad", help="страница одного объявления: page_id рекламодателя, его объявления (до 30) и счётчик")
    a.add_argument("--library-ids", default="", help="через запятую")
    a.add_argument("--candidates", action="store_true", help="взять example_ad из 01-master/candidates.csv")
    p = sub.add_parser("page")
    p.add_argument("--page-ids", required=True, help="через запятую, ID страниц Ad Library (view_all_page_id)")
    w = sub.add_parser("windows", help="(устарел: фильтр дат накопительный) окна по датам")
    w.add_argument("--page-id", required=True)
    w.add_argument("--from-month", required=True, help="YYYY-MM — месяц самого раннего запуска")
    f = sub.add_parser("full", help="все активные объявления страницы: курсор по дате запуска (этап 2)")
    f.add_argument("--page-id", required=True)
    pr = sub.add_parser("probe", help="одна проверочная загрузка страницы с границей даты и сортировкой")
    pr.add_argument("--page-id", required=True)
    pr.add_argument("--max-date", required=True)
    pr.add_argument("--sort", choices=["grouped", "desc", "asc"], default="grouped", help="grouped или total_impressions desc/asc")
    g = sub.add_parser("gapfill", help="добор объявлений в окнах курсора, где счётчик вырос больше чем на 30")
    g.add_argument("--page-id", required=True)
    g.add_argument("--max-loads", type=int, default=12)
    args = ap.parse_args()

    if args.mode == "gapfill":
        try:
            run_gapfill(args.page_id, args.max_loads)
        except RateLimited:
            sys.exit(3)
        return
    if args.mode == "probe":
        try:
            run_probe(args.page_id, args.max_date, args.sort)
        except RateLimited:
            sys.exit(3)
        return
    if args.mode == "full":
        try:
            run_full(args.page_id)
        except RateLimited:
            sys.exit(3)
        return
    if args.mode == "windows":
        try:
            run_windows(args.page_id, args.from_month)
        except RateLimited:
            sys.exit(3)
        return

    if args.mode == "discover":
        jobs = [(r["query"], keyword_url(r["query"]), RAW / "discover" / f"{slug(r['query'])}.json")
                for r in load_keywords(args.limit)]
    elif args.mode == "brands":
        with (HERE / "01-master" / "candidates.csv").open(encoding="utf-8") as fh:
            names = [r["search_hint"].split(": ", 1)[1] for r in csv.DictReader(fh) if r["search_hint"]]
        names = names[:args.limit] if args.limit else names
        jobs = [(n, keyword_url(n), RAW / "brands" / f"{slug(n)}.json") for n in names]
    elif args.mode == "ad":
        ids = [x.strip() for x in args.library_ids.split(",") if x.strip()]
        if args.candidates:
            with (HERE / "01-master" / "candidates.csv").open(encoding="utf-8") as fh:
                ids += [re.search(r"id=(\d+)", r["example_ad"]).group(1) for r in csv.DictReader(fh)
                        if re.search(r"id=(\d+)", r["example_ad"] or "")]
            ids = list(dict.fromkeys(ids))
        jobs = [(lid, library_url(id=lid), RAW / "ad" / f"{lid}.json") for lid in ids]
    else:
        ids = [x.strip() for x in args.page_ids.split(",") if x.strip()]
        jobs = [(pid, page_url(pid), RAW / "page" / f"{pid}.json") for pid in ids]
    try:
        run_jobs(jobs)
    except RateLimited:
        sys.exit(3)


if __name__ == "__main__":
    main()
