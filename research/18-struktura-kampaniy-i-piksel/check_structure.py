#!/usr/bin/env python3
"""Проверяет structure.json перед заливкой через Meta MCP.

Запуск: python3 check_structure.py   (код выхода 1, если есть ошибки)
"""
import json
import pathlib
import re
import sys
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
STRUCTURE = HERE / "structure.json"
EVENTS = HERE / "events.json"

MAX_ADS_PER_ADSET = 5
MAX_AD_NAME = 20        # лендинг кладёт utm_content в метку бота не длиннее 20 знаков
MAX_CAMPAIGN_NAME = 18  # то же для utm_campaign (websites/ii-na-zakaz-mini/js/attribution.js)
HOOK_WORDS = {"compare", "clients", "zero", "home", "now", "math"}  # js/hooks.js
ASCII_NAME = re.compile(r"^[A-Za-z0-9_\-]+$")
NOT_FOR_META = {"V4"}


def hook_of(name: str) -> str | None:
    words = [w for w in re.split(r"[^a-z0-9]+", name.lower()) if w]
    return next((w for w in words if w in HOOK_WORDS), None)


def check_media(ad: dict) -> list[str]:
    media = ad["media"]
    if ad["format"] == "carousel":
        cards = media.get("cards_1x1") or []
        problems = [] if len(cards) >= 2 else [f"{ad['name']}: в карусели меньше 2 карточек"]
        return problems + [f"{ad['name']}: нет файла {c}" for c in cards if not pathlib.Path(c).is_file()]
    problems = []
    for key in ("feed_4x5", "stories_reels_9x16"):
        path = media.get(key)
        if not path:
            problems.append(f"{ad['name']}: не найден {key}")
        elif not pathlib.Path(path).is_file():
            problems.append(f"{ad['name']}: нет файла {path}")
    return problems


def check_ad(ad: dict) -> list[str]:
    problems = check_media(ad)
    name = ad["name"]
    if not ASCII_NAME.match(name):
        problems.append(f"{name}: в имени не только латиница, цифры, _ и -")
    if len(name) > MAX_AD_NAME:
        problems.append(f"{name}: имя длиннее {MAX_AD_NAME} знаков, метка в боте обрежется")
    if hook_of(name) != ad["hook"]:
        problems.append(f"{name}: лендинг не найдёт хук «{ad['hook']}» в имени")
    want = 1 if ad["format"] == "video" else 3
    if len(ad["body_options"]) != want or not all(t.strip() for t in ad["body_options"]):
        problems.append(f"{name}: ожидалось {want} непустых варианта текста")
    if ad["creative_id"] in NOT_FOR_META:
        problems.append(f"{name}: креатив {ad['creative_id']} в Meta не льём")
    if ad["status"] != "PAUSED":
        problems.append(f"{name}: статус не PAUSED")
    return problems


def check_campaigns(data: dict) -> tuple[list[str], Counter, dict]:
    problems: list[str] = []
    ad_names: Counter = Counter()
    budget_by_start: dict = defaultdict(float)
    for camp in data["campaigns"]:
        if not ASCII_NAME.match(camp["name"]) or len(camp["name"]) > MAX_CAMPAIGN_NAME:
            problems.append(f"{camp['name']}: имя кампании не латиница или длиннее {MAX_CAMPAIGN_NAME}")
        if camp["status"] != "PAUSED" or camp["is_adset_budget_sharing_enabled"]:
            problems.append(f"{camp['name']}: не PAUSED или включён budget sharing")
        for adset in camp["adsets"]:
            if len(adset["ads"]) > MAX_ADS_PER_ADSET:
                problems.append(f"{adset['name']}: больше {MAX_ADS_PER_ADSET} объявлений")
            event = adset["promoted_object"]["custom_event_type"]
            if event != "COMPLETE_REGISTRATION":
                problems.append(f"{adset['name']}: событие оптимизации {event}, ожидалось COMPLETE_REGISTRATION")
            budget_by_start[adset["start"]] += adset["daily_budget_usd"]
            for ad in adset["ads"]:
                ad_names[ad["name"]] += 1
                problems += check_ad(ad)
    problems += [f"{name}: имя объявления повторяется {n} раз" for name, n in ad_names.items() if n > 1]
    return problems, ad_names, budget_by_start


def check_c1_coverage(data: dict) -> list[str]:
    """Каждый креатив волны 1 стоит в широкой кампании ровно один раз."""
    c1 = next(c for c in data["campaigns"] if c["key"] == "C1")
    used = Counter(ad["creative_id"] for a in c1["adsets"] for ad in a["ads"])
    all_ids = {ad["creative_id"] for c in data["campaigns"] for a in c["adsets"] for ad in a["ads"]}
    reserve = set(data["reserve_creatives"]) | set(data["wave2_creatives"])
    problems = [f"C1: {cid} стоит {n} раз" for cid, n in used.items() if n != 1]
    problems += [f"C1: {cid} есть в других кампаниях, но не в C1" for cid in all_ids - set(used)]
    problems += [f"C1: резервный {cid} попал в волну 1" for cid in reserve & set(used)]
    return problems


def check_events(data: dict) -> list[str]:
    if not EVENTS.is_file():
        return ["events.json ещё нет — сверка событий пропущена"]
    events = {e["name"]: e for e in json.loads(EVENTS.read_text())["events"]}
    reg = events.get("CompleteRegistration")
    if not reg or not reg.get("optimization"):
        return ["events.json: у CompleteRegistration нет пометки optimization"]
    return []


def main() -> int:
    data = json.loads(STRUCTURE.read_text())
    problems, ad_names, budget_by_start = check_campaigns(data)
    problems += check_c1_coverage(data)
    warnings = check_events(data)
    adsets = sum(len(c["adsets"]) for c in data["campaigns"])
    print(f"Кампаний: {len(data['campaigns'])}, групп: {adsets}, объявлений: {len(ad_names)}")
    for start, total in budget_by_start.items():
        print(f"  бюджет групп со стартом «{start}»: ${total:g} в день")
    for w in warnings:
        print(f"ВНИМАНИЕ: {w}")
    if problems:
        print(f"Ошибок: {len(problems)}")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("Ошибок нет.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
