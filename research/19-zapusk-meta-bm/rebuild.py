#!/usr/bin/env python3
"""Пересборка запуска Meta 1в1 на новой странице или в новом кабинете: задания для MCP, состояние, запись в репозиторий.

Зачем: 18.10 вечером Meta перестала давать доступ к странице «AI-mutaxassis kasb» (01-ПЛАН-ЗАПУСКА.md, 11.8).
Вася 18.10: «если страницу не разбанят чтоб мы сделали 1в1 без моих подтвреждений на новой странице».
Порядок работ и границы разрешения — 04-ПЕРЕСБОРКА-1В1.md. Воркфлоу — .claude/workflows/meta-rebuild-1v1.js.

Источник правды — launch.json: структура, тексты, кнопки, ссылки с метками, медиа. ID того, что уже есть в Meta, —
meta_ids.json. Обложки роликов — covers/. Объявления с картинками и роликами — одно медиа 4:5 на все места (план Б),
карусели — карточки 1:1.

Режимы:
  page    — новая страница, тот же кабинет. Кампании, группы, аудитории и медиа прежние; заново 60 креативов
            и объявлений. Старые объявления: черновики помечаем удалёнными, опубликованные ставим на паузу.
  account — новый кабинет. Заново медиа, 6 аудиторий, 2 кампании, 14 групп, 60 креативов и объявлений.

Команды (папка — рабочая, вне репозитория, например /home/user/meta_rebuild):
  init <папка> --page ID [--page-name ИМЯ] [--mode page|account] [--account ID] [--account-name ИМЯ] [--pixel ID]
  keys <папка>                        ключи заданий по этапам и ключ пробного объявления (JSON)
  jobs <папка> <этап> [--pending] [--shard I/N] [--keys-only]
                                      задания этапа (JSON); --shard — доля исполнителя I из N, --keys-only — только ключи
  job <папка> <этап> <ключ>           одно задание: что передать в MCP и что уже сделано
  save <папка> <этап> <ключ> <поле> <значение>
  is-access-error <текст>             код 0 — ошибка доступа к странице или ограничение Meta: всё остановить
  stop <папка> <причина>              стоп-флаг для всех исполнителей
  status <папка> [--check-stop] [--json]
  verify <папка> --live ФАЙЛ [--campaign ФАЙЛ] [--draft ФАЙЛ]
  apply <папка> --date ДД.ММ.ГГГГ [--reason ТЕКСТ]    ID → ids.json и meta_ids.json, строки в план и журнал
Этапы: media, audiences, campaigns, adsets (только account), creatives_ads, retire (только page), publish.
"""
import argparse
import copy
import fcntl
import json
import re
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
LAUNCH_FILE = HERE / "launch.json"
META_FILE = HERE / "meta_ids.json"
IDS_FILE = HERE / "ids.json"
PLAN_JSON = HERE / "v2_plan.json"
PLAN_MD = HERE / "01-ПЛАН-ЗАПУСКА.md"
JOURNAL_MD = HERE / "03-ЖУРНАЛ-ЗАЛИВКИ.md"

DOF = {"creative_features_spec": {k: {"enroll_status": "OPT_OUT"} for k in [
    "image_touchups", "image_brightness_and_contrast", "image_uncrop", "image_templates", "image_animation",
    "text_optimizations", "inline_comment", "enhance_cta", "adapt_to_placement", "description_automation",
    "add_text_overlay", "video_auto_crop", "reveal_details_over_time", "show_summary",
    "text_translation", "multi_photo_to_video", "image_background_gen", "site_extensions",
    "creative_stickers", "profile_card"]}}
PHASES = {"page": ["creatives_ads", "retire", "publish"],
          "account": ["media", "audiences", "campaigns", "adsets", "creatives_ads", "publish"]}
# Ответы Meta 18.10, после которых нельзя продолжать: «Cannot access page …» (код 100) и отказ «IAF (AccountRestrictionFilter)».
ACCESS_RE = re.compile(r"cannot access page|page admin|advertiser-on-behalf-of|accountrestrictionfilter|\bIAF\b|"
                       r"restrict|ограничен|not allowed to (?:advertise|create ads)|error_category\W+PERMISSION", re.I)
BAD_LIVE = {"DISAPPROVED", "WITH_ISSUES", "DELETED", "ARCHIVED"}
MODE_RU = {"page": "новая страница", "account": "новый кабинет"}
KEY_FIELDS = ("mode", "page_id", "account_id", "pixel_id")


def die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip()


@contextmanager
def state(run_dir: str, write: bool = True):
    run = Path(run_dir)
    if not (run / "state.json").exists():
        die(f"нет {run}/state.json — сначала rebuild.py init")
    with open(run / ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        st = load(run / "state.json")
        yield st
        if write:
            tmp = run / "state.tmp"
            tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(run / "state.json")


def read_state(run_dir: str) -> dict:
    with state(run_dir, write=False) as st:
        return st


def launch_ads(launch: dict):
    for camp in launch["campaigns"]:
        for adset in camp["adsets"]:
            for ad in adset["ads"]:
                yield camp, adset, ad


def is_risk(camp: dict) -> bool:
    return "RISK" in camp["labels"]


def canary_key(launch: dict) -> str:
    """Пробное объявление: первая картинка C1 — как I1-1_math_br_su в плане Б."""
    return next(ad["name"] for camp, _, ad in launch_ads(launch) if not is_risk(camp) and ad["format"] == "image")


def feed_media(ad: dict) -> dict:
    return next(m for m in ad["media"] if m["role"] == "feed_4x5")


# --- задания по этапам ------------------------------------------------------------------------------------------

def needed_media(launch: dict, meta: dict) -> dict:
    """Что загрузить в новый кабинет: 4:5 картинок и роликов, обложки роликов, карточки каруселей. Ролики первыми."""
    items = {}
    for _, _, ad in launch_ads(launch):
        if ad["format"] == "carousel":
            for m in ad["media"]:
                items[m["path"]] = dict(kind="IMAGE", url=m["url"], name=meta["media"].get(m["path"], {}).get("name") or Path(m["path"]).stem)
            continue
        feed = feed_media(ad)
        kind = "VIDEO" if ad["format"] == "video" else "IMAGE"
        items[feed["path"]] = dict(kind=kind, url=feed["url"], name=meta["media"].get(feed["path"], {}).get("name") or Path(feed["path"]).stem)
        if ad["format"] == "video":
            cov = meta["covers"][ad["creative_code"]]
            items[cov["path"]] = dict(kind="IMAGE", url=cov["uploaded_from"], name=f"{ad['creative_code']} обложка 4x5", cover=ad["creative_code"])
    return dict(sorted(items.items(), key=lambda kv: kv[1]["kind"] != "VIDEO"))


def jobs_media(st: dict, launch: dict, meta: dict) -> list[dict]:
    acc = st["target"]["account_id"]
    out = []
    for path, m in needed_media(launch, meta).items():
        out.append(dict(key=path, tool="ads_creative_upload_media",
                        args=dict(ad_account_id=acc, upload_source="URL", media_type=m["kind"], media_url=m["url"], name=m["name"]),
                        save=["video_id", "status"] if m["kind"] == "VIDEO" else ["image_hash"],
                        note="ролик готов к креативу только при status ready (ads_get_ad_videos)" if m["kind"] == "VIDEO" else ""))
    return out


def jobs_audiences(st: dict, launch: dict) -> list[dict]:
    t = st["target"]
    out = []
    for aud in launch["custom_audiences"]:
        what = f"событие {aud['event']}" if aud["event"] else "все посетители лендинга"
        out.append(dict(key=aud["name"], tool="ads_create_custom_audience", save=["id"],
                        args=dict(ad_account_id=t["account_id"], name=aud["name"], subtype="WEBSITE",
                                  description=f"{what}, {aud['days']} дней. {aud['why']}",
                                  rule=aud["rule"].replace(t["old_pixel_id"], t["pixel_id"]))))
    return out


def jobs_campaigns(st: dict, launch: dict) -> list[dict]:
    acc = st["target"]["account_id"]
    out = []
    for camp in launch["campaigns"]:
        args = dict(ad_account_id=acc, campaign_name=camp["name"], objective=camp["objective"], buying_type=camp["buying_type"],
                    special_ad_categories=json.dumps(camp["special_ad_categories"]), campaign_spend_cap=camp["spend_cap_minor"],
                    hide_ui=True)
        if camp["labels"]:
            args["adlabels"] = json.dumps([{"name": label} for label in camp["labels"]])
        out.append(dict(key=camp["name"], tool="ads_create_campaign", args=args, save=["id"],
                        note="бюджет на группу (ABO): бюджет кампании не задавать; кампания создаётся на паузе"))
    return out


def jobs_adsets(st: dict, launch: dict) -> list[dict]:
    t = st["target"]
    ph = st["phases"]
    old_aud = {aud["meta_id"]: aud["name"] for aud in launch["custom_audiences"]}
    out = []
    for camp in launch["campaigns"]:
        camp_id = ph["campaigns"].get(camp["name"], {}).get("id")
        for adset in camp["adsets"]:
            missing = [] if camp_id else [f"кампания {camp['name']}"]
            tgt = copy.deepcopy(adset["targeting"])
            excluded = []
            for x in tgt.get("excluded_custom_audiences", []):
                name = old_aud.get(x["id"], x["id"])
                new_id = ph["audiences"].get(name, {}).get("id")
                if not new_id:
                    missing.append(f"аудитория {name}")
                excluded.append({"id": new_id or f"<{name}>"})
            if excluded:
                tgt["excluded_custom_audiences"] = excluded
            promoted = dict(adset["promoted_object"], pixel_id=t["pixel_id"])
            args = dict(ad_account_id=t["account_id"], campaign_id=camp_id or f"<{camp['name']}>", ad_set_name=adset["name"],
                        billing_event=adset["billing_event"], optimization_goal=adset["optimization_goal"],
                        destination_type=adset["destination_type"], promoted_object=json.dumps(promoted, separators=(",", ":")),
                        daily_budget=adset["daily_budget_minor"], bid_strategy=adset["bid_strategy"],
                        attribution_spec=json.dumps(adset["attribution_spec"], separators=(",", ":")),
                        targeting=json.dumps(tgt, ensure_ascii=False, separators=(",", ":")), hide_ui=True)
            if is_risk(camp):
                args["adlabels"] = json.dumps([{"name": "RISK"}])
            job = dict(key=f"{camp['name']}/{adset['name']}", tool="ads_create_ad_set", args=args, save=["id"],
                       ready=not missing, missing=missing)
            if adset["paused_until_interests"]:
                job["after"] = dict(tool="ads_update_entity", save=["paused"],
                                    args=dict(ad_account_id=t["account_id"], entity_id="<id группы>", entity_type="ad_set",
                                              fields=json.dumps({"status": "PAUSED"})),
                                    note="группа по интересам: на паузе, пока Вася не добавит интересы (11.7)")
            out.append(job)
    return out


def media_ref(st: dict, meta: dict, path: str, kind: str) -> str | None:
    src = meta["media"].get(path, {}) if st["target"]["mode"] == "page" else st["phases"]["media"].get(path, {})
    return src.get("video_id" if kind == "video" else "image_hash")


def cover_ref(st: dict, meta: dict, code: str) -> str | None:
    cov = meta["covers"].get(code, {})
    if st["target"]["mode"] == "page":
        return cov.get("image_hash")
    return st["phases"]["media"].get(cov.get("path", ""), {}).get("image_hash")


def jobs_creatives_ads(st: dict, launch: dict, meta: dict) -> list[dict]:
    t = st["target"]
    ph = st["phases"]
    out = []
    for camp, adset, ad in launch_ads(launch):
        missing = []

        def need(value, what):
            if not value:
                missing.append(what)
            return value or f"<{what}>"

        cr = dict(ad_account_id=t["account_id"], name=ad["display_name"], page_id=t["page_id"], link_url=ad["link_url"],
                  headline=ad["title"], call_to_action_type=ad["call_to_action"], message=ad["body_fallback"],
                  degrees_of_freedom_spec=json.dumps(DOF))
        if ad["format"] == "carousel":
            cr["cards"] = [dict(image_hash=need(media_ref(st, meta, m["path"], "image"), m["role"]), headline=ad["title"])
                           for m in ad["media"]]
        elif ad["format"] == "image":
            cr["image_hash"] = need(media_ref(st, meta, feed_media(ad)["path"], "image"), "картинка 4:5")
        else:
            cr["video_id"] = need(media_ref(st, meta, feed_media(ad)["path"], "video"), "ролик 4:5")
            cr["image_hash"] = need(cover_ref(st, meta, ad["creative_code"]), "обложка ролика")
        if t["mode"] == "page":
            adset_id = adset["meta_id"]
        else:
            adset_id = ph["adsets"].get(f"{camp['name']}/{adset['name']}", {}).get("id")
        done = ph["creatives_ads"].get(ad["name"], {})
        ad_args = dict(ad_account_id=t["account_id"], ad_set_id=need(adset_id, "группа"), ad_name=ad["display_name"],
                       creative=json.dumps({"creative_id": done["creative_id"]}) if done.get("creative_id") else "<{\"creative_id\": ID из шага 1}>",
                       conversion_domain=ad["conversion_domain"], hide_ui=True)
        if is_risk(camp):
            ad_args["adlabels"] = json.dumps([{"name": "RISK"}])
        out.append(dict(key=ad["name"], campaign=camp["name"], adset=adset["name"], risk=is_risk(camp), format=ad["format"],
                        steps=[dict(tool="ads_create_creative", args=cr, save=["creative_id"]),
                               dict(tool="ads_create_ad", args=ad_args, save=["ad_id"])],
                        ready=not missing, missing=missing))
    return out


def jobs_retire(st: dict) -> list[dict]:
    """Старые объявления от прежней страницы. Только те, у которых уже есть замена от новой страницы,
    и прежние черновики плана Б (ads_v3_replaced) — их заменили ещё 18.10. Без замены объявление не трогаем."""
    acc = st["target"]["account_id"]
    replaced = {k for k, v in st["phases"]["creatives_ads"].items() if v.get("ad_id")}
    return [dict(key=o["ad_id"], tool="ads_update_entity", name=o["name"], campaign=o["campaign"],
                 published_hint=o["state"].startswith("опубликовано"),
                 args=dict(ad_account_id=acc, entity_id=o["ad_id"], entity_type="ad"),
                 fields_if_live=json.dumps({"status": "PAUSED"}), fields_if_draft=json.dumps({"status": "DELETED"}),
                 save=["action", "done"]) for o in st["old_ads"] if o["where"] == "ads_v3_replaced" or o["name"] in replaced]


def jobs_publish(st: dict, launch: dict) -> list[dict]:
    t = st["target"]
    ph = st["phases"]
    c1 = next(c for c in launch["campaigns"] if not is_risk(c))
    # объявления с ошибкой (при создании или при прошлой попытке публикации) остаются в черновике
    ads = [ph["creatives_ads"][ad["name"]] for adset in c1["adsets"] for ad in adset["ads"]
           if ph["creatives_ads"].get(ad["name"], {}).get("ad_id") and not ph["creatives_ads"][ad["name"]].get("errors")]
    ad_ids = [r["ad_id"] for r in ads if not r.get("published")]
    if t["mode"] == "page":
        if not ad_ids:
            return []
        args = dict(ad_account_id=t["account_id"], entity_id=ad_ids[0], entity_type="ad", object_ids=ad_ids,
                    publish_as_active=False)
    else:
        camp_id = ph["campaigns"].get(c1["name"], {}).get("id")
        adset_ids = [ph["adsets"].get(f"{c1['name']}/{s['name']}", {}).get("id") for s in c1["adsets"]]
        if not camp_id or not all(adset_ids):
            return []
        args = dict(ad_account_id=t["account_id"], entity_id=camp_id, entity_type="campaign",
                    object_ids=[camp_id, *adset_ids, *ad_ids], publish_as_active=False)
    return [dict(key=c1["name"], tool="ads_activate_entity", args=args, save=["done", "result"],
                 note="только C1 и только publish_as_active=false: кампания остаётся на паузе. RISK не публиковать")]


def build_jobs(st: dict, phase: str) -> list[dict]:
    if phase not in PHASES[st["target"]["mode"]]:
        die(f"этапа {phase} нет в режиме {st['target']['mode']}: {', '.join(PHASES[st['target']['mode']])}")
    launch, meta = load(LAUNCH_FILE), load(META_FILE)
    jobs = {"media": lambda: jobs_media(st, launch, meta), "audiences": lambda: jobs_audiences(st, launch),
            "campaigns": lambda: jobs_campaigns(st, launch), "adsets": lambda: jobs_adsets(st, launch),
            "creatives_ads": lambda: jobs_creatives_ads(st, launch, meta), "retire": lambda: jobs_retire(st),
            "publish": lambda: jobs_publish(st, launch)}[phase]()
    done = st["phases"].get(phase, {})
    for j in jobs:
        j["done"] = done.get(j["key"], {})
        j["complete"] = is_complete(phase, j["done"], j)
    return jobs


def is_complete(phase: str, done: dict, job: dict) -> bool:
    if phase == "creatives_ads":
        return bool(done.get("ad_id"))
    if phase == "media":
        return bool(done.get("image_hash") or (done.get("video_id") and done.get("status") == "ready"))
    if phase == "adsets":
        return bool(done.get("id")) and ("after" not in job or bool(done.get("paused")))
    if phase in ("retire", "publish"):
        return bool(done.get("done"))
    return bool(done.get("id"))


# --- команды ----------------------------------------------------------------------------------------------------

def cmd_init(a) -> None:
    run = Path(a.run_dir)
    launch, meta, ids = load(LAUNCH_FILE), load(META_FILE), load(IDS_FILE)
    if not re.fullmatch(r"\d{5,}", a.page):
        die("--page: ID страницы — только цифры")
    if a.page == ids["page_id"]:
        die("это та же страница, что в ids.json: если её вернули — продолжать план Б (build_v4_jobs.py, 01-ПЛАН-ЗАПУСКА.md, 11.8)")
    if a.mode == "account":
        if not (a.account and a.pixel):
            die("режим account: нужны --account и --pixel (пиксель должен быть доступен новому кабинету)")
        if a.account == ids["ad_account_id"]:
            die("--account тот же, что в ids.json: для того же кабинета — режим page")
    target = dict(mode=a.mode, page_id=a.page, page_name=a.page_name or "",
                  account_id=a.account or ids["ad_account_id"],
                  account_name=a.account_name or (ids["ad_account_name"] if a.mode == "page" else ""),
                  pixel_id=a.pixel or ids["pixel_id"], old_page_id=ids["page_id"], old_account_id=ids["ad_account_id"],
                  old_pixel_id=ids["pixel_id"], repo_commit=git_head(), launch_version=launch["version"])
    if (run / "state.json").exists():
        old = load(run / "state.json")["target"]
        if any(old[k] != target[k] for k in KEY_FIELDS) and not a.force:
            die(f"в {run} уже другая пересборка ({', '.join(f'{k}={old[k]}' for k in KEY_FIELDS)}). Другая папка или --force")
        print(f"продолжаю пересборку в {run}")
        return cmd_status(argparse.Namespace(run_dir=a.run_dir, check_stop=False, json=False))
    old_ads = []
    if a.mode == "page":
        old_ads = [dict(ad_id=v["ad_id"], name=k, campaign=v["campaign"], adset=v["adset"], state=v.get("state", ""), where="ads")
                   for k, v in meta["ads"].items()]
        old_ads += [dict(ad_id=v["ad_id"], name=k, campaign=v["campaign"], adset=v["adset"], state=v.get("state", ""),
                         where="ads_v3_replaced") for k, v in meta.get("ads_v3_replaced", {}).items() if not v.get("deleted")]
    run.mkdir(parents=True, exist_ok=True)
    st = dict(target=target, stop=None, old_ads=old_ads, phases={p: {} for p in PHASES[a.mode]}, verify=None)
    (run / "state.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"пересборка {a.mode}: страница {a.page}, кабинет {target['account_id']}, пиксель {target['pixel_id']} → {run}")
    cmd_status(argparse.Namespace(run_dir=a.run_dir, check_stop=False, json=False))


def cmd_keys(a) -> None:
    st = read_state(a.run_dir)
    out = {phase: [j["key"] for j in build_jobs(st, phase)] for phase in PHASES[st["target"]["mode"]]}
    out["canary"] = canary_key(load(LAUNCH_FILE))
    out["mode"] = st["target"]["mode"]
    out["target"] = st["target"]
    print(json.dumps(out, ensure_ascii=False))


def cmd_jobs(a) -> None:
    jobs = build_jobs(read_state(a.run_dir), a.phase)
    if a.shard:
        i, n = (int(x) for x in a.shard.split("/"))
        jobs = jobs[i::n]
    if a.pending:
        jobs = [j for j in jobs if not j["complete"]]
    if a.keys_only:
        print("\n".join(j["key"] for j in jobs))
        return
    print(json.dumps(jobs, ensure_ascii=False, indent=1))


def cmd_job(a) -> None:
    job = next((j for j in build_jobs(read_state(a.run_dir), a.phase) if j["key"] == a.key), None)
    if not job:
        die(f"нет задания {a.key} на этапе {a.phase}")
    print(json.dumps(job, ensure_ascii=False, indent=1))


def cmd_save(a) -> None:
    with state(a.run_dir) as st:
        if a.phase not in st["phases"]:
            die(f"этапа {a.phase} нет в режиме {st['target']['mode']}")
        rec = st["phases"][a.phase].setdefault(a.key, {})
        if a.field in ("creative_id", "ad_id", "id", "image_hash", "video_id") and rec.get(a.field) not in (None, a.value) and not a.force:
            die(f"{a.phase}/{a.key}: {a.field} уже {rec[a.field]} — второй объект не создавать, сначала разобраться (--force перезапишет)")
        rec[a.field] = a.value
    print(a.phase, a.key, a.field, a.value)


def cmd_is_access_error(a) -> None:
    raise SystemExit(0 if ACCESS_RE.search(" ".join(a.text)) else 1)


def cmd_stop(a) -> None:
    with state(a.run_dir) as st:
        st["stop"] = dict(reason=" ".join(a.reason)[:2000])
    print("стоп-флаг поставлен:", " ".join(a.reason)[:300])


def summary(st: dict) -> dict:
    out = dict(mode=st["target"]["mode"], page_id=st["target"]["page_id"], stop=st["stop"], phases={})
    for phase in PHASES[st["target"]["mode"]]:
        jobs = build_jobs(st, phase)
        errors = {j["key"]: j["done"]["errors"] for j in jobs if j["done"].get("errors") and not j["complete"]}
        out["phases"][phase] = dict(total=len(jobs), complete=sum(j["complete"] for j in jobs), errors=errors)
    out["verify"] = st.get("verify")
    return out


def cmd_status(a) -> None:
    st = read_state(a.run_dir)
    if a.check_stop:
        if st["stop"]:
            print("СТОП:", st["stop"]["reason"][:300])
            raise SystemExit(3)
        print("стоп-флага нет")
        return
    s = summary(st)
    if a.json:
        print(json.dumps(s, ensure_ascii=False))
        return
    print(f"режим {s['mode']}, страница {s['page_id']}" + (f" — СТОП: {s['stop']['reason'][:200]}" if s["stop"] else ""))
    for phase, p in s["phases"].items():
        print(f"  {phase:14} {p['complete']}/{p['total']}" + (f", ошибок {len(p['errors'])}" if p["errors"] else ""))
    if s["verify"]:
        print("  проверка:", s["verify"]["summary"])


def entities(path: str) -> list[dict]:
    """Чтение ads_get_ad_entities (live), сохранённое в файл: {"ad_entities": "<json>"} или список."""
    o = load(Path(path))
    if isinstance(o, dict):
        o = o.get("ad_entities", o.get("data", o))
    if isinstance(o, str):
        o = json.loads(o)
    if isinstance(o, dict):
        o = o.get("data", [o])
    return o


def drafts(path: str) -> list[dict]:
    o = load(Path(path))
    d = o.get("ad_drafts", o) if isinstance(o, dict) else o
    return json.loads(d) if isinstance(d, str) else d


def draft_value(obj: dict, key: str):
    v = obj.get("values", {}).get(key)
    return v.get("new") if isinstance(v, dict) and "new" in v else v


def cmd_verify(a) -> None:
    st = read_state(a.run_dir)
    launch = load(LAUNCH_FILE)
    ph = st["phases"]
    c1 = {ad["name"] for camp, _, ad in launch_ads(launch) if not is_risk(camp)}
    new = {k: v for k, v in ph["creatives_ads"].items() if v.get("ad_id")}
    problems, lines = [], []
    live = {str(e.get("id")): e for e in entities(a.live)}
    c1_new = {k: v["ad_id"] for k, v in new.items() if k in c1}
    by_status: dict[str, int] = {}
    for name, ad_id in c1_new.items():
        e = live.get(ad_id)
        if not e:
            problems.append(f"{name} ({ad_id}): нет среди опубликованных")
            continue
        eff = e.get("effective_status", "?")
        by_status[eff] = by_status.get(eff, 0) + 1
        if eff in BAD_LIVE:
            problems.append(f"{name} ({ad_id}): {eff}")
    lines.append(f"C1: опубликовано {sum(by_status.values())} из {len(c1_new)} созданных ({len(c1)} по плану); "
                 + ", ".join(f"{k} {v}" for k, v in sorted(by_status.items())))
    if a.campaign:
        camps = entities(a.campaign)
        c1_name = next(c["name"] for c in launch["campaigns"] if not is_risk(c))
        camp = next((c for c in camps if c.get("name") == c1_name), None)
        if not camp:
            problems.append(f"кампания {c1_name}: нет в чтении")
        elif camp.get("status") != "PAUSED":
            problems.append(f"кампания {c1_name}: status {camp.get('status')}, должна быть PAUSED")
        else:
            lines.append(f"кампания {c1_name}: PAUSED, effective_status {camp.get('effective_status')}")
    if a.draft:
        objs = {o["ad_object_id"]: o for o in drafts(a.draft) if o.get("ad_object_type") == "ad"}
        risk_new = {k: v["ad_id"] for k, v in new.items() if k not in c1}
        ok = 0
        for name, ad_id in risk_new.items():
            o = objs.get(ad_id)
            errs = o.get("active_errors") if o else None
            if not o:
                problems.append(f"{name} ({ad_id}): нет в черновике RISK")
            elif draft_value(o, "status") == "DELETED" or (errs and errs not in ("[]", [])):
                problems.append(f"{name} ({ad_id}): в черновике {draft_value(o, 'status')}, ошибки {str(errs)[:200]}")
            else:
                ok += 1
        lines.append(f"RISK: в черновике без ошибок {ok} из {len(risk_new)}")
    result = dict(ok=not problems, summary="; ".join(lines), problems=problems)
    with state(a.run_dir) as s:
        s["verify"] = result
    print("\n".join(lines))
    if problems:
        print("ПРОБЛЕМЫ:\n- " + "\n- ".join(problems))
        raise SystemExit(1)
    print("проверка пройдена")


def remap_ids(path: Path, mapping: dict) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in mapping.items():
        if old and new:
            text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    path.write_text(text, encoding="utf-8")


def cmd_apply(a) -> None:
    st = read_state(a.run_dir)
    if st.get("applied") and not a.force:
        die(f"уже записано в репозиторий {st['applied']} — повтор задвоит строки (--force, если точно нужно)")
    t = st["target"]
    ph = st["phases"]
    launch, meta, ids = load(LAUNCH_FILE), load(META_FILE), load(IDS_FILE)
    date, reason = a.date, a.reason
    where = {ad["name"]: (camp, adset) for camp, adset, ad in launch_ads(launch)}
    created = {k: v for k, v in ph["creatives_ads"].items() if v.get("ad_id") and k in where}
    published = bool(ph["publish"] and next(iter(ph["publish"].values())).get("done"))
    page_label = f"страница {t['page_id']}" + (f" «{t['page_name']}»" if t["page_name"] else "")

    def new_state(name: str, rec: dict) -> str:
        camp, _ = where[name]
        if is_risk(camp):
            return f"черновик, RISK до 4-го дня; пересборка 1в1 {date}, {page_label}"
        if rec.get("published") or published:
            return f"опубликовано выключенным {date}; пересборка 1в1, {page_label}"
        return f"черновик, не опубликовано; пересборка 1в1 {date}, {page_label}"

    def new_entry(name: str, rec: dict) -> dict:
        camp, adset = where[name]
        return dict(creative_id=rec["creative_id"], ad_id=rec["ad_id"], campaign=camp["name"], adset=adset["name"],
                    state=new_state(name, rec))

    retired = ph.get("retire", {})
    counts = dict(deleted=sum(1 for r in retired.values() if r.get("done") and r.get("action") == "DELETED"),
                  paused=sum(1 for r in retired.values() if r.get("done") and r.get("action") == "PAUSED"))

    def retire_note(entry: dict) -> dict:
        r = retired.get(entry["ad_id"], {})
        if not r.get("done"):
            return entry
        note = {"DELETED": f"помечено удалённым {date} (пересборка 1в1)", "PAUSED": f"на паузе с {date} (пересборка 1в1)"}[r["action"]]
        return dict(entry, state=f"{entry.get('state', '')}; {note}", deleted=r["action"] == "DELETED")

    if t["mode"] == "page":
        prev = meta.setdefault(f"previous_page_{t['old_page_id']}", dict(
            note=f"Объявления от страницы {t['old_page_id']} до пересборки 1в1 {date} (04-ПЕРЕСБОРКА-1В1.md). {reason}",
            ads={}, ads_v3_replaced={}))
        for name, v in meta.pop("ads_v3_replaced", {}).items():
            prev["ads_v3_replaced"][name] = retire_note(v)
        for name, rec in created.items():
            if name in meta["ads"]:
                prev["ads"][name] = retire_note(meta["ads"][name])
            meta["ads"][name] = new_entry(name, rec)
        ids.setdefault("old_pages", []).append(dict(page_id=t["old_page_id"], until=date, why=reason))
    else:
        prev_key = f"previous_account_{t['old_account_id']}"
        meta[prev_key] = {k: meta[k] for k in ("campaigns", "adsets", "audiences", "media", "covers", "ads", "ads_v3_replaced") if k in meta}
        mapping = {}
        new_aud = {k: v["id"] for k, v in ph["audiences"].items() if v.get("id")}
        mapping.update({meta["audiences"].get(k): v for k, v in new_aud.items()})
        new_camps = {k: v["id"] for k, v in ph["campaigns"].items() if v.get("id")}
        new_adsets = {k: v["id"] for k, v in ph["adsets"].items() if v.get("id")}
        mapping.update({meta["adsets"].get(k): v for k, v in new_adsets.items()})
        media_meta = meta["media"]
        new_media = {}
        for path, rec in ph["media"].items():
            if rec.get("image_hash") or rec.get("video_id"):
                name = media_meta.get(path, {}).get("name") or Path(path).stem
                new_media[path] = {k: rec[k] for k in ("image_hash", "video_id") if rec.get(k)} | {"name": name}
        covers = {code: dict(c, image_hash=new_media[c["path"]]["image_hash"]) for code, c in meta["covers"].items()
                  if c["path"] in new_media}
        meta.update(campaigns=new_camps, adsets=new_adsets, audiences=new_aud, media=new_media, covers=covers,
                    ads={name: new_entry(name, rec) for name, rec in created.items()})
        meta.pop("ads_v3_replaced", None)
        remap_ids(PLAN_JSON, mapping)
        ids.setdefault("old_accounts", []).append(dict(ad_account_id=t["old_account_id"], pixel_id=t["old_pixel_id"],
                                                       page_id=t["old_page_id"], until=date, why=reason))
        ids.update(ad_account_id=t["account_id"], ad_account_name=t["account_name"] or ids["ad_account_name"], pixel_id=t["pixel_id"])
    ids["page_id"] = t["page_id"]
    ids["page_note"] = (f"«{t['page_name'] or 'новая страница'}». С {date} — вместо страницы {t['old_page_id']}: {reason} "
                        "Пересборка 1в1 — 04-ПЕРЕСБОРКА-1В1.md.")
    c1_names = {n for n, (camp, _) in where.items() if not is_risk(camp)}
    n_c1, n_risk = sum(n in c1_names for n in created), sum(n not in c1_names for n in created)
    tot_c1, tot_risk = len(c1_names), len(where) - len(c1_names)
    verify = st.get("verify") or {}
    stop = st.get("stop")
    note = (f"{date}: пересборка 1в1, {MODE_RU[t['mode']]}, {page_label}: объявлений {len(created)} из {len(where)} — C1 {n_c1}/{tot_c1}, "
            f"RISK {n_risk}/{tot_risk}; C1 {'опубликована выключенной' if published else 'не опубликована'}"
            + (f"; старых: удалено {counts['deleted']}, на паузе {counts['paused']}" if t["mode"] == "page" else "")
            + (f"; остановлено: {stop['reason'][:200]}" if stop else ""))
    meta["progress"][f"rebuild_{date}"] = note
    meta["_note"] += f" | {date}: пересборка 1в1 (04-ПЕРЕСБОРКА-1В1.md), прежние ID — в previous_*."
    META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    IDS_FILE.write_text(json.dumps(ids, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    journal = [
        f"| {date} | Пересборка 1в1, {MODE_RU[t['mode']]}: {page_label}, кабинет `{t['account_id']}` (`04-ПЕРЕСБОРКА-1В1.md`) | "
        f"MCP; задания — `rebuild.py`, воркфлоу `meta-rebuild-1v1` | {reason} Создано объявлений {len(created)} из {len(where)}: "
        f"C1 {n_c1}/{tot_c1}, RISK {n_risk}/{tot_risk}. ID — в `meta_ids.json` |",
    ]
    if t["mode"] == "page":
        journal.append(f"| {date} | Старые объявления от страницы {t['old_page_id']} | MCP `ads_update_entity` | "
                       f"Черновиков помечено удалёнными {counts['deleted']}, опубликованных на паузе {counts['paused']}. "
                       f"Прежние ID — `meta_ids.json` → `previous_page_{t['old_page_id']}` |")
    journal.append(f"| {date} | Публикация C1 | MCP `ads_activate_entity`, `publish_as_active=false` | "
                   + ("Опубликована выключенной. " if published else "Не публиковалась. ")
                   + (f"Проверка вживую: {verify.get('summary', '—')}" + ("" if verify.get("ok", True) else f"; проблемы: {'; '.join(verify.get('problems', []))[:500]}"))
                   + (f". Остановлено: {stop['reason'][:300]}" if stop else "") + " |")
    JOURNAL_MD.write_text(JOURNAL_MD.read_text(encoding="utf-8").rstrip("\n") + "\n" + "\n".join(journal) + "\n", encoding="utf-8")

    plan = PLAN_MD.read_text(encoding="utf-8").rstrip("\n")
    n = max(int(x) for x in re.findall(r"^## (\d+)\.", plan, re.M)) + 1
    section = [
        "", f"## {n}. Пересборка 1в1 — {date}", "",
        f"**Почему.** {reason} Разрешение Васи 18.10: «если страницу не разбанят чтоб мы сделали 1в1 без моих подтвреждений "
        "на новой странице». Ранбук — `04-ПЕРЕСБОРКА-1В1.md`.", "",
        "| Что | Состояние |", "|---|---|",
        f"| Страница | `{t['page_id']}`{' «' + t['page_name'] + '»' if t['page_name'] else ''} вместо `{t['old_page_id']}` |",
        f"| Кабинет | `{t['account_id']}`" + (f" вместо `{t['old_account_id']}`, пиксель `{t['pixel_id']}`" if t["mode"] == "account" else ", прежний") + " |",
        f"| Объявления | созданы заново {len(created)} из {len(where)}: C1 {n_c1} из {tot_c1}, RISK {n_risk} из {tot_risk}. "
        "Имена, метки, тексты, кнопки и ссылки прежние |",
        f"| C1 | {'опубликована выключенной: кампания на паузе, показов нет' if published else 'объявления не опубликованы'} |",
        "| RISK | в черновике до 4-го дня, публикация — по команде Васи |",
    ]
    if t["mode"] == "page":
        section.append(f"| Старые объявления | черновиков помечено удалёнными {counts['deleted']}, опубликованных на паузе {counts['paused']}; "
                       f"прежние ID — `meta_ids.json` → `previous_page_{t['old_page_id']}` |")
    section += [f"| Проверка вживую | {verify.get('summary', 'не делалась')} |"]
    if verify.get("problems"):
        section.append(f"| Проблемы | {'; '.join(verify['problems'])[:800]} |")
    if stop:
        section.append(f"| Остановлено | {stop['reason'][:500]} |")
    section += ["", "**Что осталось Васе:** интересы в 6 группах (11.7, п. 2); включение C1 — по его команде; RISK — с 4-го дня по команде.", ""]
    PLAN_MD.write_text(plan + "\n" + "\n".join(section), encoding="utf-8")
    with state(a.run_dir) as s:
        s["applied"] = date
    print(note)
    print("дальше: python3 build_launch.py && python3 check_launch.py && python3 build_utm.py, коммит и пуш")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init")
    s.add_argument("run_dir")
    s.add_argument("--page", required=True)
    s.add_argument("--page-name", default="")
    s.add_argument("--mode", choices=["page", "account"], default="page")
    s.add_argument("--account", default="")
    s.add_argument("--account-name", default="")
    s.add_argument("--pixel", default="")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_init)
    s = sub.add_parser("keys")
    s.add_argument("run_dir")
    s.set_defaults(fn=cmd_keys)
    s = sub.add_parser("jobs")
    s.add_argument("run_dir")
    s.add_argument("phase")
    s.add_argument("--pending", action="store_true")
    s.add_argument("--shard", default="")
    s.add_argument("--keys-only", action="store_true")
    s.set_defaults(fn=cmd_jobs)
    s = sub.add_parser("job")
    s.add_argument("run_dir")
    s.add_argument("phase")
    s.add_argument("key")
    s.set_defaults(fn=cmd_job)
    s = sub.add_parser("save")
    s.add_argument("run_dir")
    s.add_argument("phase")
    s.add_argument("key")
    s.add_argument("field")
    s.add_argument("value")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_save)
    s = sub.add_parser("is-access-error")
    s.add_argument("text", nargs="+")
    s.set_defaults(fn=cmd_is_access_error)
    s = sub.add_parser("stop")
    s.add_argument("run_dir")
    s.add_argument("reason", nargs="+")
    s.set_defaults(fn=cmd_stop)
    s = sub.add_parser("status")
    s.add_argument("run_dir")
    s.add_argument("--check-stop", action="store_true")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_status)
    s = sub.add_parser("verify")
    s.add_argument("run_dir")
    s.add_argument("--live", required=True)
    s.add_argument("--campaign", default="")
    s.add_argument("--draft", default="")
    s.set_defaults(fn=cmd_verify)
    s = sub.add_parser("apply")
    s.add_argument("run_dir")
    s.add_argument("--date", required=True)
    s.add_argument("--force", action="store_true")
    s.add_argument("--reason", default="Прежняя страница недоступна: Meta отвечает «Cannot access page» (01-ПЛАН-ЗАПУСКА.md, 11.8).")
    s.set_defaults(fn=cmd_apply)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
