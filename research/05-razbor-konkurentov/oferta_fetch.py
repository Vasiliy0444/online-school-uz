#!/usr/bin/env python3
"""Публичные оферты школ: ссылки «oferta» со снятых страниц → текст оферты рядом со снимками лендингов.

Берёт ссылки из 03-lendingi/<school>/*/page.md, чей текст или адрес содержит oferta / оферта / shartnoma,
только на доменах школы (01-master/shortlist.csv). PDF скачивает (GET) и переводит в текст через pdftotext -layout,
HTML-страницу снимает тем же браузером, что и лендинги. Страницы оплаты и формы не открывает.
Выход: 03-lendingi/<school>/oferta-<slug>/{page.md, meta.json}; сам PDF — в ~/Data/.../lendingi/<school>/oferta-<slug>/.
Запуск: ~/.venvs/fb-ads-library/bin/python oferta_fetch.py
"""
import asyncio
import csv
import json
import random
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

from landings_snapshot import DATA, L, UA, render, slug

HERE = Path(__file__).resolve().parent
LINK_RE = re.compile(r"\[([^\]]{0,80})\]\((https?://[^)\s]+)")
OFERTA_RE = re.compile(r"ofert|оферт|shartnoma|dogovor", re.I)


def oferta_links() -> dict[str, set[str]]:
    with (HERE / "01-master" / "shortlist.csv").open(encoding="utf-8") as fh:
        domains = {r["school_id"]: [d.strip() for d in r["domains"].split(";") if d.strip()] for r in csv.DictReader(fh)}
    snapped = {json.loads(m.read_text(encoding="utf-8"))["url"].split("#")[0] for m in L.glob("*/*/meta.json")}
    found: dict[str, set[str]] = {}
    for page in L.glob("*/*/page.md"):
        school = page.parent.parent.name
        for text, url in LINK_RE.findall(page.read_text(encoding="utf-8")):
            url = url.split("#")[0]  # якоря (#tariffs, #form) ведут на ту же страницу
            host = (urlsplit(url).hostname or "").removeprefix("www.")
            own = any(host == d or host.endswith("." + d) for d in domains.get(school, []))
            if own and OFERTA_RE.search(text + url) and url not in snapped:
                found.setdefault(school, set()).add(url)
    return found


def pdf_text(url: str, target: Path) -> tuple[str, dict]:
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=60)
    info = {"live_status": resp.status_code, "content_type": resp.headers.get("content-type", "")}
    if resp.status_code != 200 or not resp.content.startswith(b"%PDF"):
        return "", info
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(resp.content)
    result = subprocess.run(["pdftotext", "-layout", str(target), "-"], capture_output=True, text=True, timeout=120)
    return result.stdout, {**info, "pdf": str(target), "bytes": len(resp.content)}


def main() -> None:
    for school, urls in sorted(oferta_links().items()):
        for url in sorted(urls):
            folder = L / school / f"oferta-{slug(url)}"
            if (folder / "meta.json").exists():
                continue
            meta = {"school_id": school, "url": url, "sources": "ссылка «оферта» на снятой странице", "stage_auto": "оферта или оплата",
                    "is_archive": False, "snapshot_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            if urlsplit(url).path.lower().endswith(".pdf"):
                text, info = pdf_text(url, DATA / school / folder.name / "oferta.pdf")
            else:
                page = asyncio.run(render(url))
                text, info = page["markdown"], {"live_status": page["status"], "final_url": page["final_url"], "title": page["title"]}
            meta.update(info, text_chars=len(text))
            folder.mkdir(parents=True, exist_ok=True)
            if text:
                (folder / "page.md").write_text(text, encoding="utf-8")
            (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"{school} | {len(text):>6} симв. | {url}", flush=True)
            time.sleep(random.uniform(3, 5))


if __name__ == "__main__":
    main()
