#!/usr/bin/env python3
"""Пилот Google Ads Transparency Center: есть ли у школ реклама в регионе UZ и какие поля приходят.

Только прямое соединение (без прокси), на блокировку — стоп.
Запуск:
    ~/.venvs/gads-transparency/bin/python google_pilot.py qadam.online proweb.uz englify.uz najottalim.uz
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ["GOOGLE_ADS_TRANSPARENCY_PROXY"] = "direct"
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path.insert(0, str(PROJECT / "tools" / "google-ads-transparency-mcp" / "src"))

from google_ads_transparency_mcp import AdsTransparencyBlocked, GoogleAdsTransparency  # noqa: E402
from google_ads_transparency_mcp.frames import download_image, extract_video_frames  # noqa: E402

OUT = HERE / "google"
MEDIA = Path.home() / "Data/online-shkola-uz/05-razbor-konkurentov/00-pilot/google"
UZ = 2860


def raw_creatives(client: GoogleAdsTransparency, advertiser_id: str, count: int = 40) -> dict:
    body = {"2": count, "3": {"12": {"1": "", "2": True}, "13": {"1": [advertiser_id]}, "8": [UZ]}, "7": {"1": 1}}
    return client._rpc("/anji/_/rpc/SearchService/SearchCreatives", body)


def main() -> None:
    domains = sys.argv[1:]
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report: dict = {"stamp": stamp, "domains": domains, "compare": [], "advertisers": {}}
    try:
        client = GoogleAdsTransparency(region="UZ", min_interval=2.0)
        report["compare"] = client.compare_advertisers(domains)
        for row in report["compare"]:
            if row.get("status") != "ok" or row.get("parent_entity"):
                continue
            adv = row["advertiser_id"]
            raw = raw_creatives(client, adv)
            (OUT / f"raw-{adv}-{stamp}.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")
            items = raw.get("1") or []
            details = [client.get_ad_detail(adv, it["2"]) for it in items[:6] if "2" in it]
            report["advertisers"][adv] = {
                "name": row.get("advertiser_name"), "domain": row["domain"], "uz_creatives_first_page": len(items),
                "next_page_token": bool(raw.get("2")), "raw_item_keys": sorted(items[0].keys()) if items else [],
                "raw_first_item": items[0] if items else None, "details": details,
            }
            image = next((d for d in details if d["format"] == "image" and d["content"].get("image_url")), None)
            video = next((d for d in details if d["content"].get("video_url", "").startswith("https://www.youtube.com")), None)
            if image:
                path = download_image(image["content"]["image_url"], MEDIA / image["creative_id"], name=image["creative_id"])
                report["advertisers"][adv]["image_file"] = path
            if video:
                sampled = extract_video_frames(video["content"]["video_url"], MEDIA / video["creative_id"], frames=4)
                report["advertisers"][adv]["video_file"] = sampled
    except AdsTransparencyBlocked as exc:
        report["blocked"] = str(exc)[:500]
    (OUT / f"pilot-{stamp}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({
        "compare": report["compare"], "blocked": report.get("blocked"),
        "advertisers": {k: {kk: v[kk] for kk in ("name", "domain", "uz_creatives_first_page", "next_page_token", "raw_item_keys", "raw_first_item")}
                        | {"formats": [d["format"] for d in v["details"]], "last_shown": [d["last_shown"] for d in v["details"]],
                           "image_file": v.get("image_file"), "video_frames": (v.get("video_file") or {}).get("frames")}
                        for k, v in report["advertisers"].items()},
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
