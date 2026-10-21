"""FIN 439 Project 1 Oracle: reproducible local analyst workbench.

COMMANDS (Python 3 stdlib only):
  py orcl_project1_application.py --summary
  py orcl_project1_application.py --export
  py orcl_project1_application.py --tests
  py orcl_project1_application.py --demo-failure
  py orcl_project1_application.py                  # Tkinter graphical workbench

Finance caveat: August 31 2026 STATEMENT anchor, not a contemporaneous trade date.
11.4% WACC and FY2032 terminal FCFF are UNVERIFIED research sensitivities.
Negative FCFF and failed financing are never silently erased. No investment advice.
"""
import argparse
import copy
import json
import math
from pathlib import Path

import orcl_project1_post_q1_proforma as model
import orcl_project1_valuation_bridge as val
from orcl_project1_fcff import discount_cash_flows

ROOT = Path(__file__).resolve().parent
MARKET_PRICE = 129.59  # Historical ORCL unadjusted 2026-10-19 close, stockanalysis.com
MARKET_DATE = "2026-10-19"
PRICE_SOURCE = "https://stockanalysis.com/stocks/orcl/history/"
TERMINAL_CAPEX_INCREMENT = 0.0  # Base normalization assumption: no incremental capex vs FY31 (unverified)
ASSUMPTION_GRID = {
    "growth_shift_pp": [-2.0, 0.0, 2.0],
    "fy28_capex_pct": [-10.0, 0.0, 10.0],
    "gross_margin_shift_pp": [-1.0, 0.0, 1.0],
    "wacc_pct": [10.4, 11.4, 12.4],
    "terminal_growth_pct": [2.0, 3.0, 4.0],
    "terminal_capex_delta": [0., 5000., 10000.],
}
DRIVER_CHALLENGES = {
    "growth_shift_pp": {"base":0, "bounds":"-2 to +2 percentage points on FY28-FY31 growth", "basis":"Lab 11 analyst scenario; cloud demand", "challenge":"FY28-31 contract conversion may slow", "evidence":"Quarterly cloud revenue and remaining performance obligations"},
    "fy28_capex_pct": {"base":0, "bounds":"-10% to +10% of FY2028 $70bn capex", "basis":"Lab 11 spending sensitivity", "challenge":"Capacity and cooling/build delays or procurement inflation", "evidence":"FY2027 quarterly capex, vendor/lease commitments and delivered capacity"},
    "gross_margin_shift_pp": {"base":0, "bounds":"-1 to +1 pp FY28-FY31 pre-depreciation gross margin", "basis":"Analyst stress test, not guidance", "challenge":"GPU/server economics, power expenses, cloud mix", "evidence":"Reported cloud cost of revenue and margin trend"},
    "wacc_pct": {"base":11.4, "bounds":"9.4%-13.4%; Lab 06 assumed base", "basis":"Historical teaching model assumption; not a market-calibrated WACC", "challenge":"Cost of capital and capital-structure uncertainty", "evidence":"Contemporaneous Treasury yield, defensible beta/ERP, marginal borrowing cost, capital weights"},
    "terminal_capex_delta": {"base":0, "bounds":"0-10,000 USD millions extra FY2032 normalized capex", "basis":"Stress only: spending required to sustain the installed base", "challenge":"Marginal replacement of GPU/server fleets could be substantially higher", "evidence":"Asset useful lives, FY2032 run-rate purchase commitments"},
    "terminal_growth_pct": {"base":3, "bounds":"1%-4%; < WACC", "basis":"Lab 06 terminal-growth assumption", "challenge":"Long-run cloud maturity and sustained reinvestment", "evidence":"Contract renewals, asset-life studies and normalized FY2032 investments"},
}


def run_case(*, growth_shift_pp=0., fy28_capex_pct=0., gross_margin_shift_pp=0.,
             wacc_pct=11.4, terminal_growth_pct=3., terminal_capex_delta=0.,
             crash_on_error=False):
    """One-at-a-time scenario; financing failures return explicit INVALID status."""
    config = dict(growth_shift_pp=float(growth_shift_pp), fy28_capex_pct=float(fy28_capex_pct),
                  gross_margin_shift_pp=float(gross_margin_shift_pp),
                  wacc_pct=float(wacc_pct), terminal_growth_pct=float(terminal_growth_pct),
                  terminal_capex_delta=float(terminal_capex_delta))
    try:
        if not all(math.isfinite(x) for x in config.values()):
            raise ValueError("Nonfinite driver")
        if not (-2<=config["growth_shift_pp"]<=2 and -10<=config["fy28_capex_pct"]<=10
                and -1<=config["gross_margin_shift_pp"]<=1 and 9.4<=wacc_pct<=13.4
                and 1<=terminal_growth_pct<=4 and 0<=terminal_capex_delta<=20000):
            raise ValueError("Driver exceeds documented bounds")
        a=copy.deepcopy(model.BASE)
        a["annual_revenue_growth_after_2027"]=[x+growth_shift_pp/100 for x in a["annual_revenue_growth_after_2027"]]
        a["future_capex"][1]*=1+fy28_capex_pct/100
        a["gross_margin_before_depreciation"]=[x+gross_margin_shift_pp/100 for x in a["gross_margin_before_depreciation"]]
        rows=model.project(a)
        count=model.audit_independently(rows, a)
        w,g=wacc_pct/100,terminal_growth_pct/100
        if g>=w: raise ValueError("WACC must exceed terminal growth")
        # A user-changeable terminal reinvestment penalty is deducted from FY2032 cash flow.
        # Terminal profits are NOT increased when capex rises; no speculative revenue reward.
        terminal_fcff=rows[-1]["fcff"]*(1+g)-terminal_capex_delta
        if terminal_fcff<=0: raise ValueError("Terminal FCFF not positive")
        dcf=discount_cash_flows([r["fcff"] for r in rows],
                                [r["time_years_from_2026_08_31"] for r in rows],
                                w,terminal_fcff,g)
        if dcf["enterprise_value"]<=0:raise ValueError("Nonpositive enterprise value")
        bridge=val.common_equity_bridge(dcf["enterprise_value"])
        return {"status":"PASS_WITH_MATERIAL_VALUATION_LIMITATIONS", "drivers":config,
                "audited_checks":count,"forecast":rows,"dcf":dcf,"bridge":bridge,
                "terminal_share_pct":100*dcf["terminal_value_share"],
                "indicative_per_share":bridge["indicative_dollars_per_share_NOT_FINAL"],
                "market_price_reference":MARKET_PRICE, "market_price_date":MARKET_DATE,
                "market_price_source":PRICE_SOURCE,"valuation_not_final":True}
    except (ValueError,OverflowError,ZeroDivisionError) as exc:
        if crash_on_error:raise
        return {"status":"INVALID", "drivers":config,"failure":str(exc), "valuation_not_final":True}


def scenarios():
    result={}
    for key,vals in ASSUMPTION_GRID.items():
        for value in vals:
            args={}
            if key in ("growth_shift_pp","fy28_capex_pct","gross_margin_shift_pp"):
                args[key]=value
            elif key in ("wacc_pct","terminal_growth_pct"):
                args[key]=value
            elif key == "terminal_capex_delta":args[key]=value
            case=run_case(**args)
            result[f"{key}:{value:+g}"]={
                "status":case["status"], "failure":case.get("failure"),
                "value_per_share":case.get("indicative_per_share"),
                "fy2031_ebit":case.get("forecast",[{}])[-1].get("ebit") if case.get("forecast") else None,
                "fy2031_fcff":case.get("forecast",[{}])[-1].get("fcff") if case.get("forecast") else None,
            }
    return result


def combined_cases():
    """Causal THREE scenario paths: independently labeled, never probabilities."""
    cases={
      "low": dict(growth_shift_pp=-1.0, fy28_capex_pct=0.,gross_margin_shift_pp=-.5),
      "base": dict(),
      "high": dict(growth_shift_pp=2.0, fy28_capex_pct=-5., gross_margin_shift_pp=.5),
      "stress_invalid": dict(growth_shift_pp=-2.0,fy28_capex_pct=10.,gross_margin_shift_pp=-1.),
    }
    ans={}
    for name,inputs in cases.items():
        x=run_case(**inputs)
        ans[name]={"drivers":inputs,"status":x["status"],"failure":x.get("failure"),
          "indicative_per_share":x.get("indicative_per_share"),
          "fy2031_ebit":x["forecast"][-1]["ebit"] if x.get("forecast") else None,
          "fy2031_fcff":x["forecast"][-1]["fcff"] if x.get("forecast") else None}
    return ans


def two_way_wacc_growth_grid():
    """Change WACC and terminal growth in cross-product cells; base operating forecast."""
    results={}
    for w in ASSUMPTION_GRID["wacc_pct"]:
        results[f"{w:.1f}%"]={}
        for g in ASSUMPTION_GRID["terminal_growth_pct"]:
            x=run_case(wacc_pct=w,terminal_growth_pct=g)
            results[f"{w:.1f}%"][f"{g:.1f}%"]={"status":x["status"],"indicative_per_share":x.get("indicative_per_share")}
    return results


def price_implied_terminal_fcff(base):
    """Reverse DCF: FY2032 steady FCFF needed to match observed price, holding other items fixed."""
    b=base["bridge"]
    target_common=MARKET_PRICE*b["shares_millions"]
    required_ev=(target_common - b["plus_cash_in_bridge"] - b["plus_marketable_securities"]
        + b["minus_senior_notes_and_borrowings"] + b["minus_finance_leases"]
        + b["minus_preferred_claim"] + b["minus_noncontrolling_interests"])
    w=base["drivers"]["wacc_pct"]/100
    g=base["drivers"]["terminal_growth_pct"]/100
    exp_pv=base["dcf"]["pv_explicit"]
    years=base["forecast"][-1]["time_years_from_2026_08_31"]
    required_terminal=(required_ev-exp_pv)*(1+w)**years
    required_fcff=required_terminal*(w-g)
    return {"target_market_price_date":MARKET_DATE,"price":MARKET_PRICE,
            "market_implied_terminal_fy2032_fcff_millions":required_fcff,
            "base_unverified_terminal_fy2032_fcff_millions":base["dcf"]["terminal_fcff"],
            "additional_terminal_fcff_required_millions":required_fcff-base["dcf"]["terminal_fcff"],
            "caveat":"Reverse calculation compares Oct19 quote with an Aug31-based forecast without a Sep/Oct stub; interpret as scale test only"}


def peers():
    """Frozen Sep10 independent comparables; EV/revenue excludes operational leases consistently."""
    # Stock prices and P/E from student's frozen Lab 08; 2026 FY 10Ks for debt/cash/revenue.
    # MSFT debt as disclosed $46,136m principal due, vs balance-sheet debt may differ.
    # Using outstanding-share cover count, NOT diluted weighted-average shares.
    data=[
        {"ticker":"MSFT","price":492.44,"shares":7425.545491,"revenue":331839,
         "debt":46136,"cash_and_short_investments":76843,"gaap_eps":17.95,
         "annual_filing":"https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm",
         "qualification":"Diversified consumer/ads/gaming and OpenAI EPS effect; marginal debt carrying/principal basis difference"},
        {"ticker":"CRM","price":243.,"shares":923.,"revenue":41525,
         "debt":14500,"cash_and_short_investments":9565,"gaap_eps":7.80,
         "annual_filing":"https://www.sec.gov/Archives/edgar/data/1108524/000110852426000060/crm-20260131.htm",
         "qualification":"Predominantly CRM applications, not Oracle infrastructure; cover shares Feb25"},
    ]
    for p in data:
        p["equity_market_cap_millions"]=p["price"]*p["shares"]
        p["ev_millions"]=p["equity_market_cap_millions"]+p["debt"]-p["cash_and_short_investments"]
        p["ev_to_reported_revenue"]=p["ev_millions"]/p["revenue"]
        p["gaap_pe"]=p["price"]/p["gaap_eps"]
        p["price_as_of"]="2026-09-10"
        p["pricing_source"]="Student's prior Lab 08 source map / https://stockanalysis.com/stocks/{}/history/".format(p["ticker"].lower())
    return data


def report():
    base=run_case()
    assert base["status"].startswith("PASS")
    return {"title":"ORCL Project 1 -- Research Workbench", "prepared":"2026-10-19",
       "investment_user":"Buy-side investment committee; no existing ORCL position in mandate",
       "action":"WATCH / DEFER initiating; re-evaluate after independent validation",
       "valuation_as_of_note":"August 31, 2026 reported-balance anchor; reported Q1 10-Q published later. No Sep-Oct stub; market Oct19 only an out-of-period comparator.",
       "market_reference":{"date":MARKET_DATE,"price":MARKET_PRICE,"source":PRICE_SOURCE},
       "base":base, "one_at_a_time_scenarios":scenarios(),
       "joint_causal_cases":combined_cases(), "wacc_terminal_growth_2way":two_way_wacc_growth_grid(),"reverse_dcf":price_implied_terminal_fcff(base),
       "peer_comparison_archived_sep10":peers(),"assumption_challenges":DRIVER_CHALLENGES,
       "evidence":{"oracle_q1":"https://www.sec.gov/Archives/edgar/data/1341439/000119312526389274/orcl-20260831.htm",
          "oracle_annual":"https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm",
          "historical_lab08":"https://github.com/edheeres05/ORCL_Research/blob/main/lab08_oracle.md",
          "lab11":"https://github.com/edheeres05/Proforma/blob/main/lab11_orcl_EthanHeeres.md"},
       "fy2026_normalized_earnings_screen":{"reported_net_income_millions":17087,"one_time_ampere_gain_millions_approx":2700,"illustrative_tax_rate_for_gain":0.18,"proxy_net_income_ex_ampere_gain_millions":17087-2700*(1-.18),"disposition":"Analyst normalization only; not GAAP and not substituted into operating EBIT. Confirm tax basis and other nonrecurring items."},
       "unresolved":["WACC factors are illustrative not market-sourced", "Terminal FY2032 reinvestment is not justified",
           "Model freezes operating and finance leases and other liabilities", "Post-Q1 forecast is a stub and does not reconcile Sep1-Oct19 actual cash flows",
           "Historical peer EV/revenue uses latest FY reporting periods, not identical TTM dates", "SBC and final fully diluted share count remain unresolved",
           "Prior Lab11 locked AI-off test is historical; current user prediction in assisted chat does not independently establish new AI-off status"]}


def test_suite():
    import unittest
    class TestWorkbench(unittest.TestCase):
        def test_base(self): self.assertTrue(run_case()["status"].startswith("PASS"))
        def test_reconcile(self):
            x=run_case();self.assertEqual(x["audited_checks"],52)
            self.assertAlmostEqual(x["bridge"]["bridge_gap"],0,places=5)
        def test_discount(self):
            self.assertGreater(run_case(wacc_pct=10.4)["indicative_per_share"],run_case()["indicative_per_share"])
            self.assertLess(run_case(terminal_growth_pct=2)["indicative_per_share"],run_case()["indicative_per_share"])
        def test_growth(self):
            self.assertGreater(run_case(growth_shift_pp=2)["forecast"][-1]["ebit"],run_case()["forecast"][-1]["ebit"])
        def test_capex(self):
            self.assertLess(run_case(fy28_capex_pct=-10)["forecast"][1]["capex"],run_case()["forecast"][1]["capex"])
            self.assertEqual(run_case(fy28_capex_pct=10)["status"],"INVALID")
        def test_margin(self): self.assertGreater(run_case(gross_margin_shift_pp=1)["forecast"][-1]["ebit"],run_case()["forecast"][-1]["ebit"])
        def test_fail_loudly(self):
            r=model.project();r[0]["cash"]-=1000
            with self.assertRaises(ValueError):model.audit_independently(r)
        def test_reverse(self): self.assertGreater(price_implied_terminal_fcff(run_case())["market_implied_terminal_fy2032_fcff_millions"],0)
        def test_base_reset_integrity(self):
            a=run_case()["indicative_per_share"]; run_case(fy28_capex_pct=-10)
            self.assertAlmostEqual(a,run_case()["indicative_per_share"])
        def test_boundaries(self):
            self.assertEqual(run_case(growth_shift_pp=9)["status"],"INVALID")
            self.assertEqual(run_case(wacc_pct=math.nan)["status"],"INVALID")
        def test_joint_and_grid(self):
            c=combined_cases();self.assertTrue(all(c[k]["status"].startswith("PASS") for k in ("low","base","high")))
            self.assertEqual(c["stress_invalid"]["status"],"INVALID")
            self.assertEqual(len(two_way_wacc_growth_grid()),3)
        def test_peer(self):
            for p in peers():
                self.assertGreater(p["ev_to_reported_revenue"],0)
                self.assertAlmostEqual(p["gaap_pe"]*p["gaap_eps"],p["price"])
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(TestWorkbench))
    if not result.wasSuccessful():raise SystemExit(1)


def launch_gui():
    try: import tkinter as tk
    except ImportError as e: raise SystemExit("Tkinter absent; use --summary or --export") from e
    win=tk.Tk();win.title("ORCL Project 1 | Analyst Workbench (illustrative)");win.geometry("1100x750")
    win.configure(bg="#101c2e")
    panel=tk.Frame(win,bg="#101c2e");panel.pack(fill="x",padx=12,pady=10)
    title=tk.Label(panel,text="ORACLE  |  PRO FORMA WORKBENCH",font=("Segoe UI",17,"bold"),fg="white",bg="#101c2e")
    title.pack(anchor="w")
    tk.Label(panel,text="Research-only; terminal WACC / reinvestment NOT independently validated; fiscal Aug31 balance proxy vs Oct19 market price",fg="#ffcf6e",bg="#101c2e",font=("Segoe UI",9)).pack(anchor="w")
    controls=tk.Frame(win,bg="#182c47");controls.pack(fill="x",padx=12,pady=(0,10))
    defs=[("Growth shift FY28-31 (pp)","growth_shift_pp",-2,2,.5,0),
          ("FY28 CapEx change (%)","fy28_capex_pct",-10,10,2,0),
          ("Gross margin shift (pp)","gross_margin_shift_pp",-1,1,.25,0),
          ("WACC (%)","wacc_pct",9.4,13.4,.2,11.4),
          ("Terminal growth (%)","terminal_growth_pct",1,4,.25,3),
          ("Extra FY32 CapEx ($m)","terminal_capex_delta",0,10000,2500,0)]
    slider_vars={}
    for j,(label,key,lo,hi,res,base) in enumerate(defs):
        f=tk.Frame(controls,bg="#182c47");f.grid(row=0,column=j,sticky="nsew",padx=9,pady=9)
        tk.Label(f,text=label,bg="#182c47",fg="white",font=("Segoe UI",9,"bold")).pack(anchor="w")
        v=tk.DoubleVar(value=base);slider_vars[key]=v
        tk.Scale(f,variable=v,from_=lo,to=hi,orient="horizontal",resolution=res,length=186,
                 bg="#182c47",fg="white",highlightthickness=0,troughcolor="#486384",
                 activebackground="#83a5da",command=lambda _x:refresh()).pack()
        controls.grid_columnconfigure(j,weight=1)
    status=tk.Label(win,text="",anchor="w",justify="left",font=("Consolas",11,"bold"),bg="#101c2e",fg="white")
    status.pack(fill="x",padx=14)
    tbox=tk.Text(win,wrap="none",font=("Consolas",10),bg="#f0f4fa",fg="#192b40",height=19)
    tbox.pack(fill="both",expand=True,padx=12,pady=8)
    def display(s):
        tbox.configure(state="normal");tbox.delete("1.0","end");tbox.insert("end",s);tbox.configure(state="disabled")
    def refresh():
        if not tbox.winfo_exists():return
        x=run_case(**{k:v.get() for k,v in slider_vars.items()})
        if x["status"]=="INVALID":
            status.config(text="INVALID -- model rejects inputs: "+x["failure"],fg="#ff7373")
            display("INCOHERENT ASSUMPTIONS: financing / accounting limitations.\n"+x["failure"]+"\nRestore base or change one driver.\nNO valuation reported for invalid state.")
            return
        status.config(text=f"PASS ({x['audited_checks']} independent checks) | Illustrative share: ${x['indicative_per_share']:,.2f} | Terminal share {x['terminal_share_pct']:.1f}% -- NOT investment-ready",fg="#a0f1bd")
        s="FY          Revenue      EBIT        CFO       CAPEX       FCFF      CASH     REVOLVER\n"
        for r in x["forecast"]:
            s+=f"{r['year']} {r['revenue']:>13,.0f} {r['ebit']:>10,.0f} {r['cash_from_operations']:>10,.0f} {r['capex']:>10,.0f} {r['fcff']:>10,.0f} {r['cash']:>9,.0f} {r['revolver']:>9,.0f}\n"
        s+="\nAug31 EV/equity bridge (USD m):\n"
        b=x['bridge']
        s+=f"Enterprise: {b['enterprise_value']:,.1f}; + eligible cash {b['plus_cash_in_bridge']:,.1f}; + investments {b['plus_marketable_securities']:,.1f}\n"
        s+=f"- notes {b['minus_senior_notes_and_borrowings']:,.1f}; - finance leases {b['minus_finance_leases']:,.1f}; - preferred {b['minus_preferred_claim']:,.1f}; - NCI {b['minus_noncontrolling_interests']:,.1f}\n"
        s+=f"Model equity {b['estimated_common_equity']:,.1f} / {b['shares_millions']:,.3f}m shares = ${x['indicative_per_share']:,.2f}\n"
        s+="\nForecast = Q2-Q4 FY27 stub + FY28-31. Costs, lease lives, WACC, terminal growth not independently certified.\n"
        s+="October 19 quoted price $129.59 is reference only; missing Sep-Oct stub prevents date-matched conclusion."
        display(s)
    buttons=tk.Frame(win,bg="#101c2e");buttons.pack(fill="x",padx=12,pady=8)
    def reset():
        for _,k,_,_,_,b in defs:slider_vars[k].set(b)
        refresh()
    def fail():
        r=model.project();r[0]["cash"]-=1000
        try: model.audit_independently(r)
        except ValueError as exc:
            status.config(text="DELIBERATE FAILURE CAUGHT (no model change saved)",fg="#ff7373")
            display("INTENTIONAL BROKEN BALANCE-SHEET TEST\n"+str(exc)+"\n\nPress Reset Base to recover.")
        else:
            status.config(text="CRITICAL: intentional failure was missed",fg="red")
    def show_sens():
        a=scenarios();s="ONE-DRIVER-AT-A-TIME, BASE RESTORED FOR EVERY TEST\n"
        for k,v in a.items():
            s+=f"{k:>28}: {v['status']:<9} " + (f"${v['value_per_share']:,.2f}/share" if v['value_per_share'] is not None else v['failure']) + "\n"
        display(s);status.config(text="Scenario table shown: failure rows are excluded, not given invented prices",fg="#ffcf6e")
    for title,cb in [("Reset base",reset),("Show one-way sensitivities",show_sens),("Demonstrate failed check",fail)]:
        tk.Button(buttons,text=title,command=cb,font=("Segoe UI",10,"bold"),padx=10,pady=5).pack(side="left",padx=5)
    refresh();win.mainloop()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ("summary","export","tests","demo-failure"):p.add_argument("--"+flag,action="store_true")
    a=p.parse_args()
    if a.tests:test_suite();return
    if a.demo_failure:
        r=model.project();r[0]["cash"]-=1000
        try:model.audit_independently(r)
        except ValueError as e:print("EXPECTED FAILURE CAUGHT:",e);return
        raise SystemExit("FAIL: broken accounting undetected")
    if a.export:
        path=ROOT/"output"/"visible_output.json";path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(report(),indent=2,allow_nan=False),encoding="utf-8")
        print("Saved",path);return
    if a.summary:
        x=report();b=x['base'];print("ORCL RESEARCH: WATCH/DEFER, NO INITIATION")
        print("Illustrative dollar/share",round(b['indicative_per_share'],2),"; terminal share",round(b['terminal_share_pct'],1),"%")
        for k,v in x['one_at_a_time_scenarios'].items(): print(k,v['status'],v['value_per_share'] if v['value_per_share'] is not None else v['failure'])
        return
    launch_gui()

if __name__=="__main__":main()
