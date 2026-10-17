"""Независимый Python-двойник финмодели. Считает те же показатели без формул Excel."""


def _event(p, reg, att1, att2, ap_rate, bk_rate, or_rate, price):
    part = reg * att1 * att2
    ap, bk, orr = part * ap_rate, part * bk_rate, part * or_rate
    noact = max(0.0, part - ap - bk - orr)
    noshow = max(0.0, reg - part)
    m_bk, m_or = bk * p["m_bk"], orr * p["m_or"]
    dialogs = (noact * p["ai_eng_att"] + noshow * p["ai_eng_no"]) * p["bot_share"]
    ai_pay = dialogs * p["ai_pay"]
    hot = dialogs * p["ai_hot"]
    m_hot = hot * p["m_hot"]
    sales = ap + m_bk + m_or + ai_pay + m_hot
    upsell = sales * p["upsell_rate"]
    rev = sales * price + upsell * p["upsell_price"]
    mgr_rev = (m_bk + m_or + m_hot) * price + upsell * p["upsell_price"]
    ai_rev = (ai_pay + m_hot) * price
    return dict(part=part, ap=ap, bk=bk, orr=orr, noact=noact, noshow=noshow, dialogs=dialogs,
                ai_pay=ai_pay, hot=hot, m_hot=m_hot, m_bk=m_bk, m_or=m_or, sales=sales,
                upsell=upsell, rev=rev, mgr_rev=mgr_rev, ai_rev=ai_rev)


def _money(p, rev, own_n):
    pay_own = max(0.0, 1 - p["pay_full"] - p["pay_partner"])
    first = 1.0 if own_n == 1 else p["own_first"]
    now_gross = rev * (p["pay_full"] * (1 - p["acq"]) + p["pay_partner"] * (1 - p["partner_fee"])
                       + pay_own * first * (1 - p["acq"]))
    tail = rev * pay_own * (1 - first) * (1 - p["own_default"]) * (1 - p["acq"])
    monthly = tail / (own_n - 1) if own_n > 1 else 0.0
    refund = rev * p["refund"]
    return dict(now_gross=now_gross, tail=tail, monthly=monthly, refund=refund,
                net=now_gross + tail - refund, pay_own=pay_own, first=first)


def compute(p):
    r = {}
    r["impr"] = p["budget"] / p["cpm"] * 1000 if p["cpm"] > 0 else 0.0
    r["clicks"] = r["impr"] * p["ctr"]
    r["reg"] = r["clicks"] * p["cr_reg"]
    r["cpl"] = p["budget"] / r["reg"] if r["reg"] > 0 else 0.0
    c = _event(p, r["reg"], p["att1"], p["att2"], p["ap_rate"], p["bk_rate"], p["or_rate"], p["price_cold"])
    ch_from_cold = r["reg"] * p["ch_sub"]
    churn = (p["ch_start"] + ch_from_cold + p["ch_org"]) * p["ch_churn"]
    ch_buyers = c["sales"] * p["ch_sub"]
    ch_base = max(0.0, p["ch_start"] + ch_from_cold + p["ch_org"] - churn - ch_buyers)
    w_bot_rest = max(0.0, (r["reg"] * p["bot_share"] - c["sales"]) * (1 - p["ch_sub"]))
    w_reg_paid = p["w_budget"] / p["w_cpl"] if p["w_cpl"] > 0 else 0.0
    w_reg = ch_base * p["w_reg_ch_rate"] + w_bot_rest * p["w_reg_bot_rate"] + w_reg_paid
    w = _event(p, w_reg, p["w_att1"], p["w_att2"], p["w_ap_rate"], p["w_bk_rate"], p["w_or_rate"], p["price_warm"])
    own_n = max(1, min(12, round(p["own_term"])))
    cm, wm = _money(p, c["rev"], own_n), _money(p, w["rev"], own_n)
    rev_total = c["rev"] + w["rev"]
    pay_own, first = cm["pay_own"], cm["first"]
    loss_acq = rev_total * (p["pay_full"] + pay_own * first + pay_own * (1 - first) * (1 - p["own_default"])) * p["acq"]
    loss_fee = rev_total * p["pay_partner"] * p["partner_fee"]
    loss_default = rev_total * pay_own * (1 - first) * p["own_default"]
    loss_refund = cm["refund"] + wm["refund"]
    net_money = cm["net"] + wm["net"]
    months = p["gap"] + 1
    sales_total = c["sales"] + w["sales"]
    costs = dict(
        ads=p["budget"] + p["w_budget"],
        one_time=p["ai_setup"] + p["one_time_other"],
        ai=p["ai_sub"] * months + (c["dialogs"] + w["dialogs"]) * p["ai_dialog_cost"],
        mgr=p["m_salary"] * months + (c["mgr_rev"] + w["mgr_rev"]) * p["m_pct"],
        team=p["team"], services=p["services"] * months, curators=sales_total * p["curator"],
        tax=net_money * p["tax"])
    costs_total = sum(costs.values())
    profit_pre = net_money - costs_total
    r.update(dict(
        part=c["part"], c_sales=c["sales"], c_rev=c["rev"], c_dialogs=c["dialogs"], ch_base=ch_base,
        w_reg=w_reg, w_part=w["part"], w_sales=w["sales"], w_rev=w["rev"], w_dialogs=w["dialogs"],
        rev_total=rev_total, net_money=net_money, losses_total=loss_acq + loss_fee + loss_default + loss_refund,
        loss_acq=loss_acq, loss_fee=loss_fee, loss_default=loss_default, loss_refund=loss_refund,
        cash_now_total=cm["now_gross"] - cm["refund"] + wm["now_gross"] - wm["refund"],
        cash_tail_total=cm["tail"] + wm["tail"], c_own_monthly=cm["monthly"], w_own_monthly=wm["monthly"],
        costs_total=costs_total, profit_pre=profit_pre,
        profit_school=profit_pre - max(0.0, profit_pre) * p["partner_share"],
        owner_money=(profit_pre - max(0.0, profit_pre) * p["partner_share"])
        - max(0.0, profit_pre - max(0.0, profit_pre) * p["partner_share"]) * p["div_tax"],
        profit_recurring=profit_pre + costs["one_time"],
        romi=profit_pre / costs["ads"] if costs["ads"] > 0 else 0.0,
        sales_total=sales_total, months=months, **{"cost_" + k: v for k, v in costs.items()}))
    money_ratio = net_money / rev_total if rev_total > 0 else 0.0
    if r["reg"] > 0:
        r["cpl_be_cycle"] = (rev_total * money_ratio * (1 - p["tax"])
                             - (c["dialogs"] + w["dialogs"]) * p["ai_dialog_cost"]
                             - (c["mgr_rev"] + w["mgr_rev"]) * p["m_pct"]
                             - sales_total * p["curator"]) / r["reg"]
    else:
        r["cpl_be_cycle"] = 0.0
    # касса по месяцам
    warm_m = months
    fixed_monthly = p["ai_sub"] + p["m_salary"] + p["services"] + p["team"] / months
    c_var = p["budget"] + c["dialogs"] * p["ai_dialog_cost"] + c["mgr_rev"] * p["m_pct"] + c["sales"] * p["curator"]
    w_var = p["w_budget"] + w["dialogs"] * p["ai_dialog_cost"] + w["mgr_rev"] * p["m_pct"] + w["sales"] * p["curator"]
    cum, cum_min, flows = 0.0, 0.0, []
    for m in range(1, 19):
        inflow = 0.0
        if m == 1:
            inflow += cm["now_gross"] - cm["refund"]
        if 2 <= m <= own_n:
            inflow += cm["monthly"]
        if m == warm_m:
            inflow += wm["now_gross"] - wm["refund"]
        if warm_m + 1 <= m <= warm_m + own_n - 1:
            inflow += wm["monthly"]
        outflow = (c_var + p["ai_setup"] + p["one_time_other"] if m == 1 else 0.0) \
            + (w_var if m == warm_m else 0.0) + (fixed_monthly if m <= months else 0.0) + p["tax"] * inflow
        cum += inflow - outflow
        cum_min = min(cum_min, cum)
        flows.append((m, inflow, outflow, cum))
    r["cash_gap"] = cum_min
    r["flows"] = flows
    return r


def scenario(defaults, idx):
    return {k: v[idx] for k, v in defaults.items()}


if __name__ == "__main__":
    import sys
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    from model_defaults import DEF
    for i, name in enumerate(["Минимум", "Оптимум", "Максимум"]):
        p = scenario(DEF, i)
        r = compute(p)
        print(f"\n== {name}: reg {r['reg']:.0f} CPL ${r['cpl']:.2f} part {r['part']:.0f} | cold sales {r['c_sales']:.1f} "
              f"rev ${r['c_rev']:,.0f} conv {r['c_sales']/r['reg']:.2%} ROAS {r['c_rev']/p['budget']:.2f}x")
        print(f"   channel {r['ch_base']:.0f} warm reg {r['w_reg']:.0f} part {r['w_part']:.0f} sales {r['w_sales']:.1f} rev ${r['w_rev']:,.0f} "
              f"({r['w_rev']/r['rev_total']:.0%})")
        print(f"   revenue ${r['rev_total']:,.0f} net ${r['net_money']:,.0f} (losses {r['losses_total']/r['rev_total']:.1%}) "
              f"now ${r['cash_now_total']:,.0f} tail ${r['cash_tail_total']:,.0f}")
        print("   costs", {k[5:]: round(v) for k, v in r.items() if k.startswith('cost_')}, f"total ${r['costs_total']:,.0f}")
        print(f"   PROFIT ${r['profit_pre']:,.0f} | w/o one-time ${r['profit_recurring']:,.0f} | ROMI {r['romi']:.2f}x | "
              f"CPL max ${r['cpl_be_cycle']:.2f} | cash gap ${r['cash_gap']:,.0f}")
