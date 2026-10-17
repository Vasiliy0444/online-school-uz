"""Цифры и Python-расчёт для одной вкладки «Модель продаж - гибридная».
Сценарии везде в порядке: минимум, средний, максимум. Общий план этапа 1 = средний сценарий."""

S1 = {  # этап 1 — запуск через вебинар (холодный трафик)
    "traffic": (5000, 5000, 5000),
    "cpl": (7.8125, 4.0, 2.0),
    "att": (0.20, 0.30, 0.40),
    "peak_pct": (0.60, 0.60, 0.60),
    "cv_order": (0.05, 0.06, 0.08),
    "cv_autopay": (0.010, 0.015, 0.020),
    "cv_prepay": (0.015, 0.020, 0.030),
    "op_bk": (0.60, 0.70, 0.80),
    "op_or": (0.25, 0.35, 0.45),
    "check": (300, 300, 300),
    "tg_sub": (0.15, 0.25, 0.30),
}

S2 = {  # этап 2 — запуск через ТГ-канал, марафон 2 дня
    "ch_start": (0, 0, 0),
    "ch_org": (100, 200, 300),
    "ch_churn": (0.15, 0.10, 0.08),
    "cv_reg": (0.10, 0.15, 0.20),
    "att1": (0.35, 0.45, 0.55),
    "att2": (0.55, 0.65, 0.70),
    "cv_autopay": (0.02, 0.03, 0.04),
    "cv_bk": (0.03, 0.04, 0.05),
    "cv_order": (0.06, 0.08, 0.10),
    "op_bk": (0.60, 0.70, 0.80),
    "op_or": (0.25, 0.35, 0.45),
    "check": (300, 300, 300),
}

AI = {  # ставки дожима в боте: ИИ-продавец + менеджер (для статичной строки «CV ОП» в сценариях)
    "bot": (1.0, 1.0, 1.0),
    "eng_att": (0.20, 0.25, 0.30),
    "eng_no": (0.06, 0.08, 0.10),
    "ai_pay": (0.010, 0.015, 0.020),
    "ai_hot": (0.06, 0.08, 0.10),
    "m_hot": (0.20, 0.25, 0.30),
}

TOT = {  # итог двух этапов
    "full": 0.60, "partner": 0.25, "acq": 0.015, "fee": 0.18, "term": 3, "first": 0.40, "default": 0.15,
    "refund": 0.05, "ai_setup": 1300, "ai_sub": 130, "salary": 300, "m_pct": 0.10, "team": 1500,
    "services": 150, "curator": 15, "tax": 0.04, "months": 2,
}


def _g(p, i):
    return {k: v[i] for k, v in p.items()}


def ai_conv(ai):
    return ai["ai_pay"] + ai["ai_hot"] * ai["m_hot"]


def stage1(p, i, cv_dozhim, other_sources=0.0):
    g = _g(p, i)
    r = {"traffic": g["traffic"], "cpl": g["cpl"], "check": g["check"], "tg_sub": g["tg_sub"]}
    r["target_reg"] = g["traffic"] / g["cpl"] if g["cpl"] > 0 else 0.0
    r["reg"] = r["target_reg"] + other_sources
    r["part"] = r["reg"] * g["att"]
    r["peak"] = r["part"] * g["peak_pct"]
    r["orders"] = r["part"] * g["cv_order"]
    r["orders_sum"] = r["orders"] * g["check"]
    r["autopay"] = r["part"] * g["cv_autopay"]
    r["autopay_sum"] = r["autopay"] * g["check"]
    r["prepay"] = r["part"] * g["cv_prepay"]
    r["op_leads"] = r["orders"] + r["prepay"]
    r["op_leads_sum"] = r["op_leads"] * g["check"]
    r["op_bk_plan"] = g["op_bk"] * r["prepay"]
    r["op_or_plan"] = g["op_or"] * r["orders"]
    r["nonbuy"] = max(0.0, r["reg"] - r["orders"] - r["autopay"] - r["prepay"])
    r["cv_web"] = cv_dozhim
    r["web_plan"] = cv_dozhim * r["nonbuy"]
    r["op_paid"] = r["web_plan"] + r["op_or_plan"] + r["op_bk_plan"]
    r["op_sum"] = r["op_paid"] * g["check"]
    r["plan"] = r["op_sum"] + r["autopay_sum"]
    r["roi"] = r["plan"] / g["traffic"] if g["traffic"] > 0 else 0.0
    r["tg_sub_n"] = r["reg"] * g["tg_sub"]
    return r


def stage1_blended_cv(p, i, ai):
    r = stage1(p, i, 0.0)
    noact = max(0.0, r["part"] - r["orders"] - r["autopay"] - r["prepay"])
    noshow = max(0.0, r["reg"] - r["part"])
    sales = (noact * ai["eng_att"] + noshow * ai["eng_no"]) * ai["bot"] * ai_conv(ai)
    return sales / r["nonbuy"] if r["nonbuy"] > 0 else 0.0


def stage2(p, i, s1r, cv_dozhim):
    g = _g(p, i)
    r = {"check": g["check"]}
    r["from_s1"] = s1r["tg_sub_n"]
    r["buyers"] = (s1r["op_paid"] + s1r["autopay"]) * s1r["tg_sub"]
    r["base"] = max(0.0, (g["ch_start"] + r["from_s1"] + g["ch_org"]) * (1 - g["ch_churn"]) - r["buyers"])
    r["reg"] = r["base"] * g["cv_reg"]
    r["part"] = r["reg"] * g["att1"] * g["att2"]
    r["autopay"] = r["part"] * g["cv_autopay"]
    r["bk"] = r["part"] * g["cv_bk"]
    r["orders"] = r["part"] * g["cv_order"]
    r["op_leads"] = r["bk"] + r["orders"]
    r["op_bk_plan"] = r["bk"] * g["op_bk"]
    r["op_or_plan"] = r["orders"] * g["op_or"]
    r["nonbuy"] = max(0.0, r["reg"] - r["autopay"] - r["bk"] - r["orders"])
    r["cv_dozhim"] = cv_dozhim
    r["dozhim_plan"] = r["nonbuy"] * cv_dozhim
    r["op_total"] = r["dozhim_plan"] + r["op_or_plan"] + r["op_bk_plan"]
    r["op_sum"] = r["op_total"] * g["check"]
    r["autopay_total"] = r["autopay"]
    r["total"] = r["op_total"] + r["autopay"]
    r["plan"] = r["total"] * g["check"]
    return r


def stage2_blended_cv(p, i, s1r, ai):
    r = stage2(p, i, s1r, 0.0)
    noact = max(0.0, r["part"] - r["autopay"] - r["bk"] - r["orders"])
    noshow = max(0.0, r["reg"] - r["part"])
    sales = (noact * ai["eng_att"] + noshow * ai["eng_no"]) * ai["bot"] * ai_conv(ai)
    return sales / r["nonbuy"] if r["nonbuy"] > 0 else 0.0


def blended_rates(s1=S1, s2=S2, ai_p=AI):
    """Статичные ставки дожима по сценариям: считаются один раз при сборке, как вводные шаблона."""
    cv1, cv2 = [], []
    for i in range(3):
        ai = _g(ai_p, i)
        c1 = stage1_blended_cv(s1, i, ai)
        cv1.append(c1)
        cv2.append(stage2_blended_cv(s2, i, stage1(s1, i, c1), ai))
    return cv1, cv2


def compute(s1=S1, s2=S2, tot=TOT, cv1=None, cv2=None, other_sources=0.0):
    if cv1 is None or cv2 is None:
        cv1, cv2 = blended_rates(s1, s2)
    out = {}
    names = ("min", "mid", "max")
    for i, n in enumerate(names):
        out[f"s1_{n}"] = stage1(s1, i, cv1[i], other_sources if n == "mid" else 0.0)
    out["s1_plan"] = out["s1_mid"]
    for i, n in enumerate(names):
        out[f"s2_{n}"] = stage2(s2, i, out[f"s1_{n}"], cv2[i])
    a, b, t = out["s1_mid"], out["s2_mid"], tot
    r = {}
    r["rev1"], r["rev2"] = a["plan"], b["plan"]
    r["op_plan"] = a["op_sum"] + b["op_sum"]
    r["launch"] = r["rev1"] + r["rev2"]
    r["students"] = a["op_paid"] + a["autopay"] + b["total"]
    own = max(0.0, 1 - t["full"] - t["partner"])
    first = 1.0 if round(t["term"]) <= 1 else t["first"]
    r["own"] = own
    r["now"] = r["launch"] * (t["full"] * (1 - t["acq"]) + t["partner"] * (1 - t["fee"]) + own * first * (1 - t["acq"])) \
        - r["launch"] * t["refund"]
    r["later"] = r["launch"] * own * (1 - first) * (1 - t["default"]) * (1 - t["acq"])
    r["net"] = r["now"] + r["later"]
    r["losses"] = r["launch"] - r["net"]
    r["traffic"] = a["traffic"]
    r["costs"] = (r["traffic"] + t["ai_setup"] + t["ai_sub"] * t["months"] + t["salary"] * t["months"]
                  + t["m_pct"] * r["op_plan"] + t["team"] + t["services"] * t["months"]
                  + t["curator"] * r["students"] + t["tax"] * r["net"])
    r["profit"] = r["net"] - r["costs"]
    r["profit_rec"] = r["profit"] + t["ai_setup"]
    r["roas"] = r["launch"] / r["traffic"] if r["traffic"] > 0 else 0.0
    r["payback"] = r["net"] / r["costs"] if r["costs"] > 0 else 0.0
    r["ok"] = "ДА" if r["profit"] >= 0 else "НЕТ"
    r["start_cash"] = r["traffic"] + t["ai_setup"] + t["team"] + t["ai_sub"] + t["salary"] + t["services"]
    out["total"] = r
    return out


if __name__ == "__main__":
    cv1, cv2 = blended_rates()
    print("blended cv stage1:", [f"{c:.4%}" for c in cv1], "stage2:", [f"{c:.4%}" for c in cv2])
    o = compute(cv1=cv1, cv2=cv2)
    for n in ("min", "mid", "max"):
        a, b = o[f"s1_{n}"], o[f"s2_{n}"]
        print(f"{n}: этап1 рег {a['reg']:.0f} продаж {a['op_paid'] + a['autopay']:.1f} план ${a['plan']:,.0f} ROAS {a['roi']:.0%} "
              f"подписались {a['tg_sub_n']:.0f} | этап2 база {b['base']:.0f} рег {b['reg']:.0f} продаж {b['total']:.1f} план ${b['plan']:,.0f}")
    t = o["total"]
    print({k: (round(v) if isinstance(v, float) else v) for k, v in t.items()})
