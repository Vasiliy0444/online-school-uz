#!/usr/bin/env python3
"""Скачать материалы курсов (Яндекс Диск, YouTube, Telegram) и расшифровать видео локальным mlx-whisper.

Запуск в Терминале (ноутбук на зарядке, крышка открыта):
  caffeinate -i python3 "<путь к этому файлу>"

Список задач — manifest.json рядом (Claude дописывает его по ходу работы; скрипт перечитывает раз в минуту).
  yadisk          — публичная папка Яндекс Диска, скачивается целиком через API Яндекса;
  youtube         — ролик, звук через yt-dlp;
  telegram_files  — документы, скачанные в Telegram: ищутся в ~/Downloads по части имени;
  telegram_videos — видео, скачанные в Telegram: ищутся по длительности (ffprobe) в ~/Downloads и в папке Telegram.
Видео и звук -> ~/Data/online-shkola-uz/07-prototip-produkta/<курс>/ (не Рабочий стол: его синхронизирует iCloud).
Документы -> <курс>/istochniki/, расшифровки -> <курс>/transkripty/<имя>.txt (с таймкодами) и .json.
Модель: mlx-whisper large-v3-turbo из кеша (запасная — large-v3), language="ru", condition_on_previous_text=False.
Журнал — log.txt, состояние — status.json. Продолжает с места остановки.
Скрипт завершается, когда всё из манифеста готово и в нём стоит "finish_when_done": true (или через 8 часов).
"""
import json
import os
import shutil
import ssl
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent                # .../07-prototip-produkta/_scripts
ROOT = HERE.parent                                     # .../07-prototip-produkta
DATA = Path.home() / "Data" / "online-shkola-uz" / "07-prototip-produkta"
MANIFEST = HERE / "manifest.json"
LOG = HERE / "log.txt"
STATUS = HERE / "status.json"
PROBE_CACHE = HERE / "probe_cache.json"
YA_API = "https://cloud-api.yandex.net/v1/disk/public/resources"
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}
AUDIO_EXT = {".mp3", ".m4a", ".ogg", ".oga", ".opus", ".wav", ".aac", ".flac"}
DOC_EXT = {".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".csv", ".txt", ".md", ".png", ".jpg", ".jpeg", ".webp", ".key", ".pages", ".numbers", ".zip", ".rtf", ".html"}
MODELS = ["mlx-community/whisper-large-v3-turbo", "mlx-community/whisper-large-v3-mlx"]
PROMPTS = {
    "dymshakov": "Лекция Олега Дымшакова о запусках онлайн-курсов: продукт, продуктовая линейка, прототип программы, "
                 "продажник, воронка, трипваер, флагман, ценообразование, упаковка.",
    "timochko": "Урок Михаила Тимочко «Формула запуска»: прототип продукта, большое обещание, программа курса, "
                "тарифы, вау-фишки, продуктовая линейка, анализ конкурентов, продающий сайт, вебинар.",
}
MAX_HOURS = 8
START = time.time()
SELF_MTIME = Path(__file__).stat().st_mtime


def _ssl_ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:  # noqa: BLE001
        pass
    for ca in ("/etc/ssl/cert.pem", "/opt/homebrew/etc/openssl@3/cert.pem", "/usr/local/etc/openssl@3/cert.pem"):
        if Path(ca).exists():
            return ssl.create_default_context(cafile=ca)
    return ssl.create_default_context()


SSL_CTX = _ssl_ctx()

status = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "yadisk": {}, "youtube": {}, "telegram_files": {},
          "telegram_videos": {}, "transcripts": {}, "done": False}
probe_cache = {}
done_once = set()


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def save_status():
    status["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    PROBE_CACHE.write_text(json.dumps(probe_cache, ensure_ascii=False), encoding="utf-8")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def safe(name):
    return nfc(name).replace(":", " -").replace("/", "-").strip().rstrip(".").strip() or "_"


def course_dirs(course):
    src, tr, data = ROOT / course / "istochniki", ROOT / course / "transkripty", DATA / course
    for d in (src, tr, data):
        d.mkdir(parents=True, exist_ok=True)
    return src, tr, data


# ---------- Яндекс Диск ----------

def api_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
        return json.loads(r.read().decode("utf-8"))


def ya_walk(pk, path):
    offset = 0
    while True:
        q = urllib.parse.urlencode({"public_key": pk, "path": path, "limit": 200, "offset": offset})
        items = api_get(f"{YA_API}?{q}").get("_embedded", {}).get("items", [])
        for it in items:
            if it["type"] == "dir":
                yield from ya_walk(pk, it["path"])
            else:
                yield it
        if len(items) < 200:
            return
        offset += 200


def download(url, dest, size):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and (not size or dest.stat().st_size == size):
        return "exists"
    tmp = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    got, mark = 0, 100 * 2**20
    with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as r, tmp.open("wb") as f:
        while True:
            chunk = r.read(2**20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if got >= mark:
                log(f"   … {got / 2**20:.0f} / {size / 2**20:.0f} МБ")
                mark += 100 * 2**20
    if size and tmp.stat().st_size != size:
        raise RuntimeError(f"размер {tmp.stat().st_size} != {size}")
    tmp.rename(dest)
    return "ok"


def do_yadisk(item, queue):
    course = item["course"]
    src, _, data = course_dirs(course)
    root_len = len([p for p in item["path"].split("/") if p])
    log(f"Яндекс Диск [{course}]: {item['path']}")
    for it in ya_walk(item["public_key"], item["path"]):
        parts = [safe(p) for p in it["path"].split("/") if p][root_len:]
        key = f"{course}:yadisk/" + "/".join(parts)
        is_video = Path(it["name"]).suffix.lower() in VIDEO_EXT or it.get("media_type") == "video"
        dest = (data / "yadisk" if is_video else src / "yadisk").joinpath(*parts)
        url = it.get("file")
        if not url:
            q = urllib.parse.urlencode({"public_key": item["public_key"], "path": it["path"]})
            url = api_get(f"{YA_API}/download?{q}")["href"]
        log(f" ↓ {'/'.join(parts)} ({it.get('size', 0) / 2**20:.1f} МБ)")
        for attempt in range(3):
            try:
                status["yadisk"][key] = download(url, dest, it.get("size", 0))
                break
            except Exception as e:  # noqa: BLE001
                status["yadisk"][key] = f"error: {e}"
                log(f"   ошибка ({attempt + 1}/3): {e}")
                time.sleep(10)
        save_status()
        if is_video and dest.exists():
            queue.append((course, "yadisk — " + " — ".join(Path(*parts).with_suffix("").parts), dest))


# ---------- YouTube ----------

def ytdlp_cmd():
    exe = shutil.which("yt-dlp")
    return [exe] if exe else [sys.executable, "-m", "yt_dlp"]


def js_runtime():
    home = Path.home()
    cands = [("bun", home / ".bun" / "bin" / "bun"), ("deno", home / ".deno" / "bin" / "deno")]
    cands += [("node", p) for p in sorted((home / ".nvm" / "versions" / "node").glob("*/bin/node"), reverse=True)]
    for name in ("node", "bun", "deno"):
        w = shutil.which(name)
        if w:
            cands.append((name, Path(w)))
    cands += [("node", Path("/opt/homebrew/bin/node")), ("node", Path("/usr/local/bin/node"))]
    for name, p in cands:
        if p.exists():
            return f"{name}:{p}"
    return None


def yt_files(out, vid):
    return [p for p in out.glob("*") if f"[{vid}]" in p.name and p.suffix not in (".part", ".ytdl", ".json")]


def do_youtube(item, queue):
    course = item["course"]
    _, _, data = course_dirs(course)
    out = data / "youtube"
    out.mkdir(parents=True, exist_ok=True)
    vid = urllib.parse.parse_qs(urllib.parse.urlparse(item["url"]).query).get("v", ["video"])[0]
    existing = yt_files(out, vid)
    if not existing:
        log(f"YouTube [{course}]: {item['url']}")
        base = ytdlp_cmd() + ["-f", "bestaudio[ext=m4a]/bestaudio/best", "--no-playlist", "--write-info-json",
                              "-o", str(out / "%(title).120s [%(id)s].%(ext)s")]
        js = js_runtime()
        variants = []
        if js:
            variants.append(["--js-runtimes", js])
        variants += [["--extractor-args", f"youtube:player_client={c}"] for c in ("tv_simply", "android_vr", "web_safari", "mweb", "ios")]
        ok, err = False, ""
        for extra in variants:
            r = subprocess.run(base + extra + [item["url"]], capture_output=True, text=True)
            if r.returncode == 0 and yt_files(out, vid):
                ok = True
                log(f"   yt-dlp ok ({' '.join(extra)})")
                break
            err = r.stderr.strip()[-300:]
            log(f"   yt-dlp не вышло с {' '.join(extra)}: {err[-160:]}")
        if not ok:
            status["youtube"][item["url"]] = f"error: {err}"
            save_status()
            return False
        existing = yt_files(out, vid)
    if not existing:
        return False
    p = existing[0]
    # описание ролика — рядом с источниками
    info = [q for q in out.glob("*") if f"[{vid}]" in q.name and q.name.endswith(".info.json")]
    if info:
        try:
            j = json.loads(info[0].read_text(encoding="utf-8"))
            src, _, _ = course_dirs(course)
            (src / f"youtube-{vid}.md").write_text(
                f"# {j.get('title')}\n\n- Ссылка: {item['url']}\n- Канал: {j.get('channel')}\n- Дата: {j.get('upload_date')}\n"
                f"- Длительность: {j.get('duration')} с\n\n## Описание\n\n{j.get('description') or ''}\n", encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    status["youtube"][item["url"]] = f"ok: {p.name}"
    save_status()
    queue.append((course, "youtube — " + p.stem, p))
    return True


# ---------- Telegram ----------

def tg_roots():
    home = Path.home()
    roots = [home / "Downloads", home / "Movies"]
    roots += sorted((home / "Library" / "Group Containers").glob("*ru.keepcoder.Telegram*"))
    return roots


def iter_files(root, max_depth):
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            if len(Path(dirpath).relative_to(root).parts) >= max_depth:
                dirnames[:] = []
            for fn in filenames:
                yield Path(dirpath) / fn
    except Exception as e:  # noqa: BLE001
        log(f"   нет доступа к {root}: {e}")


def duration(p):
    try:
        st = p.stat()
    except Exception:  # noqa: BLE001
        return 0.0
    k = f"{p}|{st.st_size}|{int(st.st_mtime)}"
    if k not in probe_cache:
        try:
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                 capture_output=True, text=True, timeout=60).stdout.strip()
            probe_cache[k] = float(out) if out and out != "N/A" else 0.0
        except Exception:  # noqa: BLE001
            probe_cache[k] = 0.0
    return probe_cache[k]


def scan_videos(since):
    """Все свежие большие файлы с длительностью: [(path, size, duration)]."""
    found = []
    for root in tg_roots():
        if not root.exists():
            continue
        depth = 8 if "Group Containers" in str(root) else 3
        for p in iter_files(root, depth):
            n = p.name.lower()
            if "partial" in n or n.endswith((".part", ".download", ".crdownload", ".jpg", ".png", ".pdf", ".json")):
                continue
            try:
                st = p.stat()
            except Exception:  # noqa: BLE001
                continue
            if st.st_size < 3 * 2**20 or st.st_mtime < since:
                continue
            if time.time() - st.st_mtime < 20:      # ещё пишется
                continue
            d = duration(p)
            if d > 0:
                found.append((p, st.st_size, d))
    return found


def do_tg_files(items):
    dl = Path.home() / "Downloads"
    for it in items:
        key = f"{it['course']}:{it['pattern']}{it.get('ext', '')}"
        if status["telegram_files"].get(key, "").startswith("ok"):
            continue
        src, _, _ = course_dirs(it["course"])
        hits = []
        for p in iter_files(dl, 3):
            n = nfc(p.name).lower()
            if nfc(it["pattern"]).lower() in n and n.endswith(it.get("ext", "")) and not n.endswith((".part", ".download")):
                hits.append(p)
        if hits:
            for hit in hits:
                dest = src / "telegram" / safe(hit.name)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copy2(hit, dest)
                log(f"Telegram файл [{it['course']}]: {hit.name}")
            status["telegram_files"][key] = "ok: " + ", ".join(safe(h.name) for h in hits)
        else:
            status["telegram_files"][key] = "waiting"
    save_status()


def do_tg_videos(items, queue):
    pending = [it for it in items if not status["telegram_videos"].get(f"{it['course']}:{it['name']}", "").startswith("ok")]
    if not pending:
        return
    found = scan_videos(since=time.time() - 3 * 86400)
    for it in pending:
        key = f"{it['course']}:{it['name']}"
        _, _, data = course_dirs(it["course"])
        tol = it.get("tolerance_s", 3)
        cands = [(p, s, d) for p, s, d in found if abs(d - it["duration"]) <= tol]
        if it.get("size_mb"):
            cands = [c for c in cands if abs(c[1] / 2**20 - it["size_mb"]) / it["size_mb"] < 0.05
                     or abs(c[1] / 1e6 - it["size_mb"]) / it["size_mb"] < 0.05]
        if not cands:
            status["telegram_videos"][key] = "waiting"
            continue
        p, s, d = max(cands, key=lambda c: c[1])
        ext = p.suffix if p.suffix.lower() in VIDEO_EXT else ".mp4"
        dest = data / "telegram" / (safe(it["name"]) + ext)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or dest.stat().st_size != s:
            shutil.copy2(p, dest)
        status["telegram_videos"][key] = f"ok: {p}"
        log(f"Telegram видео [{it['course']}]: «{it['name']}» <- {p}")
        queue.append((it["course"], "telegram — " + safe(it["name"]), dest))
    save_status()


def do_watch_folders(items, queue):
    """Папки, куда Вася сохраняет файлы из Telegram: видео/аудио -> расшифровка, документы -> istochniki."""
    for it in items:
        root = Path(os.path.expanduser(it["path"]))
        root.mkdir(parents=True, exist_ok=True)
        src, _, _ = course_dirs(it["course"])
        key = f"{it['course']}:{root}"
        n_media = n_docs = 0
        for p in sorted(iter_files(root, 4)):
            n = p.name.lower()
            if n.startswith(".") or n.endswith((".part", ".download", ".crdownload")):
                continue
            try:
                st = p.stat()
            except Exception:  # noqa: BLE001
                continue
            if time.time() - st.st_mtime < 20:
                continue
            rel = p.relative_to(root)
            ext = p.suffix.lower()
            if ext in VIDEO_EXT or ext in AUDIO_EXT:
                n_media += 1
                title = "telegram — " + " — ".join(safe(x) for x in rel.with_suffix("").parts)
                queue.append((it["course"], title, p))
            elif ext in DOC_EXT:
                n_docs += 1
                dest = src / "telegram" / Path(*[safe(x) for x in rel.parts])
                if not dest.exists() or dest.stat().st_size != st.st_size:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, dest)
                    log(f"Папка [{it['course']}]: документ {rel}")
        status.setdefault("watch_folders", {})[key] = f"медиа {n_media}, документов {n_docs}"
    save_status()


# ---------- расшифровка ----------

_model = {"name": None}


def ts(x):
    x = int(x)
    return f"{x // 3600:02d}:{x % 3600 // 60:02d}:{x % 60:02d}"


def transcribe(course, title, path):
    _, tr, _ = course_dirs(course)
    out_txt = tr / (safe(title)[:150] + ".txt")
    out_json = out_txt.with_suffix(".json")
    key = f"{course}:{title}"
    if out_txt.exists() and out_json.exists():
        status["transcripts"][key] = "ok (было)"
        return
    import mlx_whisper
    t0 = time.time()
    dur = duration(path)
    log(f"Расшифровка [{course}]: {title} ({dur / 60:.0f} мин)")
    status["transcripts"][key] = "running"
    save_status()
    result, err = None, None
    for model in ([_model["name"]] if _model["name"] else MODELS):
        try:
            result = mlx_whisper.transcribe(str(path), path_or_hf_repo=model, language="ru",
                                            initial_prompt=PROMPTS.get(course), condition_on_previous_text=False,
                                            verbose=None)
            _model["name"] = model
            break
        except Exception as e:  # noqa: BLE001
            err = e
            log(f"   модель {model} не сработала: {e}")
    if result is None:
        status["transcripts"][key] = f"error: {err}"
        save_status()
        return
    segs = [{"start": round(s["start"], 2), "end": round(s["end"], 2), "text": s["text"].strip()}
            for s in result.get("segments") or []]
    out_json.write_text(json.dumps({"source": str(path.name), "course": course, "title": title, "model": _model["name"],
                                    "language": "ru", "duration_s": dur, "segments": segs},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# {title}", f"# источник: {path.name}; модель: {_model['name']}; длительность: {ts(dur)}", ""]
    lines += [f"[{ts(s['start'])}] {s['text']}" for s in segs if s["text"]]
    out_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")
    took = (time.time() - t0) / 60
    status["transcripts"][key] = f"ok ({took:.1f} мин)"
    log(f"   готово за {took:.1f} мин -> {course}/transkripty/{out_txt.name}")
    save_status()


# ---------- главный цикл ----------

def main():
    global probe_cache
    log(f"=== старт, python {sys.version.split()[0]} ({sys.executable})")
    try:
        import mlx_whisper  # noqa: F401
    except Exception as e:  # noqa: BLE001
        log(f"!!! в этом python нет mlx_whisper: {e}")
        status["error"] = f"mlx_whisper: {e}"
        save_status()
        sys.exit(1)
    if PROBE_CACHE.exists():
        try:
            probe_cache = json.loads(PROBE_CACHE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            probe_cache = {}
    transcribed = set()
    while True:
        try:
            if Path(__file__).stat().st_mtime != SELF_MTIME:
                log("run.py обновлён — перезапускаюсь")
                save_status()
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except OSError:
            pass
        try:
            m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            log(f"manifest.json не читается ({e}) — жду минуту")
            time.sleep(60)
            continue
        queue = []
        for it in m.get("yadisk", []):
            k = "ya:" + it["public_key"] + it["path"]
            if k not in done_once:
                try:
                    do_yadisk(it, queue)
                    done_once.add(k)
                except Exception as e:  # noqa: BLE001
                    log(f"Яндекс Диск ошибка: {e}")
        for it in m.get("youtube", []):
            k = "yt:" + it["url"]
            if k not in done_once:
                try:
                    if do_youtube(it, queue):
                        done_once.add(k)
                except Exception as e:  # noqa: BLE001
                    log(f"YouTube ошибка: {e}")
        # видео из Telegram, найденные раньше (в т.ч. до перезапуска)
        for it in m.get("telegram_videos", []):
            _, _, data = course_dirs(it["course"])
            for p in (data / "telegram").glob("*"):
                if p.stem == safe(it["name"]):
                    queue.append((it["course"], "telegram — " + safe(it["name"]), p))
        do_tg_files(m.get("telegram_files", []))
        try:
            do_watch_folders(m.get("watch_folders", []), queue)
        except Exception as e:  # noqa: BLE001
            log(f"Папки ошибка: {e}")
        try:
            do_tg_videos(m.get("telegram_videos", []), queue)
        except Exception as e:  # noqa: BLE001
            log(f"Telegram поиск ошибка: {e}")
        for course, title, path in queue:
            if (course, title) in transcribed:
                continue
            transcribe(course, title, path)
            transcribed.add((course, title))
            do_tg_files(m.get("telegram_files", []))     # между длинными расшифровками проверяем новое
        pending = [k for sect in ("telegram_files", "telegram_videos") for k, v in status[sect].items()
                   if not v.startswith("ok")]
        status["pending"] = pending
        save_status()
        if m.get("finish_when_done") and not pending:
            break
        if time.time() - START > MAX_HOURS * 3600:
            log("прошло 8 часов — останавливаюсь; перезапустите, если что-то не докачалось")
            break
        time.sleep(60)
    status["done"] = True
    save_status()
    log("=== всё готово")


if __name__ == "__main__":
    main()
