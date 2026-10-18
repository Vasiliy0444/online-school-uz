"""Задания 18.10 вечером, план Б: объявления с картинками и видео без Instagram.

Креатив с разным медиа для лент и для Stories/Reels Meta не публикует без аккаунта Instagram (ошибка 1772103),
а поставить «страницу Facebook вместо Instagram» инструмент MCP не умеет. Вася сказал делать без него, поэтому
каждое такое объявление создаётся заново с одним медиа 4:5 на все места — как у каруселей, которые опубликовались.
Имя, метка, текст, заголовок, кнопка и ссылка — прежние; прежнее объявление (черновик, не публиковалось) → DELETED.

create — креатив (картинка 4:5 или ролик 4:5 с обложкой) + объявление в той же группе. Уже пересобранные
(прежняя версия лежит в meta_ids.json → ads_v3_replaced, новая — в ads) в задания не попадают;
delete — прежнее объявление с разными медиа: ID только из ads_v3_replaced или, пока объявление не пересобрано, из ads.
Помеченные удалёнными ("deleted": true в ads_v3_replaced) в delete не попадают.
Обложки роликов — covers/<код>.jpg (кадр 4:5 на 1-й секунде). Их загружают в Meta по ссылке raw и пишут хэш
в meta_ids.json → covers. В креатив идёт хэш: с ссылкой инструмент кладёт в video_data и ссылку, и хэш, и Meta
отказывает (ObjectStorySpecRedundant, 1443051).
Данные — launch.json и meta_ids.json. Запуск: python3 build_v4_jobs.py <папка>
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LAUNCH = json.loads((HERE / "launch.json").read_text(encoding="utf-8"))
META = json.loads((HERE / "meta_ids.json").read_text(encoding="utf-8"))
COVERS = HERE / "covers"
COVER_AT_S = 1

DOF = {"creative_features_spec": {k: {"enroll_status": "OPT_OUT"} for k in [
    "image_touchups", "image_brightness_and_contrast", "image_uncrop", "image_templates", "image_animation",
    "text_optimizations", "inline_comment", "enhance_cta", "adapt_to_placement", "description_automation",
    "add_text_overlay", "video_auto_crop", "reveal_details_over_time", "show_summary",
    "text_translation", "multi_photo_to_video", "image_background_gen", "site_extensions",
    "creative_stickers", "profile_card"]}}


def cover(code: str, video_path: str) -> Path:
    """Обложка ролика: кадр 4:5 на 1-й секунде, как превью в реестре UTM."""
    out = COVERS / f"{code}.jpg"
    if not out.exists():
        COVERS.mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(COVER_AT_S), "-i", str(ROOT / video_path),
                        "-frames:v", "1", "-q:v", "2", str(out)], check=True)
    return out


def main() -> None:
    out_dir = Path(sys.argv[1])
    page_id = LAUNCH["account"]["page_id"]
    create, delete = [], []
    for camp in LAUNCH["campaigns"]:
        risk = "RISK" in camp["labels"]
        for adset in camp["adsets"]:
            for ad in adset["ads"]:
                if ad["format"] == "carousel":
                    continue
                replaced = META.get("ads_v3_replaced", {}).get(ad["name"])
                old = replaced or META["ads"][ad["name"]]
                if not old.get("deleted"):
                    delete.append(dict(name=ad["name"], ad_id=old["ad_id"], creative_id=old["creative_id"]))
                if replaced:
                    continue
                feed = next(m for m in ad["media"] if m["role"] == "feed_4x5")
                cr = dict(name=ad["display_name"], page_id=page_id, link_url=ad["link_url"], headline=ad["title"],
                          call_to_action_type=ad["call_to_action"], message=ad["body_fallback"],
                          degrees_of_freedom_spec=json.dumps(DOF))
                if ad["format"] == "image":
                    cr["image_hash"] = feed["meta"]["image_hash"]
                else:
                    cover(ad["creative_code"], feed["path"])
                    cr["video_id"] = feed["meta"]["video_id"]
                    cr["image_hash"] = META["covers"][ad["creative_code"]]["image_hash"]
                new_ad = dict(ad_name=ad["display_name"], ad_set_id=adset["meta_id"], conversion_domain=ad["conversion_domain"])
                if risk:
                    new_ad["adlabels"] = json.dumps([{"name": "RISK"}])
                create.append(dict(name=ad["name"], campaign=camp["name"], adset=adset["name"], format=ad["format"],
                                   creative=cr, ad=new_ad))
    out_dir.mkdir(parents=True, exist_ok=True)
    for label, data in (("create", create), ("delete", delete)):
        (out_dir / f"{label}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    c1 = sum(1 for j in create if j["campaign"] == LAUNCH["campaigns"][0]["name"])
    done = len(META.get("ads_v3_replaced", {}))
    assert len(create) + done == 54, (len(create), done)
    print(f"пересобрано {done} из 54; создать {len(create)} (C1 {c1}, RISK {len(create) - c1}; "
          f"видео {sum(j['format'] == 'video' for j in create)}), пометить удалёнными {len(delete)} → {out_dir}")


if __name__ == "__main__":
    main()
