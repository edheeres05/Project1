"""Project 1, revision 1: connect Ethan Heeres's existing Oracle statements to FCFF.

Run beside the preserved original: python orcl_project1_fcff.py
Standard library only; USD millions. This is AI-assisted work dated 2026-10-19.

This revision validates the cash-flow connection, not a final investment value.
It deliberately withholds a share price until timing, terminal reinvestment,
WACC and the enterprise-to-common-equity bridge have been reconciled.
It does not execute a new operating-input sensitivity or supply a student's
human-authored, AI-off prediction. Original lab files remain unchanged.
"""

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import orcl_proforma_EthanHeeres as original


REVISION_DATE = "2026-10-19"
SOURCE_COMMIT = "929330384066f82f9607f74bd5dedac9ed678cd7"
SOURCE_URL = (
    "https://github.com/edheeres05/Proforma/blob/"
    + SOURCE_COMMIT + "/orcl_proforma_EthanHeeres.py"
)
Q1_FILING = (
    "https://www.sec.gov/Archives/edgar/data/1341439/"
    "000119312526389274/orcl-20260831.htm"
)


def close_enough(label, actual, expected, tolerance=1e-6):
    if not all(math.isfinite(x) for x in (actual, expected)):
        raise ValueError(f"{label}: nonfinite value")
    if abs(actual - expected) > tolerance:
        raise ValueError(f"{label}: {actual} != {expected}")


def linked_fcff(rows, assumptions):
    """Trace operating profit to signed FCFF and independently reconcile CFO.

    PROVISIONAL operating treatment of net customer advances: retain the cash
    change in contract liabilities in working capital. It is not an independent
    debt inflow and cannot also be added to equity value. A financing treatment
    needs a separate contract-liability and settlement schedule before use.

    Original customer interest is noncash: its CFO add-back is already present.
    Add back only debt/revolver interest when going from CFO to unlevered cash,
    and replace levered taxes with taxes on EBIT. Adding customer interest again
    would double count it. No credit is assumed for operating tax losses.
    """
    output = []
    for row in rows:
        ebit = row["operating_income"]
        operating_tax = max(ebit, 0.0) * assumptions["tax_rate"]
        nopat = ebit - operating_tax
        cash_change_in_nwc = (
            row["change_working_assets"] - row["net_customer_cash_advances"]
        )
        fcff = (
            nopat + row["depreciation"] + row["amortization"]
            - row["capex"] - cash_change_in_nwc
        )
        # Debt issuance, principal payments and common/preferred dividends do
        # not enter enterprise free cash flow. The tax replacement also removes
        # the tax benefit of noncash customer financing expense.
        extra_unlevered_tax = operating_tax - row["tax"]
        fcff_from_cfo = (
            row["cfo"] - row["capex"] + row["interest"]
            - extra_unlevered_tax
        )
        close_enough(f"FY{row['year']} FCFF reconciliation", fcff, fcff_from_cfo)
        output.append({
            "fiscal_year": row["year"],
            "revenue": row["revenue"],
            "ebit": ebit,
            "operating_tax": operating_tax,
            "nopat": nopat,
            "depreciation": row["depreciation"],
            "amortization": row["amortization"],
            "capex": row["capex"],
            "change_working_assets": row["change_working_assets"],
            "net_customer_advances": row["net_customer_cash_advances"],
            "cash_change_in_operating_working_capital": cash_change_in_nwc,
            "fcff": fcff,
            "cfo": row["cfo"],
            "debt_and_revolver_interest": row["interest"],
            "original_non_cash_customer_interest": row["customer_interest"],
            "tax_adjustment_to_unlevered_basis": extra_unlevered_tax,
            "fcff_from_cfo": fcff_from_cfo,
            "fcff_reconciliation_gap": fcff - fcff_from_cfo,
        })
    return output


def discount_cash_flows(cash_flows, payment_times, wacc,
                        terminal_fcff, terminal_growth):
    """Generic end-of-period enterprise DCF; every negative cash flow is kept.

    The caller must build and justify normalized terminal FCFF independently.
    This function never silently grows a final-year investment cycle forever.
    """
    if not cash_flows or len(cash_flows) != len(payment_times):
        raise ValueError("Require one future payment time per cash flow")
    values = [*cash_flows, *payment_times, wacc, terminal_fcff, terminal_growth]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("DCF inputs must be finite")
    if not (wacc > terminal_growth >= 0.0):
        raise ValueError("Require WACC > terminal growth >= 0")
    if terminal_fcff <= 0:
        raise ValueError("Normalized terminal FCFF must be positive")
    if any(t <= 0 for t in payment_times):
        raise ValueError("Cash flows must be strictly after the valuation date")
    if any(b <= a for a, b in zip(payment_times, payment_times[1:])):
        raise ValueError("Payment times must strictly increase")
    pv_each = [cf / (1 + wacc) ** t
               for cf, t in zip(cash_flows, payment_times)]
    terminal_value = terminal_fcff / (wacc - terminal_growth)
    pv_terminal = terminal_value / (1 + wacc) ** payment_times[-1]
    enterprise_value = sum(pv_each) + pv_terminal
    return {
        "pv_explicit_cash_flows": pv_each,
        "pv_explicit": sum(pv_each),
        "terminal_fcff": terminal_fcff,
        "terminal_value": terminal_value,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise_value,
        "terminal_value_share": (
            pv_terminal / enterprise_value if enterprise_value > 0 else None
        ),
    }


def prospective_times(valuation_date, periods):
    """Reject a full-year flow that includes time before the valuation date.

    periods = [(cash_flow_start_date, cash_flow_end_date), ...].
    An actual/forecast stub must be constructed upstream, not fabricated by
    changing the discount exponent on a full fiscal-year cash flow.
    """
    value_date = dt.date.fromisoformat(valuation_date)
    times = []
    for start_text, end_text in periods:
        start = dt.date.fromisoformat(start_text)
        end = dt.date.fromisoformat(end_text)
        if start <= value_date or end < start:
            raise ValueError("Remove elapsed/actual cash flows before valuation")
        times.append((end - value_date).days / 365.0)
    return times


def validation_record(rows, fcff_rows):
    original.assert_balanced(rows)
    checks = [{
        "name": "Preserved five-year accounting and funding checks",
        "status": "PASS",
        "scope": "Original base assumptions only; not a fresh-environment cold run",
    }, {
        "name": "EBIT-based FCFF reconciles to cash-flow-statement FCFF",
        "status": "PASS",
        "maximum_absolute_gap_usd_millions": max(
            abs(r["fcff_reconciliation_gap"]) for r in fcff_rows
        ),
    }]
    # Course example already in the student's repository; not fictional rubric
    # example data and not an Oracle input or a new operating-input experiment.
    training_path = []
    cf = 100.0
    for g in (0.08, 0.06, 0.05, 0.04, 0.03):
        cf *= 1 + g
        training_path.append(cf)
    training = discount_cash_flows(training_path, [1, 2, 3, 4, 5],
                                   0.10, cf * 1.03, 0.03)
    training_per_share = (training["enterprise_value"] + 50 - 300) / 50
    close_enough("Course known answer", training_per_share, 27.4974, 0.00005)
    checks.append({"name": "Existing course DCF known answer", "status": "PASS",
                   "expected_rounded": 27.4974, "actual": training_per_share})
    # A negative cash requirement must not silently disappear from PV.
    negative = discount_cash_flows([-100.0, 110.0], [1, 2], .10, 10.0, .02)
    close_enough("Signed cash-flow PV", negative["pv_explicit"], 0.0)
    checks.append({"name": "Negative cash flows retained", "status": "PASS"})
    try:
        prospective_times("2026-09-24", [("2026-06-01", "2027-05-31")])
    except ValueError:
        checks.append({"name": "Elapsed fiscal-year cash flows rejected",
                       "status": "PASS"})
    else:
        raise ValueError("Timing guard accepted elapsed cash flows")
    return checks


def build_result():
    rows = original.project()
    original.assert_balanced(rows)
    fcff_rows = linked_fcff(rows, original.ASSUMPTIONS)
    return {
        "status": "INTERMEDIATE_REVISION_NOT_READY_FOR_INVESTMENT_CONCLUSION",
        "revision_date": REVISION_DATE,
        "authorship": "AI-assisted implementation; analyst review pending",
        "units": "USD millions; rates as decimals",
        "preserved_source": {
            "repository_file": SOURCE_URL,
            "github_commit": SOURCE_COMMIT,
            "local_sha256": hashlib.sha256(
                Path(original.__file__).read_bytes()).hexdigest(),
        },
        "intended_decision_as_of": "2026-09-24",
        "forecast_periods": "FY2027-FY2031; original full fiscal-year periods",
        "statement_opening_date": "2026-05-31",
        "base_assumptions": original.ASSUMPTIONS,
        "fcff_formula": "EBIT - unlevered tax + D&A - capex - cash change in operating NWC",
        "customer_advance_treatment": "Provisional operating contract-liability treatment",
        "statements": rows,
        "linked_fcff": fcff_rows,
        "validation": validation_record(rows, fcff_rows),
        "value_per_share": None,
        "recommendation": None,
        "withheld_until_resolved": [
            "Build remaining FY2027 forecast after Q1 actuals; use a documented September stub.",
            "Reconcile August 31 reported balances to chosen valuation date, including completed ATM issue.",
            "Normalize terminal reinvestment, operating leases and customer-contract balances.",
            "Document WACC components and distinguish financing debt from operating liabilities.",
            "Complete cash, investments, debt, finance leases, preferred, NCI and diluted-share bridge.",
        ],
        "source_checks_new_in_this_revision": [
            {"item": "September 24 unadjusted closing market price",
             "legacy_value": 139.52, "checked_value": 139.54,
             "units": "USD per share",
             "source": "https://www.wsj.com/market-data/quotes/ORCL/historical-prices?eafs_enabled=false",
             "locator": "09/24/26 row, Close column",
             "effect": "Use corrected quote only when a consistent dated valuation is ready"},
            {"item": "Latest reported balance sheet and actual Q1 cash flows",
             "period_end": "2026-08-31", "source": Q1_FILING,
             "locator": "pp. 1, 5; Notes 5 and 6; EPS note; cover page",
             "effect": "Quarter already occurred before September 24; full-year forecast cannot all be prospective"},
        ],
        "locked_changed_input_record": {
            "new_test_run": False,
            "human_ai_off_prediction": "Not supplied by this revision",
            "rule": "Save human-authored prediction and immutable pre-run state before selected new test",
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print full executed record")
    args = parser.parse_args()
    result = build_result()
    if args.json:
        print(json.dumps(result, indent=2, allow_nan=False))
        return
    print("ORCL PROJECT 1 — REVISION 1: STATEMENTS TO FCFF")
    print("INTERMEDIATE WORK; SHARE PRICE AND RECOMMENDATION WITHHELD")
    print("USD millions; original full fiscal years, not September stub periods")
    print(f"{'FY':>5} {'EBIT':>13} {'NOPAT':>13} {'D&A':>13} {'Capex':>13} {'Cash dNWC':>13} {'FCFF':>13}")
    for r in result["linked_fcff"]:
        print(f"{r['fiscal_year']:>5} {r['ebit']:>13,.2f} {r['nopat']:>13,.2f} "
              f"{r['depreciation']+r['amortization']:>13,.2f} {r['capex']:>13,.2f} "
              f"{r['cash_change_in_operating_working_capital']:>13,.2f} {r['fcff']:>13,.2f}")
    for check in result["validation"]:
        print(f"{check['status']}: {check['name']}")
    print("Still required before a share valuation:")
    for item in result["withheld_until_resolved"]:
        print("- " + item)
    print("No new operating-input sensitivity executed; human AI-off prediction remains required.")


if __name__ == "__main__":
    main()
