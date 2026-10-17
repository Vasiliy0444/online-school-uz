"""Раскладывает готовые креативы (render/uz) по папкам + превью-листы.

«АКТУАЛЬНЫЕ креативы УЗ — Meta» в папке проекта — всё, что проверил носитель (15.10 и 17.10.2026),
пересобирается целиком. С 17.10 папка живёт здесь, а не на рабочем столе: Вася разобрал стол по CURSOR.
PENDING (нет в проверке носителя) — папкой «На перевод — …» внутри неё вместе с docx для переводчика.

python3 package.py
"""
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import native_fixes as NF

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "render" / "uz"
DEST = ROOT / "АКТУАЛЬНЫЕ креативы УЗ — Meta"
PENDING = []  # I1-3, I1-3B, I3-2 носитель проверил 17.10.2026
PENDING_DEST = DEST / f"На перевод — {', '.join(PENDING)}"
NATIVE_DOCX = ROOT / "Тексты креативов UZ-RU — проверено носителем 2026-10-15.docx"
NATIVE_DOCX_1017 = ROOT / "Тексты креативов I1-3, I1-3B, I3-2 — проверено носителем 2026-10-17.docx"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
# Зелёная метка Finder ставится цветом (номер 2), а не именем тега:
# в реестре тегов этого Mac имя «绿色» привязано к серому.
LABEL_JS = ("ObjC.import('Foundation'); function run(argv) { return $.NSURL.fileURLWithPath(argv[0])"
            ".setResourceValueForKeyError($(2), $.NSURLLabelNumberKey, null); }")

GROUPS = [
    ("01 Инста — эксперт на фото", ["I1-1", "I1-2", "I1-3", "I1-3B", "I1-4"]),
    ("02 Инста — вопрос-ответ", ["I2-1", "I2-2", "I2-3", "I2-4"]),
    ("03 Инста — текст и фон", ["I3-1", "I3-2", "I3-3"]),
    ("04 Мемы", ["M1", "M3", "M4", "M5", "M6", "M7", "M2"]),
    ("05 Видео", ["V1", "V2"]),
    ("06 Красивые — карусели 1x1", ["K2-1", "K2-1b", "K2-3", "K2-4"]),
    ("08 Инста — короткие тексты (A-B)", ["I1-1S", "I1-2S", "I2-1S", "I2-2S", "I2-3S", "I2-4S", "I3-1S", "I3-3S"]),
]
SRC_SHORT = ROOT / "render" / "uz_short"
MONTAGE = ROOT / "montage-remotion" / "out"
RATIO = {"story": "9x16", "feed": "4x5"}
DOCS = {
    "README-папки.md": "_АКТУАЛЬНО — прочитай первым.md",
    NATIVE_DOCX.name: "Тексты креативов — UZ, проверено носителем 15.10.docx",
    NATIVE_DOCX_1017.name: "Тексты креативов I1-3, I1-3B, I3-2 — UZ, проверено носителем 17.10.docx",
}


def hint(cid: str, ru: dict) -> str:
    c = ru.get(cid) or ru.get(cid.rstrip("S"))
    if not c:
        return ""
    f = c["fields_ru"]
    t = f.get("headline") or f.get("question") or f.get("top") or f.get("title_line1") or f.get("line1") or (f.get("scenes") or [""])[0] or f.get("caption") or ""
    if cid == "M1":
        t = "Научись создавать сайты"
    if cid == "M2":
        t = "Пишем от руки"
    t = "".join(ch for ch in t if ch not in '/\\:*?"<>|«»').strip()
    words = t.split()[:6]
    while words and words[-1].lower() in {"в", "на", "и", "за", "по", "с", "до", "вообще", "хочу"}:
        words.pop()
    return " ".join(words).rstrip(",.—- ")


def sheet(files, out: Path, cell=(300, 533)):
    files = [f for f in files if f.suffix == ".png"]
    if not files:
        return
    cols = min(6, len(files))
    rows = (len(files) + cols - 1) // cols
    W, H = cell
    img = Image.new("RGB", (cols * W, rows * (H + 30)), "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 15)
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB")
        im.thumbnail((W - 8, H - 8))
        x, y = (i % cols) * W, (i // cols) * (H + 30)
        img.paste(im, (x + (W - im.width) // 2, y + (H - im.height) // 2))
        d.text((x + 6, y + H + 6), f.name[:40], fill="black", font=font)
    img.save(out, quality=86)


def overview(dest: Path):
    """Один лист со всеми креативами — чтобы посмотреть с телефона."""
    picks = []
    for folder, ids in GROUPS:
        for cid in ids:
            if cid in PENDING:
                continue
            if cid.startswith("K"):
                c1 = SRC / f"{cid}_card1.png"
                if c1.exists():
                    picks.append((c1, f"{cid} карусель"))
                continue
            st = (SRC_SHORT if cid.endswith("S") else SRC) / f"{cid}_story.png"
            if st.exists():
                picks.append((st, cid))
            elif (SRC / f"{cid}_story.mp4").exists():
                fr = SRC / f"_{cid}_frame.png"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", {"V1": "8.6", "M2": "20.2"}.get(cid, "9.5"), "-i", str(SRC / f"{cid}_story.mp4"), "-frames:v", "1", str(fr)], check=False)
                if fr.exists():
                    picks.append((fr, f"{cid} видео"))
    mv = MONTAGE / "V3_montaj_story.mp4"
    if mv.exists():
        fr = SRC / "_V3_frame.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "20.5", "-i", str(mv), "-frames:v", "1", str(fr)], check=False)
        if fr.exists():
            picks.append((fr, "V3 монтаж"))
    W, H, cols = 270, 480, 8
    rows = (len(picks) + cols - 1) // cols
    img = Image.new("RGB", (cols * W, rows * (H + 34) + 70), "white")
    d = ImageDraw.Draw(img)
    title = f"АКТУАЛЬНЫЕ креативы УЗ — Meta, {date.today():%d.%m.%Y}. Сторис 9x16; у каждой картинки есть версия 4x5 для ленты"
    d.text((16, 18), title, fill="black", font=ImageFont.truetype(FONT, 26))
    font = ImageFont.truetype(FONT, 18)
    for i, (f, label) in enumerate(picks):
        im = Image.open(f).convert("RGB")
        im.thumbnail((W - 10, H - 10))
        x, y = (i % cols) * W, 70 + (i // cols) * (H + 34)
        img.paste(im, (x + (W - im.width) // 2, y + (H - im.height) // 2))
        d.text((x + 8, y + H + 6), label, fill="black", font=font)
    img.save(dest / "Обзор всех креативов.jpg", quality=85)


def copy_creative(cid: str, dest: Path, h: str) -> list:
    """Файлы креатива — обе пропорции или карточки карусели — в dest."""
    if cid.startswith("K"):
        cards = sorted(SRC.glob(f"{cid}_card*.png"), key=lambda p: int(p.stem.split("card")[1]))
        sub = dest / f"{cid} — карусель"
        sub.mkdir(exist_ok=True)
        pairs = [(p, sub / f"{cid}_{p.stem.split('_')[1]}_1x1.png") for p in cards]
    else:
        src = SRC_SHORT if cid.endswith("S") else SRC
        pairs = [(src / f"{cid}_{fmt}.{ext}", dest / f"{cid} {h} — {ratio}.{ext}".replace("  ", " "))
                 for fmt, ratio in RATIO.items() for ext in ("png", "mp4")]
        pairs = [(p, q) for p, q in pairs if p.exists()]
    for p, q in pairs:
        shutil.copy2(p, q)
    return [q for _, q in pairs]


def copy_montage(d: Path) -> list:
    """V3 (Remotion) и V4/V4б (HyperFrames) — в папку «05 Видео»."""
    copied = []
    for fmt, ratio in RATIO.items():
        mp = MONTAGE / f"V3_montaj_{fmt}.mp4"
        if mp.exists():
            q = d / f"V3 Монтаж как в референсе (без Никиты) — {ratio}.mp4"
            shutil.copy2(mp, q)
            copied.append(q)
    for name, title in (("V4_final_story.mp4", "V4 Монтаж на HyperFrames (без Никиты) — 9x16"),
                        ("V4_final_feed_4x5.mp4", "V4 Монтаж на HyperFrames (без Никиты) — 4x5"),
                        ("V4b_bez_fbstore_story.mp4", "V4б без fbstore (безопаснее для Meta) — 9x16"),
                        ("V4b_bez_fbstore_feed_4x5.mp4", "V4б без fbstore (безопаснее для Meta) — 4x5")):
        vp = ROOT / "v4-hyperframes" / "renders" / name
        if vp.exists():
            q = d / f"{title}.mp4"
            shutil.copy2(vp, q)
            copied.append(q)
    return copied


def tag_green(path: Path) -> None:
    """Зелёная метка Finder: папку с актуальными креативами видно сразу. rmtree её стирает — ставим заново."""
    subprocess.run(["osascript", "-l", "JavaScript", "-e", LABEL_JS, str(path)], check=False, capture_output=True)


def package_pending(ru: dict) -> None:
    """Креативы без проверки носителя — отдельной папкой внутри DEST. docx переводчика не перезаписываем."""
    PENDING_DEST.mkdir(exist_ok=True)
    for cid in PENDING:
        copy_creative(cid, PENDING_DEST, hint(cid, ru))
    docx = PENDING_DEST / f"Тексты на перевод — {', '.join(PENDING)}.docx"
    if not docx.exists():
        NF.export(PENDING, docx)
    print("на перевод →", PENDING_DEST)


def main():
    ru = {c["id"]: c for c in json.loads((ROOT / "creatives_ru.json").read_text(encoding="utf-8"))["creatives"]}
    ru.update({c["id"]: c for c in json.loads((ROOT / "creatives_ru_short.json").read_text(encoding="utf-8"))["creatives"]})
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    total = 0
    for folder, ids in GROUPS:
        d = DEST / folder
        d.mkdir()
        copied = []
        for cid in (x for x in ids if x not in PENDING):
            files = copy_creative(cid, d, hint(cid, ru))
            if not files:
                print("НЕТ ФАЙЛОВ, креатив не попал в папку:", cid)
            copied += files
        if folder.startswith("05"):
            copied += copy_montage(d)
        total += len(copied)
        sheet([c for c in copied if c.suffix == ".png"], d / "_превью.jpg", (240, 427) if "карусели" not in folder else (300, 300))
        print(folder, len(copied))
    for src, dst in DOCS.items():
        shutil.copy2(ROOT / src, DEST / dst)
    overview(DEST)
    tag_green(DEST)
    print("total", total, "→", DEST)
    if PENDING:
        package_pending(ru)


if __name__ == "__main__":
    main()
