"""Задания на 60 объявлений пересборки 17.10 (v2_plan.json): креатив + объявление на каждое.

Медиа, тексты, заголовок и кнопка берутся из launch.json (по коду креатива), структура — из v2_plan.json.
Имя объявления: {креатив}_{хук}_{аудитория}. Ссылка — сразу на лендинг из v2_plan.json, метки:
utm_source=meta, utm_medium=paid, utm_campaign=<кампания>, utm_term=<группа>, utm_content=<объявление>.
Запуск: python3 build_v2_jobs.py <папка для заданий>
"""
import json
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = json.loads((HERE / "v2_plan.json").read_text(encoding="utf-8"))
LAUNCH = json.loads((HERE / "launch.json").read_text(encoding="utf-8"))
OUT = Path(sys.argv[1])
CHUNKS = 4

DOF = {"creative_features_spec": {k: {"enroll_status": "OPT_OUT"} for k in [
    "image_touchups", "image_brightness_and_contrast", "image_uncrop", "image_templates", "image_animation",
    "text_optimizations", "inline_comment", "enhance_cta", "adapt_to_placement", "description_automation",
    "add_text_overlay", "video_auto_crop", "reveal_details_over_time", "show_summary",
    "text_translation", "multi_photo_to_video", "image_background_gen", "site_extensions",
    "creative_stickers", "profile_card"]}}
STORIES_REELS = {"publisher_platforms": ["facebook", "instagram"],
                 "facebook_positions": ["story", "facebook_reels"], "instagram_positions": ["story", "reels"]}

by_code = {ad["creative_code"]: ad for c in LAUNCH["campaigns"] for s in c["adsets"] for ad in s["ads"]}
page_id = LAUNCH["account"]["page_id"]
jobs = []
for camp, c in PLAN["campaigns"].items():
    risk = camp.endswith("risk_2610")
    for adset, a in c["adsets"].items():
        for code in PLAN["types"][a["type"]]:
            src = by_code[code]
            name = f"{code}_{src['hook']}_{a['aud']}"
            assert len(name) <= 20, name
            q = urllib.parse.urlencode(dict(utm_source="meta", utm_medium="paid", utm_campaign=camp,
                                            utm_term=adset, utm_content=name))
            cr = dict(name=name, page_id=page_id, link_url=f"{PLAN['landing']}?{q}", headline=src["title"],
                      call_to_action_type=src["call_to_action"], message=src["body_fallback"],
                      degrees_of_freedom_spec=json.dumps(DOF))
            media = {x["role"]: x["meta"] for x in src["media"]}
            if src["format"] == "carousel":
                cr["cards"] = [{"image_hash": x["meta"]["image_hash"], "headline": src["title"]} for x in src["media"]]
            else:
                key = "image_hash" if src["format"] == "image" else "video_id"
                cr["placement_customizations"] = [{key: media["feed_4x5"][key]},
                                                  dict({key: media["stories_reels_9x16"][key]}, **STORIES_REELS)]
            ad = dict(ad_name=name, ad_set_id=a["id"], conversion_domain="aibuyurtma.com")
            if risk:
                ad["adlabels"] = json.dumps([{"name": "RISK"}])
            jobs.append(dict(name=name, campaign=camp, adset=adset, format=src["format"], creative=cr, ad=ad))

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=1), encoding="utf-8")
for i in range(CHUNKS):
    part = jobs[i::CHUNKS]
    (OUT / f"chunk_{i + 1}.json").write_text(json.dumps(part, ensure_ascii=False, indent=1), encoding="utf-8")
names = [j["name"] for j in jobs]
assert len(names) == len(set(names)) == 60, (len(names), len(set(names)))
print(f"{len(jobs)} заданий → {OUT}; чанков {CHUNKS} по {len(jobs[0::CHUNKS])}")
