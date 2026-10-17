"""Независимый расчёт заполненного шаблона на Python — для сверки с формулами книги."""


def cold_block(p, i, reg, traffic, cv_web):
    g = {k: v[i] for k, v in p.items() if isinstance(v, tuple)}
    r = {"reg": reg, "traffic": traffic, "cv_web": cv_web}
    r["part"] = reg * g["att"]
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
    r["web_plan"] = cv_web * max(0.0, r["part"] - r["orders"] - r["autopay"] - r["prepay"])
    r["op_paid"] = r["web_plan"] + r["op_or_plan"] + r["op_bk_plan"]
    r["op_sum"] = r["op_paid"] * g["check"]
    r["plan"] = r["op_sum"] + r["autopay_sum"]
    r["roi"] = r["plan"] / traffic if traffic > 0 else 0.0
    r["check"] = g["check"]
    return r


def warm_block(p, i, cold_reg, cold_sales, cv_dozhim=None, ai=None):
    g = {k: v[i] for k, v in p.items() if isinstance(v, tuple)}
    r = {"cold_reg": cold_reg}
    r["ch_from_cold"] = cold_reg * g["ch_sub"]
    r["ch_buyers"] = cold_sales * g["ch_sub"]
    r["base"] = max(0.0, (g["ch_start"] + r["ch_from_cold"] + g["ch_org"]) * (1 - g["ch_churn"]) - r["ch_buyers"])
    r["reg"] = r["base"] * g["cv_reg"]
    r["part"] = r["reg"] * g["att1"] * g["att2"]
    r["autopay"] = r["part"] * g["cv_autopay"]
    r["bk"] = r["part"] * g["cv_bk"]
    r["orders"] = r["part"] * g["cv_order"]
    r["op_leads"] = r["bk"] + r["orders"]
    r["op_bk_plan"] = r["bk"] * g["op_bk"]
    r["op_or_plan"] = r["orders"] * g["op_or"]
    nonbuy = max(0.0, r["reg"] - r["autopay"] - r["bk"] - r["orders"])
    if cv_dozhim is None:
        noact = max(0.0, r["part"] - r["autopay"] - r["bk"] - r["orders"])
        noshow = max(0.0, r["reg"] - r["part"])
        conv = ai["ai_pay"] + ai["ai_hot"] * ai["m_hot"]
        cv_dozhim = ((noact * ai["eng_att"] + noshow * ai["eng_no"]) * ai["bot"] * conv / nonbuy) if nonbuy > 0 else 0.0
    r["cv_dozhim"] = cv_dozhim
    r["dozhim_plan"] = nonbuy * cv_dozhim
    r["op_total"] = r["dozhim_plan"] + r["op_or_plan"] + r["op_bk_plan"]
    r["op_sum"] = r["op_total"] * g["check"]
    r["autopay_total"] = r["autopay"]
    r["total"] = r["op_total"] + r["autopay"]
    r["plan"] = r["total"] * g["check"]
    r["check"] = g["check"]
    return r


def cv_web_rate(ai):
    return ai["eng_att"] * ai["bot"] * (ai["ai_pay"] + ai["ai_hot"] * ai["m_hot"])


def compute(cold, warm, ai_scen, s3, s5, s6, traffic):
    out = {}
    # трафик
    t_reg = traffic["target_budget"] / traffic["target_cpl"] if traffic["target_cpl"] > 0 else 0.0
    tg_reg = traffic["tg_budget"] / traffic["tg_cpl"] if traffic["tg_cpl"] > 0 else 0.0
    vk_reg = traffic["vk_budget"] / traffic["vk_cpl"] if traffic["vk_cpl"] > 0 else 0.0
    budget_total = traffic["target_budget"] + traffic["tg_budget"] + traffic["vk_budget"]
    out["traffic"] = {"target_reg": t_reg, "reg_total": t_reg + tg_reg + vk_reg, "budget_total": budget_total}
    # холодный: основной блок + сценарии
    base_cold = cold_block(cold, 0, t_reg, budget_total, cv_web_rate(s3))
    out["B_base"] = base_cold
    for j, name in enumerate(["B_min", "B_mid", "B_max"], start=1):
        ai = {k: v[j - 1] for k, v in ai_scen.items()}
        out[name] = cold_block(cold, j, cold["reg"][j], cold["traffic"][j], cv_web_rate(ai))
    # тёплый: основной блок + сценарии
    out["A_base"] = warm_block(warm, 0, base_cold["reg"], base_cold["op_paid"] + base_cold["autopay"], ai=s3)
    for j, (name, bname) in enumerate([("A_min", "B_min"), ("A_opt", "B_mid"), ("A_max", "B_max")], start=1):
        ai = {k: v[j - 1] for k, v in ai_scen.items()}
        b = out[bname]
        out[name] = warm_block(warm, j, b["reg"], b["op_paid"] + b["autopay"], ai=ai)
    # гибридная
    s1 = out["A_base"]
    c = base_cold
    s2 = {"op_paid": c["op_bk_plan"] + c["op_or_plan"]}
    s2["cv_op"] = s2["op_paid"] / c["op_leads"] if c["op_leads"] > 0 else 0.0
    s2["op_sum"] = s2["op_paid"] * c["check"]
    s2["plan"] = s2["op_sum"] + c["autopay_sum"]
    s2["roi"] = s2["plan"] / c["traffic"] if c["traffic"] > 0 else 0.0
    out["C_s2"] = s2
    s3r = {}
    s3r["noact"] = max(0.0, c["part"] - c["orders"] - c["autopay"] - c["prepay"])
    s3r["noshow"] = max(0.0, c["reg"] - c["part"])
    s3r["dialogs"] = (s3r["noact"] * s3["eng_att"] + s3r["noshow"] * s3["eng_no"]) * s3["bot"]
    s3r["ai_paid"] = s3r["dialogs"] * s3["ai_pay"]
    s3r["hot"] = s3r["dialogs"] * s3["ai_hot"]
    s3r["m_paid"] = s3r["hot"] * s3["m_hot"]
    s3r["total"] = s3r["ai_paid"] + s3r["m_paid"]
    s3r["plan"] = s3r["total"] * c["check"]
    out["C_s3"] = s3r
    out["C_s4"] = {"op_plan": s1["op_sum"] + s2["op_sum"] + s3r["plan"], "launch_plan": s1["plan"] + s2["plan"] + s3r["plan"]}
    # шаг 5 — деньги
    m = {}
    own = max(0.0, 1 - s5["full"] - s5["partner"])
    term_n = max(1, min(12, round(s5["term"])))
    first = 1.0 if term_n <= 1 else s5["first"]
    m["cold_rev"] = s2["plan"] + s3r["plan"]
    m["warm_rev"] = s1["plan"]
    m["rev"] = m["cold_rev"] + m["warm_rev"]

    def now(rev):
        return rev * (s5["full"] * (1 - s5["acq"]) + s5["partner"] * (1 - s5["fee"]) + own * first * (1 - s5["acq"])) - rev * s5["refund"]

    def monthly(rev):
        return rev * own * (1 - first) * (1 - s5["default"]) * (1 - s5["acq"]) / (term_n - 1) if term_n > 1 else 0.0
    m["cold_now"], m["warm_now"] = now(m["cold_rev"]), now(m["warm_rev"])
    m["cold_month"], m["warm_month"] = monthly(m["cold_rev"]), monthly(m["warm_rev"])
    m["now"] = m["cold_now"] + m["warm_now"]
    m["later"] = (m["cold_month"] + m["warm_month"]) * (term_n - 1)
    m["loss_acq"] = m["rev"] * (s5["full"] + own * first + own * (1 - first) * (1 - s5["default"])) * s5["acq"]
    m["loss_fee"] = m["rev"] * s5["partner"] * s5["fee"]
    m["loss_def"] = m["rev"] * own * (1 - first) * s5["default"]
    m["loss_ref"] = m["rev"] * s5["refund"]
    m["net"] = m["now"] + m["later"]
    m["term_n"] = term_n
    out["C_s5"] = m
    # шаг 6 — расходы и прибыль
    e = {}
    e["ads"] = budget_total
    e["months"] = s5["gap"] + 1
    e["cold_students"] = s2["op_paid"] + c["autopay"] + s3r["total"]
    e["warm_students"] = s1["total"]
    e["cold_mgr_rev"] = (s2["op_paid"] + s3r["m_paid"]) * c["check"]
    e["warm_mgr_rev"] = s1["op_total"] * s1["check"]
    e["cost_ai"] = s6["ai_setup"] + s6["ai_sub"] * e["months"] + s3r["dialogs"] * s6["ai_dialog"]
    e["cost_mgr"] = s6["salary"] * e["months"] + (e["cold_mgr_rev"] + e["warm_mgr_rev"]) * s6["m_pct"]
    e["cost_team"] = s6["team"]
    e["cost_services"] = s6["services"] * e["months"]
    e["cost_cur"] = (e["cold_students"] + e["warm_students"]) * s6["curator"]
    e["cost_tax"] = m["net"] * s6["tax"]
    e["costs"] = e["ads"] + e["cost_ai"] + e["cost_mgr"] + e["cost_team"] + e["cost_services"] + e["cost_cur"] + e["cost_tax"]
    e["net"] = m["net"]
    e["profit"] = m["net"] - e["costs"]
    e["profit_rec"] = e["profit"] + s6["ai_setup"]
    after_partner = e["profit"] - max(0.0, e["profit"]) * s6["partner_share"]
    e["owner"] = after_partner - max(0.0, after_partner) * s6["div_tax"]
    e["romi"] = e["profit"] / e["ads"] if e["ads"] > 0 else 0.0
    e["start_cash"] = e["ads"] + s6["ai_setup"] + s6["team"] + s6["ai_sub"] + s6["salary"] + s6["services"]
    e["cold_var"] = e["ads"] + s6["ai_setup"] + s3r["dialogs"] * s6["ai_dialog"] + e["cold_mgr_rev"] * s6["m_pct"] + e["cold_students"] * s6["curator"]
    e["warm_var"] = e["warm_mgr_rev"] * s6["m_pct"] + e["warm_students"] * s6["curator"]
    e["fixed_month"] = s6["ai_sub"] + s6["salary"] + s6["services"] + s6["team"] / e["months"]
    out["C_s6"] = e
    # касса по месяцам
    flows, cum, low = [], 0.0, 0.0
    wm = e["months"]
    for mo in range(1, 19):
        inflow = (m["cold_now"] if mo == 1 else 0.0) + (m["cold_month"] if 2 <= mo <= term_n else 0.0) \
            + (m["warm_now"] if mo == wm else 0.0) + (m["warm_month"] if wm + 1 <= mo <= wm + term_n - 1 else 0.0)
        outflow = (e["cold_var"] if mo == 1 else 0.0) + (e["warm_var"] if mo == wm else 0.0) \
            + (e["fixed_month"] if mo <= wm else 0.0) + s6["tax"] * inflow
        cum += inflow - outflow
        low = min(low, cum)
        flows.append((mo, inflow, outflow, inflow - outflow, cum))
    out["cash"] = {"flows": flows, "low": low}
    return out
