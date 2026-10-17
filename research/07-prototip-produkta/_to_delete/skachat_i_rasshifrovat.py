#!/usr/bin/env python3
"""Скачать материалы Дымшакова (Яндекс Диск + видео из Telegram) и расшифровать их mlx-whisper.

Запуск (в Терминале, ноутбук на зарядке):
  caffeinate -i python3 "<этот файл>"

Что делает (продолжает с места остановки, можно перезапускать):
  1. Яндекс Диск «Дымшаков | Запуски / 04. Протипирование» — через публичный API Яндекса.
     Видео -> ~/Data/online-shkola-uz/07-prototip-produkta/dymshakov/yadisk/ (не на Рабочий стол: его синхронизирует iCloud).
     docx/jpeg -> ../istochniki/yadisk/
  2. Telegram «Олег Дымшаков | Все о запусках за один день»: PDF «Идеальный_продукт…» из ~/Downloads -> ../istochniki/telegram/,
     видео «Блок 2» (1:41:08) ищет в ~/Downloads и в папке Telegram, ждёт до 40 минут, пока его скачают.
  3. Расшифровка: mlx-whisper large-v3-turbo (из кеша), language="ru", condition_on_previous_text=False.
     Итог -> ../transkripty/<имя>.txt (с таймкодами) и .json.
Журнал — _scripts/log.txt, состояние — _scripts/status.json.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent            # .../dymshakov/_scripts
BASE = HERE.parent                                  # .../dymshakov
SRC = BASE / "istochniki"
TR = BASE / "transkripty"
DATA = Path.home() / "Data" / "online-shkola-uz" / "07-prototip-produkta" / "dymshakov"
LOG = HERE / "log.txt"
STATUS = HERE / "status.json"

PUBLIC_KEY = "https://disk.yandex.ru/d/TKrkqyopySGL_g"
YA_ROOT = "/04. Протипирование"
API = "https://cloud-api.yandex.net/v1/disk/public/resources"

TG_VIDEO_DURATION = 6068          # 1:41:08
TG_PDF_PATTERN = "идеальный_продукт"
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}

MODELS = ["mlx-community/whisper-large-v3-turbo", "mlx-community/whisper-large-v3-mlx"]
PROMPT = ("Лекция Олега Дымшакова о запусках онлайн-курсов: продукт, продуктовая линейка, прототип программы, "
          "продажник, воронка, трипваер, флагман, ценообразование, упаковка, запуск.")

status = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "downloads": {}, "telegram": {}, "transcripts": {}, "done": False}


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def save_status():
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def safe(name):
    return nfc(name).replace(":", " -").replace("/", "-").strip().rstrip(".") or "_"


def api_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def ya_list(path):
    items, offset = [], 0
    while True:
        q = urllib.parse.urlencode({"public_key": PUBLIC_KEY, "path": path, "limit": 200, "offset": offset})
        j = api_get(f"{API}?{q}")
        batch = j.get("_embedded", {}).get("items", [])
        items += batch
        if len(batch) < 200:
            return items
        offset += 200


def ya_walk(path):
    for it in ya_list(path):
        if it["type"] == "dir":
            yield from ya_walk(it["path"])
        else:
            yield it


def download(url, dest, size):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size == size:
        return "exists"
    tmp = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    done, next_mark = 0, 50 * 2**20
    with urllib.request.urlopen(req, timeout=120) as r, tmp.open("wb") as f:
        while True:
            chunk = r.read(2**20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if done >= next_mark:
                log(f"   … {done / 2**20:.0f} / {size / 2**20:.0f} МБ")
                next_mark += 50 * 2**20
    if size and tmp.stat().st_size != size:
        raise RuntimeError(f"размер {tmp.stat().st_size} != {size}")
    tmp.rename(dest)
    return "ok"


def step_yadisk():
    log("1. Яндекс Диск: список файлов")
    videos = []
    for it in ya_walk(YA_ROOT):
        rel_parts = [safe(p) for p in it["path"].split("/")[2:]]   # без "/04. Протипирование"
        is_video = Path(it["name"]).suffix.lower() in VIDEO_EXT or it.get("media_type") == "video"
        dest = (DATA / "yadisk" if is_video else SRC / "yadisk").joinpath(*rel_parts)
        key = "/".join(rel_parts)
        url = it.get("file")
        if not url:
            q = urllib.parse.urlencode({"public_key": PUBLIC_KEY, "path": it["path"]})
            url = api_get(f"{API}/download?{q}")["href"]
        log(f" ↓ {key} ({it.get('size', 0) / 2**20:.1f} МБ)")
        for attempt in range(3):
            try:
                status["downloads"][key] = download(url, dest, it.get("size", 0))
                break
            except Exception as e:  # noqa: BLE001
                log(f"   ошибка ({attempt + 1}/3): {e}")
                status["downloads"][key] = f"error: {e}"
                time.sleep(10)
        save_status()
        if is_video and dest.exists():
            videos.append(("yadisk/" + key, dest))
    return videos


def ffprobe_duration(p):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                             capture_output=True, text=True, timeout=60).stdout.strip()
        return float(out) if out else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def candidate_dirs():
    home = Path.home()
    dirs = [home / "Downloads", home / "Downloads" / "Telegram Desktop", home / "Movies"]
    gc = home / "Library" / "Group Containers"
    try:
        dirs += [d for d in gc.glob("*ru.keepcoder.Telegram*")]
    except Exception:  # noqa: BLE001
        pass
    return dirs


def iter_files(root, max_depth):
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            depth = len(Path(dirpath).relative_to(root).parts)
            if depth >= max_depth:
                dirnames[:] = []
            for fn in filenames:
                yield Path(dirpath) / fn
    except Exception as e:  # noqa: BLE001
        log(f"   нет доступа к {root}: {e}")


def find_tg_pdf():
    dl = Path.home() / "Downloads"
    for p in iter_files(dl, 3):
        n = nfc(p.name).lower()
        if n.endswith(".pdf") and TG_PDF_PATTERN in n:
            dest = SRC / "telegram" / safe(p.name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(p, dest)
            log(f"2. PDF из Telegram: {p} -> {dest.name}")
            status["telegram"]["pdf"] = str(dest.name)
            return True
    log("2. PDF «Идеальный продукт» в ~/Downloads не найден")
    status["telegram"]["pdf"] = "not found"
    return False


def find_tg_video():
    for root in candidate_dirs():
        if not root.exists():
            continue
        depth = 8 if "Group Containers" in str(root) else 3
        for p in iter_files(root, depth):
            try:
                size = p.stat().st_size
            except Exception:  # noqa: BLE001
                continue
            if not (400 * 2**20 <= size <= 600 * 2**20):
                continue
            if p.name.endswith((".part", ".download")):
                continue
            d = ffprobe_duration(p)
            if abs(d - TG_VIDEO_DURATION) <= 10:
                return p
    return None


def step_tg_video(wait_minutes):
    deadline = time.time() + wait_minutes * 60
    while True:
        p = find_tg_video()
        if p:
            dest = DATA / "telegram" / "Блок 2. Идеальный продукт и продуктовая линейка.mp4"
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists() or dest.stat().st_size != p.stat().st_size:
                shutil.copy2(p, dest)
            log(f"2. Видео «Блок 2» найдено: {p}")
            status["telegram"]["video"] = str(p)
            save_status()
            return ("telegram/Блок 2. Идеальный продукт и продуктовая линейка", dest)
        if time.time() > deadline:
            log("2. Видео «Блок 2» так и не появилось — перезапустите скрипт, когда оно скачается в Telegram")
            status["telegram"]["video"] = "not found"
            save_status()
            return None
        status["telegram"]["video"] = "waiting"
        save_status()
        log("   жду видео «Блок 2» из Telegram (проверяю раз в минуту)…")
        time.sleep(60)


_model = {"name": None}


def transcribe(key, path):
    out_txt = TR / (safe(Path(key).with_suffix("").as_posix().replace("/", " — ")) + ".txt")
    out_json = out_txt.with_suffix(".json")
    if out_txt.exists() and out_json.exists():
        status["transcripts"][key] = "exists"
        return
    import mlx_whisper
    t0 = time.time()
    dur = ffprobe_duration(path)
    log(f"3. Расшифровка: {key} ({dur / 60:.0f} мин)")
    result, last_err = None, None
    for model in ([_model["name"]] if _model["name"] else MODELS):
        try:
            result = mlx_whisper.transcribe(str(path), path_or_hf_repo=model, language="ru", initial_prompt=PROMPT,
                                            condition_on_previous_text=False, verbose=None)
            _model["name"] = model
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            log(f"   модель {model} не сработала: {e}")
    if result is None:
        status["transcripts"][key] = f"error: {last_err}"
        save_status()
        return
    segs = [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip()}
            for s in result.get("segments") or []]
    TR.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({"source": key, "model": _model["name"], "language": "ru", "duration_s": dur,
                                    "segments": segs}, ensure_ascii=False, indent=1), encoding="utf-8")

    def ts(x):
        x = int(x)
        return f"{x // 3600:02d}:{x % 3600 // 60:02d}:{x % 60:02d}"
    lines = [f"# {key}", f"# модель: {_model['name']}, длительность: {ts(dur)}", ""]
    lines += [f"[{ts(s['start'])}] {s['text']}" for s in segs if s["text"]]
    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    took = time.time() - t0
    log(f"   готово за {took / 60:.1f} мин -> {out_txt.name}")
    status["transcripts"][key] = f"ok ({took / 60:.1f} мин)"
    save_status()


def main():
    for d in (SRC, TR, DATA):
        d.mkdir(parents=True, exist_ok=True)
    log(f"=== старт, python {sys.version.split()[0]} ({sys.executable})")
    try:
        import mlx_whisper  # noqa: F401
    except Exception as e:  # noqa: BLE001
        log(f"!!! не найден mlx_whisper в этом python: {e}")
        status["error"] = f"mlx_whisper: {e}"
        save_status()
        sys.exit(1)
    videos = step_yadisk()
    find_tg_pdf()
    save_status()
    for key, path in videos:
        transcribe(key, path)
    tg = step_tg_video(wait_minutes=40)
    if tg:
        transcribe(*tg)
    status["done"] = True
    status["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_status()
    log("=== всё готово")


if __name__ == "__main__":
    main()
