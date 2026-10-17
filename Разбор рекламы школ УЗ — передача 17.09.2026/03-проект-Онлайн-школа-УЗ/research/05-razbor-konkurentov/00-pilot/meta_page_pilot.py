#!/usr/bin/env python3
"""Пилот: полный список активных объявлений одной страницы в Meta Ad Library.

Настоящий headless Chromium через crawl4ai — как в прошлом скане, без stealth-режимов,
без подмены navigator, без куки и прокси. Объявления берём из ответов, которые страница
получает сама (встроенный JSON документа и /api/graphql/ при прокрутке).

Запуск (окружение прошлого скана):
    ~/.venvs/fb-ads-library/bin/python meta_page_pilot.py 100093860176934 --scrolls 8
"""
import argparse
import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
OUT = HERE / "meta"
ACCEPT_LANGUAGE = "en-US,en;q=0.9"
SCRIPT_JSON_RE = re.compile(r'<script type="application/json"[^>]*>(.*?)</script>', re.S)
RESULTS_RE = re.compile(r"~?\s?([\d,]+)\s+results?")


def page_url(page_id: str) -> str:
    return "https://www.facebook.com/ads/library/?" + urlencode({
        "active_status": "active", "ad_type": "all", "country": "UZ",
        "is_targeted_country": "false", "media_type": "all",
        "search_type": "page", "view_all_page_id": page_id,
    })


def json_payloads(text: str) -> list:
    """Все JSON-документы из ответа: построчный graphql или встроенные <script type=application/json>."""
    found = []
    blocks = SCRIPT_JSON_RE.findall(text) if "<script" in text[:5000] or "<html" in text[:500].lower() else [text]
    for block in blocks:
        for line in block.splitlines() or [block]:
            line = line.strip()
            if line.startswith("for (;;);"):
                line = line[len("for (;;);"):]
            if not line or line[0] not in "[{":
                continue
            try:
                found.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return found


def collect_ads(node, sink: dict) -> None:
    if isinstance(node, dict):
        if "ad_archive_id" in node and isinstance(node.get("snapshot"), dict):
            sink.setdefault(str(node["ad_archive_id"]), node)
        for value in node.values():
            collect_ads(value, sink)
    elif isinstance(node, list):
        for value in node:
            collect_ads(value, sink)


async def render(url: str, scrolls: int) -> dict:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

    browser = BrowserConfig(headless=True, browser_type="chromium", viewport_width=1400,
                            viewport_height=1600, headers={"Accept-Language": ACCEPT_LANGUAGE})
    js = ("await new Promise(r=>setTimeout(r,8000));"
          + "".join("window.scrollTo(0, document.body.scrollHeight);"
                    "await new Promise(r=>setTimeout(r,3500));" for _ in range(scrolls)))
    run = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, delay_before_return_html=5,
                           page_timeout=60000 + scrolls * 5000, js_code=[js], locale="en-US",
                           timezone_id="Asia/Tashkent", capture_network_requests=True)
    async with AsyncWebCrawler(config=browser) as crawler:
        result = await crawler.arun(url=url, config=run)
    md = result.markdown.raw_markdown if hasattr(result.markdown, "raw_markdown") else str(result.markdown or "")
    return {"status_code": result.status_code, "markdown": md, "html": result.html or "",
            "network": result.network_requests or []}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("page_id")
    ap.add_argument("--scrolls", type=int, default=8)
    ap.add_argument("--debug", action="store_true", help="сохранить HTML, markdown и список сетевых событий")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    url = page_url(args.page_id)
    started = time.time()
    data = asyncio.run(render(url, args.scrolls))

    ads: dict = {}
    sources = {"document": 0, "graphql": 0}
    relevant = []
    for event in data["network"]:
        if event.get("event_type") != "response":
            continue
        body = ((event.get("body") or {}).get("text")) or ""
        if "ad_archive_id" not in body:
            continue
        kind = "graphql" if "/api/graphql" in event["url"] else "document"
        before = len(ads)
        for payload in json_payloads(body):
            collect_ads(payload, ads)
        sources[kind] += len(ads) - before
        relevant.append({"url": event["url"], "status": event.get("status"), "kind": kind, "body": body})
    if not ads and "ad_archive_id" in data["html"]:
        for payload in json_payloads(data["html"]):
            collect_ads(payload, ads)
        sources["document"] += len(ads)

    counter = RESULTS_RE.search(data["markdown"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if args.debug:
        (OUT / f"debug-{args.page_id}-{stamp}.html").write_text(data["html"], encoding="utf-8")
        (OUT / f"debug-{args.page_id}-{stamp}.md").write_text(data["markdown"], encoding="utf-8")
        events = [{"type": e.get("event_type"), "url": e.get("url"), "status": e.get("status"),
                   "resource": e.get("resource_type"), "body_len": len(((e.get("body") or {}).get("text")) or ""),
                   "body_head": (((e.get("body") or {}).get("text")) or "")[:300]}
                  for e in data["network"] if e.get("event_type") in ("response", "request")]
        (OUT / f"debug-{args.page_id}-{stamp}-network.json").write_text(
            json.dumps(events, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / f"capture-{args.page_id}-{stamp}.json").write_text(
        json.dumps({"url": url, "status_code": data["status_code"], "responses": relevant}, ensure_ascii=False),
        encoding="utf-8")
    (OUT / f"ads-{args.page_id}-{stamp}.json").write_text(json.dumps(ads, ensure_ascii=False, indent=1), encoding="utf-8")
    first = next(iter(ads.values()), {})
    print(json.dumps({
        "page_id": args.page_id, "status_code": data["status_code"], "seconds": round(time.time() - started),
        "ads_parsed": len(ads), "by_source": sources, "counter_text": counter.group(0) if counter else None,
        "network_events": len(data["network"]), "responses_with_ads": len(relevant),
        "ad_keys": sorted(first.keys()), "snapshot_keys": sorted((first.get("snapshot") or {}).keys()),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
