#!/usr/bin/env python3
"""Склейка страниц Meta в школы (без сети) → 01-master/schools.csv.

Склеиваем только с доказательством:
  - общий домен лендинга (кроме общих площадок: соцсети, формы, конструкторы без своего поддомена);
  - общий аккаунт Instagram или Telegram в ссылках объявлений.
Похожие названия без общих ссылок не склеиваем — только помечаем «проверить на воротах 1».
Колонка evidence — чем подтверждена склейка. Ручные поправки — 01-master/schools_manual.csv
(school_id, page_ids через «;», name, track, niche, note) — применяются поверх автоматической склейки.
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = HERE / "01-master"
SHARED_HOSTS = {"instagram.com", "facebook.com", "fb.me", "m.me", "wa.me", "t.me", "telegram.me", "youtube.com", "youtu.be",
                "forms.gle", "docs.google.com", "google.com", "tiktok.com", "apps.apple.com", "play.google.com", "itunes.apple.com",
                "taplink.cc", "linktr.ee", "vercel.app", "tilda.ws", "netlify.app", "wixsite.com", "lovable.app", "bit.ly"}
EARNING = {"маркетплейсы", "маркетинг и SMM", "монтаж и видео", "ИИ", "фриланс, IT, дизайн", "заработок в целом", "бизнес и финансы"}


def norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9а-я]+", "", name.lower())


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "school"


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}
        self.why: dict[str, set[str]] = defaultdict(set)

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str, reason: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra
            self.why[ra] |= self.why.pop(rb, set())
        self.why[ra].add(reason)


def split(value: str) -> list[str]:
    return [v.strip() for v in (value or "").split(";") if v.strip()]


def main() -> None:
    with (M / "pages.csv").open(encoding="utf-8") as fh:
        pages = {p["page_id"]: p for p in csv.DictReader(fh)}
    uf = UnionFind()
    owners = defaultdict(set)
    for pid, p in pages.items():
        uf.find(pid)
        for host in split(p["landing_domains"]):
            if host not in SHARED_HOSTS and not any(host.endswith("." + s) and s in {"instagram.com", "facebook.com"} for s in SHARED_HOSTS):
                owners[f"домен {host}"].add(pid)
        for platform in ("instagram", "telegram"):
            for handle in split(p[platform]):
                owners[f"{platform} {handle}"].add(pid)
    for reason, pids in owners.items():
        pids = sorted(pids)
        for other in pids[1:]:
            uf.union(pids[0], other, reason)

    groups = defaultdict(list)
    for pid in pages:
        groups[uf.find(pid)].append(pid)
    by_name = defaultdict(list)
    for root, pids in groups.items():
        by_name[norm_name(pages[max(pids, key=lambda x: float(pages[x]["ads_seen"] or 0))]["page_name"])[:12]].append(root)

    manual = {}
    if (M / "schools_manual.csv").exists():
        with (M / "schools_manual.csv").open(encoding="utf-8") as fh:
            manual = {r["school_id"]: r for r in csv.DictReader(fh)}
    covered = {pid for r in manual.values() for pid in split(r["page_ids"])}

    def niche_of(p: dict) -> str:
        return p["niche_top"] if p["niche_top"] and p["niche_top"] != "без явной ниши" else (p.get("candidate_niche") or "без явной ниши")

    def is_education(p: dict) -> bool:
        """Кандидат из скана 03 / брифа / карты блогеров — или по текстам объявлений это обучение на узбекском."""
        if p.get("candidate_name"):
            return True
        info = float(p["info_share"]) if p["info_share"] not in ("", None) else 0.0
        uz = float(p["uz_share"]) if p["uz_share"] not in ("", None) else 0.0
        return info >= 0.5 and uz >= 0.5 and niche_of(p) in EARNING | {"языки"}

    excluded = {pid for pid, p in pages.items() if not is_education(p)}
    rows = []
    for school_id, r in manual.items():
        pids = [p for p in split(r["page_ids"]) if p in pages]

        def union(column: str, skip_shared: bool = False) -> str:
            values = {v for p in pids for v in split(pages[p][column]) if not (skip_shared and v in SHARED_HOSTS)}
            return "; ".join(sorted(values))

        rows.append({"school_id": school_id, "name": r["name"], "page_ids": r["page_ids"], "track": r.get("track") or "заработок",
                     "niche": r.get("niche", ""), "domains": union("landing_domains", skip_shared=True),
                     "instagram": union("instagram"), "telegram": union("telegram"), "youtube": union("youtube"),
                     "evidence": f"ручное решение: {r.get('note', '')}", "check": ""})
    for root, pids in groups.items():
        pids = [p for p in pids if p not in covered and p not in excluded]
        if not pids:
            continue
        main = max(pids, key=lambda x: (float(pages[x]["counter"] or 0), float(pages[x]["ads_seen"] or 0)))
        niche = niche_of(pages[main])
        similar = [r for r in by_name[norm_name(pages[main]["page_name"])[:12]] if r != root]
        rows.append({
            "school_id": slug(pages[main]["page_name"]) + "-" + main[-4:],
            "name": pages[main]["page_name"],
            "page_ids": "; ".join(pids),
            "track": ("английский" if any(float(pages[p].get("english_ads") or 0) > 0 for p in pids) else "языки (другие)")
                     if niche == "языки" else ("заработок" if niche in EARNING else "другое"),
            "niche": niche,
            "domains": "; ".join(sorted({h for p in pids for h in split(pages[p]["landing_domains"]) if h not in SHARED_HOSTS})),
            "instagram": "; ".join(sorted({h for p in pids for h in split(pages[p]["instagram"])})),
            "telegram": "; ".join(sorted({h for p in pids for h in split(pages[p]["telegram"])})),
            "youtube": "; ".join(sorted({h for p in pids for h in split(pages[p]["youtube"])})),
            "evidence": " | ".join(sorted(uf.why.get(root, set()))) or "одна страница",
            "check": "похожие названия у других страниц — проверить на воротах 1" if similar else "",
        })
    with (M / "schools.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"pages: {len(pages)} (не обучение или не узбекский: {len(excluded)}) → schools: {len(rows)} "
          f"(склеено: {sum(1 for r in rows if ';' in r['page_ids'])}, на проверку: {sum(1 for r in rows if r['check'])})")


if __name__ == "__main__":
    main()
