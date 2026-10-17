"""Общие функции раздела 05: пути, чтение сырых загрузок Meta и плоская строка объявления.

Разметка текста (язык, ниша, воронка, цены, риск) — из ../03-reklama-meta/classify.py, без изменений.
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
DATA = Path.home() / "Data" / "online-shkola-uz" / "05-razbor-konkurentov"
RAW_META = DATA / "raw" / "meta"
TASHKENT = timezone(timedelta(hours=5))

sys.path.insert(0, str(PROJECT / "research" / "03-reklama-meta"))
import classify  # noqa: E402

DCO_TEMPLATE_RE = re.compile(r"\{\{[^}]+\}\}")
INSTAGRAM_RE = re.compile(r"(?:instagram\.com|instagr\.am)/([A-Za-z0-9_.]{2,30})", re.I)
TELEGRAM_RE = re.compile(r"(?:t\.me|telegram\.me)/(?!\+|joinchat|s/)([A-Za-z0-9_]{4,32})", re.I)
YOUTUBE_RE = re.compile(r"youtube\.com/(@[A-Za-z0-9_.-]{2,60}|channel/[A-Za-z0-9_-]{10,})", re.I)
NOT_HANDLES = {"p", "reel", "reels", "stories", "explore", "share", "accounts", "tv"}


def load_raw(kind: str) -> list[dict]:
    """Все сохранённые загрузки одного режима meta_collect.py (discover, brands, ad, page)."""
    return [json.loads(p.read_text(encoding="utf-8")) | {"_file": p.name}
            for p in sorted((RAW_META / kind).glob("*.json"))]


def unwrap_link(url: str | None) -> str:
    if not url:
        return ""
    parts = urlsplit(url)
    if parts.netloc.endswith("l.facebook.com") and parts.path.startswith("/l.php"):
        return unquote(parse_qs(parts.query).get("u", [url])[0])
    return url


def domain_of(url: str | None) -> str:
    host = (urlsplit(unwrap_link(url)).hostname or "").lower()
    return host.removeprefix("www.")


def ad_text(ad: dict) -> str:
    """Текст объявления: основной текст, заголовок, описание и тексты карточек (без шаблонов DCO)."""
    snap = ad.get("snapshot") or {}
    parts = [((snap.get("body") or {}).get("text") or ""), snap.get("title") or "", snap.get("link_description") or ""]
    for card in snap.get("cards") or []:
        parts += [card.get("body") or "", card.get("title") or "", card.get("link_description") or ""]
    text = " ".join(p for p in parts if p and not DCO_TEMPLATE_RE.fullmatch(p.strip()))
    return classify.clean_body(DCO_TEMPLATE_RE.sub(" ", text))


def ad_links(ad: dict) -> list[str]:
    snap = ad.get("snapshot") or {}
    links = [unwrap_link(snap.get("link_url"))] + [unwrap_link(c.get("link_url")) for c in snap.get("cards") or []]
    return [l for l in dict.fromkeys(links) if l]


def social_handles(text: str, links: list[str]) -> dict[str, list[str]]:
    blob = " ".join([text, *links])
    found = {
        "instagram": [h for h in INSTAGRAM_RE.findall(blob) if h.lower() not in NOT_HANDLES],
        "telegram": TELEGRAM_RE.findall(blob),
        "youtube": YOUTUBE_RE.findall(blob),
    }
    return {k: list(dict.fromkeys(v)) for k, v in found.items() if v}


def flat_ad(ad: dict, fetched_at: str) -> dict:
    """Одна строка на объявление — всё, что нужно для порогов, тегов и отчёта."""
    snap = ad.get("snapshot") or {}
    fetched = datetime.fromisoformat(fetched_at).astimezone(TASHKENT)
    start = datetime.fromtimestamp(ad["start_date"], TASHKENT) if ad.get("start_date") else None
    text = ad_text(ad)
    links = ad_links(ad)
    main_link = links[0] if links else ""
    prices, incomes = classify.parse_money(text)
    videos = snap.get("videos") or []
    images = snap.get("images") or []
    cards = snap.get("cards") or []
    return {
        "library_id": str(ad.get("ad_archive_id")),
        "ad_url": f"https://www.facebook.com/ads/library/?id={ad.get('ad_archive_id')}",
        "page_id": str(ad.get("page_id") or snap.get("page_id") or ""),
        "page_name": ad.get("page_name") or snap.get("page_name") or "",
        "page_likes": snap.get("page_like_count") or "",
        "page_profile_uri": snap.get("page_profile_uri") or "",
        "page_categories": "; ".join(snap.get("page_categories") or []),
        "started": start.date().isoformat() if start else "",
        "days_running": (fetched.date() - start.date()).days if start else "",
        "is_active": ad.get("is_active"),
        "collation_id": ad.get("collation_id") or "",
        "collation_count": ad.get("collation_count") or 1,
        "display_format": snap.get("display_format") or "",
        "platforms": "; ".join(ad.get("publisher_platform") or []),
        "n_videos": len(videos) + sum(1 for c in cards if c.get("video_hd_url") or c.get("video_sd_url")),
        "n_images": len(images) + sum(1 for c in cards if c.get("original_image_url") or c.get("resized_image_url")),
        "n_cards": len(cards),
        "cta_text": snap.get("cta_text") or "",
        "cta_type": snap.get("cta_type") or "",
        "link_url": main_link,
        "landing_domain": domain_of(main_link),
        "all_links": " | ".join(links),
        "lang": classify.detect_lang(text),
        "info_score": classify.info_score(text),
        "niches": "; ".join(classify.classify_niches(text, [])),
        "funnels": "; ".join(classify.classify_funnel(text, snap.get("cta_text"), domain_of(main_link))),
        "price_min_uzs": min(prices) if prices else "",
        "income_claim_max_uzs": max(incomes) if incomes else "",
        "risk_flag": classify.is_risky(text),
        "socials": json.dumps(social_handles(text, links), ensure_ascii=False),
        "text": text,
        "fetched_at": fetched_at,
    }
