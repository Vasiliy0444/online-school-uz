#!/usr/bin/env python3
"""Кадры и расшифровка видеокреативов — функции скилла watch, настройки выбраны на пилоте (00-pilot/ИТОГИ-ПИЛОТА.md).

Для каждого скачанного видео (журнал 02-reklama/manifest_media_<school>.csv, статус ok, kind video_hd|video_sd):
  - frames/hook/     — кадры 0–3 с, 2 кадра в секунду (7 штук), ширина 512;
  - frames/overview/ — 4 кадра равномерно по ролику;
  - thumb.jpg        — кадр на 1-й секунде, ширина 360 (для галереи отчёта);
  - transcript.json / transcript.txt — mlx-whisper large-v3, language="uz", подсказка на узбекской латинице,
    condition_on_previous_text=False; флаги качества: доля кириллицы, повторы, мало текста.
Итог — 02-reklama/transcripts_index.csv. Продолжает с места остановки. Сеть не нужна (модель в кеше).
Запуск: python3 frames_transcribe.py --school qadam
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

WATCH = Path.home() / ".claude" / "skills" / "watch" / "scripts"
sys.path.insert(0, str(WATCH))
from frames import extract, get_metadata  # noqa: E402  (скилл watch)
from whisper import extract_audio  # noqa: E402  (скилл watch)

import mlx_whisper  # noqa: E402

HERE = Path(__file__).resolve().parent
MODEL = "mlx-community/whisper-large-v3-mlx"
PROMPT = "Assalomu alaykum. Bugun daromad, kurs, o'qish va ish haqida gaplashamiz."
OVERVIEW_FRAMES = 4
FIELDS = ["school", "library_id", "video", "duration_s", "hook_frames", "overview_frames", "thumb", "transcript_txt",
          "chars", "chars_per_s", "cyrillic_share", "repeated_segments", "quality", "seconds"]


def quality(text: str, segments: list[dict], duration: float) -> dict:
    letters = re.findall(r"\w", text)
    cyr = len(re.findall(r"[А-Яа-яЁёЎўҚқҒғҲҳІіӘәҮүҰұӨө]", text)) / max(1, len(letters))
    texts = [s["text"].strip().lower() for s in segments if len(s["text"].strip()) > 15]
    repeated = sum(texts.count(t) - 1 for t in set(texts) if texts.count(t) > 1)
    cps = len(text) / duration if duration else 0.0
    if not text:
        flag = "без речи"
    elif cyr > 0.2 or repeated >= 2 or (duration > 8 and cps < 2):
        flag = "низкое"
    else:
        flag = "черновое"
    return {"chars": len(text), "chars_per_s": round(cps, 1), "cyrillic_share": round(cyr, 2),
            "repeated_segments": repeated, "quality": flag}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--school", required=True)
    args = ap.parse_args()
    manifest = HERE / "02-reklama" / f"manifest_media_{args.school}.csv"
    index_path = HERE / "02-reklama" / "transcripts_index.csv"
    done = set()
    rows = []
    if index_path.exists():
        with index_path.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
            done = {r["video"] for r in rows}
    with manifest.open(encoding="utf-8") as fh:
        videos = [r for r in csv.DictReader(fh) if r["status"] == "ok" and r["kind"] in ("video_hd", "video_sd")]
    # У динамических объявлений (DCO) несколько роликов в одной папке: файлы первого ролика — без суффикса,
    # остальных — с «-slot<N>», иначе кадры и расшифровка последнего ролика затирают первый.
    first_slot: dict[str, int] = {}
    for item in videos:
        folder_key = str(Path(item["file"]).parent)
        first_slot[folder_key] = min(first_slot.get(folder_key, 99), int(item["slot"] or 0))
    for item in videos:
        video = Path(item["file"])
        if str(video) in done or not video.exists():
            continue
        started = time.time()
        folder = video.parent
        suffix = "" if int(item["slot"] or 0) == first_slot[str(folder)] else f"-slot{item['slot']}"
        meta = get_metadata(str(video))
        duration = meta["duration_seconds"]
        hook = extract(str(video), folder / "frames" / f"hook{suffix}", fps=2.0, resolution=512, max_frames=7,
                       start_seconds=0.0, end_seconds=min(3.0, duration or 3.0))
        overview = extract(str(video), folder / "frames" / f"overview{suffix}", fps=max(0.05, OVERVIEW_FRAMES / max(duration, 1.0)),
                           resolution=512, max_frames=OVERVIEW_FRAMES)
        thumb = folder / f"thumb{suffix}.jpg"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", "1", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "5", str(thumb)], check=False)
        text, segments = "", []
        if meta.get("has_audio"):
            audio = extract_audio(str(video), folder / f"audio{suffix}.mp3")
            result = mlx_whisper.transcribe(str(audio), path_or_hf_repo=MODEL, language="uz", initial_prompt=PROMPT,
                                            condition_on_previous_text=False)
            segments = [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip()}
                        for s in result.get("segments") or []]
            text = " ".join(s["text"] for s in segments if s["text"])
        q = quality(text, segments, duration)
        (folder / f"transcript{suffix}.json").write_text(json.dumps({"model": MODEL, "language": "uz", "segments": segments, **q},
                                                           ensure_ascii=False, indent=1), encoding="utf-8")
        (folder / f"transcript{suffix}.txt").write_text(
            "\n".join(f"[{int(s['start']) // 60:02d}:{int(s['start']) % 60:02d}] {s['text']}" for s in segments), encoding="utf-8")
        rows.append({"school": args.school, "library_id": item["library_id"] + suffix, "video": str(video),
                     "duration_s": round(duration, 1), "hook_frames": len(hook), "overview_frames": len(overview),
                     "thumb": str(thumb) if thumb.exists() else "", "transcript_txt": str(folder / f"transcript{suffix}.txt"),
                     **q, "seconds": round(time.time() - started, 1)})
        print(f"{item['library_id']}: {round(duration)}s video, quality={q['quality']}, {rows[-1]['seconds']}s", flush=True)
        with index_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    # Листы кадров для разметки агентами (и уменьшенные картинки статичных объявлений)
    subprocess.run([sys.executable, str(HERE / "contact_sheets.py"), "--school", args.school], check=False)


if __name__ == "__main__":
    main()
