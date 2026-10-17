#!/usr/bin/env python3
"""Сверяет пересчитанную книгу с Python-двойником и проверяет сверки/проверки внутри книги.

Использование: python3 verify_model.py <recalculated.xlsx> <rowmap.json> [defaults_module]
"""
import importlib
import json
import sys
from pathlib import Path

from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).parent))
from twin import compute, scenario  # noqa: E402

S1, S2 = "Декомпозиция цикла", "Деньги по месяцам"
KEYS = ["reg", "cpl", "part", "c_sales", "c_rev", "c_dialogs", "ch_base", "w_reg", "w_part", "w_sales", "w_rev",
        "w_dialogs", "rev_total", "loss_acq", "loss_fee", "loss_default", "loss_refund", "losses_total", "net_money",
        "cash_now_total", "cash_tail_total", "c_own_monthly", "w_own_monthly", "cost_ads", "cost_one_time", "cost_ai",
        "cost_mgr", "cost_team", "cost_services", "cost_curators", "cost_tax", "costs_total", "profit_pre",
        "profit_recurring", "profit_school", "owner_money", "romi", "sales_total", "months", "cpl_be_cycle"]
CHECKS = ["chk_cold", "chk_ai", "chk_warm", "chk_pay", "chk_money", "chk_unit"]


def main():
    path, rowmap_path = sys.argv[1], sys.argv[2]
    defaults = importlib.import_module(sys.argv[3] if len(sys.argv) > 3 else "model_defaults").DEF
    return verify(path, rowmap_path, defaults)


def verify(path, rowmap_path, defaults, quiet=False):
    meta = json.loads(Path(rowmap_path).read_text())
    rowmap, cols, s2 = meta["rowmap"], meta["cols"], meta["s2"]
    wb = load_workbook(path, data_only=True)
    ws1, ws2 = wb[S1], wb[S2]
    problems = 0
    for sc, col in enumerate(cols):
        p = scenario(defaults, sc)
        r = compute(p)
        for key in KEYS:
            got = ws1[f"{col}{rowmap[key]}"].value
            exp = r[key]
            if got is None or abs(float(got) - exp) > max(0.01, abs(exp) * 1e-9):
                problems += 1
                print(f"MISMATCH sc{sc} {key}: book={got} twin={exp}")
        for key in CHECKS:
            val = ws1[f"{col}{rowmap[key]}"].value
            if val not in ("ок", "—"):
                problems += 1
                print(f"CHECK FAIL sc{sc} {key}: {val}")
        ci, co, cn, cc = s2["blocks"][sc]
        for m, inflow, outflow, cum in r["flows"]:
            row = s2["m0"] + m - 1
            for col2, exp in ((ci, inflow), (co, outflow), (cc, cum)):
                got = ws2[f"{col2}{row}"].value
                if got is None or abs(float(got) - exp) > 0.01:
                    problems += 1
                    print(f"CASH MISMATCH sc{sc} m{m} {col2}: book={got} twin={exp}")
        for label, cell in (("сверка поступлений", f"{ci}{s2['chk_in']}"), ("сверка расходов", f"{co}{s2['chk_out']}")):
            if abs(float(ws2[cell].value)) > 0.01:
                problems += 1
                print(f"S2 RECON FAIL sc{sc} {label}: {ws2[cell].value}")
        gap_book = ws2[f"{cc}{s2['gap']}"].value
        if abs(float(gap_book) - r["cash_gap"]) > 0.01:
            problems += 1
            print(f"GAP MISMATCH sc{sc}: book={gap_book} twin={r['cash_gap']}")
        book_profit = ws1[col + str(rowmap["profit_pre"])].value
        if not quiet:
            print(f"sc{sc}: reg={r['reg']:.0f} sales={r['sales_total']:.1f} revenue=${r['rev_total']:,.0f} "
                  f"net=${r['net_money']:,.0f} costs=${r['costs_total']:,.0f} profit=${r['profit_pre']:,.0f} "
                  f"| book profit=${book_profit:,.0f}")
    print("PROBLEMS:", problems)
    return problems


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
