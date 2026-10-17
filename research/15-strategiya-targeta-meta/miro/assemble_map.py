#!/usr/bin/env python3
"""Собирает итоговое дерево карты: map.json стратега + ветки с текстами.

В map.json ветки «Тексты рекламных креативов» и «Тексты под постами»
содержат заглушки __CREATIVES__ и __POSTS__. Сюда подставляются короткие
узлы по каждому тексту (id, джоб, формула, заголовок) со ссылками на
документы во фреймах с полными текстами.

Запуск:
    python3 assemble_map.py map.json final.json --static ../04-texts-static.json \
        --video ../04-texts-video.json --posts ../05-texts-posts.json [--links links.json]
links.json — {"doc_1_1": "<miro id>", ..., "doc_p_J1": "<miro id>"} после создания фреймов B и C.
"""
import argparse
import json

BOARD = "https://miro.com/app/board/uXjVHjwddk0=/?moveToWidget="
MAX_WORDS = 12

TYPE_SHORT = {
    "1.1": "1.1 Эксперт на картинке",
    "1.2": "1.2 Вопрос-ответ",
    "1.3": "1.3 Текст и фон",
    "2": "2 Красивые дизайны",
    "3": "3 Обращения спикера",
}


def texts_word(n):
    if n % 10 == 1 and n % 100 != 11:
        return "текст"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "текста"
    return "текстов"


def short(text, words=MAX_WORDS):
    parts = str(text or "").replace("\n", " ").split()
    return " ".join(parts[:words]) + ("…" if len(parts) > words else "")


def text_label(t, is_video):
    title = t.get("hook") if is_video else (t.get("headline") or t.get("hook"))
    ab = " (A/B)" if t.get("ab_of") else ""
    wave = " · 2-я волна" if str(t.get("wave", "1")) == "2" else ""
    return f"{t['id']}{ab} · {t.get('job', '')} · {t.get('formula', '')}{wave}\n«{short(title)}»"


def creatives_children(static_path, video_path, links):
    kids = []
    for path, is_video in ((static_path, False), (video_path, True)):
        if not path:
            continue
        for ctype in json.load(open(path))["types"]:
            texts = ctype.get("texts", [])
            doc_key = f"doc_{ctype['id'].replace('.', '_')}"
            node = {
                "title": f"{TYPE_SHORT.get(ctype['id'], ctype['id'] + ' ' + ctype['title'])}: {len(texts)} {texts_word(len(texts))}\nполные тексты →",
                "bold_first": True,
                "children": [{"title": text_label(t, is_video)} for t in texts],
            }
            if links.get(doc_key):
                node["link"] = BOARD + links[doc_key]
            kids.append(node)
    return kids


def posts_children(posts_path, links):
    data = json.load(open(posts_path))
    groups = {}
    for p in data["posts"]:
        groups.setdefault(p.get("job", "Общие"), []).append(p)
    kids = []
    for job, posts in groups.items():
        doc_key = f"doc_p_{job}".replace(" ", "_")
        node = {
            "title": f"{job}: {len(posts)} {texts_word(len(posts))}\nполные тексты →",
            "bold_first": True,
            "children": [
                {"title": f"{p['id']}{' (A/B)' if p.get('ab_of') else ''} · {p.get('formula', '')} · {p.get('length', '')}\n«{short(p.get('headline') or p.get('primary_text'))}»"}
                for p in posts
            ],
        }
        if links.get(doc_key):
            node["link"] = BOARD + links[doc_key]
        kids.append(node)
    if data.get("cheatsheet"):
        node = {"title": "Шпаргалка формул →"}
        if links.get("doc_p_formulas"):
            node["link"] = BOARD + links["doc_p_formulas"]
        kids.append(node)
    return kids


def replace_placeholder(tree, marker, children):
    for br in tree["branches"]:
        if any(k.get("title") == marker for k in br.get("children", [])):
            br["children"] = children
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("map")
    ap.add_argument("out")
    ap.add_argument("--static")
    ap.add_argument("--video")
    ap.add_argument("--posts")
    ap.add_argument("--links")
    args = ap.parse_args()
    tree = json.load(open(args.map))
    links = json.load(open(args.links)) if args.links else {}
    ok_c = replace_placeholder(tree, "__CREATIVES__", creatives_children(args.static, args.video, links))
    ok_p = replace_placeholder(tree, "__POSTS__", posts_children(args.posts, links))
    json.dump(tree, open(args.out, "w"), ensure_ascii=False, indent=1)
    print(f"креативы подставлены: {ok_c}, посты подставлены: {ok_p} → {args.out}")


if __name__ == "__main__":
    main()
