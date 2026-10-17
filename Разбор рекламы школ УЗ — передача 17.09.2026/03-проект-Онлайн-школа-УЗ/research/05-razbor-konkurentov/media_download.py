#!/usr/bin/env python3
"""Скачивание креативов Meta по сохранённым JSON страниц (meta_collect.py) — один файл на уникальный медиафайл.

Что качаем для каждого объявления:
  - видео: video_hd_url, если нет — video_sd_url; превью video_preview_image_url;
  - картинки: original_image_url, если нет — resized_image_url;
  - карусели и динамические объявления (DCO): то же для каждой карточки snapshot.cards[].
Одинаковый файл (одинаковое имя файла на CDN без параметров) качается один раз, остальные объявления ссылаются на него.
Если ссылка CDN истекла (403/410), видео берём через yt-dlp по ссылке объявления (экстрактор facebook:ads).

Паузы: 2–4 с между файлами. Куки, прокси и подмены не используются. Продолжает с места остановки.
Запуск:  python3 media_download.py --raw-dir ~/Data/online-shkola-uz/05-razbor-konkurentov/raw/meta/page --school qadam
Выход:   ~/Data/.../kreativy/<school>/meta/<library_id>/…  и  02-reklama/manifest_media_<school>.csv
"""
import argparse
import csv
import hashlib
import json
import random
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests

HERE = Path(__file__).resolve().parent
DATA = Path.home() / "Data" / "online-shkola-uz" / "05-razbor-konkurentov"
PAUSE_RANGE = (2.0, 4.0)
TIMEOUT = 180
FIELDS = ["school", "library_id", "page_id", "slot", "kind", "media_key", "status", "file", "bytes", "sha256",
          "duration_s", "width", "height", "source"]


def media_key(url: str) -> str:
    return Path(urlsplit(url).path).name


def items_for_ad(ad: dict) -> list[tuple[str, str, str]]:
    """(slot, kind, url) по объявлению: slot = 0 для основного креатива, 1..N для карточек."""
    snap = ad.get("snapshot") or {}
    out: list[tuple[str, str, str]] = []

    def add(slot: str, block: dict) -> None:
        video = block.get("video_hd_url") or block.get("video_sd_url")
        if video:
            out.append((slot, "video_hd" if block.get("video_hd_url") else "video_sd", video))
            if block.get("video_preview_image_url"):
                out.append((slot, "video_preview", block["video_preview_image_url"]))
        image = block.get("original_image_url") or block.get("resized_image_url")
        if image:
            out.append((slot, "image", image))

    for video in snap.get("videos") or []:
        add("0", video)
    for image in snap.get("images") or []:
        add("0", image)
    for i, card in enumerate(snap.get("cards") or [], 1):
        add(str(i), card)
    return out


def probe(path: Path) -> tuple[str, str, str]:
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                             "stream=width,height:format=duration", "-of", "json", str(path)],
                            capture_output=True, text=True)
    try:
        data = json.loads(result.stdout or "{}")
        stream = (data.get("streams") or [{}])[0]
        duration = (data.get("format") or {}).get("duration", "")
        return (f"{float(duration):.1f}" if duration else ""), str(stream.get("width", "")), str(stream.get("height", ""))
    except (ValueError, json.JSONDecodeError):
        return "", "", ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, target: Path) -> str:
    """Возвращает статус: ok | expired | error:<код>."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".part")
    try:
        with requests.get(url, stream=True, timeout=TIMEOUT) as resp:
            if resp.status_code in (403, 410):
                return "expired"
            if resp.status_code != 200:
                return f"error:{resp.status_code}"
            with tmp.open("wb") as fh:
                for chunk in resp.iter_content(1 << 20):
                    fh.write(chunk)
    except requests.RequestException as exc:
        return f"error:{type(exc).__name__}"
    tmp.rename(target)
    return "ok"


def ytdlp_fallback(library_id: str, target: Path) -> str:
    result = subprocess.run(["yt-dlp", "--quiet", "--no-warnings", "--sleep-requests", "2", "-f", "b",
                             "-o", str(target), f"https://www.facebook.com/ads/library/?id={library_id}"],
                            capture_output=True, text=True, timeout=600)
    return "ok" if result.returncode == 0 and target.exists() else f"error:yt-dlp:{result.returncode}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", required=True, type=Path, help="папка с JSON от meta_collect.py")
    ap.add_argument("--school", required=True, help="короткий id школы для папок")
    ap.add_argument("--page-ids", default="", help="оставить только эти page_id (через запятую)")
    args = ap.parse_args()

    keep = {x.strip() for x in args.page_ids.split(",") if x.strip()}
    ads: dict[str, dict] = {}
    for raw in sorted(args.raw_dir.expanduser().glob("*.json")):
        for lib_id, ad in json.loads(raw.read_text(encoding="utf-8")).get("ads", {}).items():
            if not keep or str(ad.get("page_id")) in keep:
                ads.setdefault(lib_id, ad)

    manifest = HERE / "02-reklama" / f"manifest_media_{args.school}.csv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    done = {}
    if manifest.exists():
        with manifest.open(encoding="utf-8") as fh:
            done = {(r["library_id"], r["slot"], r["kind"]): r for r in csv.DictReader(fh)}
    seen_files = {r["media_key"]: r for r in done.values() if r["status"] in ("ok", "duplicate")}

    rows = list(done.values())
    for lib_id, ad in ads.items():
        for slot, kind, url in items_for_ad(ad):
            if (lib_id, slot, kind) in done:
                continue
            key = media_key(url)
            ext = Path(key).suffix or (".mp4" if kind.startswith("video") and kind != "video_preview" else ".jpg")
            target = DATA / "kreativy" / args.school / "meta" / lib_id / f"{lib_id}_{slot}_{kind}{ext}"
            row = {"school": args.school, "library_id": lib_id, "page_id": ad.get("page_id"), "slot": slot, "kind": kind,
                   "media_key": key, "status": "", "file": "", "bytes": "", "sha256": "", "duration_s": "", "width": "",
                   "height": "", "source": "cdn"}
            if key in seen_files:
                row.update(status="duplicate", file=seen_files[key]["file"])
            else:
                status = download(url, target)
                if status == "expired" and kind in ("video_hd", "video_sd"):
                    status, row["source"] = ytdlp_fallback(lib_id, target), "yt-dlp"
                row["status"] = status
                if status == "ok":
                    duration, width, height = probe(target)
                    row.update(file=str(target), bytes=target.stat().st_size, sha256=sha256(target),
                               duration_s=duration, width=width, height=height)
                    seen_files[key] = row
                time.sleep(random.uniform(*PAUSE_RANGE))
            rows.append(row)
            print(f"{lib_id} slot={slot} {kind}: {row['status']} {row['bytes']}", flush=True)
            with manifest.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)


if __name__ == "__main__":
    main()
