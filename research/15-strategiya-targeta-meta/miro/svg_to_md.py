"""Достаёт текст из выгрузки canvas_read_as_svg (Miro MCP) и пишет markdown.

Порядок: сверху вниз, слева направо (по абсолютным координатам).
Запуск: python3 svg_to_md.py <json-файл выгрузки> <выходной .md> "<название фрейма>" "<ссылка>"
"""
import html
import json
import re
import sys
import xml.etree.ElementTree as ET

TAG_RE = re.compile(r"<[^>]+>")


def clean(text):
    text = html.unescape(text or "")
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</(p|li|div)>", "\n", text)
    text = re.sub(r"<li>", "• ", text)
    text = TAG_RE.sub("", text)
    text = html.unescape(text)
    lines = [l.strip() for l in text.split("\n")]
    return "\n".join(l for l in lines if l)


def collect(node, ox, oy, out):
    tag = node.tag.split("}")[-1]
    tr = node.attrib.get("transform", "")
    m = re.match(r"translate\(([-\d.]+),\s*([-\d.]+)\)", tr)
    if tag == "g" and m:
        ox, oy = ox + float(m.group(1)), oy + float(m.group(2))
    x = float(node.attrib.get("x", 0) or 0) + ox
    y = float(node.attrib.get("y", 0) or 0) + oy
    text = ""
    if tag in ("textArea", "text"):
        text = "".join(node.itertext()) if len(node) else (node.text or "")
        if len(node):
            text = ET.tostring(node, encoding="unicode", method="xml")
            text = re.sub(r"^<[^>]+>|</[^>]+>$", "", text)
    elif node.attrib.get("data-content"):
        text = node.attrib["data-content"]
    elif node.attrib.get("data-title") and tag not in ("rect",) :
        text = node.attrib["data-title"]
    elif tag == "foreignObject":
        text = "".join(node.itertext())
    if tag == "line":
        text = ""
    t = clean(text)
    if t:
        out.append((round(y / 40), x, t))
    for child in list(node):
        collect(child, ox, oy, out)


def main():
    src, dst, title, url = sys.argv[1:5]
    raw = open(src).read()
    data = json.loads(raw)
    svg = data["svg"]
    root = ET.fromstring(svg)
    out = []
    for child in list(root):
        collect(child, 0, 0, out)
    out.sort(key=lambda r: (r[0], r[1]))
    with open(dst, "w") as f:
        f.write(f"# Miro: {title}\n\nИсточник: [доска Miro]({url}). Выгрузка через Miro MCP (canvas_read_as_svg) 10.10.2026. Текст по порядку на доске: сверху вниз, слева направо.\n\n---\n\n")
        for _, _, t in out:
            f.write(t + "\n\n")
    print(dst, len(out), "блоков", sum(len(t) for _, _, t in out), "символов")


if __name__ == "__main__":
    main()
