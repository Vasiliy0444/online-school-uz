#!/usr/bin/env python3
"""Расшифровка записей созвона о программе (чат «Никита Попко», 28.09.2026).

Локально, без интернета: mlx-whisper, модель whisper-large-v3-turbo, русский язык.
Настройки — как у research/07-prototip-produkta/_scripts/run.py.
Для каждой записи <имя>.m4a пишет <имя>.txt (текст с таймкодами) и <имя>.json (сегменты).

Запуск:
    python3 rasshifrovat.py zapis-1-dlinnaya.m4a zapis-2-korotkaya.m4a
"""
import json
import sys
import time
from pathlib import Path

import mlx_whisper

MODEL = "mlx-community/whisper-large-v3-turbo"


def stamp(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def transcribe(path: Path) -> None:
    started = time.time()
    result = mlx_whisper.transcribe(str(path), path_or_hf_repo=MODEL, language="ru",
                                    condition_on_previous_text=False, verbose=False)
    segments = result.get("segments", [])
    lines = [f"[{stamp(seg['start'])}] {seg['text'].strip()}" for seg in segments if seg["text"].strip()]
    path.with_suffix(".txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.with_suffix(".json").write_text(json.dumps(segments, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{path.name}: {len(lines)} фраз, {time.time() - started:.0f} с")


def main() -> None:
    files = [Path(a) for a in sys.argv[1:]]
    if not files:
        sys.exit("Укажите файлы .m4a")
    for f in files:
        if not f.exists():
            sys.exit(f"Нет файла: {f}")
        transcribe(f)


if __name__ == "__main__":
    main()
