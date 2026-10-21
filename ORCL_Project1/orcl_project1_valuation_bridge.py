"""Oracle Project 1 / Revision 4: illustrative FCFF DCF + common-equity bridge.

Requires the unchanged original and revisions 1-3 in this folder.

Run:
  py orcl_project1_valuation_bridge.py
  py orcl_project1_valuation_bridge.py --json > orcl_project1_valuation_revision4.json
  py orcl_project1_valuation_bridge.py --cash-policy total
  py orcl_project1_valuation_bridge.py --break-bridge

IMPORTANT: a diagnostic on the 2026-08-31 BALANCE-SHEET anchor, not a
tradeable 2026-08-31 price. The FY27 Q1 10-Q was published after that date.
Neither the WACC nor the long-run cash flow is verified or normalized. Do NOT
use the indicative value as a final investment recommendation. In particular,
this does NOT satisfy the human-authored AI-OFF locked operating-input test.

All amounts USD millions, shares millions, $/share. Standard library only.
"""
import argparse
import copy
import json
import math

import orcl_project1_post_q1_proforma as proforma
from orcl_project1_fcff import discount_cash_flows

RECORD_DATE = "2026-10-19"
FINANCIAL_STATEMENT_DATE = "2026-08-31"
STATEMENT_SOURCE = proforma.FILING
# Reading the 10-Q uses hindsight from its later public filing date. Do NOT
# call the statement anchor a contemporaneously available market valuation.
SOURCE_SHARE_COUNT = 3023.736  # cover, common shares outstanding Sep 7, 2026
TERMINAL_WARNING_THRESHOLD = .80  # alert threshold, not a value judgment
WACC_GRID = (.104, .114, .124)
G_GRID = (.02, .03, .04)


def finite_positive(name, value, allow_zero=False):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name}: finite number required")
    if value < 0 if allow_zero else value <= 0:
        raise ValueError(f"{name}: {'nonnegative' if allow_zero else 'positive'} number required")
    return float(value)


def source_bridge(opening=None):
    """Build the *reported-balance* starting bridge, without future issuance.

    Debt = separate reported notes and finance leases. Operating-lease
    liabilities remain operating: lease operating expenses remain in EBIT.
    Customer prepayments are provisionally in operating working capital and
    cannot also be subtracted again as financial debt.
    """
    o = proforma.OPEN if opening is None else opening
    proforma.opening_checks()  # ensures original historical amounts, too
    if abs(o["notes_borrowings"] - (7625 + 117712)) > 1e-6:
        raise ValueError("Reported current+noncurrent notes bridge is broken")
    if abs(o["finance_lease_liabilities"] - (749 + 8436)) > 1e-6:
        raise ValueError("Reported finance-lease bridge is broken")
    if abs(o["operating_lease_liabilities"] - (4027 + 30594)) > 1e-6:
        raise ValueError("Reported operating-lease classification is broken")
    if abs(o["deferred_revenues"] - (14686 + 16103)) > 1e-6:
        raise ValueError("Deferred revenues may not disappear or become double-counted debt")
    if abs(o["restricted_cash_in_prepaid"] - 2565) > 1e-6:
        raise ValueError("Restricted cash must be separately identified")
    if abs(o["cash"]-36369) > 1e-6:
        raise ValueError("Opening unrestricted cash no longer matches 10-Q")
    if abs(o["marketable_securities"]-708) > 1e-6:
        raise ValueError("Opening marketable securities no longer match 10-Q")
    if abs(o["preferred_equity"]-4954) > 1e-6 or abs(o["noncontrolling_interests"]-424)>1e-6:
        raise ValueError("Preferred equity or minority interest source link broken")
    assets, liabilities, equity = proforma.totals(o)
    proforma.assert_close("bridge reported assets", assets, 303259)
    proforma.assert_close("bridge reported balance", assets, liabilities+equity)
    return {
        "unrestricted_cash": o["cash"],
        "marketable_securities": o["marketable_securities"],
        "restricted_cash_EXCLUDED": o["restricted_cash_in_prepaid"],
        "senior_notes_and_borrowings": o["notes_borrowings"],
        "finance_lease_liabilities": o["finance_lease_liabilities"],
        "operating_lease_liabilities_NOT_FINANCIAL_DEBT": o["operating_lease_liabilities"],
        "customer_deferred_revenues_NOT_FINANCIAL_DEBT": o["deferred_revenues"],
        "preferred_equity_claim": o["preferred_equity"],
        "noncontrolling_interests": o["noncontrolling_interests"],
        "cover_common_shares_millions": SOURCE_SHARE_COUNT,
        "reported_assets": assets,
        "reported_liabilities": liabilities,
        "reported_equity": equity,
    }


def common_equity_bridge(enterprise_value, cash_policy="excess",
                         preferred_policy="outstanding_claim", minimum_cash=None,
                         opening=None):
    """Demonstrate mutually exclusive treatments of the convertible preferred.

    - outstanding_claim: subtract book preferred ($4,954m) and divide by the
      September 7 outstanding 3,023.736m common shares; excludes future SBC.
    - if_converted: do not subtract preferred, but add the ORIGINAL MODEL'S
      speculative 31.238m conversion shares. This is a diagnostic alternative,
      NOT a verified 2029 share count or fair-value treatment.

    A reserved operational cash amount is NOT 'excess cash' for the enterprise
    bridge. Both policies reported to show dependency on classification.
    """
    finite_positive("enterprise value", enterprise_value, allow_zero=True)
    b = source_bridge(opening)
    floor = (proforma.BASE["minimum_cash"] if minimum_cash is None else minimum_cash)
    finite_positive("minimum cash reserve", floor, allow_zero=True)
    if cash_policy not in ("excess", "total"):
        raise ValueError("cash_policy must be excess or total")
    if preferred_policy not in ("outstanding_claim", "if_converted"):
        raise ValueError("Invalid preferred conversion policy")
    # No floor reserve is added twice; required operational cash is kept in EV.
    cash_added = (max(0., b["unrestricted_cash"]-floor)
                  if cash_policy == "excess" else b["unrestricted_cash"])
    pref_claim = b["preferred_equity_claim"] if preferred_policy == "outstanding_claim" else 0.
    conversion_shares = (0. if preferred_policy == "outstanding_claim" else
                         proforma.BASE["preferred_conversion_shares"])
    shares = b["cover_common_shares_millions"] + conversion_shares
    deductions = (b["senior_notes_and_borrowings"] + b["finance_lease_liabilities"]
                  + b["noncontrolling_interests"] + pref_claim)
    common_equity = (enterprise_value + cash_added
                     + b["marketable_securities"] - deductions)
    check = (common_equity + deductions - enterprise_value - cash_added
             - b["marketable_securities"])
    if abs(check)>1e-6: raise ValueError("Broken EV-to-common bridge")
    if shares<=0: raise ValueError("Nonpositive shares")
    return {
        "cash_policy": cash_policy, "preferred_policy": preferred_policy,
        "minimum_operating_cash_reserve": floor,
        "enterprise_value": enterprise_value,
        "plus_cash_in_bridge": cash_added,
        "plus_marketable_securities": b["marketable_securities"],
        "minus_senior_notes_and_borrowings": b["senior_notes_and_borrowings"],
        "minus_finance_leases": b["finance_lease_liabilities"],
        "minus_preferred_claim": pref_claim,
        "minus_noncontrolling_interests": b["noncontrolling_interests"],
        "NOT_SUBTRACTED_lease_operating": b["operating_lease_liabilities_NOT_FINANCIAL_DEBT"],
        "NOT_SUBTRACTED_customer_funding": b["customer_deferred_revenues_NOT_FINANCIAL_DEBT"],
        "EXCLUDED_restricted_cash": b["restricted_cash_EXCLUDED"],
        "estimated_common_equity": common_equity,
        "shares_millions": shares,
        "indicative_dollars_per_share_NOT_FINAL": common_equity/shares,
        "bridge_gap": check,
    }


def discounted_case(rows, wacc, growth, cash_policy="excess",
                    preferred_policy="outstanding_claim"):
    """Signed DCF of the existing *unchanged* operating forecast.

    The legacy terminal rule simply grows FY2031 FCFF into FY2032, WITHOUT
    independent capex, leases or working-capital normalization; unverified.
    """
    finite_positive("WACC", wacc)
    finite_positive("terminal growth", growth, allow_zero=True)
    if wacc<=growth: raise ValueError("WACC must be greater than terminal growth")
    fcff = [r["fcff"] for r in rows]
    future_times = [r["time_years_from_2026_08_31"] for r in rows]
    if fcff[-1]<=0: raise ValueError("Positive final-year FCFF required for simple terminal rule")
    terminal_fcff = fcff[-1]*(1+growth)
    dcf = discount_cash_flows(fcff, future_times, wacc, terminal_fcff, growth)
    ev = dcf["enterprise_value"]
    if ev < 0: raise ValueError("Negative EV under the illustrative DCF; do not form price")
    bridge = common_equity_bridge(ev, cash_policy, preferred_policy)
    return {"wacc": wacc, "terminal_growth": growth,
            "terminal_rule": "UNVERIFIED: FY2031 signed FCFF × (1+terminal_growth)",
            "dcf": dcf, "equity_bridge": bridge,
            "terminal_share_alert": dcf["terminal_value_share"] > TERMINAL_WARNING_THRESHOLD,
            "used_signed_negative_cash_flows": any(x<0 for x in fcff)}


def wacc_growth_grid(rows, cash_policy="excess", preferred_policy="outstanding_claim"):
    """WACC/g sensitivity required by rubric, not locked OPERATING-input test."""
    return [
        {"wacc": w, "terminal_growth": g,
         "indicative_dollars_per_share_NOT_FINAL": discounted_case(
             rows,w,g,cash_policy,preferred_policy)["equity_bridge"]
             ["indicative_dollars_per_share_NOT_FINAL"]}
        for w in WACC_GRID for g in G_GRID
    ]


def maths_tests(rows, cash_policy="excess"):
    """Mathematical boundaries only: NOT a student's AI-off input prediction."""
    out=[]
    for w,g in [(0.10, 0.10), (0.03,0.04)]:
        try: discounted_case(rows,w,g,cash_policy)
        except ValueError: out.append({"check":f"reject WACC {w:g} <= g {g:g}","status":"PASS"})
        else: raise ValueError("DCF boundary test did not reject")
    base=discounted_case(rows,.114,.03,cash_policy)
    up=discounted_case(rows,.124,.03,cash_policy)
    down=discounted_case(rows,.104,.03,cash_policy)
    if not (down["dcf"]["enterprise_value"] > base["dcf"]["enterprise_value"] >
            up["dcf"]["enterprise_value"]):
        raise ValueError("Illustrative WACC directional response not as expected")
    out.append({"check":"WACC monotonic EV on legacy base","status":"PASS"})
    low_g=discounted_case(rows,.114,.02,cash_policy)
    high_g=discounted_case(rows,.114,.04,cash_policy)
    if not (low_g["dcf"]["enterprise_value"] < base["dcf"]["enterprise_value"] <
            high_g["dcf"]["enterprise_value"]):
        raise ValueError("Illustrative terminal-growth directional response incorrect")
    out.append({"check":"terminal-growth monotonic EV on legacy base","status":"PASS"})
    for mode in ["excess", "total"]:
        item=discounted_case(rows,.114,.03,mode)
        if abs(item["equity_bridge"]["bridge_gap"])>1e-6:
            raise ValueError("EV/common bridge did not reconcile")
    out.append({"check":"both cash-policy EV/equity bridges reconcile","status":"PASS"})
    # Undiscounted negative early years must be retained (not zero-clipped).
    if not (rows[0]["fcff"]<0 and rows[1]["fcff"]<0):
        raise ValueError("Signed first-two-year FCFF path changed")
    out.append({"check":"negative FY27/FY28 FCFF retained","status":"PASS"})
    return out


def build_result(cash_policy="excess"):
    rows = proforma.project()
    independent = proforma.audit_independently(rows)
    bridge = source_bridge()
    base = discounted_case(rows,.114,.03,cash_policy)
    conversion = discounted_case(rows,.114,.03,cash_policy,"if_converted")
    grid=wacc_growth_grid(rows,cash_policy)
    tests=maths_tests(rows,cash_policy)
    return {
        "status":"INTERMEDIATE_DIAGNOSTIC_NOT_A_FINAL_FINANCIAL_VALUATION",
        "revision":4, "date_prepared":RECORD_DATE,
        "balance_sheet_anchor":FINANCIAL_STATEMENT_DATE,
        "NOT_contemporaneous_value_as_of":FINANCIAL_STATEMENT_DATE,
        "intended_committee_price_date_not_yet_reconciled":"2026-09-24",
        "units":"USD millions; shares millions; prices USD/share",
        "filing_source":STATEMENT_SOURCE,
        "model_source":"orcl_project1_post_q1_proforma.py (revision 3, unmodified)",
        "historical_evidence_bridge":bridge,
        "forecast_audited_check_count":independent,
        "legacy_assumptions_NOT independently validated":{"WACC":.114,"terminal_growth":.03},
        "base_diagnostic":base,
        "alternate_preferred_if_converted_UNVERIFIED":conversion["equity_bridge"],
        "alternate_cash_policy_total":discounted_case(rows,.114,.03,"total")["equity_bridge"],
        "wacc_growth_grid_NOT_operating_test":grid,
        "mathematical_tests":tests,
        "terminal_dependency_pct":base["dcf"]["terminal_value_share"]*100,
        "final_value_per_share":None,
        "recommendation":None,
        "student_AI_off_operating_prediction_submitted":False,
        "new_operating_input_sensitivity_executed":False,
        "material_open_items":[
            "WACC 11.4% and g 3% are unverified legacy Lab06 values, NOT approved committee inputs.",
            "Terminal FCFF is mechanically grown from FY2031; build maintenance/growth capex, future lease, SBC and deferred-revenue schedules first.",
            "Lease operating charges vs debt classification need independently reviewed cash flow consistency.",
            "Preferred if-converted scenario is hypothetical; verify conversion share economics and future dilution.",
            "Operating cash reserve (default $10B) is an analyst choice, not a verified excess cash claim.",
            "Aug31 balance sheet was not public on Aug31: pick a disclosed post-filing committee date and handle the intervening stub.",
            "Credible Oracle causal scenarios, market quote with matching date and comps/reverse DCF are still required.",
            "Student must independently write, timestamp and freeze an AI-off operating-input prediction BEFORE the required changed-input run.",
        ],
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--cash-policy", choices=["excess","total"], default="excess")
    ap.add_argument("--break-bridge",action="store_true",
                    help="Expected failure: deliberately corrupt restricted cash / cash")
    args=ap.parse_args()
    if args.break_bridge:
        broken=copy.deepcopy(proforma.OPEN)
        broken["finance_lease_liabilities"] += 1
        source_bridge(broken)  # must raise before any valuation
        raise AssertionError("Unreachable -- source guard failed")
    output=build_result(args.cash_policy)
    if args.json:
        print(json.dumps(output, indent=2, allow_nan=False))
        return
    base=output["base_diagnostic"]
    print("ORCL PROJECT 1 - REVISION 4 / ILLUSTRATIVE EV-TO-COMMON BRIDGE")
    print("NOT FINAL; not a contemporaneous August 31 tradable valuation")
    print("Derived from unchanged post-Q1 five-year forecast; USD millions")
    print("Historical Aug31 balance source:", output["filing_source"])
    print("Signed PV of FY2027-remain through FY2031 FCFF: "
          f"{base['dcf']['pv_explicit']:,.2f}")
    print(f"PV of UNVERIFIED terminal value: {base['dcf']['pv_terminal']:,.2f}")
    print(f"Illustrative enterprise value: {base['dcf']['enterprise_value']:,.2f}")
    e=base["equity_bridge"]
    print("EV-to-common: +eligible cash "
          f"{e['plus_cash_in_bridge']:,.2f}; +marketables {e['plus_marketable_securities']:,.2f}; "
          f"-notes {e['minus_senior_notes_and_borrowings']:,.2f}; "
          f"-finance leases {e['minus_finance_leases']:,.2f}; "
          f"-preferred {e['minus_preferred_claim']:,.2f}; "
          f"-NCI {e['minus_noncontrolling_interests']:,.2f}")
    print(f"ILLUSTRATIVE common equity {e['estimated_common_equity']:,.2f}; "
          f"shares {e['shares_millions']:,.3f}m")
    print(f"DIAGNOSTIC ONLY ${e['indicative_dollars_per_share_NOT_FINAL']:,.2f}/share")
    print(f"Terminal concentration {output['terminal_dependency_pct']:.1f}% of EV: "
          "HIGH (flagged if >80%)")
    print("WACC/g grid: DIAGNOSTIC $/share; no operating-input changes")
    print("WACC \\ g   "+"  ".join(f"{g:>8.1%}" for g in G_GRID))
    for w in WACC_GRID:
        points=[x for x in output["wacc_growth_grid_NOT_operating_test"] if x["wacc"]==w]
        print(f"{w:>8.1%}   "+"  ".join(f"{x['indicative_dollars_per_share_NOT_FINAL']:8.2f}" for x in points))
    print(f"PASS: {output['forecast_audited_check_count']} pro-forma checks; "
          f"{len(output['mathematical_tests'])} supplementary DCF and bridge checks")
    print("NO student locked operating-input sensitivity performed. NO final recommendation.")


if __name__ == "__main__":
    main()
