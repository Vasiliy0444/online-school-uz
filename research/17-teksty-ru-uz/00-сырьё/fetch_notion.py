#!/usr/bin/env python3
"""Выгружает публичную Notion-базу «База знаний таргетологов» в markdown, дословно.

    python3 fetch_notion.py            # пишет notion-baza-targetologov/*.md рядом со скриптом

Ходит в публичный API страницы (без входа). Страницы рекурсивно: подстраницы тоже сохраняются.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HOST = "https://gigantic-primrose-e9e.notion.site"
ROOT_ID = "c7d724ad-27b0-4062-8163-1978e36224a8"
OUT = Path(__file__).resolve().parent / "notion-baza-targetologov"
BLOCKS = {}


def post(path, body):
    # curl вместо urllib: у Python с python.org на macOS нет корневых сертификатов
    result = subprocess.run(
        ["curl", "-sS", "-m", "60", "-X", "POST", f"{HOST}/api/v3/{path}",
         "-H", "Content-Type: application/json", "-d", json.dumps(body)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def unwrap(rec):
    value = rec.get("value", {})
    return value.get("value", value) if isinstance(value, dict) else {}


def absorb(record_map):
    for bid, rec in record_map.get("block", {}).items():
        block = unwrap(rec)
        if block:
            block["_space"] = rec.get("spaceId")
            BLOCKS[bid] = block


def load_page(page_id):
    cursor, chunk = {"stack": []}, 0
    while True:
        data = post("loadPageChunk", {
            "page": {"id": page_id}, "limit": 200, "cursor": cursor,
            "chunkNumber": chunk, "verticalColumns": False,
        })
        absorb(data["recordMap"])
        cursor = data["cursor"]
        chunk += 1
        if not cursor["stack"]:
            break
    fill_missing(page_id)


def missing_under(root_id):
    """Блоки внутри страницы root_id, которых ещё нет; в подстраницы не заходим."""
    space = BLOCKS[root_id].get("_space")
    found, stack = [], list(BLOCKS[root_id].get("content", []))
    while stack:
        cid = stack.pop()
        block = BLOCKS.get(cid)
        if block is None:
            found.append((cid, space))
        elif block.get("type") != "page":
            stack.extend(block.get("content", []))
    return found


def fill_missing(root_id):
    while True:
        missing = missing_under(root_id)
        if not missing:
            return
        reqs = [{"pointer": {"table": "block", "id": cid, "spaceId": sp}, "version": -1}
                for cid, sp in missing[:100]]
        data = post("syncRecordValuesMain", {"requests": reqs})
        before = len(BLOCKS)
        absorb(data.get("recordMap", {}))
        if len(BLOCKS) == before:
            print(f"не удалось догрузить {len(missing)} блоков: {str(data)[:200]}", file=sys.stderr)
            return


def rich(title):
    parts = []
    for chunk in title or []:
        text = chunk[0]
        for fmt in (chunk[1] if len(chunk) > 1 else []):
            if fmt[0] == "a":
                text = f"[{text}]({fmt[1]})"
            elif fmt[0] == "b":
                text = f"**{text}**"
        parts.append(text)
    return "".join(parts)


def render(bid, depth=0, subpages=None):
    block = BLOCKS.get(bid)
    if not block:
        return []
    btype = block.get("type")
    props = block.get("properties", {})
    text = rich(props.get("title"))
    pad = "  " * depth
    lines = []
    if btype == "page" and depth > 0:
        if subpages is not None:
            subpages.append(bid)
        return [f"{pad}- [страница] {text}"]
    prefix = {
        "header": "# ", "sub_header": "## ", "sub_sub_header": "### ",
        "bulleted_list": f"{pad}- ", "numbered_list": f"{pad}1. ",
        "to_do": f"{pad}- [ ] ", "quote": "> ", "toggle": f"{pad}▸ ",
        "callout": "💡 ",
    }.get(btype)
    if btype == "divider":
        lines.append("---")
    elif btype in ("image", "video", "embed", "bookmark", "file"):
        src = rich(props.get("source")) or rich(props.get("link"))
        caption = rich(props.get("caption"))
        lines.append(f"[{btype}] {caption} {src}".strip())
    elif btype == "code":
        lines.append("```\n" + text + "\n```")
    elif btype in ("column_list", "column", "page"):
        pass
    elif prefix is not None:
        lines.append(prefix + text)
    elif text:
        lines.append(pad + text)
    child_depth = depth + 1 if btype in ("bulleted_list", "numbered_list", "to_do", "toggle") else depth
    for cid in block.get("content", []):
        lines.extend(render(cid, child_depth, subpages))
    return lines


def slug(title):
    return re.sub(r"[^\w\-]+", "-", title, flags=re.U).strip("-")[:60] or "bez-nazvaniya"


def dump(page_id, order, seen):
    if page_id in seen:
        return
    seen.add(page_id)
    load_page(page_id)
    block = BLOCKS[page_id]
    title = rich(block.get("properties", {}).get("title")) or "bez-nazvaniya"
    subpages = []
    lines = [f"# {title}", ""]
    for cid in block.get("content", []):
        lines.extend(render(cid, 0, subpages))
    path = OUT / f"{order:02d}-{slug(title)}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{path.name}: {len(lines)} строк, подстраниц {len(subpages)}")
    for sub in subpages:
        dump(sub, order * 10 + 1 + subpages.index(sub), seen)


def main():
    OUT.mkdir(exist_ok=True)
    load_page(ROOT_ID)
    root = BLOCKS[ROOT_ID]
    seen = {ROOT_ID}
    order = 1
    for cid in root.get("content", []):
        stack = [cid]
        while stack:
            current = stack.pop(0)
            block = BLOCKS.get(current)
            if not block:
                continue
            if block.get("type") == "page":
                dump(current, order, seen)
                order += 1
            else:
                stack.extend(block.get("content", []))


if __name__ == "__main__":
    sys.exit(main())
