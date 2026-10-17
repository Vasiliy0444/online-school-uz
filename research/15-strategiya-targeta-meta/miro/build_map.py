#!/usr/bin/env python3
"""Генератор mind map «Узбекистан трафик» для Miro (формат canvas-composer SVG).

Берёт дерево карты из JSON и рисует его по шаблону Васи: центр — крупный
текст без плашки, ветки первого уровня — цветные скруглённые плашки, линии
изогнутые и в цвет ветки, глубже — светлые оттенки цвета ветки.

Запуск:
    python3 build_map.py map.json out.svg [--state state.json]

Если передан state.json (соответствие «путь узла → data-miro-id» после
первой отправки), узлы с известным id выходят как правки, а не как новые.
"""
import argparse
import colorsys
import html
import json
import math

FONT = "noto_sans"

# Ширина узла, шрифт и внутренний отступ по уровням
LEVEL_STYLE = {
    1: {"w": 560, "fs": 36, "bold": True, "pad": 26},
    2: {"w": 560, "fs": 26, "bold": False, "pad": 20},
    3: {"w": 600, "fs": 22, "bold": False, "pad": 18},
    4: {"w": 640, "fs": 20, "bold": False, "pad": 16},
}
CENTER = {"w": 760, "h": 260, "fs": 72}
H_GAP = {1: 200, 2: 120, 3: 100, 4: 90}   # от родителя до ребёнка по горизонтали
V_GAP = 24                                 # между соседними узлами
BRANCH_V_GAP = 140                         # между ветками первого уровня
FRAME_PAD = 160
HEADER_H = 260
CHAR_W = 0.56                              # средняя ширина буквы в долях шрифта
LINE_H = 1.42


def hex_to_hls(hexc):
    hexc = hexc.lstrip("#")
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)


def hls_to_hex(h, l, s):
    r, g, b = colorsys.hls_to_rgb(h, max(0, min(1, l)), max(0, min(1, s)))
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def darker(hexc):
    """Обводка: светлота ×0,7, насыщенность ×1,1 — правило из скилла Miro."""
    h, l, s = hex_to_hls(hexc)
    return hls_to_hex(h, l * 0.7, s * 1.1)


def ink(hexc):
    """Цвет текста того же оттенка: светлота около 22%."""
    h, _, s = hex_to_hls(hexc)
    return hls_to_hex(h, 0.22, min(1, s * 0.9))


def tint(hexc, amount):
    """Смешать с белым: amount=0 — исходный цвет, 1 — белый."""
    hexc = hexc.lstrip("#")
    rgb = [int(hexc[i:i + 2], 16) for i in (0, 2, 4)]
    mixed = [round(c + (255 - c) * amount) for c in rgb]
    return "#%02x%02x%02x" % tuple(mixed)


def count_lines(text, width, fs, pad):
    per_line = max(8, int((width - 2 * pad) / (fs * CHAR_W)))
    total = 0
    for para in text.split("\n"):
        words = para.split()
        if not words:
            total += 1
            continue
        lines, cur = 1, 0
        for word in words:
            size = len(word)
            if cur == 0:
                cur = size
            elif cur + 1 + size <= per_line:
                cur += 1 + size
            else:
                lines += 1
                cur = size
        total += lines
    return total


def style_for(level):
    return LEVEL_STYLE[min(level, 4)]


def measure(node, level, path):
    node["level"] = level
    node["path"] = path
    st = style_for(level)
    node["w"] = node.get("width") or st["w"]
    lines = count_lines(node["title"], node["w"], st["fs"], st["pad"])
    node["h"] = math.ceil(lines * st["fs"] * LINE_H + 2 * st["pad"])
    kids = node.get("children", [])
    for i, kid in enumerate(kids):
        measure(kid, level + 1, f"{path}.{i + 1}")
    if kids:
        kids_h = sum(k["sub_h"] for k in kids) + V_GAP * (len(kids) - 1)
        node["sub_h"] = max(node["h"], kids_h)
    else:
        node["sub_h"] = node["h"]


def place(node, edge_x, top, side):
    """edge_x — край узла, обращённый к родителю."""
    center_y = top + node["sub_h"] / 2
    node["x"] = edge_x if side == "right" else edge_x - node["w"]
    node["y"] = center_y - node["h"] / 2
    node["side"] = side
    kids = node.get("children", [])
    if not kids:
        return
    kids_h = sum(k["sub_h"] for k in kids) + V_GAP * (len(kids) - 1)
    y = center_y - kids_h / 2
    gap = H_GAP[min(node["level"] + 1, 4)]
    next_edge = node["x"] + node["w"] + gap if side == "right" else node["x"] - gap
    for kid in kids:
        place(kid, next_edge, y, side)
        y += kid["sub_h"] + V_GAP


def walk(node):
    yield node
    for kid in node.get("children", []):
        yield from walk(kid)


def layout(tree):
    for i, br in enumerate(tree["branches"]):
        measure(br, 1, f"b{i + 1}")
    cx, cy = 0.0, 0.0
    for side in ("right", "left"):
        branches = [b for b in tree["branches"] if b["side"] == side]
        branches.sort(key=lambda b: b.get("pos", tree["branches"].index(b)))
        total = sum(b["sub_h"] for b in branches) + BRANCH_V_GAP * (len(branches) - 1)
        y = cy - total / 2
        edge = cx + CENTER["w"] / 2 + H_GAP[1] if side == "right" else cx - CENTER["w"] / 2 - H_GAP[1]
        for br in branches:
            place(br, edge, y, side)
            y += br["sub_h"] + BRANCH_V_GAP
    nodes = [n for br in tree["branches"] for n in walk(br)]
    min_x = min(min(n["x"] for n in nodes), cx - CENTER["w"] / 2)
    max_x = max(max(n["x"] + n["w"] for n in nodes), cx + CENTER["w"] / 2)
    min_y = min(min(n["y"] for n in nodes), cy - CENTER["h"] / 2)
    max_y = max(max(n["y"] + n["h"] for n in nodes), cy + CENTER["h"] / 2)
    dx = FRAME_PAD - min_x
    dy = FRAME_PAD + HEADER_H - min_y
    for n in nodes:
        n["x"] = round(n["x"] + dx)
        n["y"] = round(n["y"] + dy)
    center = {
        "x": round(cx - CENTER["w"] / 2 + dx),
        "y": round(cy - CENTER["h"] / 2 + dy),
    }
    width = round(max_x - min_x + 2 * FRAME_PAD)
    height = round(max_y - min_y + 2 * FRAME_PAD + HEADER_H)
    return nodes, center, width, height


def esc_attr(text):
    """Текст узла → значение data-content: переносы строк → <br>, всё экранировано."""
    parts = [html.escape(line, quote=True) for line in text.split("\n")]
    return "&lt;br&gt;".join(parts)


def palette(branch):
    """Цвета ветки: заливка, обводка, линия, текст. Можно переопределить в JSON."""
    color = branch["color"]
    h, l, s = hex_to_hls(color)
    return {
        "fill": color,
        "stroke": branch.get("stroke") or hls_to_hex(h, l * 0.8, s),
        "line": branch.get("line") or color,
        "ink": branch.get("ink") or ink(color),
    }


def colors_for(node, pal):
    if node["level"] == 1:
        fill = pal["fill"]
    elif node["level"] == 2:
        fill = tint(pal["fill"], 0.62)
    else:
        fill = tint(pal["fill"], 0.84)
    return fill, pal["stroke"], pal["ink"]


def miro_attr(state, path):
    mid = state.get(path)
    return f' data-miro-id="{mid}"' if mid else ""


def node_svg(node, pal, state):
    st = style_for(node["level"])
    fill, stroke, text_color = colors_for(node, pal)
    align = "center" if node["level"] == 1 or node.get("center") else "left"
    content = node["title"]
    if node.get("link"):
        label = html.escape(content.split("\n")[0], quote=True)
        rest = "\n".join(content.split("\n")[1:])
        anchor = f'&lt;a href=&quot;{html.escape(node["link"], quote=True)}&quot;&gt;{label}&lt;/a&gt;'
        data_content = anchor + ("&lt;br&gt;" + esc_attr(rest) if rest else "")
    else:
        data_content = esc_attr(content)
    if node.get("bold_first") and "\n" in content:
        first, rest = content.split("\n", 1)
        rest_html = esc_attr(rest)
        if node.get("link"):
            href = html.escape(node["link"], quote=True)
            rest_html = f'&lt;a href=&quot;{href}&quot;&gt;{rest_html}&lt;/a&gt;'
        data_content = f"&lt;b&gt;{html.escape(first, quote=True)}&lt;/b&gt;&lt;br&gt;{rest_html}"
    weight = "bold" if st["bold"] else "normal"
    nid = "n_" + node["path"].replace(".", "_")
    return (
        f'<rect id="{nid}"{miro_attr(state, node["path"])} x="{node["x"]}" y="{node["y"]}" '
        f'width="{node["w"]}" height="{node["h"]}" rx="16" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="2" data-text-color="{text_color}" data-font-family="{FONT}" '
        f'data-font-size="{st["fs"]}" data-font-weight="{weight}" data-text-align="{align}" '
        f'data-text-align-vertical="middle" data-content="{data_content}" />'
    )


def connector_svg(parent_id, child, pal, state):
    side = child["side"]
    start_side, end_side = ("right", "left") if side == "right" else ("left", "right")
    width = 4 if child["level"] == 1 else 3 if child["level"] == 2 else 2
    cid = "c_" + child["path"].replace(".", "_")
    stroke = pal["line"] if child["level"] == 1 else pal["stroke"]
    return (
        f'<line id="{cid}"{miro_attr(state, "c:" + child["path"])} x1="0" y1="0" x2="1" y2="1" '
        f'data-start="{parent_id}" data-end="n_{child["path"].replace(".", "_")}" '
        f'stroke="{stroke}" stroke-width="{width}" data-shape="curved" '
        f'data-start-side="{start_side}" data-end-side="{end_side}" />'
    )


def build(tree, state, origin):
    nodes, center, width, height = layout(tree)
    fx, fy = origin
    title = html.escape(tree["frame_title"], quote=True)
    out = ['<svg xmlns="http://www.w3.org/2000/svg">']
    out.append(f'<g id="fA"{miro_attr(state, "frame")} transform="translate({fx},{fy})" data-frame="{title}">')
    out.append(f'<rect data-type="frame" x="0" y="0" width="{width}" height="{height}" fill="#ffffff" data-title="{title}" />')
    header = html.escape(tree["header"], quote=True)
    sub = html.escape(tree["subheader"], quote=True)
    out.append(f'<textArea id="hdr"{miro_attr(state, "hdr")} x="{FRAME_PAD}" y="64" width="{width - 2 * FRAME_PAD}" fill="#1a1a1a" font-family="{FONT}" font-size="67" font-weight="bold">{header}</textArea>')
    out.append(f'<textArea id="sub"{miro_attr(state, "sub")} x="{FRAME_PAD}" y="164" width="{width - 2 * FRAME_PAD}" fill="#595959" font-family="{FONT}" font-size="33">{sub}</textArea>')
    # линии раньше узлов, чтобы узлы лежали поверх
    for br in tree["branches"]:
        pal = palette(br)
        out.append(connector_svg("n_center", br, pal, state))
        for node in walk(br):
            for kid in node.get("children", []):
                out.append(connector_svg("n_" + node["path"].replace(".", "_"), kid, pal, state))
    center_text = esc_attr(tree["title"])
    out.append(
        f'<rect id="n_center"{miro_attr(state, "center")} x="{center["x"]}" y="{center["y"]}" '
        f'width="{CENTER["w"]}" height="{CENTER["h"]}" fill="#ffffff" stroke="none" '
        f'data-text-color="#1a1a1a" data-font-family="{FONT}" data-font-size="{CENTER["fs"]}" '
        f'data-font-weight="bold" data-text-align="center" data-text-align-vertical="middle" '
        f'data-content="{center_text}" />'
    )
    for br in tree["branches"]:
        pal = palette(br)
        for node in walk(br):
            out.append(node_svg(node, pal, state))
    out.append("</g>")
    out.append("</svg>")
    return "\n".join(out), nodes, center, width, height


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tree")
    parser.add_argument("out")
    parser.add_argument("--state")
    parser.add_argument("--x", type=int, default=48200)
    parser.add_argument("--y", type=int, default=0)
    args = parser.parse_args()
    tree = json.load(open(args.tree))
    state = json.load(open(args.state)) if args.state else {}
    svg, nodes, center, width, height = build(tree, state, (args.x, args.y))
    open(args.out, "w").write(svg)
    layout_dump = {n["path"]: {"x": n["x"], "y": n["y"], "w": n["w"], "h": n["h"], "title": n["title"][:60]} for n in nodes}
    layout_dump["center"] = center
    layout_dump["frame"] = {"x": args.x, "y": args.y, "w": width, "h": height}
    json.dump(layout_dump, open(args.out + ".layout.json", "w"), ensure_ascii=False, indent=1)
    print(f"узлов: {len(nodes)}, фрейм {width}×{height}, SVG {len(svg)} символов → {args.out}")


if __name__ == "__main__":
    main()
