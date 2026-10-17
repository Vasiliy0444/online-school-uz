#!/usr/bin/env python3
"""Скан Meta Ad Library по списку запросов: реклама, показанная в Узбекистане.

Запуск из этой папки:
    ~/.venvs/fb-ads-library/bin/python sweep.py --pilot          # 5 пробных запросов (pilot=1)
    ~/.venvs/fb-ads-library/bin/python sweep.py                  # все запросы из keywords.csv
    ~/.venvs/fb-ads-library/bin/python sweep.py --only "SMM kurs,target"

Для каждого запроса пишет raw/<slug>.json: запрос, группа, URL, время, код ответа,
число карточек, разобранные карточки и полный markdown страницы (для повторного разбора).
Уже скачанные запросы пропускает, поэтому скан можно прервать и продолжить.
Если три запроса подряд вернули пустую страницу без фразы «No ads match» — это похоже
на блокировку, скан останавливается с кодом 2.
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
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

HERE = Path(__file__).resolve().parent
TOOL_DIR = HERE.parent.parent / "tools" / "facebook-ads-library-mcp"
sys.path.insert(0, str(TOOL_DIR))

from facebook_ads_mcp_complete import _parse_ad_library_markdown  # noqa: E402

AD_LIBRARY_BASE = "https://www.facebook.com/ads/library/"
COUNTRY = "UZ"
NO_RESULTS_MARKERS = ("No ads match", "no results", "0 results")
BLOCK_STREAK_LIMIT = 3
MAX_ATTEMPTS = 3
MAX_COOLDOWNS = 2
COOLDOWN_SECONDS = 600
SLEEP_SUSPECT_SECONDS = 240  # обычный запрос идёт ~40 с; 15.09.2026 при сне ноутбука запросы шли 258–978 с
# Разбор карточек в сборщике завязан на английский интерфейс («Library ID», «Started running on»,
# «Sponsored»). Без явного языка Meta отдала headless-браузеру страницу на французском,
# и ни одна карточка не разобралась (пилот 15.09.2026, лог sweep-pilot1-french.log).
BROWSER_LOCALE = "en-US"
ACCEPT_LANGUAGE = "en-US,en;q=0.9"


async def render_ad_library_en(url: str, wait_seconds: int, scroll_rounds: int) -> dict:
    """Копия `_render_ad_library` из сборщика (коммит ea3c877) с английским интерфейсом.

    Отличия от оригинала только в языке: заголовок Accept-Language и locale браузера.
    Ожидание загрузки, прокрутка и таймауты — как у автора.
    """
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

    browser = BrowserConfig(headless=True, browser_type="chromium",
                            viewport_width=1400, viewport_height=1600,
                            headers={"Accept-Language": ACCEPT_LANGUAGE})
    hydrate_ms = max(3, wait_seconds) * 1000
    rounds = max(0, int(scroll_rounds))
    js = (
        f"await new Promise(r=>setTimeout(r,{hydrate_ms}));"
        + "".join(
            "window.scrollTo(0, document.body.scrollHeight);"
            "await new Promise(r=>setTimeout(r,2500));"
            for _ in range(rounds)
        )
        + "window.scrollTo(0, document.body.scrollHeight);"
    )
    run = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        delay_before_return_html=max(3, wait_seconds),
        page_timeout=max(90000, 20000 + rounds * 3000),
        js_code=[js],
        locale=BROWSER_LOCALE,
        timezone_id="Asia/Tashkent",
    )
    async with AsyncWebCrawler(config=browser) as crawler:
        result = await crawler.arun(url=url, config=run)
        md = result.markdown.raw_markdown if hasattr(result.markdown, "raw_markdown") else str(result.markdown)
        return {"markdown": md or "", "status_code": result.status_code}


def build_url(query: str) -> str:
    params = {
        "active_status": "active",
        "ad_type": "all",
        "country": COUNTRY,
        "is_targeted_country": "false",
        "media_type": "all",
        "q": query,
        "search_type": "keyword_unordered",
    }
    return AD_LIBRARY_BASE + "?" + urlencode(params, quote_via=quote)


def slugify(index: int, query: str) -> str:
    ascii_part = re.sub(r"[^0-9a-zA-Z]+", "-", query).strip("-").lower()[:40] or "q"
    digest = hashlib.md5(query.encode("utf-8")).hexdigest()[:6]
    return f"{index:03d}-{ascii_part}-{digest}"


def load_keywords(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for i, row in enumerate(rows, start=1):
        row["index"] = i
        row["scroll"] = int(row.get("scroll") or 8)
        row["pilot"] = row.get("pilot") == "1"
    return rows


def select_rows(rows: list[dict], pilot: bool, only: str | None, limit: int | None) -> list[dict]:
    if pilot:
        rows = [r for r in rows if r["pilot"]]
    if only:
        wanted = {w.strip() for w in only.split(",") if w.strip()}
        rows = [r for r in rows if r["query"] in wanted or r["group"] in wanted]
    return rows[:limit] if limit else rows


def looks_blocked(markdown: str) -> bool:
    if any(marker.lower() in markdown.lower() for marker in NO_RESULTS_MARKERS):
        return False
    return "Ad Library" not in markdown or len(markdown) < 2000


def log(line: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    text = f"[{stamp}] {line}"
    print(text, flush=True)
    with (HERE / "sweep.log").open("a", encoding="utf-8") as fh:
        fh.write(text + "\n")


def run_query(row: dict, wait_seconds: int, scroll_override: int | None) -> dict:
    url = build_url(row["query"])
    scroll_rounds = scroll_override if scroll_override is not None else row["scroll"]
    started = time.time()
    rendered = asyncio.run(render_ad_library_en(url, wait_seconds, scroll_rounds))
    markdown = rendered.get("markdown") or ""
    ads = _parse_ad_library_markdown(markdown)
    return {
        "query": row["query"],
        "group": row["group"],
        "script": row["script"],
        "url": url,
        "country": COUNTRY,
        "scroll_rounds": scroll_rounds,
        "wait_seconds": wait_seconds,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status_code": rendered.get("status_code"),
        "seconds": round(time.time() - started, 1),
        "cards": len(ads),
        "blocked_suspected": not ads and looks_blocked(markdown),
        "ads": ads,
        "markdown": markdown,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--keywords", default=str(HERE / "keywords.csv"))
    parser.add_argument("--pilot", action="store_true", help="только запросы с pilot=1")
    parser.add_argument("--only", help="запросы или группы через запятую")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--wait", type=int, default=10, help="секунд на загрузку страницы")
    parser.add_argument("--scroll", type=int, help="переопределить число прокруток для всех запросов")
    parser.add_argument("--pause-min", type=float, default=12.0)
    parser.add_argument("--pause-max", type=float, default=25.0)
    args = parser.parse_args()

    raw_dir = HERE / "raw"
    raw_dir.mkdir(exist_ok=True)
    rows = select_rows(load_keywords(Path(args.keywords)), args.pilot, args.only, args.limit)
    log(f"старт: {len(rows)} запросов, wait={args.wait}, pause={args.pause_min}-{args.pause_max}s")

    block_streak = 0
    cooldowns_used = 0
    done = 0
    for n, row in enumerate(rows, start=1):
        out_path = raw_dir / f"{slugify(row['index'], row['query'])}.json"
        if out_path.exists():
            log(f"{n}/{len(rows)} пропуск (уже есть): {row['query']}")
            continue

        for attempt in range(1, MAX_ATTEMPTS + 1):
            result = attempt_query(row, args)
            if result is not None and not failed(result):
                break
            seconds = result["seconds"] if result else 0
            if seconds > SLEEP_SUSPECT_SECONDS:
                # Запрос шёл в разы дольше обычных ~40 с — так бывает, когда компьютер засыпает.
                log(f"{n}/{len(rows)} «{row['query']}»: {seconds} c без карточек — похоже, компьютер засыпал, повтор")
                continue
            block_streak += 1
            if block_streak >= BLOCK_STREAK_LIMIT:
                if cooldowns_used >= MAX_COOLDOWNS:
                    log("пустые ответы продолжаются и после паузы — остановка, результаты сбойных запросов не сохранены")
                    return 2
                cooldowns_used += 1
                log(f"три пустых ответа подряд — пауза {COOLDOWN_SECONDS // 60} мин и повтор")
                time.sleep(COOLDOWN_SECONDS)
                block_streak = 0
        else:
            log(f"{n}/{len(rows)} «{row['query']}»: не удалось за {MAX_ATTEMPTS} попытки — пропуск, запрос не сохранён")
            continue

        if failed(result):
            log(f"{n}/{len(rows)} «{row['query']}»: пусто — не сохранено, повторится при следующем запуске")
            continue
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        done += 1
        block_streak = 0
        advertisers = len({a.get("advertiser") for a in result["ads"]})
        log(f"{n}/{len(rows)} «{row['query']}»: карточек {result['cards']}, рекламодателей {advertisers}, "
            f"код {result['status_code']}, {result['seconds']} c")
        if n < len(rows):
            time.sleep(random.uniform(args.pause_min, args.pause_max))

    log(f"готово: скачано {done} из {len(rows)}")
    return 0


def failed(result: dict) -> bool:
    """Пустой результат из-за сбоя: браузер не отдал страницу или она похожа на блокировку.

    Честный ноль («No ads match») сбоем не считается и сохраняется, чтобы не перезапрашивать.
    """
    return result["cards"] == 0 and (result["status_code"] is None or result["blocked_suspected"])


def attempt_query(row: dict, args: argparse.Namespace) -> dict | None:
    try:
        return run_query(row, args.wait, args.scroll)
    except Exception as exc:  # сеть, таймаут браузера — фиксируем и повторяем
        log(f"ОШИБКА «{row['query']}»: {exc!r}")
        return None


if __name__ == "__main__":
    sys.exit(main())
