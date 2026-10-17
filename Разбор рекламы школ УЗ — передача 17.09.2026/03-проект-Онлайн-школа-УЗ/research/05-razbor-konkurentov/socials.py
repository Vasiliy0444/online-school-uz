#!/usr/bin/env python3
"""Подписчики школ в соцсетях — только публичные страницы, без входа.

Вход: 01-master/social_handles.csv — колонки school_id, platform (telegram|youtube|instagram|tiktok|facebook), handle, found_via.
Выход: 01-master/socials.csv — по строке на аккаунт.

  telegram  — страница t.me/<handle>: тип (канал / группа / личный / бот) и число подписчиков или участников;
              для каналов — лента t.me/s/<handle>: медиана просмотров последних постов, даты, внешние ссылки.
  youtube   — yt-dlp без скачивания: channel_follower_count. На проверку «вы не бот» — стоп.
  instagram, tiktok, facebook — не собираются скриптом: переносятся с пустыми числами для ручного замера
              во встроенном браузере (Instagram — по 5 профилей, пауза 20–30 минут).
Паузы: Telegram 2–3 с, YouTube 5 с. Продолжает с места остановки.
"""
import csv
import html
import json
import random
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
IN = HERE / "01-master" / "social_handles.csv"
OUT = HERE / "01-master" / "socials.csv"
UA = "Mozilla/5.0 (research; online-shkola-uz)"
FIELDS = ["school_id", "platform", "handle", "url", "account_type", "followers", "followers_raw", "posts_seen",
          "median_views", "views_per_follower", "last_post_at", "external_links", "found_via", "measured_at", "method", "note"]


def number(text: str) -> int | None:
    text = text.strip().upper().replace(" ", "").replace(",", ".")
    match = re.match(r"^([\d.]+)([KM]?)$", text)
    if not match:
        digits = re.sub(r"\D", "", text)
        return int(digits) if digits else None
    value = float(match.group(1)) * {"": 1, "K": 1_000, "M": 1_000_000}[match.group(2)]
    return int(round(value))


def telegram(handle: str) -> dict:
    handle = handle.lstrip("@").strip("/")
    page = requests.get(f"https://t.me/{handle}", headers={"User-Agent": UA}, timeout=30).text
    extra = re.search(r'<div class="tgme_page_extra">\s*([^<]*?)\s*</div>', page)
    extra_text = html.unescape(extra.group(1)) if extra else ""
    row = {"url": f"https://t.me/{handle}", "followers_raw": extra_text, "method": "t.me page"}
    if "subscriber" in extra_text:
        row["account_type"] = "канал"
    elif "member" in extra_text:
        row["account_type"] = "группа"
    elif handle.lower().endswith("bot"):
        row["account_type"] = "бот"
    elif extra_text.startswith("@") or not extra_text:
        row["account_type"] = "личный аккаунт или нет страницы"
    count = re.match(r"([\d\s]+)", extra_text)
    row["followers"] = int(re.sub(r"\s", "", count.group(1))) if count and re.sub(r"\s", "", count.group(1)) else ""
    if row.get("account_type") == "канал":
        time.sleep(random.uniform(2, 3))
        feed = requests.get(f"https://t.me/s/{handle}", headers={"User-Agent": UA}, timeout=30).text
        views = [number(v) for v in re.findall(r'<span class="tgme_widget_message_views">([^<]+)</span>', feed)]
        views = [v for v in views if v is not None]
        dates = re.findall(r'<time datetime="([^"]+)"', feed)
        links = sorted({l for l in re.findall(r'href="(https?://[^"]+)"', feed)
                        if not re.match(r"https?://(t\.me/s?/?%s|telegram\.org)" % re.escape(handle), l, re.I)})
        median = statistics.median(views) if views else ""
        row.update(posts_seen=len(views), median_views=median, last_post_at=dates[-1] if dates else "",
                   views_per_follower=round(median / row["followers"], 3) if median and row["followers"] else "",
                   external_links=" | ".join(links[:30]), method="t.me page + t.me/s feed")
    return row


def youtube(handle: str) -> dict:
    url = handle if handle.startswith("http") else f"https://www.youtube.com/@{handle.lstrip('@')}"
    result = subprocess.run(["yt-dlp", "-J", "--flat-playlist", "--playlist-end", "1", "--sleep-requests", "2",
                             f"{url.rstrip('/')}/videos"], capture_output=True, text=True, timeout=180)
    if "confirm you" in result.stderr.lower() and "bot" in result.stderr.lower():
        raise RuntimeError("YouTube просит подтвердить, что это не бот — стоп")
    if result.returncode != 0:
        return {"url": url, "note": f"yt-dlp error: {result.stderr.strip()[-160:]}", "method": "yt-dlp"}
    data = json.loads(result.stdout)
    return {"url": url, "account_type": "канал", "followers": data.get("channel_follower_count") or "",
            "followers_raw": str(data.get("channel_follower_count") or ""), "method": "yt-dlp channel metadata"}


def main() -> None:
    if not IN.exists():
        sys.exit(f"нет входного файла {IN}")
    with IN.open(encoding="utf-8") as fh:
        handles = list(csv.DictReader(fh))
    done = {}
    if OUT.exists():
        with OUT.open(encoding="utf-8") as fh:
            done = {(r["platform"], r["handle"].lower()): r for r in csv.DictReader(fh)}
    rows = list(done.values())
    for h in handles:
        key = (h["platform"], h["handle"].lower())
        if key in done:
            continue
        base = {f: "" for f in FIELDS} | {"school_id": h["school_id"], "platform": h["platform"], "handle": h["handle"],
                                          "found_via": h.get("found_via", ""),
                                          "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        try:
            if h["platform"] == "telegram":
                base.update(telegram(h["handle"]))
                time.sleep(random.uniform(2, 3))
            elif h["platform"] == "youtube":
                base.update(youtube(h["handle"]))
                time.sleep(5)
            else:
                base.update(method="вручную (встроенный браузер)", note="замерить вручную")
        except RuntimeError as exc:
            print(f"STOP: {exc}", flush=True)
            break
        except requests.RequestException as exc:
            base.update(note=f"ошибка сети: {type(exc).__name__}")
        rows.append(base)
        done[key] = base
        print(f"{h['platform']:9} {h['handle']:30} {base.get('account_type', '')} {base.get('followers', '')}", flush=True)
        with OUT.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
