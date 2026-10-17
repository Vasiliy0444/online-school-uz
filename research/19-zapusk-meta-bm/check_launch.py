#!/usr/bin/env python3
"""Проверка launch.json и реестра перед заливкой в Meta.

    python3 check_launch.py            # файлы, размеры, имена, тексты, бюджеты, свежесть сборки
    python3 check_launch.py --online   # плюс: ссылки raw отдают файл того же размера

Выход: 0 — ошибок нет (предупреждения возможны), 1 — есть ошибки.
"""
import json
import re
import subprocess
import sys
import urllib.request

import build_launch as L

B = L.B
NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
CAMPAIGN_RE = re.compile(r"^[a-z0-9_]+$")
START_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
SIZES = {"feed_4x5": (1080, 1350), "stories_reels_9x16": (1080, 1920)}
CARD_SIZE = (1080, 1080)
MAX_ADS_PER_ADSET = 5
MIN_DAILY_MINOR = 100  # минимум кабинета по ads_get_ad_accounts, центов
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".mp4", ".mov"}


def pick_hook(utm_content: str) -> str | None:
    """Как pickHook в websites/ii-na-zakaz-mini/js/hooks.js."""
    words = [w for w in re.split(r"[^a-z0-9]+", utm_content.lower()) if w]
    if "math" in words:
        i = words.index("math")
        return "math_a" if i + 1 < len(words) and words[i + 1] == "a" else "math_b"
    return next((k for k in ("compare", "clients", "zero", "home", "now") if k in words), None)


def git_ok(commit: str, path: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{commit}:{path}"], cwd=L.ROOT,
                          capture_output=True).returncode == 0


def check_media(label: str, kind: str, media: list[dict], errors: list[str]) -> None:
    if kind == "carousel":
        if not 2 <= len(media) <= 10:
            errors.append(f"{label}: карточек {len(media)}, нужно 2–10")
        expected = {m["role"]: CARD_SIZE for m in media}
    else:
        roles = [m["role"] for m in media]
        if roles != list(SIZES):
            errors.append(f"{label}: форматы {roles}, нужны 4x5 и 9x16")
        expected = SIZES
    for m in media:
        where = f"{label} {m['role']}"
        if not m.get("path"):
            errors.append(f"{where}: файл не найден")
            continue
        if m["path"].split("/")[-1].startswith("V4 "):
            errors.append(f"{where}: V4 с fbstore.shop — в Meta не лить")
        path = L.ROOT / m["path"]
        if not path.exists():
            errors.append(f"{where}: нет файла {m['path']}")
            continue
        if path.stat().st_size != m.get("bytes"):
            errors.append(f"{where}: размер на диске {path.stat().st_size}, в launch.json {m.get('bytes')} — пересобрать")
        if (m.get("width"), m.get("height")) != expected.get(m["role"]):
            errors.append(f"{where}: {m.get('width')}×{m.get('height')}, нужно {expected.get(m['role'])}")
        if kind == "video" and not m.get("duration_s"):
            errors.append(f"{where}: не удалось прочитать длительность видео")
        if not m.get("commit") or not m.get("url"):
            errors.append(f"{where}: файл не закоммичен или изменён — ссылки raw нет")
        elif not git_ok(m["commit"], m["path"]):
            errors.append(f"{where}: в коммите {m['commit'][:7]} нет файла")


def check_ad(ad: dict, adset: dict, camp: dict, errors: list[str], warnings: list[str]) -> None:
    label = f"{camp['name']}/{adset['name']}/{ad['name']}"
    if not NAME_RE.match(ad["name"]) or len(ad["name"]) > 20:
        errors.append(f"{label}: имя объявления — латиница, цифры, _ и -, не длиннее 20 знаков")
    want = "math_b" if ad["hook"] == "math" else ad["hook"]
    if pick_hook(ad["name"]) != want:
        errors.append(f"{label}: лендинг выберет хук {pick_hook(ad['name'])!r}, нужен {want!r}")
    if not START_RE.match(ad["bot_start_tag"]):
        errors.append(f"{label}: метка бота {ad['bot_start_tag']!r} длиннее 64 знаков или с лишними символами")
    if ad["creative_code"] in L.NEVER:
        errors.append(f"{label}: креатив {ad['creative_code']} — не для Meta")
    if not ad["body_options"] or not all(t.strip() for t in ad["body_options"]) or not ad["body_fallback"].strip():
        errors.append(f"{label}: пустой основной текст")
    expected_bodies = 1 if ad["format"] == "video" else 3
    if len(ad["body_options"]) != expected_bodies:
        errors.append(f"{label}: вариантов текста {len(ad['body_options'])}, нужно {expected_bodies}")
    for text in ad["body_options"]:
        if re.search("[А-Яа-яЁё]", text):
            errors.append(f"{label}: кириллица в узбекском тексте")
            break
    if ad["title"] != B.HEADLINE or ad["call_to_action"] != B.CTA or ad["description"] != "":
        errors.append(f"{label}: заголовок, описание или кнопка не по плану")
    if "{{ad.name}}" not in ad["url_tags"] or "utm_source=meta" not in ad["url_tags"]:
        errors.append(f"{label}: в параметрах URL нет utm_source=meta или {{{{ad.name}}}}")
    if not (ad["link_url"].startswith("https://") or ad["link_url"] == "{{LANDING_URL}}"):
        errors.append(f"{label}: ссылка {ad['link_url']!r} без https://")
    if camp["labels"] != ad["labels"]:
        errors.append(f"{label}: метки объявления {ad['labels']} не совпадают с кампанией {camp['labels']}")
    if ad["risk"] in ("medium", "high") and "RISK" not in camp["labels"]:
        errors.append(f"{label}: креатив риска «{ad['risk']}» стоит не в RISK-кампании")
    if ad["risk"] == "low" and "RISK" in camp["labels"]:
        warnings.append(f"{label}: креатив низкого риска в RISK-кампании")
    check_media(label, ad["format"], ad["media"], errors)


def check_structure(launch: dict, errors: list[str], warnings: list[str]) -> None:
    codes, names = [], []
    caps = 0
    for camp in launch["campaigns"]:
        caps += camp["spend_cap_usd"]
        if not CAMPAIGN_RE.match(camp["name"]) or len(camp["name"]) > 18:
            errors.append(f"{camp['name']}: имя кампании — строчная латиница, цифры и _, не длиннее 18 знаков")
        if camp["budget_level"] != "ADSET" or camp["is_adset_budget_sharing_enabled"] is not False:
            errors.append(f"{camp['name']}: нужен бюджет на группу и выключенный делёж бюджета")
        days = L.DAYS_IN_WEEK.get(camp["start"])
        per_day = sum(a["daily_budget_usd"] for a in camp["adsets"])
        if days is None:
            errors.append(f"{camp['name']}: неизвестный день старта {camp['start']!r}")
        elif per_day * days > camp["spend_cap_usd"]:
            errors.append(f"{camp['name']}: ${per_day:g} × {days} дн. больше лимита трат ${camp['spend_cap_usd']}")
        for adset in camp["adsets"]:
            if adset["daily_budget_minor"] < MIN_DAILY_MINOR:
                errors.append(f"{camp['name']}/{adset['name']}: бюджет меньше минимума кабинета")
            if len(adset["ads"]) > MAX_ADS_PER_ADSET:
                errors.append(f"{camp['name']}/{adset['name']}: объявлений {len(adset['ads'])}, максимум {MAX_ADS_PER_ADSET}")
            if adset["promoted_object"]["custom_event_type"] != "LEAD":
                errors.append(f"{camp['name']}/{adset['name']}: событие не Lead")
            if set(adset["targeting"]["publisher_platforms"]) != {"facebook", "instagram"}:
                errors.append(f"{camp['name']}/{adset['name']}: плейсменты не Facebook + Instagram")
            for ad in adset["ads"]:
                codes.append(ad["creative_code"])
                names.append(ad["name"])
                check_ad(ad, adset, camp, errors, warnings)
    if caps > launch["week_cap_usd"]:
        errors.append(f"лимиты трат кампаний ${caps} больше недельного потолка ${launch['week_cap_usd']}")
    dupes = sorted({c for c in codes if codes.count(c) > 1})
    if dupes:
        errors.append(f"креативы стоят больше одного раза: {dupes}")
    if len(set(names)) != len(names):
        errors.append("имена объявлений повторяются")
    plan_1510 = {code for adset in B.CAMPAIGNS[0]["adsets"] for code in adset["ads"]}
    if set(codes) != plan_1510:
        errors.append(f"креативы волны 1 не совпадают с планом 15.10: нет {sorted(plan_1510 - set(codes))}, "
                      f"лишние {sorted(set(codes) - plan_1510)}")


def check_registry(registry: list[dict], errors: list[str], warnings: list[str]) -> None:
    seen = {m["path"] for item in registry for m in item["media"] if m.get("path")}
    folder = B.CREO_DIR
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(L.ROOT).as_posix()
        if path.is_file() and path.suffix.lower() in MEDIA_EXT and not path.name.startswith("_") \
                and "Обзор всех креативов" not in path.name and rel not in seen:
            warnings.append(f"файл без кода креатива в реестре: {rel}")
    for item in registry:
        if item["status"] == "не распределён":
            warnings.append(f"{item['code']}: не распределён ни в волну, ни в резерв")
        if item["code"] not in L.NEVER and not item["ad_name"]:
            check_media(item["code"], item["kind"], item["media"], errors)


def check_fresh(launch: dict, registry: list[dict], errors: list[str]) -> None:
    fresh_launch, fresh_registry, fresh_md = L.build_all()
    if fresh_launch != launch or fresh_registry != registry or fresh_md != L.OUT_MD.read_text(encoding="utf-8"):
        errors.append("launch.json, registry.json или реестр устарели — запустить python3 build_launch.py")


def check_placeholders(launch: dict, warnings: list[str]) -> None:
    account = launch["account"]
    for key in ("pixel_id", "page_id", "instagram_user_id"):
        if not account.get(key):
            warnings.append(f"ids.json: {key} не задан — до заливки нужен реальный ID (этап 0 плана)")


def check_online(launch: dict, errors: list[str]) -> None:
    media = [m for c in launch["campaigns"] for a in c["adsets"] for ad in a["ads"] for m in ad["media"] if m.get("url")]
    for m in media:
        req = urllib.request.Request(m["url"], method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                size = int(resp.headers.get("Content-Length", -1))
                if resp.status != 200 or size != m["bytes"]:
                    errors.append(f"{m['path']}: raw отдаёт {resp.status}, {size} байт вместо {m['bytes']}")
        except Exception as exc:  # сеть или 404 — всё ошибка: Meta не скачает файл
            errors.append(f"{m['path']}: raw недоступен ({exc})")
    print(f"ссылок raw проверено: {len(media)}")


def main() -> int:
    launch = json.loads(L.OUT_LAUNCH.read_text(encoding="utf-8"))
    registry = json.loads(L.OUT_REGISTRY.read_text(encoding="utf-8"))
    errors, warnings = [], []
    check_fresh(launch, registry, errors)
    check_structure(launch, errors, warnings)
    check_registry(registry, errors, warnings)
    check_placeholders(launch, warnings)
    if "--online" in sys.argv:
        check_online(launch, errors)
    n_ads = sum(len(a["ads"]) for c in launch["campaigns"] for a in c["adsets"])
    for line in errors:
        print("ОШИБКА  ", line)
    for line in warnings:
        print("ВНИМАНИЕ", line)
    print(f"Кампаний {len(launch['campaigns'])}, объявлений {n_ads}, креативов в реестре {len(registry)}. "
          f"Итог: ошибок {len(errors)}, предупреждений {len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
