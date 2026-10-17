#!/usr/bin/env python3
"""Этап 2: полный сбор рекламы Meta короткого списка и скачивание медиа — по школам, по очереди.

Для каждой страницы школы (01-master/shortlist.csv):
  1) meta_collect.py windows --page-id <id> --from-month <месяц самого раннего увиденного запуска>;
  2) сразу media_download.py по окнам этой страницы (ссылки CDN истекают).
Лимит Meta (код выхода 3) — стоп всей очереди. Всё продолжается с места остановки.
Запуск (фоном, с caffeinate):  python3 stage2_run.py [--schools qadam,najot-talim]
"""
import argparse
import csv
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
FB_PY = Path.home() / ".venvs" / "fb-ads-library" / "bin" / "python"
DATA = Path.home() / "Data" / "online-shkola-uz" / "05-razbor-konkurentov"
ORDER = ["qadam", "najot-talim", "shahlo-alikhanova", "bir-group", "logist-academy", "it-house", "englify", "inter-nation", "hbs-academy"]
csv.field_size_limit(10**9)


def log(message: str) -> None:
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}"
    print(line, flush=True)
    with (DATA / "logs" / "stage2_run.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def earliest_month(page_id: str) -> str:
    with (HERE / "01-master" / "ads_seen.csv").open(encoding="utf-8") as fh:
        starts = sorted(r["started"] for r in csv.DictReader(fh) if r["page_id"] == page_id and r["started"])
    return starts[0][:7] if starts else datetime.now().strftime("%Y-%m")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schools", default="")
    args = ap.parse_args()
    only = [s for s in args.schools.split(",") if s]
    with (HERE / "01-master" / "shortlist.csv").open(encoding="utf-8") as fh:
        shortlist = {r["school_id"]: r for r in csv.DictReader(fh)}
    first = True
    for school_id in (only or ORDER):
        school = shortlist[school_id]
        for page_id in [p.strip() for p in school["page_ids"].split(";") if p.strip()]:
            if not first:
                time.sleep(random.uniform(30, 45))  # пауза между страницами, даже если медиа скачались быстро
            first = False
            log(f"{school_id} page {page_id}: full list by launch-date cursor")
            code = subprocess.run([str(FB_PY), str(HERE / "meta_collect.py"), "full", "--page-id", page_id], cwd=HERE).returncode
            if code == 3:
                log("RATE LIMIT — stage 2 stopped")
                sys.exit(3)
            if code != 0:
                log(f"{school_id} page {page_id}: full exit {code} — skip media, continue")
                continue
            code = subprocess.run([sys.executable, str(HERE / "media_download.py"), "--raw-dir", str(DATA / "raw" / "meta" / "full" / page_id),
                                   "--school", school_id, "--page-ids", page_id], cwd=HERE).returncode
            log(f"{school_id} page {page_id}: media exit {code}")
    log("stage 2 done")


if __name__ == "__main__":
    main()
