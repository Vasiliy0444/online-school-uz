#!/usr/bin/env python3
"""Этап 3 по мере готовности этапа 2: как только у школы скачаны медиа всех страниц — кадры и расшифровка её видео.

Готовность школы — в журнале logs/stage2_run.log есть строка «<school> page <id>: media exit» для каждой её страницы.
Работает локально (ffmpeg + mlx-whisper), сеть не нужна. Проверка раз в 2 минуты; выходит, когда обработаны все школы
или когда этап 2 завершился («stage 2 done» / «RATE LIMIT»), а новых готовых школ нет.
Запуск: python3 stage3_run.py
"""
import csv
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = Path.home() / "Data" / "online-shkola-uz" / "05-razbor-konkurentov"
STAGE2_LOG = DATA / "logs" / "stage2_run.log"
ORDER = ["qadam", "najot-talim", "shahlo-alikhanova", "bir-group", "logist-academy", "it-house", "englify", "inter-nation", "hbs-academy"]


def log(message: str) -> None:
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {message}"
    print(line, flush=True)
    with (DATA / "logs" / "stage3_run.log").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main() -> None:
    with (HERE / "01-master" / "shortlist.csv").open(encoding="utf-8") as fh:
        pages = {r["school_id"]: [p.strip() for p in r["page_ids"].split(";") if p.strip()] for r in csv.DictReader(fh)}
    done: set[str] = set()
    while len(done) < len(ORDER):
        text = STAGE2_LOG.read_text(encoding="utf-8") if STAGE2_LOG.exists() else ""
        ready = [s for s in ORDER if s not in done and all(re.search(rf"{re.escape(s)} page {p}: media exit", text) for p in pages[s])]
        for school in ready:
            log(f"{school}: frames and transcripts start")
            code = subprocess.run([sys.executable, str(HERE / "frames_transcribe.py"), "--school", school], cwd=HERE).returncode
            log(f"{school}: frames and transcripts exit {code}")
            done.add(school)
        if not ready:
            if re.search(r"stage 2 done|RATE LIMIT — stage 2 stopped", text):
                log(f"stage 2 finished; schools processed: {sorted(done)}")
                return
            time.sleep(120)
    log("stage 3 done")


if __name__ == "__main__":
    main()
