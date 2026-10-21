"""FIN 439 ORCL Project 1 -- Revision 3, post-Q1 pro-forma WORKING DRAFT.

Run beside existing revisions:
    py orcl_project1_post_q1_proforma.py
    py orcl_project1_post_q1_proforma.py --json > orcl_project1_post_q1_proforma_revision3.json

USD millions. Opening = Oracle's reported August 31, 2026 balance sheet.
FY2027 forecast = Q2-Q4 ONLY, with separately reported Q1 actuals. FY2028-31
are full-year forecasts. This is an AUGUST 31 diagnostic, NOT a Sep24 valuation:
no unsupported Sep1-Sep24 stub, final common share value, or recommendation.

This MODEL IS PROVISIONAL: assumes certain historically disclosed lease balances,
other liabilities and restricted cash remain fixed; uses original user-specified
pro-forma annual revenue/capex/deferred revenue targets. It is not GAAP guidance.

Evidence: Oracle FY27 Q1 10-Q (period ended Aug 31, filed Sep 2026), pp 1-2,
5, notes 5 (deferred revenues) and 6 (leases), 7 (ATM):
https://www.sec.gov/Archives/edgar/data/1341439/000119312526389274/orcl-20260831.htm
Original assumptions: orcl_proforma_EthanHeeres.py (not modified).
"""
import argparse
import copy
import json
import math

import orcl_proforma_EthanHeeres as original
import orcl_project1_q1_bridge as bridge
from orcl_project1_fcff import discount_cash_flows

REPORT_DATE = "2026-10-19"
VALUATION_ANCHOR = "2026-08-31"  # Future cash flows from Sep 1 onward, not Sep 24
INTENDED_FINAL_AS_OF = "2026-09-24"  # Not yet supported without an actual/forecast stub
FILING = bridge.FILING_URL
DAYS = {2027: 0.75, 2028: 1.75, 2029: 2.75, 2030: 3.75, 2031: 4.75}
YEARS = [2027, 2028, 2029, 2030, 2031]
TOL = 1e-6

# Values in USD millions; these splits MUST sum to the 10-Q line items.
# Explicit components prevent financing/customer-contract/leases being counted twice.
OPEN = {
    "revenue_annual_anchor": original.HISTORY[2026]["revenue"],
    "cash": 36369.0, "marketable_securities": 708.0,
    "receivables": 11394.0, "prepaid_operating": 7159.0 - 2565.0,
    "restricted_cash_in_prepaid": 2565.0,
    "ppe": 127845.0, "operating_lease_rou_assets": 33967.0,
    "goodwill": 62267.0, "deferred_tax_assets": 11625.0,
    "intangibles": 3027.0,  # Q1 MD&A confirms disclosed net acquired intangible assets
    "other_nc_assets": 11925.0 - 3027.0,
    "notes_borrowings": 7625.0 + 117712.0,
    "finance_lease_liabilities": 749.0 + 8436.0,
    "revolver": 0.0,
    "accounts_payable": 11063.0,
    "accrued_compensation": 1760.0,
    "deferred_revenues": 14686.0 + 16103.0,
    "other_current_liabilities_residual": 12380.0 - 4027.0 - 749.0,
    "taxes_payable": 12060.0,
    "operating_lease_liabilities": 4027.0 + 30594.0,
    "other_nc_liabilities_residual": 28183.0 - 16103.0 - 8436.0,
    "preferred_equity": 4954.0,
    "noncontrolling_interests": 424.0,
    "common_parent_equity": 64319.0 - 1114.0 - 1387.0,
}

# User's previous forecast retained as the ANCHOR, not retroactively labelled guidance.
# First-year amounts in the schedule are future 9-month flows, NOT full FY2027.
BASE = {
    "annual_revenue_fy27": 90000.0,
    "annual_revenue_growth_after_2027": [0.25, 0.20, 0.15, 0.10],
    "fy27_annual_ebit_anchor": original.project()[0]["operating_income"],
    "gross_margin_before_depreciation": [0.75] * 4,
    "sga_to_gross_profit": [0.21, 0.20, 0.20, 0.20],
    "rd_to_revenue": [0.115, 0.11, 0.105, 0.10],
    "depreciation_to_opening_ppe_annual": 0.12,
    "amortization_future": [731 - 202, 694, 620, 582, 377],
    "restructuring_after_fy27": [750.0, 500.0, 0.0, 0.0],
    "future_capex": [92500.0 - 28499.0, 70000.0, 50000.0, 40000.0, 40000.0],
    "receivables_to_revenue": original.ASSUMPTIONS["receivables_to_revenue"],
    "prepaid_operating_to_revenue": original.ASSUMPTIONS["prepaid_to_revenue"],
    # Annual deferred revenue movement $20B FY27 less Q1 $15.36B CFO changes.
    # Simplifying: treat these projected changes as cash; not separate financing.
    "future_cash_change_in_deferred_revenues": [20000.0 - 11363.0 - 3997.0,
                                                15000.0, 5000.0, -5000.0, 0.0],
    # Financing remains an assumption, not a 10-Q disclosed forecast.
    # Original FY27 principal $7,210 less Q1 actual senior debt $4,202.
    # Finance leases separately HELD FIXED because a full lease schedule is pending.
    "new_notes_borrowings": [20000.0, 25000.0, 0.0, 0.0, 0.0],
    "notes_repayments": [7210.0 - 4202.0, 10145.0, 5500.0, 7250.0, 9750.0],
    "debt_rate": 0.045,
    "revolver_rate": 0.065,
    "tax_rate": 0.18,
    "minimum_cash": 10000.0,
    "revolver_limit": 10000.0,
    "future_common_equity_issuance": [0.0] * 5,  # Q1 ATM already in OPEN.
    "common_shares_millions": 3024.0,  # Aug31 10-Q rounded outstanding
    "annual_dividend_per_common_share": 2.0,
    "preferred_dividends_future": [325.0 - 81.0, 325.0, 203.125, 0.0, 0.0],
    "preferred_conversion_shares": original.ASSUMPTIONS["preferred_conversion_shares"],
    "test_wacc_unverified": 0.114,  # Preserved Lab06 illustrative assumption
    "test_terminal_growth_unverified": 0.03,
}

ASSET_FIELDS = ("cash", "marketable_securities", "receivables", "prepaid_operating",
                "restricted_cash_in_prepaid", "ppe", "operating_lease_rou_assets",
                "goodwill", "deferred_tax_assets", "intangibles", "other_nc_assets")
LIABILITY_FIELDS = ("notes_borrowings", "finance_lease_liabilities", "revolver",
                    "accounts_payable", "accrued_compensation", "deferred_revenues",
                    "other_current_liabilities_residual", "taxes_payable",
                    "operating_lease_liabilities", "other_nc_liabilities_residual")
EQUITY_FIELDS = ("preferred_equity", "noncontrolling_interests", "common_parent_equity")


def totals(r):
    assets = sum(r[x] for x in ASSET_FIELDS)
    liabilities = sum(r[x] for x in LIABILITY_FIELDS)
    equity = sum(r[x] for x in EQUITY_FIELDS)
    return assets, liabilities, equity


def assert_close(name, actual, expected):
    if not math.isfinite(actual) or abs(actual - expected) > TOL:
        raise ValueError(f"{name}: {actual:,.5f} vs expected {expected:,.5f}")


def opening_checks():
    a, l, e = totals(OPEN)
    for label, observed, expected in (
        ("Aug31 assets to filing", a, 303259),
        ("Aug31 liabilities to filing", l, 303259 - 67196),
        ("Aug31 equity to filing", e, 67196),
        ("Aug31 accounting equation", a, l + e),
        ("current balance line split", 7604 + 4027 + 749, 12380),
        ("noncurrent balance line split", 3644 + 16103 + 8436, 28183),
        ("restricted cash + unrestricted cash", 2565 + 36369, 38934),
    ):
        assert_close(label, observed, expected)
    return 7


def project(a=None):
    """Return five prospective modeled periods, FY27 remaining + FY28-FY31.

    Revenue and cash flow are forecast, not actual. Retain signed FCFF. Debt and
    equity issuance are only POST-Aug31. No implicit plug to equity/other assets.
    """
    a = copy.deepcopy(BASE if a is None else a)
    opening_checks()
    prior = dict(OPEN)
    out = []
    fy27_total = a["annual_revenue_fy27"]
    original_q1 = bridge.Q1_ACTUALS
    for i, year in enumerate(YEARS):
        t = 0.75 if i == 0 else 1.0
        fy_revenue = (fy27_total if i == 0 else
                      out[-1]["full_fiscal_year_revenue"] *
                      (1 + a["annual_revenue_growth_after_2027"][i-1]))
        revenue = fy_revenue - original_q1["revenue"] if i == 0 else fy_revenue
        if revenue <= 0:
            raise ValueError("Nonpositive projected revenue")
        depreciation = prior["ppe"] * a["depreciation_to_opening_ppe_annual"] * t
        amort = a["amortization_future"][i]
        if i == 0:
            # Explicit, reviewable annual-target-minus-reported-Q1 construction.
            ebit = a["fy27_annual_ebit_anchor"] - original_q1["operating_income"]
            restructuring = None  # EBIT total embedded in original anchor
            operating_costs = revenue - ebit
            if operating_costs < depreciation + amort:
                raise ValueError("FY27 implied cash operating costs impossible")
        else:
            pre_da_gp = revenue * a["gross_margin_before_depreciation"][i-1]
            gp = pre_da_gp - depreciation
            sga = gp * a["sga_to_gross_profit"][i-1]
            rd = revenue * a["rd_to_revenue"][i-1]
            restructuring = a["restructuring_after_fy27"][i-1]
            ebit = gp - sga - rd - amort - restructuring
            operating_costs = revenue - ebit
        debt_base = prior["notes_borrowings"] + prior["finance_lease_liabilities"]
        interest = debt_base * a["debt_rate"] * t + prior["revolver"] * a["revolver_rate"] * t
        # No repeat of original speculative 5% customer financing accretion;
        # disclosed Q1 interest on these customer prepayments was immaterial.
        pretax = ebit - interest
        taxes = max(pretax, 0.0) * a["tax_rate"]
        net_income = pretax - taxes
        capex = a["future_capex"][i]
        cash_advances = a["future_cash_change_in_deferred_revenues"][i]
        # Prior annual revenue (rather than 9-month flow) is used for working
        # capital estimates. The August quarter was the reported opening state.
        rec = fy_revenue * a["receivables_to_revenue"]
        prepay = fy_revenue * a["prepaid_operating_to_revenue"]
        delta_rec = rec - prior["receivables"]
        delta_pre = prepay - prior["prepaid_operating"]
        # Hold AP/comp/taxes/leases/other historical line items at stated level.
        # Note that freezing leases is NOT a forecast of actual lease obligations.
        cfo = net_income + depreciation + amort - delta_rec - delta_pre + cash_advances
        new_notes = a["new_notes_borrowings"][i]
        repay_notes = a["notes_repayments"][i]
        new_common_equity = a["future_common_equity_issuance"][i]
        # Preserve the original student's assumed FY2029 preferred conversion.
        # Transfer preferred carrying amount within equity WITHOUT cash proceeds.
        shares = (a["common_shares_millions"]+
                  (a["preferred_conversion_shares"] if year >= 2029 else 0.0))
        common_divs = shares * a["annual_dividend_per_common_share"] * t
        preferred_after = 0.0 if year >= 2029 else prior["preferred_equity"]
        conversion_book_amount = prior["preferred_equity"] - preferred_after
        preferred_divs = a["preferred_dividends_future"][i]
        cash_pre_revolver = (prior["cash"] + cfo - capex + new_notes - repay_notes
                             + new_common_equity - common_divs - preferred_divs)
        draw = (min(a["minimum_cash"]-cash_pre_revolver,
                    max(0, a["revolver_limit"]-prior["revolver"]))
                if cash_pre_revolver < a["minimum_cash"] else
                -min(prior["revolver"], cash_pre_revolver-a["minimum_cash"]))
        change_financing = (new_notes - repay_notes + new_common_equity - common_divs
                            - preferred_divs + draw)
        cash_change = cfo - capex + change_financing
        r = dict(prior)
        r.update({
            "year": year, "period": "Q2-Q4 remaining 9 months" if i == 0 else "full FY",
            "time_years_from_2026_08_31": DAYS[year],
            "full_fiscal_year_revenue": fy_revenue,
            "revenue": revenue, "operating_costs_including_da": operating_costs,
            "ebit": ebit, "depreciation": depreciation, "amortization": amort,
            "restructuring": restructuring, "interest": interest,
            "pretax": pretax, "taxes": taxes, "net_income": net_income,
            "capex": capex, "cash_advances": cash_advances,
            "receivables": rec, "prepaid_operating": prepay,
            "ppe": prior["ppe"] + capex - depreciation,
            "intangibles": prior["intangibles"] - amort,
            "deferred_revenues": prior["deferred_revenues"] + cash_advances,
            "notes_borrowings": prior["notes_borrowings"] + new_notes - repay_notes,
            "new_notes": new_notes, "repay_notes": repay_notes,
            "new_common_equity": new_common_equity,
            "shares": shares, "preferred_equity": preferred_after,
            "preferred_conversion_book_transfer": conversion_book_amount,
            "common_divs": common_divs, "preferred_divs": preferred_divs,
            "common_parent_equity": prior["common_parent_equity"] + net_income
                                    + new_common_equity - common_divs - preferred_divs
                                    + conversion_book_amount,
            "cash_from_operations": cfo, "cash_from_investing": -capex,
            "cash_from_financing": change_financing,
            "change_cash": cash_change,
            "cash": prior["cash"] + cash_change,
            "revolver_draw": draw, "revolver": prior["revolver"] + draw,
            "cash_pre_revolver": cash_pre_revolver,
        })
        r["fcff"] = (ebit - max(ebit,0)*a["tax_rate"] + depreciation + amort
                    - delta_rec - delta_pre + cash_advances - capex)
        r["fcff_from_cfo"] = (cfo - capex + interest -
                               (max(ebit,0)-max(pretax,0))*a["tax_rate"])
        r["balance_gap"] = totals(r)[0] - totals(r)[1] - totals(r)[2]
        r["cash_flow_gap"] = (r["cash"] - prior["cash"] - cfo + capex - change_financing)
        r["fcff_gap"] = r["fcff"]-r["fcff_from_cfo"]
        r["ppe_gap"] = r["ppe"]-prior["ppe"]-capex+depreciation
        r["deferred_revenue_gap"] = r["deferred_revenues"]-prior["deferred_revenues"]-cash_advances
        r["debt_gap"] = r["notes_borrowings"]-prior["notes_borrowings"]-new_notes+repay_notes
        r["equity_gap"] = (r["common_parent_equity"]-prior["common_parent_equity"]
                           -net_income-new_common_equity+common_divs+preferred_divs
                           -conversion_book_amount)
        r["cash_floor_gap"] = min(0, r["cash"]-a["minimum_cash"])
        for label in ("balance_gap", "cash_flow_gap", "fcff_gap", "ppe_gap",
                      "deferred_revenue_gap", "debt_gap", "equity_gap", "cash_floor_gap"):
            assert_close(f"FY{year} {label}", r[label], 0.0)
        if r["revolver"] > a["revolver_limit"] + TOL or r["revolver"] < -TOL:
            raise ValueError(f"FY{year} revolver unavailable")
        for key in ("cash", "receivables", "prepaid_operating", "ppe", "deferred_revenues",
                    "notes_borrowings", "intangibles", "other_nc_assets"):
            if r[key] < 0:
                raise ValueError(f"FY{year} negative {key}")
        out.append(r)
        prior = r
    return out


def audit_independently(rows, a=BASE):
    """Recalculate critical links from raw fields; ignores stored gap summaries.

    Useful for a deliberate broken-input demo: a user cannot pass this audit
    by leaving stale PASS flags after mutating a row.
    """
    opening_checks()
    previous = OPEN
    for r in rows:
        year = r["year"]
        assets, liabilities, equity = totals(r)
        assert_close(f"FY{year} balance sheet", assets, liabilities+equity)
        assert_close(f"FY{year} cash and cashflow",
                     r["cash"]-previous["cash"],
                     r["cash_from_operations"]+r["cash_from_investing"]+r["cash_from_financing"])
        assert_close(f"FY{year} cash flow components",
                     r["cash_from_financing"],
                     r["new_notes"]-r["repay_notes"]+r["new_common_equity"]
                     -r["common_divs"]-r["preferred_divs"]+r["revolver_draw"])
        assert_close(f"FY{year} FCFF from CFO", r["fcff"], r["fcff_from_cfo"])
        assert_close(f"FY{year} PP&E",
                     r["ppe"], previous["ppe"]+r["capex"]-r["depreciation"])
        assert_close(f"FY{year} net debt",
                     r["notes_borrowings"],
                     previous["notes_borrowings"]+r["new_notes"]-r["repay_notes"])
        assert_close(f"FY{year} deferred revenues",
                     r["deferred_revenues"], previous["deferred_revenues"]+r["cash_advances"])
        assert_close(f"FY{year} preferred conversion transfer",
                     r["preferred_conversion_book_transfer"],
                     previous["preferred_equity"]-r["preferred_equity"])
        assert_close(f"FY{year} equity",
                     r["common_parent_equity"], previous["common_parent_equity"]
                     +r["net_income"]+r["new_common_equity"]-r["common_divs"]-r["preferred_divs"]
                     +r["preferred_conversion_book_transfer"])
        if r["cash"] < a["minimum_cash"]-TOL:
            raise ValueError(f"FY{year} cash below minimum despite funding policy")
        if not (-TOL <= r["revolver"] <= a["revolver_limit"]+TOL):
            raise ValueError(f"FY{year} revolver exceeds capacity")
        previous = r
    return 7 + 9*len(rows)


def build_result():
    rows = project()
    independent_checks = audit_independently(rows)
    # A functioning, SIGNED, numeric DCF core. Terminal FCFF is provisionally
    # straight-grown from FY2031; this is NOT yet a justified terminal policy.
    w, g = BASE["test_wacc_unverified"], BASE["test_terminal_growth_unverified"]
    dcf = discount_cash_flows([r["fcff"] for r in rows],
                              [r["time_years_from_2026_08_31"] for r in rows],
                              w, rows[-1]["fcff"] * (1+g), g)
    return {
        "status": "INTERMEDIATE_WORKING_PRO_FORMA_NOT_INVESTMENT_READY",
        "revision": 3, "report_date": REPORT_DATE,
        "model_anchor": VALUATION_ANCHOR,
        "intended_final_valuation_as_of": INTENDED_FINAL_AS_OF,
        "units": "USD millions; shares in millions",
        "evidence": {"q1_10q": FILING, "original_lab": "orcl_proforma_EthanHeeres.py"},
        "original_fy2027_q1_actuals_not_forecast": bridge.Q1_ACTUALS,
        "opening_balance_as_reported_aug31": OPEN,
        "opening_balanced_check_count": opening_checks(),
        "independent_total_accounting_checks": independent_checks,
        "original_student_anchors_and_explicit_revisions": BASE,
        "forecast_periods": rows,
        "fy2027_full_year_revenue_implied": rows[0]["revenue"] + bridge.Q1_ACTUALS["revenue"],
        "fy2027_full_year_ebit_implied": rows[0]["ebit"] + bridge.Q1_ACTUALS["operating_income"],
        "fy2027_full_year_capex_implied": rows[0]["capex"] + bridge.Q1_ACTUALS["capital_expenditures"],
        "q1_atm_proceeds_recognized_in_opening_only": 19909,
        "post_aug31_common_equity_issuance": [r["new_common_equity"] for r in rows],
        "financing_customer_advances_in_operating_working_capital_only": True,
        "experimental_signed_dcf_engine_AUG31_only_NOT_final": dcf,
        "value_per_share": None,
        "committee_decision": None,
        "new_human_changed_input_test_performed": False,
        "new_ai_off_prediction_substituted": False,
        "checks": {
            "opening_reported_balance_splits": "PASS (7 checks)",
            "each_period_balance_cash_flow_fcff_debt_ppe_equity_and_liquidity": "PASS",
            "fresh_independent_audit": "PASS (52 independent checks)",
            "unrestricted_cash_vs_restricted_cash": "PASS",
            "FY27_Q1_not_double_counted": "PASS (structural)",
            "preferred_conversion_noncash_equity_transfer": "PASS (original assumption, year FY2029)",
            "FCFF_negative_values_preserved": "PASS (signed cash flows)",
        },
        "material_issues_remaining": [
            "Build a documented Sep1-Sep24 stub or formally move the committee valuation date to Aug31.",
            "Replace original FY27 residual EBIT anchor with independent prospective operating assumptions; test expense line allocations.",
            "Build finance and operating lease cash flows and ROU asset roll-forwards; 10-Q Note 6 identifies $288B uncommenced lease commitments.",
            "Separate customer prepayments with significant financing component from ordinary recurring deferred revenues; validate settlement cash flows and interest.",
            "Determine credible revenue/capex/customer-prepayment scenarios and financing stress: Q1 already reported, not repeated.",
            "Forecast currently treats future stock-based compensation as cash-settled rather than adding back noncash SBC and modeling new share dilution.",
            "Normalize terminal FCFF reinvestment. Unverified Lab06 WACC and 3% growth are diagnostic placeholders ONLY.",
            "Confirm enterprise-to-common equity bridge, restricted cash, finance leases, FY2029 preferred conversion timing and diluted current share count.",
            "Obtain your own AI-off directional prediction and timestamp BEFORE any changed operating-input experiment.",
            "Then add causal low/base/high cases, reverse DCF, source-checked comps and adjustable controls.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--break-balance", action="store_true",
                        help="Deliberate failure demonstration; expected ValueError")
    parser.add_argument("--break-cash-flow", action="store_true",
                        help="Deliberate cashflow failure; expected ValueError")
    args = parser.parse_args()
    out = build_result()
    if args.break_balance:
        out["forecast_periods"][0]["cash"] -= 1000
        audit_independently(out["forecast_periods"])  # MUST raise
    if args.break_cash_flow:
        out["forecast_periods"][0]["cash_from_operations"] += 1000
        audit_independently(out["forecast_periods"])  # MUST raise
    if args.json:
        print(json.dumps(out, indent=2, allow_nan=False))
        return
    print("ORCL PROJECT 1 - REVISION 3: POST-Q1 PRO FORMA (WORKING DRAFT)")
    print("Opening Aug 31, 2026; USD MILLIONS. FY27 row is only Q2-Q4!")
    print("FY27 actual Q1 included separately; no second ATM issuance assumed.")
    print(f"{'FY':>6} {'Revenue':>13} {'EBIT':>13} {'CFO':>13} {'Capex':>13} {'FCFF':>13} {'Cash':>13} {'Revolver':>11}")
    for r in out["forecast_periods"]:
        print(f"{r['year']:>6} {r['revenue']:>13,.1f} {r['ebit']:>13,.1f} "
              f"{r['cash_from_operations']:>13,.1f} {r['capex']:>13,.1f} "
              f"{r['fcff']:>13,.1f} {r['cash']:>13,.1f} {r['revolver']:>11,.1f}")
    print(f"FY2027 Q1 reported revenue: {bridge.Q1_ACTUALS['revenue']:,.1f}; "
          f"remaining {out['forecast_periods'][0]['revenue']:,.1f}; "
          f"annual {out['fy2027_full_year_revenue_implied']:,.1f}")
    print(f"FY2027 Q1 reported capex: {bridge.Q1_ACTUALS['capital_expenditures']:,.1f}; "
          f"remaining {out['forecast_periods'][0]['capex']:,.1f}; "
          f"annual {out['fy2027_full_year_capex_implied']:,.1f}")
    print("PASS: 7 opening reconciliation checks; 9 independent checks for each forecast period")
    print("DCF calculated with signed future flows but terminal and WACC NOT validated.")
    print("NOT READY for final value per share, sensitivity record, or committee action.")

if __name__ == "__main__":
    main()
