"""FIN 439 Lab 10 -- Oracle (ORCL), Ethan Heeres, 2026-09-24.

Standard library only. Dollar amounts and shares are in millions.
Run: python orcl_proforma.py
Break the balance sheet: python orcl_proforma.py --break-check
Break the cash-flow link: python orcl_proforma.py --break-cash-flow
Test financing capacity: python orcl_proforma.py --funding-stress
See lab10_oracle.md for sources, definitions, judgments, and limitations.
The primary valuation follows the lab's POSITIVE-FCFE-ONLY instruction.
"""

import argparse
import copy
import math

YEARS = [2027, 2028, 2029, 2030, 2031]
TOLERANCE = 1e-6
SOURCES = {
    "F24": "https://www.sec.gov/Archives/edgar/data/1341439/000095017024075605/orcl-20240531.htm",
    "F25": "https://www.sec.gov/Archives/edgar/data/1341439/000095017025087926/orcl-20250531.htm",
    "F26": "https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm",
    "Q27": "https://www.sec.gov/Archives/edgar/data/1341439/000119312526389274/orcl-20260831.htm",
    "G27": "https://investor.oracle.com/investor-news/news-details/2026/Oracle-Announces-Q1-Results-Driven-by-Triple-Digit-Growth-in-Cloud-Infrastructure-Revenues/default.aspx",
    "PROVIDER": "https://stockanalysis.com/stocks/orcl/financials/cash-flow-statement/",
}

# Reported history; gross profit and SG&A are constructed consistently below.
HISTORY = {
    2024: dict(revenue=52961, direct_cost=9427+891+4825, sga=8274+1548,
               net_income=10467, inventory=None, ppe=21536, parent_equity=8704,
               total_equity=9239, depreciation=3129, capex=6866,
               tax=1274, pretax=11741, prior_revenue=49954, cfo=18673,
               constant_currency_growth=0.06, source="F24"),
    2025: dict(revenue=57399, direct_cost=11569+782+4576, sga=8651+1602,
               net_income=12443, inventory=None, ppe=43522, parent_equity=20451,
               total_equity=20969, depreciation=3867, capex=21215,
               tax=1717, pretax=14160, prior_revenue=52961, cfo=20821,
               constant_currency_growth=0.09, source="F25"),
    2026: dict(revenue=67357, direct_cost=17597+868+4556, sga=8331+1618,
               net_income=17087, inventory=None, ppe=99957, parent_equity=42508,
               total_equity=43056, depreciation=7623, capex=55663,
               tax=2467, pretax=19554, prior_revenue=57399, cfo=31977,
               constant_currency_growth=0.16, source="F26"),
}

# FY2026 opening balances. All groupings reconcile to the consolidated 10-K.
OPENING = {
    "revenue": 67357.0,
    "cash": 31289.0,
    "receivables": 10385.0,
    "prepaid": 4288.0,
    "ppe": 99957.0,
    "intangibles": 3229.0,
    "other_assets": 261759.0-31289-10385-4288-99957-3229,
    "debt": 7199.0+122342+7701,  # Includes finance-lease liabilities.
    "revolver": 0.0,
    "deferred_revenue": 9916.0+5479,
    "other_liabilities": 218703.0-(7199+122342+7701)-(9916+5479),
    "equity": 43056.0,
    "preferred_equity": 4954.0,
    "nci": 548.0,
}

# Each input is labelled and explained in the accompanying assumption table.
ASSUMPTIONS = {
    "growth": [90000/67357-1, 0.25, 0.20, 0.15, 0.10],
    "gross_margin_before_depreciation": [0.75]*5,
    "sga_to_gross_profit": [0.22, 0.21, 0.20, 0.20, 0.20],
    "rd_to_revenue": [0.12, 0.115, 0.11, 0.105, 0.10],
    "depreciation_to_opening_ppe": 0.12,
    "amortization": [731.0, 694.0, 620.0, 582.0, 377.0],
    "restructuring": [1500.0, 750.0, 500.0, 0.0, 0.0],
    "capex": [92500.0, 70000.0, 50000.0, 40000.0, 40000.0],
    "tax_rate": 0.18,
    "receivables_to_revenue": 10385/67357,
    "prepaid_to_revenue": 4288/67357,
    "net_customer_cash_advances": [20000.0, 15000.0, 5000.0, -5000.0, 0.0],
    "ordinary_deferred_revenue_baseline": 10733.0,
    "customer_financing_rate": 0.05,
    "new_debt": [20000.0, 25000.0, 0.0, 0.0, 0.0],
    "debt_repayment": [7210+620, 10145+600, 5500+600, 7250+600, 9750+600],
    "debt_rate": 0.045,
    "revolver_rate": 0.065,
    "minimum_cash": 10000.0,
    "revolver_limit": 10000.0,
    "common_equity_proceeds": [19909.0, 0.0, 0.0, 0.0, 0.0],
    "current_common_shares": 3023.736,  # 10-Q cover, September 7, 2026.
    "preferred_conversion_shares": 0.05*624.7657,
    "preferred_dividends": [325.0, 325.0, 325*7.5/12, 0.0, 0.0],
    "annual_common_dividend_per_share": 2.0,
    "cost_of_equity": 0.12,
    "terminal_growth": 0.03,
    "market_price": 139.52,
    "market_price_date": "2026-09-24, 4:00 PM EDT close (Stock Analysis)",
}


def total_assets(r):
    return sum(r[k] for k in ("cash", "receivables", "prepaid", "ppe",
                             "intangibles", "other_assets"))


def total_liabilities(r):
    return sum(r[k] for k in ("debt", "revolver", "deferred_revenue", "other_liabilities"))


def balance_gap(r):
    return total_assets(r)-total_liabilities(r)-r["equity"]


def require_zero(year, label, gap):
    if not math.isfinite(gap) or abs(gap) > TOLERANCE:
        raise ValueError(f"FY{year}: {label} gap = {gap:,.6f} million")


def project(opening=OPENING, a=ASSUMPTIONS):
    """Income statement -> noncash balances -> cash flows -> financing -> cash."""
    require_zero(2026, "opening balance sheet", balance_gap(opening))
    prev = opening.copy()
    rows = []
    for i, year in enumerate(YEARS):
        r = {"year": year}
        r["revenue"] = prev["revenue"]*(1+a["growth"][i])
        r["depreciation"] = prev["ppe"]*a["depreciation_to_opening_ppe"]
        r["direct_cost_ex_depreciation"] = r["revenue"]*(1-a["gross_margin_before_depreciation"][i])
        r["gross_profit_before_depreciation"] = r["revenue"]-r["direct_cost_ex_depreciation"]
        # All modeled PP&E depreciation is allocated to direct costs ONCE.
        r["direct_cost"] = r["direct_cost_ex_depreciation"]+r["depreciation"]
        r["gross_profit"] = r["revenue"]-r["direct_cost"]
        r["sga"] = r["gross_profit"]*a["sga_to_gross_profit"][i]
        r["rd"] = r["revenue"]*a["rd_to_revenue"][i]
        r["amortization"] = a["amortization"][i]
        r["restructuring"] = a["restructuring"][i]
        r["operating_income"] = r["gross_profit"]-r["sga"]-r["rd"]-r["amortization"]-r["restructuring"]
        # Opening balances, as in Lab 09. No circular average-balance interest.
        r["interest"] = prev["debt"]*a["debt_rate"]+prev["revolver"]*a["revolver_rate"]
        r["customer_interest"] = max(0, prev["deferred_revenue"]-a["ordinary_deferred_revenue_baseline"])*a["customer_financing_rate"]
        r["pretax"] = r["operating_income"]-r["interest"]-r["customer_interest"]
        r["tax"] = max(0, r["pretax"])*a["tax_rate"]
        r["net_income"] = r["pretax"]-r["tax"]

        r["receivables"] = r["revenue"]*a["receivables_to_revenue"]
        r["prepaid"] = r["revenue"]*a["prepaid_to_revenue"]
        r["change_working_assets"] = r["receivables"]+r["prepaid"]-prev["receivables"]-prev["prepaid"]
        r["capex"] = a["capex"][i]
        r["ppe"] = prev["ppe"]+r["capex"]-r["depreciation"]
        r["intangibles"] = prev["intangibles"]-r["amortization"]
        r["other_assets"] = prev["other_assets"]
        r["net_customer_cash_advances"] = a["net_customer_cash_advances"][i]
        # Cash advances and noncash financing accretion both increase the liability.
        r["deferred_revenue"] = prev["deferred_revenue"]+r["net_customer_cash_advances"]+r["customer_interest"]
        r["new_debt"] = a["new_debt"][i]
        r["debt_repayment"] = a["debt_repayment"][i]
        r["debt"] = prev["debt"]+r["new_debt"]-r["debt_repayment"]
        r["other_liabilities"] = prev["other_liabilities"]
        r["preferred_equity"] = opening["preferred_equity"] if year < 2029 else 0.0
        r["nci"] = opening["nci"]
        r["shares"] = a["current_common_shares"]+(a["preferred_conversion_shares"] if year >= 2029 else 0)
        r["preferred_dividends"] = a["preferred_dividends"][i]
        r["common_dividends"] = r["shares"]*a["annual_common_dividend_per_share"]
        r["equity_proceeds"] = a["common_equity_proceeds"][i]
        r["equity"] = prev["equity"]+r["net_income"]+r["equity_proceeds"]-r["common_dividends"]-r["preferred_dividends"]

        # Compensation is modeled as cash compensation; no SBC add-back/dilution.
        r["cfo"] = (r["net_income"]+r["depreciation"]+r["amortization"]
                    +r["customer_interest"]-r["change_working_assets"]
                    +r["net_customer_cash_advances"])
        r["cfi"] = -r["capex"]
        r["fcfe_before_new_borrowing"] = r["cfo"]-r["capex"]-r["debt_repayment"]-r["preferred_dividends"]
        # Include planned new term debt; exclude the discretionary liquidity revolver.
        r["fcfe"] = r["fcfe_before_new_borrowing"]+r["new_debt"]
        cash_before_revolver = prev["cash"]+r["fcfe"]+r["equity_proceeds"]-r["common_dividends"]
        if cash_before_revolver < a["minimum_cash"]:
            r["change_revolver"] = min(a["minimum_cash"]-cash_before_revolver,
                                        max(0, a["revolver_limit"]-prev["revolver"]))
        else:
            r["change_revolver"] = -min(prev["revolver"], cash_before_revolver-a["minimum_cash"])
        r["revolver"] = prev["revolver"]+r["change_revolver"]
        r["cff"] = (r["new_debt"]-r["debt_repayment"]+r["change_revolver"]
                    +r["equity_proceeds"]-r["common_dividends"]-r["preferred_dividends"])
        r["opening_cash"] = prev["cash"]
        r["change_cash"] = r["cfo"]+r["cfi"]+r["cff"]
        r["cash"] = prev["cash"]+r["change_cash"]
        r["cash_from_funding_schedule"] = cash_before_revolver+r["change_revolver"]
        r["fcfe_after_revolver"] = r["fcfe"]+r["change_revolver"]
        rows.append(r)
        prev = r
    return rows


def check_gaps(r, prev):
    return {
        "balance sheet": balance_gap(r),
        "cash-flow link": r["cash"]-prev["cash"]-r["cfo"]-r["cfi"]-r["cff"],
        "cash movement": r["change_cash"]-r["cfo"]-r["cfi"]-r["cff"],
        "funding cash link": r["cash"]-r["cash_from_funding_schedule"],
        "PP&E roll-forward": r["ppe"]-prev["ppe"]-r["capex"]+r["depreciation"],
        "intangible roll-forward": r["intangibles"]-prev["intangibles"]+r["amortization"],
        "debt roll-forward": r["debt"]-prev["debt"]-r["new_debt"]+r["debt_repayment"],
        "deferred revenue roll-forward": r["deferred_revenue"]-prev["deferred_revenue"]-r["net_customer_cash_advances"]-r["customer_interest"],
        "equity roll-forward": r["equity"]-prev["equity"]-r["net_income"]-r["equity_proceeds"]+r["common_dividends"]+r["preferred_dividends"],
        "FCFE link": r["fcfe"]-r["cfo"]+r["capex"]-r["new_debt"]+r["debt_repayment"]+r["preferred_dividends"],
    }


def assert_balanced(rows, a=ASSUMPTIONS, opening=OPENING):
    """Refuse valuation on broken accounting, nonfinite values, or unavailable cash."""
    require_zero(2026, "opening balance sheet", balance_gap(opening))
    prev = opening
    for r in rows:
        year = r["year"]
        for key, value in r.items():
            if not math.isfinite(value):
                raise ValueError(f"FY{year}: {key} is nonfinite")
        for label, gap in check_gaps(r, prev).items():
            require_zero(year, label, gap)
        if r["cash"] < a["minimum_cash"]-TOLERANCE:
            raise ValueError(f"FY{year}: cash floor gap = {r['cash']-a['minimum_cash']:,.6f} million; financing unavailable")
        if r["revolver"] < -TOLERANCE or r["revolver"] > a["revolver_limit"]+TOLERANCE:
            raise ValueError(f"FY{year}: revolver outside limit")
        for key in ("ppe", "intangibles", "debt", "deferred_revenue"):
            if r[key] < -TOLERANCE:
                raise ValueError(f"FY{year}: negative {key} = {r[key]:,.6f} million")
        prev = r


def value_equity(rows, a=ASSUMPTIONS):
    assert_balanced(rows, a)
    k, g = a["cost_of_equity"], a["terminal_growth"]
    if not (math.isfinite(k) and math.isfinite(g) and k > g >= 0):
        raise ValueError("Require finite cost of equity > terminal growth >= 0.")
    if a["current_common_shares"] <= 0 or any(r["shares"] <= 0 for r in rows):
        raise ValueError("Share counts must be positive.")
    # Terminal cash must already be positive; do not rescue a negative year.
    if rows[-1]["fcfe"] <= 0:
        raise ValueError("FY2031: negative/zero FCFE; no positive perpetual terminal value is supported.")
    # Lab 09 convention: refinance principal after year 5; debt is NOT forgiven.
    terminal_fcfe = (rows[-1]["fcfe"]+rows[-1]["debt_repayment"])*(1+g)
    terminal_value = terminal_fcfe/(k-g)
    pv_positive_per_share = sum(max(0,r["fcfe"])/r["shares"]/(1+k)**t
                                for t,r in enumerate(rows,1))
    pv_signed_per_share = sum(r["fcfe"]/r["shares"]/(1+k)**t
                              for t,r in enumerate(rows,1))
    pv_terminal_per_share = terminal_value/rows[-1]["shares"]/(1+k)**len(rows)
    value_per_share = pv_positive_per_share+pv_terminal_per_share
    return {
        "value_per_share": value_per_share,
        "equity_value_current_share_basis": value_per_share*a["current_common_shares"],
        "terminal_fcfe": terminal_fcfe,
        "terminal_value": terminal_value,
        "terminal_share": pv_terminal_per_share/value_per_share,
        "signed_fcfe_comparison": pv_signed_per_share+pv_terminal_per_share,
        "pv_positive_per_share": pv_positive_per_share,
        "pv_terminal_per_share": pv_terminal_per_share,
    }


STATEMENT_LINES = {
    "INCOME STATEMENT": [
        ("Revenue","revenue"), ("Direct costs excluding depreciation","direct_cost_ex_depreciation"),
        ("Gross profit before depreciation","gross_profit_before_depreciation"),
        ("Depreciation in direct costs","depreciation"), ("Gross profit after depreciation","gross_profit"),
        ("SG&A","sga"), ("Research and development","rd"), ("Intangible amortization","amortization"),
        ("Restructuring (cash expense)","restructuring"), ("Operating income","operating_income"),
        ("Debt and revolver interest","interest"), ("Customer financing accretion","customer_interest"),
        ("Pretax income","pretax"), ("Income tax","tax"), ("Net income","net_income")],
    "BALANCE SHEET": [
        ("Cash","cash"), ("Trade receivables","receivables"), ("Prepaid / other current assets","prepaid"),
        ("PP&E, net","ppe"), ("Intangibles, net","intangibles"), ("Other assets","other_assets"),
        ("Total assets",total_assets), ("Debt, including finance leases","debt"), ("Revolver","revolver"),
        ("Deferred revenue / customer funding","deferred_revenue"), ("Other liabilities","other_liabilities"),
        ("Total liabilities",total_liabilities),
        ("Common parent equity",lambda r:r["equity"]-r["preferred_equity"]-r["nci"]),
        ("Preferred equity","preferred_equity"), ("Noncontrolling interests","nci"), ("Total equity","equity"),
        ("Total liabilities and equity",lambda r:total_liabilities(r)+r["equity"])],
    "CASH FLOW STATEMENT": [
        ("Net income","net_income"), ("+ Depreciation","depreciation"), ("+ Intangible amortization","amortization"),
        ("+ Noncash customer financing interest","customer_interest"),
        ("- Change in operating assets",lambda r:-r["change_working_assets"]),
        ("Net cash advances / (recognition)","net_customer_cash_advances"), ("Cash from operations","cfo"),
        ("Investing cash flow: gross capex","cfi"), ("New term debt","new_debt"),
        ("Debt / finance lease principal",lambda r:-r["debt_repayment"]),
        ("Common equity proceeds","equity_proceeds"), ("Common dividends",lambda r:-r["common_dividends"]),
        ("Preferred dividends",lambda r:-r["preferred_dividends"]),
        ("Revolver draw / (repayment)","change_revolver"), ("Cash from financing","cff"),
        ("Change in cash","change_cash"), ("Opening cash","opening_cash"), ("Closing cash","cash"),
        ("FCFE before any new debt","fcfe_before_new_borrowing"),
        ("FCFE incl. term debt; before revolver","fcfe"),
        ("FCFE including revolver","fcfe_after_revolver")],
}


def print_table(title, rows, lines):
    print(f"\n{title} (USD millions; shares in millions)")
    print(f"{'':<42}"+"".join(f"{'FY'+str(r['year'])+'E':>15}" for r in rows))
    for label, field in lines:
        values = [field(r) if callable(field) else r[field] for r in rows]
        print(f"{label:<42}"+"".join(f"{0.0 if abs(v)<TOLERANCE else v:>15,.1f}" for v in values))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--break-check",action="store_true")
    parser.add_argument("--break-cash-flow",action="store_true")
    parser.add_argument("--funding-stress",action="store_true")
    args = parser.parse_args()
    a = copy.deepcopy(ASSUMPTIONS)
    if args.funding_stress:
        a["capex"][0] += 100000
    rows = project(OPENING,a)
    if args.break_check:
        rows[0]["cash"] -= 1000  # Deliberate, reversible defect.
    if args.break_cash_flow:
        rows[0]["cfo"] += 1000  # Balance sheet alone would not catch this.
    for title, lines in STATEMENT_LINES.items():
        print_table(title,rows,lines)
    print("\nCHECK BLOCK -- all accounting gaps must be zero")
    prev = OPENING
    for r in rows:
        gaps = check_gaps(r,prev)
        print(f"FY{r['year']}E: "+"; ".join(f"{label}={0.0 if abs(v)<TOLERANCE else v:,.6f}" for label,v in gaps.items()))
        print(f"  Cash {r['cash']:,.1f}; floor {a['minimum_cash']:,.1f}; revolver {r['revolver']:,.1f}/{a['revolver_limit']:,.1f}")
        if r["fcfe"] < 0:
            print("  NEGATIVE FCFE -- retained in statements; zero contribution under the lab valuation rule.")
        if r["change_revolver"] > TOLERANCE:
            print(f"  Draw {r['change_revolver']:,.1f}: capex, principal and dividends exceed internally generated cash plus planned financing at the cash floor.")
        prev = r
    try:
        v = value_equity(rows,a)
    except ValueError as exc:
        parser.exit(1,f"\nVALUATION REFUSED: {exc}\n")
    print("\nVALUATION -- LAB POSITIVE-FCFE-ONLY CONVENTION")
    print(f"Common equity value on current-share basis: ${v['equity_value_current_share_basis']:,.2f} million")
    print(f"Value per current common share: ${v['value_per_share']:,.2f}")
    print(f"Current common shares: {a['current_common_shares']:,.6f} million")
    print(f"FY2029 onward shares after preferred conversion: {rows[-1]['shares']:,.6f} million")
    print(f"Share of value after FY2031: {v['terminal_share']:.2%}")
    print(f"Same model INCLUDING negative FCFE (diagnostic): ${v['signed_fcfe_comparison']:,.2f}/share")
    print(f"Market: ${a['market_price']:.2f}; {a['market_price_date']}")
    print("Question: what growth, margins and investment burden would justify the difference?")
    print("Timing: annual classroom discounting from FY2026 year end; not a September stub-period valuation.")


if __name__ == "__main__":
    main()

