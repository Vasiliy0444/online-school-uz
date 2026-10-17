#!/usr/bin/env python3
"""Листы кадров для разметки креативов агентами — две картинки на креатив вместо одиннадцати.

Для каждой папки креатива в ~/Data/.../kreativy/<school>/meta/<library_id>/:
  sheet_hook.jpg     — кадры хука (frames/hook, 0–3 с) в один ряд, по 240 px в ширину, с подписью секунды;
  sheet_overview.jpg — обзорные кадры (frames/overview) сеткой 2×2, по 360 px, с примерным временем кадра (~M:SS);
  image_512.jpg      — для картинок: сама картинка, уменьшенная до 512 px по ширине.
Запуск: python3 contact_sheets.py --school qadam [--redo-overview]
"""
import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

DATA = Path.home() / "Data" / "online-shkola-uz" / "05-razbor-konkurentov"
HOOK_W = 240
OVERVIEW_W = 360
HOOK_TIMES = ["0.0s", "0.5s", "1.0s", "1.5s", "2.0s", "2.5s", "3.0s"]  # латиница: стандартный шрифт Pillow без кириллицы


def fit(img: Image.Image, width: int) -> Image.Image:
    return img.resize((width, max(1, round(img.height * width / img.width))))


def hook_sheet(frames: list[Path], target: Path) -> None:
    tiles = [fit(Image.open(f).convert("RGB"), HOOK_W) for f in frames]
    height = max(t.height for t in tiles) + 22
    sheet = Image.new("RGB", (HOOK_W * len(tiles), height), "white")
    draw = ImageDraw.Draw(sheet)
    for i, tile in enumerate(tiles):
        sheet.paste(tile, (i * HOOK_W, 22))
        draw.text((i * HOOK_W + 6, 4), HOOK_TIMES[i] if i < len(HOOK_TIMES) else str(i), fill="black")
    sheet.save(target, quality=80)


def video_duration(folder: Path) -> float | None:
    videos = sorted(folder.glob("*_video_hd.mp4")) + sorted(folder.glob("*_video_sd.mp4"))
    if not videos:
        return None
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(videos[0])],
                            capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def overview_sheet(frames: list[Path], target: Path, duration: float | None) -> None:
    """Кадры обзора сняты фильтром fps=4/длительность — ffmpeg берёт кадр в середине каждой четверти ролика,
    поэтому подпись ~время = (i + 0.5) × длительность / 4 (сверено разметчиком по таймерам в роликах Qadam)."""
    tiles = [fit(Image.open(f).convert("RGB"), OVERVIEW_W) for f in frames[:4]]
    cols = 2
    rows = (len(tiles) + 1) // 2
    cell_h = max(t.height for t in tiles) + 22
    sheet = Image.new("RGB", (OVERVIEW_W * cols, cell_h * rows), "white")
    draw = ImageDraw.Draw(sheet)
    for i, tile in enumerate(tiles):
        x, y = (i % cols) * OVERVIEW_W, (i // cols) * cell_h
        sheet.paste(tile, (x, y + 22))
        if duration:
            seconds = round((i + 0.5) * duration / len(tiles))
            draw.text((x + 6, y + 4), f"~{seconds // 60}:{seconds % 60:02d}", fill="black")
    sheet.save(target, quality=80)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--school", required=True)
    ap.add_argument("--redo-overview", action="store_true", help="пересобрать листы обзора (например, чтобы добавить подписи времени)")
    args = ap.parse_args()
    made = 0
    for folder in sorted((DATA / "kreativy" / args.school / "meta").glob("*")):
        hook = sorted((folder / "frames" / "hook").glob("frame_*.jpg"))
        overview = sorted((folder / "frames" / "overview").glob("frame_*.jpg"))
        if hook and not (folder / "sheet_hook.jpg").exists():
            hook_sheet(hook, folder / "sheet_hook.jpg")
            made += 1
        if overview and (args.redo_overview or not (folder / "sheet_overview.jpg").exists()):
            overview_sheet(overview, folder / "sheet_overview.jpg", video_duration(folder))
        images = [p for p in folder.glob("*_image.*")] + [p for p in folder.glob("*_0_image.*")]
        if images and not (folder / "image_512.jpg").exists():
            fit(Image.open(images[0]).convert("RGB"), 512).save(folder / "image_512.jpg", quality=82)
            made += 1
    print(f"{args.school}: sheets and resized images made: {made}")


if __name__ == "__main__":
    main()
