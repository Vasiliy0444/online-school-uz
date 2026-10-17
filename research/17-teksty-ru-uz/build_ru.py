#!/usr/bin/env python3
"""Собирает один документ «Тексты таргета УЗ — RU» из JSON стратегии.

Источник правды — JSON в ../15-strategiya-targeta-meta/ (по ним же строится доска Miro).
Правки Васи вносим в эти JSON, потом запускаем скрипт заново.

    python3 build_ru.py            # пишет 01-RU-на-согласование.md рядом со скриптом
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "15-strategiya-targeta-meta"
OUT = HERE / "01-RU-на-согласование.md"

STATIC_TITLES = {
    "1.1": "Инста: эксперт на фото",
    "1.2": "Инста: вопрос-ответ",
    "1.3": "Инста: текст на фоне",
    "2": "Красивые карусели",
}


def load(name):
    return json.loads((SRC / name).read_text(encoding="utf-8"))


def job_names():
    names = {}
    for job in load("01-djoby.json")["jobs"]:
        m = re.search(r"«([^»]+)»", job["segment"])
        names[job["id"]] = m.group(1) if m else job["title"]
    return names


def quote(text):
    return "\n".join(f"> {line}" if line else ">" for line in text.split("\n"))


def field(label, value):
    return f"- **{label}:** {value}" if value else ""


def ab_note(item):
    return f" · **B-вариант к {item['ab_of']}**" if item.get("ab_of") else ""


def render_posts(jobs):
    out = ["# Часть 1. Тексты под постами (Instagram и Facebook)", ""]
    out.append(
        "Это текст, который стоит над картинкой или видео. «Длинный» — до 900 знаков, "
        "только в ленту; «короткий» — первые ~125 знаков видны до «ещё». "
        "Пары с буквой b — вторая версия для A/B-теста.\n"
    )
    for p in load("05-texts-posts.json")["posts"]:
        out.append(
            f"## {p['id']} · {p['length']} · {jobs[p['job']]}{ab_note(p)}"
        )
        out.append(f"*Аудитория: {p['audience']}. Формула: {p['formula']}.*")
        out.append("")
        out.append("**Основной текст:**")
        out.append(quote(p["primary_text"]))
        out.append("")
        out.append(field("Заголовок", p["headline"]))
        out.append(field("Описание", p["description"]))
        out.append(field("Кнопка", p["button"]))
        out.append("")
    return out


def render_card(card):
    lines = [f"  {card['n']}. **{card['title']}**"]
    if card.get("text"):
        lines.append(f"     {card['text']}")
    if card.get("small"):
        lines.append(f"     *Мелко:* {card['small']}")
    if card.get("cta"):
        lines.append(f"     *Кнопка на карточке:* {card['cta']}")
    return lines


def render_static(jobs):
    out = ["# Часть 2. Тексты на картинках", ""]
    out.append(
        "Что написано прямо на картинке. Кнопку Meta («Подробнее» / «Зарегистрироваться») "
        "свой текст не принимает, поэтому призыв стоит на самой картинке.\n"
    )
    for ctype in load("04-texts-static.json")["types"]:
        out.append(f"## Тип {ctype['id']} — {STATIC_TITLES[ctype['id']]}")
        out.append("")
        for t in ctype["texts"]:
            out.append(f"### {t['id']} · {jobs[t['job']]}{ab_note(t)}")
            out.append(field("Заголовок", t["headline"]))
            out.append(field("Подзаголовок", t["subline"]))
            out.append(field("Плашка", t["badge"]))
            out.append(field("Призыв на картинке", t["cta"]))
            if t["small_print"]:
                out.append(field("Мелкий текст", " / ".join(t["small_print"])))
            if t["on_image_extra"]:
                out.append(field("Ещё на картинке", " / ".join(t["on_image_extra"])))
            if t.get("cards"):
                out.append("")
                out.append("**Карточки карусели:**")
                for card in t["cards"]:
                    out.extend(render_card(card))
            out.append("")
    return out


def render_video(jobs):
    video = load("04-texts-video.json")
    extras = video["extras"]
    out = ["# Часть 3. Видео-обращения спикера", ""]
    out.append(
        "Что говорит человек в кадре и что написано на экране. "
        "Как снимать — в `ТЕКСТЫ-КРЕАТИВОВ-ВИДЕО.md`.\n"
    )
    for t in video["types"][0]["texts"]:
        out.append(
            f"## {t['id']} · {t['speaker']} · {t['duration']} · {jobs[t['job']]}{ab_note(t)}"
        )
        out.append("")
        out.append("| Время | Говорит | На экране |")
        out.append("|---|---|---|")
        for s in t["scenes"]:
            out.append(f"| {s['t']} | {s['say']} | {s['screen']} |")
        out.append("")
        out.append(field("Призыв", t["cta"]))
        post_text = extras.get(t["id"], {}).get("post_text")
        if post_text:
            out.append(field("Текст под видео", post_text))
        out.append("")
    return out


DECISIONS = [
    "**$1000.** Сейчас цифра есть в P2, P5, P7, 1.1-2, 1.2-4, 1.3-1, 2-1 и 3-3. В постах — только расчётом "
    "«3–4 заказа по $300» и с оговоркой «доход зависит от твоих действий». 4 из 6 кастдевов "
    "рекламе про $1000 не верят. Оставляем так или выносим «от 0 до $1000» в заголовки?",
    "**Пары A/B.** P2 / P2b, P6 / P6b, P7 / P7b, 1.1-2 / 1.1-2b, 1.2-4 / 1.2-4b, 1.3-1 / 1.3-1b, "
    "2-1 / 2-1b, 3-1 / 3-1b. Какие запускаем, какие убираем?",
    "**Цифры Яндекс Карт** (146 из 300 в Ташкенте, 718 из 784 в 8 городах) стоят в P4, P9, P12, "
    "1.1-4, 1.2-1, 2-3, 2-4, 3-3 и 3-4. Таблицы проверки от 05.10 в проекте нет, "
    "поэтому цифры не доказать. До запуска нужна таблица: дата, города, ниши, ссылки на карточки.",
    "**Строка про такси «через год» в 2-1 и 2-1b.** A — «платят за часы за рулём», "
    "B — «тот же таксист, только машина старше».",
    "**Правки руководителя «по желанию».** 1.1-1: убрать сообщение-вопрос «А получится, если я не "
    "программист?» (на картинке два вопроса подряд). 1.3-1: плашку «Считаем открыто» заменить на "
    "«Бесплатно, в Telegram».",
    "**Живой кейс.** В 3-1, 2-2, 1.2-3, 1.2-4b, 1.1-1 нужна настоящая компания с Яндекс Карт без сайта "
    "и согласие владельца. В 3-1 в скобках стоит заглушка [автосервиса].",
    "**Узбекская речь в видео.** Кто говорит по-узбекски в 3-4 и в основной версии 3-2? "
    "Русская речь с узбекскими субтитрами — вопрос юристу (закон о рекламе ЗРУ-776).",
]


def render_decisions():
    out = ["# Что решить кроме правок текста", ""]
    out += [f"{i}. {item}" for i, item in enumerate(DECISIONS, start=1)]
    out.append("")
    return out


def main():
    jobs = job_names()
    lines = [
        "# Тексты таргета Узбекистан — на согласование (русский)",
        "",
        "Онлайн-профессия AI-специалиста, вход — бесплатный мини-курс в Telegram. "
        "Всего: 15 текстов под постами, 20 текстов на картинках, 5 видео.",
        "",
        "**Как давать правки:** по номеру. «P3: заменить заголовок на …», «1.2-2: убрать». "
        "Хорошо бы сразу сказать, какие пары A/B оставляем.",
        "",
    ]
    lines += render_posts(jobs)
    lines += render_static(jobs)
    lines += render_video(jobs)
    lines += render_decisions()
    OUT.write_text("\n".join(l for l in lines) + "\n", encoding="utf-8")
    print(f"записано: {OUT}")


if __name__ == "__main__":
    main()
