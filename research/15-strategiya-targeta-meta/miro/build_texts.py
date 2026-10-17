#!/usr/bin/env python3
"""Фреймы с полными текстами для Miro: «Тексты рекламных креативов» и «Тексты под постами».

Каждый тип креатива (и каждая группа текстов под постами) — отдельный документ
Miro (doc-виджет, markdown). Документы стоят в ряд внутри фрейма.

Запуск:
    python3 build_texts.py creatives out_b.svg --static texts-static.json --video texts-video.json --x X --y Y
    python3 build_texts.py posts out_c.svg --posts texts-posts.json --x X --y Y
"""
import argparse
import html
import json

DOC_W = 784
GAP = 64
PAD = 64
HEADER_H = 220
FRAME_H = 3600   # уточняется после создания по data-rendered-bounds


def md_escape(text):
    return html.escape(str(text or ""), quote=False)


def line(label, value):
    return f"**{label}:** {value}" if value else ""


def static_text_md(t):
    head = f"## Текст {t['id']} · {t.get('job', '')} · {t.get('formula', '')}"
    parts = [
        head,
        line("Хук", t.get("hook")),
        line("Заголовок на креативе", t.get("headline")),
        line("Подзаголовок", t.get("subline")),
        line("Плашка", t.get("badge")),
        line("Кнопка", t.get("cta")),
        line("Визуал", t.get("visual")),
        line("utm_content", t.get("utm_content")),
        line("Почему сработает", t.get("why")),
        line("Источник цифр", t.get("sources")),
    ]
    return "\n\n".join(p for p in parts if p)


def video_text_md(t):
    head = f"## Сценарий {t['id']} · {t.get('job', '')} · {t.get('formula', '')}"
    parts = [
        head,
        line("Хук", t.get("hook")),
        line("Спикер", t.get("speaker")),
        line("Длительность", t.get("duration")),
    ]
    for scene in t.get("scenes", []):
        bits = [f"**{scene.get('t', '')}.**"]
        if scene.get("say"):
            bits.append(f"Говорит: «{scene['say']}»")
        if scene.get("screen"):
            bits.append(f"Текст на экране: «{scene['screen']}»")
        if scene.get("shot"):
            bits.append(f"Кадр: {scene['shot']}")
        parts.append(" ".join(bits))
    parts += [
        line("Призыв", t.get("cta")),
        line("utm_content", t.get("utm_content")),
        line("Почему сработает", t.get("why")),
        line("Источник цифр", t.get("sources")),
    ]
    return "\n\n".join(p for p in parts if p)


def type_doc(ctype, is_video):
    lines = [f"# {ctype['id']} {ctype['title']}"]
    meta = [line("Формат", ctype.get("format")), line("Джобы", ctype.get("jobs"))]
    lines += [m for m in meta if m]
    for t in ctype.get("texts", []):
        lines.append(video_text_md(t) if is_video else static_text_md(t))
    return "\n\n".join(lines)


def post_md(p):
    head = f"## {p['id']} · {p.get('formula', '')} · {p.get('length', '')}"
    primary = str(p.get("primary_text", "")).replace("\n", "  \n")
    parts = [
        head,
        f"**Основной текст:**  \n{primary}",
        line("Заголовок", p.get("headline")),
        line("Описание", p.get("description")),
        line("Кнопка", p.get("button")),
        line("Подходит к креативам", ", ".join(p.get("fits", []))),
        line("Почему сработает", p.get("why")),
        line("Источник цифр", p.get("sources")),
    ]
    return "\n\n".join(x for x in parts if x)


def doc_svg(doc_id, x, y, markdown):
    return (
        f'<foreignObject id="{doc_id}" x="{x}" y="{y}" width="{DOC_W}" height="1105" data-type="doc">\n'
        f"{md_escape(markdown)}\n</foreignObject>"
    )


def frame_svg(frame_id, title, subtitle, docs, origin):
    fx, fy = origin
    width = PAD * 2 + len(docs) * DOC_W + (len(docs) - 1) * GAP
    t = html.escape(title, quote=True)
    out = ['<svg xmlns="http://www.w3.org/2000/svg">']
    out.append(f'<g id="{frame_id}" transform="translate({fx},{fy})" data-frame="{t}">')
    out.append(f'<rect data-type="frame" x="0" y="0" width="{width}" height="{FRAME_H}" fill="#ffffff" data-title="{t}" />')
    out.append(f'<textArea id="{frame_id}_hdr" x="{PAD}" y="{PAD}" width="{width - 2 * PAD}" fill="#1a1a1a" font-family="noto_sans" font-size="67" font-weight="bold">{t}</textArea>')
    out.append(f'<textArea id="{frame_id}_sub" x="{PAD}" y="{PAD + 100}" width="{width - 2 * PAD}" fill="#595959" font-family="noto_sans" font-size="33">{html.escape(subtitle, quote=False)}</textArea>')
    for i, (doc_id, markdown) in enumerate(docs):
        out.append(doc_svg(doc_id, PAD + i * (DOC_W + GAP), PAD + HEADER_H, markdown))
    out.append("</g>")
    out.append("</svg>")
    return "\n".join(out), width


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["creatives", "posts"])
    ap.add_argument("out")
    ap.add_argument("--static")
    ap.add_argument("--video")
    ap.add_argument("--posts")
    ap.add_argument("--x", type=int, required=True)
    ap.add_argument("--y", type=int, required=True)
    args = ap.parse_args()
    docs = []
    if args.kind == "creatives":
        for path, is_video in ((args.static, False), (args.video, True)):
            if not path:
                continue
            for ctype in json.load(open(path))["types"]:
                docs.append((f"doc_{ctype['id'].replace('.', '_')}", type_doc(ctype, is_video)))
        title = "Тексты рекламных креативов"
        subtitle = "По 3–4 текста на каждый тип креатива. У каждого — джоб, формула, хук и метка utm_content под заголовок лендинга. Русская версия на согласование, узбекская — после."
        frame_id = "fB"
    else:
        data = json.load(open(args.posts))
        groups = {}
        for p in data["posts"]:
            groups.setdefault(p.get("job", "Общие"), []).append(p)
        for job, posts in groups.items():
            body = [f"# Тексты под постами · {job}"]
            body += [post_md(p) for p in posts]
            docs.append((f"doc_p_{job}".replace(" ", "_"), "\n\n".join(body)))
        if data.get("cheatsheet"):
            docs.append(("doc_p_formulas", data["cheatsheet"]))
        title = "Тексты под постами"
        subtitle = "Основной текст, заголовок и описание для объявлений. Сгруппированы по джобам, у каждого текста — формула и длина."
        frame_id = "fC"
    svg, width = frame_svg(frame_id, title, subtitle, docs, (args.x, args.y))
    open(args.out, "w").write(svg)
    print(f"{args.kind}: документов {len(docs)}, ширина фрейма {width}, SVG {len(svg)} символов → {args.out}")


if __name__ == "__main__":
    main()
