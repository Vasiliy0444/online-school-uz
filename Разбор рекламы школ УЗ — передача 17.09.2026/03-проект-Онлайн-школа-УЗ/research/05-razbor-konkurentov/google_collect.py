#!/usr/bin/env python3
"""Google Ads Transparency Center: пробный запрос, счёт креативов в регионе UZ, полный сбор короткого списка.

Только прямое соединение (GOOGLE_ADS_TRANSPARENCY_PROXY=direct), паузы 2 с (min_interval), на блокировку — стоп.
Режимы:
  probe                        — один запрос к главной: заблокирован ли IP (капча / 429)
  counts --domains a.uz,b.uz   — рекламодатель по домену и число креативов в UZ → 01-master/google_counts.csv
  collect --advertisers AR…    — все креативы в UZ: детали, картинки, ID роликов YouTube → 02-reklama/google/
Запуск: ~/.venvs/gads-transparency/bin/python google_collect.py probe
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ["GOOGLE_ADS_TRANSPARENCY_PROXY"] = "direct"
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(PROJECT / "tools" / "google-ads-transparency-mcp" / "src"))

from google_ads_transparency_mcp import AdsTransparencyBlocked, AdsTransparencyError, GoogleAdsTransparency  # noqa: E402
from google_ads_transparency_mcp.frames import download_image  # noqa: E402

DATA = Path.home() / "Data" / "online-shkola-uz" / "05-razbor-konkurentov"
RAW = DATA / "raw" / "google"
UZ = 2860
PAGE_SIZE = 100
LOG = DATA / "logs" / "google_collect.log"


def log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def uz_creatives(client: GoogleAdsTransparency, advertiser_id: str) -> list[dict]:
    """Все креативы рекламодателя в регионе UZ — сырые записи SearchCreatives, постранично."""
    items, token = [], ""
    while True:
        body = {"2": PAGE_SIZE, "3": {"12": {"1": "", "2": True}, "13": {"1": [advertiser_id]}, "8": [UZ]}, "7": {"1": 1}}
        if token:
            body["4"] = token
        res = client._rpc("/anji/_/rpc/SearchService/SearchCreatives", body)
        items += res.get("1") or []
        token = res.get("2")
        if not token or not res.get("1"):
            return items


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    sub.add_parser("probe")
    c = sub.add_parser("counts")
    c.add_argument("--domains", required=True)
    k = sub.add_parser("collect")
    k.add_argument("--advertisers", required=True, help="AR… через запятую")
    args = ap.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    try:
        client = GoogleAdsTransparency(region="UZ", min_interval=2.0)
        if args.mode == "probe":
            log("probe: ok — IP is not blocked")
            return
        if args.mode == "counts":
            domains = [d.strip() for d in args.domains.split(",") if d.strip()]
            rows = client.compare_advertisers(domains)
            out = []
            for row in rows:
                record = dict(row)
                if row.get("status") == "ok" and not row.get("parent_entity"):
                    items = uz_creatives(client, row["advertiser_id"])
                    raw_path = RAW / "counts" / f"{row['advertiser_id']}-{stamp}.json"
                    raw_path.parent.mkdir(parents=True, exist_ok=True)
                    raw_path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
                    record.update(uz_creatives=len(items), raw_file=str(raw_path))
                out.append(record)
                log(f"counts {row['domain']}: {record.get('status')} {record.get('advertiser_name', '')} uz={record.get('uz_creatives', '')}")
            target = HERE / "01-master" / "google_counts_raw.csv"
            fields = sorted({k for r in out for k in r})
            with target.open("a" if target.exists() else "w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=fields)
                if fh.tell() == 0:
                    writer.writeheader()
                writer.writerows(out)
            return
        for adv in [a.strip() for a in args.advertisers.split(",") if a.strip()]:
            items = uz_creatives(client, adv)
            details = []
            for item in items:
                if "2" not in item:
                    continue
                detail = client.get_ad_detail(adv, item["2"])
                detail["raw_search_item"] = item
                image = detail["content"].get("image_url", "")
                if image and "content.js" not in image:
                    try:
                        detail["image_file"] = download_image(image, DATA / "kreativy" / "_google" / adv / item["2"], name=item["2"])
                    except Exception as exc:  # один битый креатив не ломает сбор
                        detail["image_error"] = str(exc)[:200]
                details.append(detail)
            target = RAW / "collect" / f"{adv}-{stamp}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(details, ensure_ascii=False, indent=1), encoding="utf-8")
            log(f"collect {adv}: {len(details)} creatives → {target}")
    except AdsTransparencyBlocked as exc:
        log(f"BLOCKED — stop: {str(exc)[:300]}")
        sys.exit(3)
    except AdsTransparencyError as exc:
        log(f"error: {str(exc)[:300]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
