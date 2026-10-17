#!/usr/bin/env python3
"""Пилот скилла watch: кадры хука и выбор модели расшифровки узбекской речи.

Для каждого скачанного видео:
  - кадры первых 3 секунд (2 кадра в секунду) функцией frames.extract из скилла watch;
  - аудио функцией whisper.extract_audio из скилла;
  - расшифровка mlx-whisper: 2 модели × (язык uz, автоопределение), с замером времени.
Запуск: python3 whisper_pilot.py
"""
import csv
import json
import re
import sys
import time
from pathlib import Path

WATCH = Path.home() / ".claude/skills/watch/scripts"
sys.path.insert(0, str(WATCH))
from frames import extract, get_metadata  # noqa: E402  (скилл watch)
from whisper import extract_audio  # noqa: E402  (скилл watch)

import mlx_whisper  # noqa: E402

HERE = Path(__file__).resolve().parent
MEDIA = Path.home() / "Data/online-shkola-uz/05-razbor-konkurentov/00-pilot/meta"
OUT = HERE / "whisper"
MODELS = {"turbo": "mlx-community/whisper-large-v3-turbo", "large-v3": "mlx-community/whisper-large-v3-mlx"}
LANGS = {"uz": "uz", "auto": None}
UZ_LATIN = re.compile(r"[oOgG][ʻ'‘’`]|\b(va|uchun|bilan|qanday|siz|bu|ham|bo'lib|kerak)\b", re.I)


def repeated_chunk(segments: list[dict]) -> bool:
    texts = [s["text"].strip().lower() for s in segments if s["text"].strip()]
    return any(texts.count(t) >= 3 for t in set(texts))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for video in sorted(MEDIA.glob("*/*_video_*.mp4")):
        lib_id = video.parent.name
        meta = get_metadata(str(video))
        hook = extract(str(video), video.parent / "frames" / "hook", fps=2.0, resolution=512, max_frames=7,
                       start_seconds=0.0, end_seconds=3.0)
        audio = extract_audio(str(video), video.parent / "audio.mp3")
        for model_key, repo in MODELS.items():
            for lang_key, lang in LANGS.items():
                t0 = time.time()
                result = mlx_whisper.transcribe(str(audio), path_or_hf_repo=repo, language=lang)
                seconds = round(time.time() - t0, 1)
                segments = [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip()}
                            for s in result.get("segments") or []]
                text = " ".join(s["text"] for s in segments)
                payload = {"library_id": lib_id, "model": repo, "language_arg": lang, "detected_language": result.get("language"),
                           "seconds": seconds, "duration_s": round(meta["duration_seconds"], 1), "segments": segments}
                (OUT / f"{lib_id}__{model_key}__{lang_key}.json").write_text(
                    json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
                rows.append({
                    "library_id": lib_id, "duration_s": round(meta["duration_seconds"], 1), "model": model_key,
                    "language_arg": lang_key, "detected_language": result.get("language"), "seconds": seconds,
                    "realtime_x": round(meta["duration_seconds"] / seconds, 1) if seconds else "",
                    "segments": len(segments), "chars": len(text), "uz_latin_markers": len(UZ_LATIN.findall(text)),
                    "repeated_chunk": repeated_chunk(segments), "hook_frames": len(hook), "text_head": text[:220],
                })
                print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    with (HERE / "whisper_pilot.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
