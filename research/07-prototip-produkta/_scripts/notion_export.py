#!/usr/bin/env python3
"""Выгрузить публичную страницу Notion (со вложенными страницами и базами) в Markdown.

Запуск: python3 notion_export.py <url-или-id> <out.md> [--source "откуда ссылка"] [--depth 2]
Работает через тот же внутренний API, что и сайт notion.so (loadPageChunk / queryCollection), только чтение.
Картинки и видео не скачиваются — помечаются [картинка] / [видео] со ссылкой, если она внешняя.
"""
import argparse
import json
import re
import ssl
import sys
import time
import urllib.request

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:  # noqa: BLE001
    CTX = ssl.create_default_context()

API = "https://www.notion.so/api/v3/"
blocks, collections, views = {}, {}, {}


def post(ep, body, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(API + ep, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            print(f"  повтор {ep}: {e}", file=sys.stderr)
            time.sleep(3)


def uuid(s):
    h = re.findall(r"[0-9a-f]{32}", s.replace("-", ""))
    i = h[0] if h else s
    return f"{i[:8]}-{i[8:12]}-{i[12:16]}-{i[16:20]}-{i[20:]}"


def val(rec):
    v = rec.get("value", {})
    return v.get("value", v) if isinstance(v, dict) else {}


def absorb(rm):
    for k, store in (("block", blocks), ("collection", collections), ("collection_view", views)):
        for bid, rec in (rm.get(k) or {}).items():
            v = val(rec)
            if v:
                store[bid] = v


def load_page(pid):
    cursor, chunk = {"stack": []}, 0
    while True:
        d = post("loadPageChunk", {"pageId": pid, "limit": 100, "cursor": cursor, "chunkNumber": chunk,
                                   "verticalColumns": False})
        absorb(d.get("recordMap", {}))
        cursor = d.get("cursor", {})
        if not cursor.get("stack"):
            break
        chunk += 1


def ensure(ids):
    missing = [i for i in ids if i not in blocks]
    for s in range(0, len(missing), 50):
        part = missing[s:s + 50]
        d = post("syncRecordValues", {"requests": [{"pointer": {"table": "block", "id": i}, "version": -1} for i in part]})
        absorb(d.get("recordMap", {}))


def rich(t):
    out = []
    for seg in t or []:
        s = seg[0]
        for fmt in (seg[1] if len(seg) > 1 else []):
            if fmt[0] == "b":
                s = f"**{s}**" if s.strip() else s
            elif fmt[0] == "s":
                s = f"~~{s}~~" if s.strip() else s
            elif fmt[0] == "a":
                s = f"[{s}]({fmt[1]})"
            elif fmt[0] == "p":
                s = f"[страница {fmt[1]}]"
        out.append(s)
    return "".join(out)


def title_of(b):
    return rich((b.get("properties") or {}).get("title"))


def prop_text(v):
    return rich(v).strip()


def render(bid, depth, level, lines, max_depth):
    b = blocks.get(bid)
    if not b or not b.get("alive", True):
        return
    t, ind = b.get("type"), "  " * level
    txt = title_of(b)
    kids = b.get("content") or []
    if t == "page" and level > 0:
        if depth < max_depth:
            lines.append(f"\n{'#' * min(depth + 2, 6)} {txt or '(без названия)'}\n")
            load_page(bid)
            for k in blocks.get(bid, {}).get("content") or []:
                render(k, depth + 1, 0, lines, max_depth)
        else:
            lines.append(f"{ind}- [подстраница] {txt}")
        return
    if t in ("header", "sub_header", "sub_sub_header"):
        lines.append(f"\n{'#' * ({'header': 2, 'sub_header': 3, 'sub_sub_header': 4}[t] + depth)} {txt}\n")
    elif t == "text":
        lines.append(f"{ind}{txt}" if txt.strip() else "")
    elif t == "bulleted_list":
        lines.append(f"{ind}- {txt}")
    elif t == "numbered_list":
        lines.append(f"{ind}1. {txt}")
    elif t == "to_do":
        chk = (b.get("properties") or {}).get("checked", [["No"]])[0][0] == "Yes"
        lines.append(f"{ind}- [{'x' if chk else ' '}] {txt}")
    elif t == "toggle":
        lines.append(f"{ind}- ▸ {txt}")
    elif t == "quote":
        lines.append(f"{ind}> {txt}")
    elif t == "callout":
        lines.append(f"{ind}> 💡 {txt}")
    elif t == "divider":
        lines.append("\n---\n")
    elif t == "code":
        lines.append(f"```\n{txt}\n```")
    elif t in ("image", "video", "file", "pdf", "audio"):
        src = ((b.get("properties") or {}).get("source") or [[""]])[0][0]
        cap = rich((b.get("properties") or {}).get("caption"))
        name = {"image": "картинка", "video": "видео", "file": "файл", "pdf": "pdf", "audio": "аудио"}[t]
        ext = src if src.startswith("http") and "secure.notion-static" not in src and "amazonaws" not in src else ""
        lines.append(f"{ind}[{name}{': ' + cap if cap else ''}{' — ' + ext if ext else ''}]")
    elif t in ("bookmark", "embed", "link_to_page"):
        link = ((b.get("properties") or {}).get("link") or [[""]])[0][0]
        lines.append(f"{ind}[{t}: {txt or link}] {link}")
    elif t == "table":
        cols = (b.get("format") or {}).get("table_block_column_order") or []
        ensure(kids)
        rows = []
        for r in kids:
            props = (blocks.get(r) or {}).get("properties") or {}
            rows.append([prop_text(props.get(c)).replace("\n", " ").replace("|", "/") for c in cols])
        if rows:
            lines.append("")
            lines.append("| " + " | ".join(rows[0]) + " |")
            lines.append("|" + "---|" * len(cols))
            for r in rows[1:]:
                lines.append("| " + " | ".join(r) + " |")
            lines.append("")
        return
    elif t in ("collection_view", "collection_view_page"):
        render_collection(b, depth, lines, max_depth)
        if t == "collection_view_page":
            return
    elif t in ("column_list", "column", "transclusion_container", "transclusion_reference", "synced_block"):
        pass
    elif txt:
        lines.append(f"{ind}{txt}")
    if kids and t not in ("page",):
        ensure(kids)
        nxt = level + 1 if t in ("bulleted_list", "numbered_list", "to_do", "toggle", "callout", "quote") else level
        for k in kids:
            render(k, depth, nxt, lines, max_depth)


def render_collection(b, depth, lines, max_depth):
    cid = b.get("collection_id") or (b.get("format") or {}).get("collection_pointer", {}).get("id")
    vids = b.get("view_ids") or []
    if cid not in collections:
        d = post("syncRecordValues", {"requests": [{"pointer": {"table": "collection", "id": cid}, "version": -1}]
                                      + [{"pointer": {"table": "collection_view", "id": v}, "version": -1} for v in vids]})
        absorb(d.get("recordMap", {}))
    col = collections.get(cid, {})
    schema = col.get("schema") or {}
    lines.append(f"\n{'#' * min(depth + 3, 6)} База «{rich(col.get('name'))}»\n")
    names = {k: v.get("name") for k, v in schema.items()}
    lines.append("Поля: " + ", ".join(f"«{n}» ({schema[k].get('type')})" for k, n in names.items()))
    if not vids:
        return
    view = views.get(vids[0], {})
    try:
        d = post("queryCollection", {
            "collection": {"id": cid, "spaceId": b.get("space_id")},
            "collectionView": {"id": vids[0], "spaceId": b.get("space_id")},
            "loader": {"type": "reducer", "reducers": {"collection_group_results": {"type": "results", "limit": 500}},
                       "searchQuery": "", "userTimeZone": "Europe/Moscow"}})
    except Exception as e:  # noqa: BLE001
        lines.append(f"(строки базы не выгрузились: {e})")
        return
    absorb(d.get("recordMap", {}))
    ids = (((d.get("result") or {}).get("reducerResults") or {}).get("collection_group_results") or {}).get("blockIds") or []
    lines.append(f"Вид: «{view.get('name', '')}» ({view.get('type', '')}), строк: {len(ids)}\n")
    for rid in ids:
        r = blocks.get(rid, {})
        props = r.get("properties") or {}
        lines.append(f"\n{'#' * min(depth + 4, 6)} {prop_text(props.get('title')) or '(без названия)'}\n")
        for k, n in names.items():
            if k == "title":
                continue
            v = prop_text(props.get(k))
            if v:
                lines.append(f"- **{n}:** {v}")
        if depth < max_depth and r.get("content"):
            load_page(rid)
            for k in blocks.get(rid, {}).get("content") or []:
                render(k, depth + 1, 0, lines, max_depth)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--source", default="")
    ap.add_argument("--depth", type=int, default=2)
    a = ap.parse_args()
    pid = uuid(a.url)
    load_page(pid)
    root = blocks.get(pid, {})
    lines = []
    if root.get("type") in ("collection_view_page", "collection_view"):
        render_collection(root, 0, lines, a.depth)
        head = rich(collections.get(root.get("collection_id"), {}).get("name"))
    else:
        head = title_of(root)
        for k in root.get("content") or []:
            render(k, 0, 0, lines, a.depth)
    body = "\n".join(lines)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    meta = (f"<!-- Источник: {a.url}\n     {a.source}\n     Выгружено {time.strftime('%d.%m.%Y')} через публичный API Notion "
            f"(_scripts/notion_export.py). Картинки и видео не выгружены (помечены [картинка]/[видео]).\n"
            f"     Платный материал — только для внутреннего использования, не публиковать. -->\n\n")
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(meta + f"# {head}\n\n" + body + "\n")
    print(f"{a.out}: {len(body.splitlines())} строк, блоков загружено {len(blocks)}")


if __name__ == "__main__":
    main()
