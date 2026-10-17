import copy, json, subprocess, sys
from pathlib import Path
from openpyxl import load_workbook
sys.path.insert(0, ".")
import template_defaults as D
from verify_template import verify
RECALC = "/Users/Bel-a/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/62ade98b-c20d-435d-bd1e-b573f3f7bff9/c9850139-8eac-49bf-9bdb-4c182fbb50f1/skills/xlsx/scripts/recalc.py"
addr = json.loads(Path("addr.json").read_text())
def run(name, book_edits, param_edit):
    wb = load_workbook("filled.xlsx")
    for key, val in book_edits.items():
        if key.startswith("SD:"):
            wb["Трафик и лидмагнитная воронка"][key[3:]] = val
        else:
            sh, col, row = addr[key]
            wb[sh][f"{col}{row}"] = val
    out = f"stress_{name}.xlsx"
    wb.save(out)
    res = json.loads(subprocess.run([sys.executable, RECALC, out, "120"], capture_output=True, text=True).stdout)
    p = dict(cold=copy.deepcopy(D.COLD), warm=copy.deepcopy(D.WARM), ai_scen=D.AI_SCEN, s3=dict(D.S3), s5=dict(D.S5), s6=dict(D.S6), traffic=dict(D.TRAFFIC))
    param_edit(p)
    probs = verify(out, "addr.json", params=p, quiet=True)
    print(f"{name}: errors={res.get('total_errors')} mismatches={probs}")
def e_budget0(p): p["traffic"]["target_budget"] = 0
def e_budget2(p): p["traffic"]["target_budget"] = 10000
def e_term1(p): p["s5"]["term"] = 1
def e_gap6(p): p["s5"]["gap"] = 6; p["s5"]["term"] = 12
def e_channel(p):
    w = p["warm"]; w["ch_start"] = (3000,) + w["ch_start"][1:]
def e_noown(p): p["s5"]["full"] = 0.70
run("budget0", {"SD:C6": 0}, e_budget0)
run("budget_x2", {"SD:C6": 10000}, e_budget2)
run("term1", {"C_s5:term": 1}, e_term1)
run("gap6_term12", {"C_s5:gap": 6, "C_s5:term": 12}, e_gap6)
run("channel3000", {"A_base:ch_start": 3000}, e_channel)
run("no_own_installment", {"C_s5:full": 0.70}, e_noown)
