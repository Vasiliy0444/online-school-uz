#!/usr/bin/env python3
"""Этап 8: данные HTML-отчёта (без сети).

Читает таблицы этапов 1–7 и пишет в 05-otchet/:
  data/report.js           — window.REPORT: мастер-список, школы, креативы и лендинги без картинок, цены, доли тегов, хуки;
  data/thumbs-<school>.js  — превью креативов (JPEG шириной 280, data URI) — галерея подгружает их по школе;
  data/shots-<school>.js   — верх мобильного скриншота лендингов (JPEG шириной 300);
  facts.json               — числа, которые отчёт показывает (их сверяет verify_report.py).
Видео и картинки остаются в ~/Data/online-shkola-uz/05-razbor-konkurentov/ — в отчёт идут только превью.
Запуск: python3 report_data.py
"""
import base64
import csv
import io
import json
import re
import statistics
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from PIL import Image

from aggregate import tier
from landings_snapshot import slug
from tag_batches import DATA, media_of

HERE = Path(__file__).resolve().parent
OUT = HERE / "05-otchet"
SNAPSHOT = date(2026, 9, 16)
USD_UZS = 11_765
THUMB_W, SHOT_W, SHOT_H = 280, 300, 640
LIFT_MIN_SCHOOLS = 3  # сравнение «топ-10 против остальных» показываем, только если оно есть минимум в 3 школах
QUOTABLE = {"черновое"}  # расшифровки «низкое» и «без речи» в отчёт не идут
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


def data_uri(path: Path, width: int, max_height: int | None = None) -> str:
    img = Image.open(path).convert("RGB")
    if max_height and img.height * width / img.width > max_height:
        img = img.crop((0, 0, img.width, int(max_height * img.width / width)))
    img = img.resize((width, max(1, round(img.height * width / img.width))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=62, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def destination(ad: dict) -> str:
    """Куда ведёт клик — по ссылке и кнопке объявления."""
    domain, link, cta = ad["landing_domain"], ad["link_url"].rstrip("/"), ad["cta_type"]
    if domain == "fb.me" and link in ("http://fb.me", "https://fb.me"):
        return "мгновенная форма Meta"  # так библиотека показывает объявления с формой заявки
    if domain in ("t.me", "telegram.me"):
        return "Telegram"
    if domain.endswith("instagram.com") or cta == "INSTAGRAM_MESSAGE":
        return "Instagram"
    if domain in ("m.me", "wa.me", "api.whatsapp.com") or cta in ("MESSAGE_PAGE", "WHATSAPP_MESSAGE"):
        return "переписка"
    if domain in ("itunes.apple.com", "apps.apple.com", "play.google.com"):
        return "приложение"
    if domain in ("forms.gle", "docs.google.com"):
        return "Google-форма"
    return "сайт" if domain else "без ссылки"


def shares(counter: Counter, total: int) -> list[dict]:
    return [{"value": k, "count": v, "share": round(v / total, 3)} for k, v in counter.most_common()] if total else []


def thumb_source(folder: Path) -> Path | None:
    for name in ("thumb.jpg", "image_512.jpg"):
        if (folder / name).exists():
            return folder / name
    return next(iter(sorted(folder.glob("*_0_video_preview.jpg")) + sorted(folder.glob("*_image.jpg"))), None)


def tag_view(tag: dict | None) -> dict | None:
    if not tag:
        return None
    hook, meaning, offer, cta, speaker = tag["hook"], tag["meaning"], tag["offer"], tag["cta"], tag["speaker"]
    return {
        "hook": hook["verbatim"], "hook_types": hook.get("types", []), "visual": hook.get("visual", []),
        "meaning": meaning.get("main", []), "income_claim": meaning.get("income_claim", ""),
        "offer": offer.get("items", []), "price_quote": offer.get("price_quote", ""),
        "cta_in_creative": cta.get("in_creative", ""), "destination": cta.get("destination", ""),
        "funnel_stage": cta.get("funnel_stage", ""), "speaker": speaker.get("role", ""),
        "speaker_name": speaker.get("public_name", ""), "style": tag.get("style", []), "format": tag["format"],
        "language": tag.get("language", ""), "subtitles": tag.get("burned_subtitles"), "risk": tag.get("risk", False),
        "confidence": tag.get("confidence", ""), "notes": tag.get("notes", ""),
    }


def creative_rows(school: str, creatives: list[dict], ads: dict, transcripts: dict, plan: dict) -> tuple[list, dict]:
    rows, thumbs = [], {}
    for c in creatives:
        lid = c["representative_id"]
        group = [lid] + [x for x in c["library_ids"].split() if x != lid]
        folder, tr = media_of(school, group, transcripts)
        ad = ads.get(lid, {})
        tag_path = HERE / "04-razbor" / "tags" / school / f"{lid}.json"
        transcript_file = Path(tr["transcript_txt"]) if tr.get("transcript_txt") else None
        quotable = tr.get("quality") in QUOTABLE and transcript_file and transcript_file.exists()
        source = thumb_source(folder)
        if source:
            thumbs[lid] = data_uri(source, THUMB_W)
        rows.append({
            "id": lid, "school": school, "ad_url": c["ad_url"], "format": c["display_format"], "ads": int(num(c["ads"], 1)),
            "copies": int(num(c["collation_max"], 1)), "first_started": c["first_started"], "last_started": c["last_started"],
            "relaunches": int(num(c["relaunches"], 1)), "days": int(num(c["max_days_running"])),
            "tier": tier(num(c["max_days_running"])), "rank": int(num(c["best_top30_rank"])) if c["best_top30_rank"] else None,
            "cta": c["cta_text"], "destination": destination(ad) if ad else "", "link": ad.get("link_url", ""),
            "domain": c["landing_domain"], "platforms": ad.get("platforms", ""), "text": ad.get("text", ""),
            "duration_s": num(tr.get("duration_s"), None) if tr else None, "transcript_quality": tr.get("quality", ""),
            "transcript": transcript_file.read_text(encoding="utf-8")[:1200] if quotable else "",
            "media_folder": str(folder), "has_thumb": bool(source), "selected_because": plan.get(lid, ""),
            "tags": tag_view(json.loads(tag_path.read_text(encoding="utf-8")) if tag_path.exists() else None),
        })
    return rows, thumbs


def ads_profile(rows: list[dict], creatives: list[dict]) -> dict:
    total = len(rows)
    days = [num(r["days_running"]) for r in rows if r["days_running"] != ""]
    durations = [c["duration_s"] for c in creatives if c["duration_s"]]
    recent_cut = (SNAPSHOT - timedelta(days=30)).isoformat()
    return {
        "ads": total, "unique_creatives": len(creatives),
        "formats": shares(Counter(r["display_format"] or "?" for r in rows), total),
        "destinations": shares(Counter(destination(r) for r in rows), total),
        "cta": shares(Counter(r["cta_text"] or "—" for r in rows), total),
        "domains": shares(Counter(r["landing_domain"] for r in rows if r["landing_domain"]), total),
        "platforms": shares(Counter(p for r in rows for p in r["platforms"].split("; ") if p), total),
        "tiers": shares(Counter(c["tier"] for c in creatives), len(creatives)),
        "days_median": statistics.median(days) if days else None, "days_max": max(days) if days else None,
        "launched_30d": sum(1 for r in rows if r["started"] >= recent_cut),
        "oldest_start": min((r["started"] for r in rows if r["started"]), default=""),
        "video_median_s": round(statistics.median(durations), 1) if durations else None,
        "income_claim_ads": sum(1 for r in rows if r["income_claim_max_uzs"]),
        "price_ads": sum(1 for r in rows if r["price_min_uzs"]),
    }


def landing_rows(school: str, snapshots: list[dict]) -> tuple[list, dict]:
    rows, shots = [], {}
    for s in snapshots:
        if s["school_id"] != school or s.get("duplicate_of"):
            continue
        name = s.get("dir") or slug(s["url"])
        path = HERE / "04-razbor" / "landings" / school / f"{name}.json"
        analysis = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        shot = Path(s["screenshot"]) if s.get("screenshot") else None
        if analysis and shot and shot.exists():
            shots[name] = data_uri(shot, SHOT_W, SHOT_H)
        rows.append({"id": name, "url": s["url"], "final_url": s.get("final_url", ""), "title": s.get("title", ""),
                     "stage": (analysis or {}).get("stage") or s.get("stage_auto", ""), "stage_auto": s.get("stage_auto", ""),
                     "is_archive": s.get("is_archive") in (True, "True"), "archive_url": s.get("archive_url", ""),
                     "sources": s.get("sources", ""), "has_shot": name in shots, "analysis": analysis})
    return rows, shots


def first_found(analyses: list[dict], key: str, prefer_stage: str | None = None) -> str:
    """Значение поля с первой страницы, где оно найдено (сначала — страницы нужного этапа, например оферта)."""
    ordered = sorted(analyses, key=lambda a: a.get("stage") != prefer_stage) if prefer_stage else analyses
    return next(((a.get(key) or {}).get("value", "") for a in ordered if (a.get(key) or {}).get("found")), "")


def money_facts(landings: list[dict]) -> dict:
    """Цены, рассрочка, гарантия и следующий шаг по разобранным страницам школы (страница может быть вариантом другой)."""
    analyses = [l["analysis"] for l in landings if l["analysis"]]
    prices = [t["price_uzs"] for a in analyses for t in ((a.get("price") or {}).get("tariffs") or []) if t.get("price_uzs")]
    found = lambda key: sum(1 for a in analyses if (a.get(key) or {}).get("found"))  # noqa: E731
    steps = Counter(a.get("next_step", "") for a in analyses if a.get("next_step") not in ("", "неизвестно"))
    return {
        "pages": len(analyses), "pages_with_price": sum(1 for a in analyses if (a.get("price") or {}).get("found")),
        "price_min_uzs": min(prices) if prices else None, "price_max_uzs": max(prices) if prices else None,
        "pages_with_installments": found("installments"), "pages_with_guarantee": found("guarantee"),
        "pages_with_discounts": found("discounts"), "pages_with_deadline": found("deadline"),
        "next_steps": dict(Counter(a.get("next_step", "") for a in analyses)),
        "main_next_step": steps.most_common(1)[0][0] if steps else "неизвестно",
        "stages": dict(Counter(a.get("stage", "") for a in analyses)),
        "installments_text": first_found(analyses, "installments", "оферта или оплата"),
        "guarantee_text": first_found(analyses, "guarantee", "оферта или оплата"),
        "discounts_text": first_found(analyses, "discounts"),
        "hidden_price_reason": next(((a.get("price") or {}).get("hidden_reason", "") for a in analyses
                                     if (a.get("price") or {}).get("hidden_reason")), ""),
    }


def school_block(s: dict, tables: dict, facts: dict) -> tuple[dict, dict, dict]:
    sid = s["school_id"]
    ads_rows = [a for a in tables["ads"].values() if a["school_id"] == sid]
    creatives, thumbs = creative_rows(sid, [c for c in tables["creatives"] if c["school_id"] == sid], tables["ads"],
                                      tables["transcripts"], tables["plan"])
    landings, shots = landing_rows(sid, tables["snapshots"])
    profile = ads_profile(ads_rows, creatives)
    coverage = [c for c in tables["coverage"] if c["school_id"] == sid]
    facts[sid] = {"ads_collected": profile["ads"], "unique_creatives": profile["unique_creatives"],
                  "meta_counter": sum(int(num(c["meta_counter"])) for c in coverage), "launched_30d": profile["launched_30d"],
                  "days_median": profile["days_median"], "days_max": profile["days_max"],
                  "video_median_s": profile["video_median_s"], "tagged": sum(1 for c in creatives if c["tags"]),
                  "landings": len(landings), "landings_analysed": sum(1 for l in landings if l["analysis"]),
                  "long_runners": sum(1 for c in creatives if c["days"] >= 60), "fresh": sum(1 for c in creatives if c["days"] <= 14),
                  "destinations": {d["value"]: d["share"] for d in profile["destinations"]},
                  "formats": {d["value"]: d["share"] for d in profile["formats"]},
                  "tiers": {d["value"]: d["share"] for d in profile["tiers"]}, "money": money_facts(landings),
                  "telegram_private": max((num(x["followers"]) for x in tables["socials"] if x["school_id"] == sid
                                           and x["platform"] == "telegram" and "приват" in x["account_type"]), default=0)}
    block = {
        "id": sid, "name": s["name"], "track": s["track"], "niche": s["niche"], "risk": s["risk"] == "True",
        "status": s["status"], "signals": {k: s[k] for k in ("meta_active", "unique_creatives", "evergreen", "recent", "followers_max")},
        "domains": [d.strip() for d in s["domains"].split(";") if d.strip()],
        "pages": [{**c, "ad_library": f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=UZ"
                   f"&search_type=page&view_all_page_id={c['page_id']}"} for c in coverage],
        "socials": [x for x in tables["socials"] if x["school_id"] == sid and x["followers"]],
        "profile": profile, "creatives": creatives, "landings": landings,
        "offers": [o for o in tables["offers"] if o["school_id"] == sid],
        "stopped": [x for x in tables["stopped"] if x["school_id"] == sid],
    }
    return block, thumbs, shots


PLACEHOLDER = re.compile(r"\{\{(?:(pct|int|num|plural|date):)?([^{}]+)\}\}")
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def plural(n: int, forms: str) -> str:
    """«921 объявление», «82 креатива», «63 страницы»: forms = «объявление/объявления/объявлений»."""
    one, few, many = forms.split("/")
    tail = n % 100
    word = many if 11 <= tail <= 14 else one if tail % 10 == 1 else few if 2 <= tail % 10 <= 4 else many
    return f"{n:,}".replace(",", " ") + f" {word}"


def fact(facts: dict, dotted: str):
    node = facts
    for part in dotted.split("|"):
        if not isinstance(node, dict) or part not in node:
            raise SystemExit(f"findings: нет факта «{dotted}»")
        node = node[part]
    return node


def render_findings(template, facts: dict, creative_school: dict):
    """Тексты выводов с числами только из facts: {{qadam|days_max}}, {{pct:shares|группа|поле|значение}}.

    Путь к факту — через «|» (в значениях тегов бывают точки). Примеры креативов должны существовать.
    """
    def fill(text: str) -> str:
        def one(m: re.Match) -> str:
            kind, path = m.group(1), m.group(2).strip()
            if kind == "plural":
                path, forms = path.rsplit(":", 1)
                return plural(int(round(float(fact(facts, path)))), forms)
            value = fact(facts, path)
            if kind == "date":
                y, mth, d = str(value).split("-")
                return f"{int(d)} {MONTHS[int(mth) - 1]} {y}"
            if kind == "pct":
                return f"{round(float(value) * 100)}%"
            if kind == "int":
                return f"{int(round(float(value))):,}".replace(",", " ")
            return f"{value:g}" if isinstance(value, float) else str(value)
        return PLACEHOLDER.sub(one, text)

    if isinstance(template, str):
        return fill(template)
    if isinstance(template, list):
        return [render_findings(x, facts, creative_school) for x in template]
    if isinstance(template, dict):
        out = {k: render_findings(v, facts, creative_school) for k, v in template.items()}
        for cid in out.get("examples", []):
            if cid not in creative_school:
                raise SystemExit(f"findings: креатива {cid} нет среди креативов короткого списка")
        return out
    return template


def share_facts(shares: list[dict]) -> dict:
    out: dict = {}
    for row in shares:
        out.setdefault(row["group"], {}).setdefault(row["field"], {})[row["value"]] = float(row["share"])
        out[row["group"]]["_n"] = int(row["creatives_in_group"])
    return out


def write_summary_md(findings: dict, report_url: str) -> None:
    """ИТОГ.md — те же выводы, что в отчёте, текстом (числа — из тех же фактов)."""
    ad = "https://www.facebook.com/ads/library/?id="
    lines = [f"# {findings['headline']}", "", findings["lede"], "",
             f"Отчёт: {report_url or 'см. 05-otchet/index.html'} · данные — `research/05-razbor-konkurentov/` · медиа — "
             "`~/Data/online-shkola-uz/05-razbor-konkurentov/`", "", "## Главное", ""]
    lines += [f"- **{s['value']}** — {s['label']}" for s in findings["stats"]] + [""]
    lines += [f"- **{t['title']}** {t['text']}" for t in findings["tldr"]] + ["", "## Схемы воронок", ""]
    lines += [f"- **{f['title']}** ({f['schools']}). {f['text']}" for f in findings["funnels"]] + ["", "## Что, вероятно, работает", ""]
    for w in findings["works"]:
        examples = ", ".join(f"[{cid}]({ad}{cid})" for cid in w.get("examples", []))
        lines += [f"### {w['claim']} — уверенность {w['confidence']}", "", w["evidence"], "", f"Примеры: {examples}", ""]
    lines += ["## Пустые места рынка", ""] + [f"- **{g['title']}** {g['text']}" for g in findings["gaps"]] + [""]
    (HERE / "ИТОГ.md").write_text("\n".join(lines), encoding="utf-8")


def write_js(path: Path, expression: str, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{expression} = {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))};\n", encoding="utf-8")


def main() -> None:
    reklama, razbor = HERE / "02-reklama", HERE / "04-razbor"
    tables = {
        "ads": {r["library_id"]: r for r in read(reklama / "ads_meta.csv")},
        "creatives": read(reklama / "creatives_unique.csv"), "coverage": read(reklama / "coverage.csv"),
        "transcripts": {r["library_id"]: r for r in read(reklama / "transcripts_index.csv")},
        "plan": {r["creative_id"]: r["selected_because"] for r in read(razbor / "tagging_plan.csv")},
        "snapshots": read(HERE / "03-lendingi" / "snapshots_index.csv"), "socials": read(HERE / "01-master" / "socials.csv"),
        "offers": read(razbor / "offers_prices.csv"), "stopped": read(reklama / "stopped_since_0916.csv"),
    }
    facts: dict = {"usd_uzs": USD_UZS, "snapshot": SNAPSHOT.isoformat()}
    schools = []
    for s in read(HERE / "01-master" / "shortlist.csv"):
        block, thumbs, shots = school_block(s, tables, facts)
        schools.append(block)
        write_js(OUT / "data" / f"thumbs-{s['school_id']}.js", f"(window.THUMBS = window.THUMBS || {{}})[{json.dumps(s['school_id'])}]", thumbs)
        write_js(OUT / "data" / f"shots-{s['school_id']}.js", f"(window.SHOTS = window.SHOTS || {{}})[{json.dumps(s['school_id'])}]", shots)
    master = read(HERE / "01-master" / "master_list.csv")
    shares = read(razbor / "shares_by_group.csv")
    facts["master_schools"] = len(master)
    facts["money_main"] = sum(1 for m in master if m["status"] == "денежная (основной порог)")
    facts["money_fallback"] = sum(1 for m in master if m["status"] == "денежная (запасной порог)")
    facts["shares"] = share_facts(shares)
    facts["agreement"] = {r["field"]: float(r["share"]) for r in read(razbor / "tag_agreement.csv")}
    facts["agreement_pairs"] = max((int(r["pairs"]) for r in read(razbor / "tag_agreement.csv")), default=0)
    lift = [r for r in read(razbor / "lift_top10.csv") if int(r["schools"]) >= LIFT_MIN_SCHOOLS]
    facts["lift"] = {}
    for r in lift:
        facts["lift"].setdefault(r["field"], {})[r["value"]] = {k: float(r[k]) for k in ("lift", "top_count", "top_n", "rest_count", "rest_n", "schools")}
    facts["all"] = {k: sum(facts[s["id"]][k] or 0 for s in schools)
                    for k in ("ads_collected", "unique_creatives", "meta_counter", "tagged", "landings_analysed", "long_runners", "fresh")}
    google_ads = read(reklama / "ads_google.csv")
    snapshot_day = SNAPSHOT.isoformat()
    facts["google"] = {"ads_any_time": len(google_ads), "schools_with_ads": len({g["school_id"] for g in google_ads}),
                       "last_shown": max((g["last_shown"] for g in google_ads), default=""),
                       "active_now": sum(1 for g in google_ads if g["last_shown"] >= snapshot_day)}
    money = [facts[s["id"]]["money"] for s in schools]
    facts["all"].update(
        schools_with_price=sum(1 for m in money if m["pages_with_price"]),
        schools_with_installments=sum(1 for m in money if m["pages_with_installments"]),
        pages_next_call=sum(m["next_steps"].get("звонок менеджера", 0) for m in money),
        pages_next_known=sum(v for m in money for k, v in m["next_steps"].items() if k not in ("", "неизвестно")),
        pages_next_telegram=sum(m["next_steps"].get("Telegram-канал", 0) + m["next_steps"].get("Telegram-бот", 0) for m in money))
    template = OUT / "findings.template.json"
    creative_school = {c["id"]: s["id"] for s in schools for c in s["creatives"]}
    findings = render_findings(json.loads(template.read_text(encoding="utf-8")), facts, creative_school) if template.exists() else None
    google = OUT / "google_status.json"
    report = {
        "facts": facts, "schools": schools, "master": master, "shares": shares, "hooks": read(razbor / "hooks_library.csv"), "lift": lift, "agreement": read(razbor / "tag_agreement.csv"),
        "sources": read(HERE / "03-lendingi" / "sources_log.csv"), "findings": findings,
        "google_status": json.loads(google.read_text(encoding="utf-8")) if google.exists() else None,
        "google_ads": google_ads,
    }
    write_js(OUT / "data" / "report.js", "window.REPORT", report)
    if findings:
        url_file = OUT / "artifact_url.txt"
        write_summary_md(findings, url_file.read_text(encoding="utf-8").strip() if url_file.exists() else "")
    (OUT / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
    size = sum(p.stat().st_size for p in (OUT / "data").glob("*.js"))
    print(f"schools: {len(schools)}, creatives: {sum(len(s['creatives']) for s in schools)}, "
          f"landings: {sum(len(s['landings']) for s in schools)}, data: {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
