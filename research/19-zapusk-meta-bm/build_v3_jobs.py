"""Задания 18.10 по просьбе Васи: названия креативов в именах, кнопка «Зарегистрироваться» на 27 объявлениях.

create — новый креатив + объявление с SIGN_UP (имя объявления _su), медиа те же, что у заменяемого;
delete — заменённое объявление (черновик, не публиковалось) → DELETED;
rename — оставшиеся объявления и их креативы: имя «utm_content · название креатива · кнопка».
Данные — launch.json (собирает build_launch.py) и meta_ids.json. Запуск: python3 build_v3_jobs.py <папка>
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAUNCH = json.loads((HERE / "launch.json").read_text(encoding="utf-8"))
META = json.loads((HERE / "meta_ids.json").read_text(encoding="utf-8"))
OUT = Path(sys.argv[1])

DOF = {"creative_features_spec": {k: {"enroll_status": "OPT_OUT"} for k in [
    "image_touchups", "image_brightness_and_contrast", "image_uncrop", "image_templates", "image_animation",
    "text_optimizations", "inline_comment", "enhance_cta", "adapt_to_placement", "description_automation",
    "add_text_overlay", "video_auto_crop", "reveal_details_over_time", "show_summary",
    "text_translation", "multi_photo_to_video", "image_background_gen", "site_extensions",
    "creative_stickers", "profile_card"]}}
STORIES_REELS = {"publisher_platforms": ["facebook", "instagram"],
                 "facebook_positions": ["story", "facebook_reels"], "instagram_positions": ["story", "reels"]}

page_id = LAUNCH["account"]["page_id"]
create, delete, rename = [], [], []
for camp in LAUNCH["campaigns"]:
    risk = "RISK" in camp["labels"]
    for adset in camp["adsets"]:
        for ad in adset["ads"]:
            if ad["replaces"]:
                old = META["ads"].get(ad["replaces"]) or META.get("ads_v2_replaced", {}).get(ad["replaces"])
                assert old, ad["replaces"]
                assert ad["format"] != "carousel", ad["name"]
                media = {x["role"]: x["meta"] for x in ad["media"]}
                key = "image_hash" if ad["format"] == "image" else "video_id"
                cr = dict(name=ad["display_name"], page_id=page_id, link_url=ad["link_url"], headline=ad["title"],
                          call_to_action_type=ad["call_to_action"], message=ad["body_fallback"],
                          degrees_of_freedom_spec=json.dumps(DOF),
                          placement_customizations=[{key: media["feed_4x5"][key]},
                                                    dict({key: media["stories_reels_9x16"][key]}, **STORIES_REELS)])
                new_ad = dict(ad_name=ad["display_name"], ad_set_id=adset["meta_id"], conversion_domain=ad["conversion_domain"])
                if risk:
                    new_ad["adlabels"] = json.dumps([{"name": "RISK"}])
                create.append(dict(name=ad["name"], campaign=camp["name"], adset=adset["name"], creative=cr, ad=new_ad))
                delete.append(dict(name=ad["replaces"], ad_id=old["ad_id"], creative_id=old["creative_id"], replaced_by=ad["name"]))
            else:
                m = META["ads"][ad["name"]]
                rename.append(dict(name=ad["name"], ad_id=m["ad_id"], creative_id=m["creative_id"], new_name=ad["display_name"],
                                   live=m.get("state", "").startswith("опубликовано")))

OUT.mkdir(parents=True, exist_ok=True)
for label, data in (("create", create), ("delete", delete), ("rename", rename)):
    (OUT / f"{label}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
assert len(create) == len(delete) == 27 and len(rename) == 33, (len(create), len(delete), len(rename))
print(f"создать {len(create)}, удалить {len(delete)}, переименовать {len(rename)} (опубликованных {sum(r['live'] for r in rename)}) → {OUT}")
