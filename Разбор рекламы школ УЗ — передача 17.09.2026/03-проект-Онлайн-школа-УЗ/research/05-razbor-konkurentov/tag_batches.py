#!/usr/bin/env python3
"""Этап 6: порции креативов для разметки агентами (без сети).

Отбор по школе (до --cap креативов): все из первых 30 «по показам», все идущие 30+ дней, все размноженные
(copies ≥ 2) и перезапущенные; остальное — случайная выборка с фиксированным зерном. Не отобранные остаются
в галерее с автоматическими данными (формат, срок, текст, расшифровка) — это указывается в отчёте.
Порция — JSON со всем, что нужно агенту: пути к листам кадров, текст объявления, расшифровка, метаданные.
Выход: 04-razbor/batches/<school>_<NN>.json и 04-razbor/tagging_plan.csv (кто отобран и почему).
Запуск: python3 tag_batches.py [--cap 30] [--batch 25]
"""
import argparse
import csv
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = Path.home() / "Data" / "online-shkola-uz" / "05-razbor-konkurentov"
OUT = HERE / "04-razbor"
SEED = 20260916
csv.field_size_limit(10**9)


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


TRANSCRIPT_HEAD, TRANSCRIPT_TAIL = 1800, 900


def transcript_excerpt(text: str) -> str:
    """Начало и конец расшифровки: хук в начале, призыв и оффер — в конце ролика."""
    if len(text) <= TRANSCRIPT_HEAD + TRANSCRIPT_TAIL:
        return text
    return f"{text[:TRANSCRIPT_HEAD]}\n[…]\n{text[-TRANSCRIPT_TAIL:]}"


def media_of(school: str, library_ids: list[str], transcripts: dict) -> tuple[Path, dict]:
    """Папка с файлами креатива и его расшифровка.

    Одинаковый медиафайл media_download.py качает один раз — в папку того объявления группы, которое встретил первым,
    а представитель группы (самое раннее объявление) может быть другим.
    """
    folders = [DATA / "kreativy" / school / "meta" / lid for lid in library_ids]
    ready = [f for f in folders if (f / "sheet_hook.jpg").exists() or (f / "image_512.jpg").exists()]
    with_media = [f for f in folders if any(f.glob(f"{f.name}_*_video_*.mp4")) or any(f.glob(f"{f.name}_*_image.*"))]
    folder = next(iter(ready + with_media + [f for f in folders if any(f.glob(f"{f.name}_*"))]), folders[0])
    transcript = next((transcripts[lid] for lid in library_ids if lid in transcripts), {})
    return folder, transcript


def reasons_for(c: dict) -> list[str]:
    reasons = []
    if c["best_top30_rank"]:
        reasons.append(f"топ-30 по показам (место {c['best_top30_rank']})")
    if num(c["max_days_running"]) >= 30:
        reasons.append(f"идёт {c['max_days_running']} дней")
    if num(c["collation_max"]) >= 2 or num(c["ads"]) >= 2:
        reasons.append(f"копий {max(num(c['collation_max']), num(c['ads'])):.0f}")
    if num(c["relaunches"]) >= 2:
        reasons.append(f"перезапусков {c['relaunches']}")
    return reasons


def select(school: str, items: list[dict], cap: int, tagged: set[str]) -> tuple[list, list, list]:
    """(уже размеченные, отобранные к разметке, не отобранные). Размеченные входят в лимит школы и в порции не попадают."""
    already, must, rest = [], [], []
    for c in items:
        reasons = reasons_for(c)
        if c["representative_id"] in tagged:
            already.append((c, ["уже размечен", *reasons]))
        else:
            (must if reasons else rest).append((c, reasons))
    # Приоритет внутри обязательных: место в топ-30 по показам, затем срок показа.
    must.sort(key=lambda cr: (num(cr[0]["best_top30_rank"], 99.0), -num(cr[0]["max_days_running"])))
    # Зерно на школу: выборка школы не меняется, когда в данные добавляются другие школы.
    rest.sort(key=lambda cr: cr[0]["representative_id"])
    random.Random(f"{SEED}-{school}").shuffle(rest)
    room = max(0, cap - len(already))
    chosen = must[:room]
    leftover = must[room:] + rest  # обязательные сверх лимита уходят в общий остаток
    extra = max(0, room - len(chosen))
    chosen += [(c, ["случайная выборка"]) for c, _ in leftover[:extra]]
    return already, chosen, leftover[extra:]


def batch_item(school: str, c: dict, reasons: list[str], ads: dict, transcripts: dict) -> dict:
    lid = c["representative_id"]
    folder, tr = media_of(school, [lid] + [x for x in c["library_ids"].split() if x != lid], transcripts)
    transcript_path = Path(tr["transcript_txt"]) if tr.get("transcript_txt") else None
    return {
        "creative_id": lid, "school_id": school, "creative_key": c["creative_key"], "ad_url": c["ad_url"],
        "display_format": c["display_format"], "ads_with_this_creative": int(num(c["ads"])),
        "copies_max": int(num(c["collation_max"], 1)), "first_started": c["first_started"],
        "max_days_running": c["max_days_running"], "relaunches": c["relaunches"], "best_top30_rank": c["best_top30_rank"],
        "cta_button": c["cta_text"], "landing_domain": c["landing_domain"],
        "link_url": ads.get(lid, {}).get("link_url", ""), "ad_text": ads.get(lid, {}).get("text", ""),
        "duration_s": tr.get("duration_s", ""), "transcript_quality": tr.get("quality", ""),
        "transcript": transcript_excerpt(transcript_path.read_text(encoding="utf-8")) if transcript_path and transcript_path.exists() else "",
        "sheet_hook": str(folder / "sheet_hook.jpg") if (folder / "sheet_hook.jpg").exists() else "",
        "sheet_overview": str(folder / "sheet_overview.jpg") if (folder / "sheet_overview.jpg").exists() else "",
        "image_512": str(folder / "image_512.jpg") if (folder / "image_512.jpg").exists() else "",
        # у динамических объявлений (DCO) видео карточек часто скачаны в папку другого объявления — остаются превью
        "preview_images": [str(p) for p in sorted(folder.glob("*_video_preview.jpg"))[:4]]
        if not (folder / "sheet_hook.jpg").exists() and not (folder / "image_512.jpg").exists() else [],
        "selected_because": "; ".join(reasons),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=30, help="креативов на школу вместе с уже размеченными")
    ap.add_argument("--batch", type=int, default=25)
    ap.add_argument("--schools", default="", help="переписать порции только этих школ (через запятую)")
    args = ap.parse_args()
    only = {x for x in args.schools.split(",") if x}
    creatives = read(HERE / "02-reklama" / "creatives_unique.csv")
    ads = {r["library_id"]: r for r in read(HERE / "02-reklama" / "ads_meta.csv")}
    transcripts = {r["library_id"]: r for r in read(HERE / "02-reklama" / "transcripts_index.csv")}
    plan, batches = [], {}
    by_school: dict[str, list[dict]] = {}
    for c in creatives:
        by_school.setdefault(c["school_id"], []).append(c)
    for school, items in sorted(by_school.items()):
        tagged = {p.stem for p in (OUT / "tags" / school).glob("*.json")}
        already, chosen, skipped = select(school, items, args.cap, tagged)
        for c, reasons in already + chosen:
            item = batch_item(school, c, reasons, ads, transcripts)
            if c["representative_id"] not in tagged:
                batches.setdefault(school, []).append(item)
            plan.append({"school_id": school, "creative_id": item["creative_id"], "selected_because": item["selected_because"],
                         "has_frames": bool(item["sheet_hook"] or item["image_512"] or item["preview_images"]),
                         "has_transcript": bool(item["transcript"])})
        plan += [{"school_id": school, "creative_id": c["representative_id"], "selected_because": "не отобран (галерея без тегов)",
                  "has_frames": "", "has_transcript": ""} for c, _ in skipped]
    (OUT / "batches").mkdir(parents=True, exist_ok=True)
    count = 0
    for school, items in batches.items():
        if only and school not in only:
            continue
        for old in (OUT / "batches").glob(f"{school}_*.json"):  # порции прошлых запусков этой школы устарели
            old.unlink()
        for i in range(0, len(items), args.batch):
            (OUT / "batches" / f"{school}_{i // args.batch + 1:02d}.json").write_text(
                json.dumps(items[i:i + args.batch], ensure_ascii=False, indent=1), encoding="utf-8")
            count += 1
    with (OUT / "tagging_plan.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(plan[0].keys()))
        writer.writeheader()
        writer.writerows(plan)
    print(f"schools: {len(batches)}, creatives to tag: {sum(len(v) for v in batches.values())}, batches: {count}")


if __name__ == "__main__":
    main()
