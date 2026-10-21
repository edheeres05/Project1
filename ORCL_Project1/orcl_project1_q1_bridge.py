"""Oracle FIN439 Project 1: FY2027 Q1 reported-actuals bridge (revision 2).

Run: python orcl_project1_q1_bridge.py
      python orcl_project1_q1_bridge.py --json

This is a reconciliation and model-rebuild checkpoint, NOT a post-Q1 three-
statement forecast or DCF. All amounts USD millions unless labelled otherwise.
Historical facts come from Oracle FY2027 Q1 Form 10-Q, period ended 2026-08-31:
https://www.sec.gov/Archives/edgar/data/1341439/000119312526389274/orcl-20260831.htm
Financial statements pp. 1, 2, 5; cash footnote p. 6; MD&A pp. 33-34.

Human review still required for prospective Sep 24, 2026 valuation, operating
lease/financing component classifications, financial sensitivity & committee view.
Preserves original uploaded Python and revision 1; makes no mutation of those.
"""
import argparse
import hashlib
import json
from pathlib import Path

import orcl_proforma_EthanHeeres as prior
from orcl_project1_fcff import linked_fcff

FILING_URL = 'https://www.sec.gov/Archives/edgar/data/1341439/000119312526389274/orcl-20260831.htm'
FORECAST_AS_OF = '2026-09-24' # Intended original Project 1 valuation date, NOT the 10-Q date
ACTUAL_AS_OF = '2026-08-31'
UNIT = 'USD millions'

# 10-Q p. 1: FULL reported categories, not residuals plugged to make totals work.
AUG31_BALANCE = {
    'assets': {
        'cash_and_equivalents': 36369,
        'marketable_securities': 708,
        'trade_receivables': 11394,
        'prepaid_and_other_current': 7159,
        'ppe_net': 127845,
        'operating_lease_rou_assets': 33967,
        'goodwill': 62267,
        'deferred_tax_assets': 11625,
        'other_noncurrent_assets': 11925,
    },
    'liabilities': {
        'current_borrowings': 7625,
        'accounts_payable': 11063,
        'accrued_compensation': 1760,
        'current_deferred_revenues': 14686,
        'other_current_liabilities': 12380,
        'noncurrent_borrowings': 117712,
        'taxes_payable': 12060,
        'noncurrent_operating_lease_liabilities': 30594,
        'other_noncurrent_liabilities': 28183,
    },
    'equity': {
        'preferred_stock': 4954,
        'common_and_apic': 64319,
        'accumulated_deficit': -1114,
        'accumulated_other_comprehensive_loss': -1387,
        'noncontrolling_interests': 424,
    },
    'reported_assets': 303259,
    'reported_equity': 67196,
}

# 10-Q pp. 2, 5 and financing discussion pp. 33-34.
Q1_ACTUALS = {
    'revenue': 19345,
    'operating_income': 6728,
    'net_income': 4760,
    'depreciation': 3156,
    'amortization': 202,
    'operating_cash_flow': 23103,
    'investing_cash_flow': -28580,
    'capital_expenditures': 28499,
    'financing_cash_flow': 13111,
    'fx_on_cash_and_restricted_cash': 11,
    'cash_and_restricted_cash_start': 31289,
    'cash_and_restricted_cash_end': 38934,
    'net_common_share_issuance_proceeds_atm': 19909,
    'estimated_atm_shares_issued_millions': 141,
    'new_significant_financing_customer_prepayments': 11363,
    'other_deferred_revenue_cash_flow_increase': 3997,
    'unrestricted_cash_and_equivalents_end': 36369,
    'current_deferred_revenue_end': 14686,
    'outstanding_common_shares_end_rounded_millions': 3024,
}

# FY2026 latest 10-K/May 31 columns in the 10-Q pp. 1 and 5.
MAY31_COMPARATORS = {
    'current_deferred_revenue': 9916,
    'outstanding_common_shares_rounded_millions': 2880,
    'total_assets': 261759,
    'total_equity': 43056,
    'cash_and_equivalents': 31289,
}


def check(name, observed, expected, tol=1e-6):
    if abs(observed - expected) > tol:
        raise ValueError(f'{name}: observed={observed}, expected={expected}')
    return {'name': name, 'status': 'PASS', 'observed': observed, 'expected': expected}


def build_bridge():
    # Preserve/verify existing original model rather than silently overwriting it.
    prior_rows = prior.project()
    prior.assert_balanced(prior_rows)
    prior_fcff = linked_fcff(prior_rows, prior.ASSUMPTIONS)
    fy27 = prior_rows[0]
    a, l, e = AUG31_BALANCE['assets'], AUG31_BALANCE['liabilities'], AUG31_BALANCE['equity']
    q = Q1_ACTUALS
    reported_assets = sum(a.values())
    reported_liabilities = sum(l.values())
    reported_equity = sum(e.values())
    checks = [
        check('Aug31 total assets tie to filed total', reported_assets, AUG31_BALANCE['reported_assets']),
        check('Aug31 total equity ties to filed total', reported_equity, AUG31_BALANCE['reported_equity']),
        check('Aug31 balance sheet balances', reported_assets, reported_liabilities + reported_equity),
        check('Q1 GAAP cash flow and FX roll-forward',
              q['cash_and_restricted_cash_start'] + q['operating_cash_flow']
              + q['investing_cash_flow'] + q['financing_cash_flow']
              + q['fx_on_cash_and_restricted_cash'],
              q['cash_and_restricted_cash_end']),
        check('Q1 ordinary reported free cash flow = CFO - capex',
              q['operating_cash_flow'] - q['capital_expenditures'], -5396),
        check('FY2027 original base still balances', prior.balance_gap(fy27), 0),
    ]
    # Quarterly cash-flow statement includes restricted cash, which cannot
    # be treated as ordinary excess cash added to an enterprise-to-equity bridge.
    restricted_cash_implied = (q['cash_and_restricted_cash_end']
                               - q['unrestricted_cash_and_equivalents_end'])
    check('Q1 implied restricted cash is nonnegative',
          min(0, restricted_cash_implied), 0)
    # The following arithmetic is NOT independent forecasts of remaining Q2-Q4.
    # It simply subtracts Q1 actuals from annual targets that were built before Q1.
    remaining_arithmetic = {
        'revenue': fy27['revenue'] - q['revenue'],
        'operating_income': fy27['operating_income'] - q['operating_income'],
        'net_income': fy27['net_income'] - q['net_income'],
        'operating_cash_flow': fy27['cfo'] - q['operating_cash_flow'],
        'capital_expenditures': fy27['capex'] - q['capital_expenditures'],
        'reported_fcff_original_not_restated_for_q1': prior_fcff[0]['fcff'],
    }
    # This is the crucial guard: FY27 original $19,909 equity issuance and
    # $20,000 net customer advances must be reforecast FROM the Q1 balance.
    # They are not automatically future cash on top of already reported Q1.
    return {
        'status': 'INTERMEDIATE_Q1_BRIDGE_NOT_A_POST_Q1_FORECAST_OR_VALUATION',
        'report_date': '2026-10-19',
        'historical_filing_period_end': ACTUAL_AS_OF,
        'intended_valuation_date': FORECAST_AS_OF,
        'amounts_unit': UNIT,
        'primary_source': FILING_URL,
        'provenance': {
            'original_module_sha256': hashlib.sha256(Path(prior.__file__).read_bytes()).hexdigest(),
            'original_model_modified': False,
            'revision1_original_modified': False,
        },
        'aug31_balance': AUG31_BALANCE,
        'aug31_reported_liabilities_calculated': reported_liabilities,
        'q1_actual': Q1_ACTUALS,
        'may31_comparators': MAY31_COMPARATORS,
        'restricted_cash_implied_from_cash_flow_end_vs_balance_sheet': restricted_cash_implied,
        'restricted_cash_excluded_from_unrestricted_cash': True,
        'reported_q1_cfo_minus_capex': q['operating_cash_flow']-q['capital_expenditures'],
        'original_fy27_targets': {
            'revenue': fy27['revenue'],
            'operating_income': fy27['operating_income'],
            'net_income': fy27['net_income'],
            'operating_cash_flow': fy27['cfo'],
            'capital_expenditures': fy27['capex'],
            'stock_issuance_proceeds_in_full_year_plan': fy27['equity_proceeds'],
            'net_customer_cash_advances_in_full_year_plan': fy27['net_customer_cash_advances'],
            'fcff': prior_fcff[0]['fcff'],
        },
        'q2_through_q4_arithmetic_remaining_targets_NOT_validated_forecasts': remaining_arithmetic,
        'comparisons': {
            'q1_percent_of_full_year_revenue': q['revenue']/fy27['revenue']*100,
            'q1_percent_of_full_year_capex': q['capital_expenditures']/fy27['capex']*100,
            'q1_percent_of_full_year_operating_cash_flow': q['operating_cash_flow']/fy27['cfo']*100,
            'current_deferred_revenue_balance_change': q['current_deferred_revenue_end'] - MAY31_COMPARATORS['current_deferred_revenue'],
            'atm_issuance_cash_already_reported': q['net_common_share_issuance_proceeds_atm'],
            'q1_atm_proceeds_equals_entire_original_fy27_assumption': q['net_common_share_issuance_proceeds_atm'] == fy27['equity_proceeds'],
        },
        'accounting_validation': checks,
        'known_unresolved_before_price': [
            'Build a new three-statement projection beginning with Aug31 reported balances, not FY2026 opening balances.',
            'As of Sep24 valuation, exclude elapsed post-Aug31 cash flows (Sep1-24) from prospective PV or document a controlled interim/stub convention.',
            'Do not add $19,909m ATM proceeds again as new financing in Sep1-May31; recheck common-share basis after Q1 issuances.',
            'Do not add first-quarter $11,363m customer prepayments again to remaining-year financing/operating cash flow.',
            'Classify significant-financing prepayments across long-term and short-term liabilities, and avoid double counting as operating cash AND separate debt.',
            'Distinguish $36,369m unrestricted cash from $38,934m cash and restricted cash; separately review $708m marketable securities.',
            'Model operating lease assets/liabilities consistently and separate preferred equity and NCI in EV-to-common bridge.',
            'Justify terminal FCFF sustainable capex/reinvestment, WACC sources and validated low/base/high scenarios.',
            'Obtain human AI-off pre-run directional prediction and locked input snapshot before the required new operating-input sensitivity test.',
            'Do not issue a final price, recommendation, or claim fresh-run validation yet.',
        ],
        'new_operating_sensitivity_run': False,
        'new_valuation_claim': False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--json', action='store_true')
    args = p.parse_args()
    report = build_bridge()
    if args.json:
        print(json.dumps(report, indent=2, allow_nan=False))
        return
    print('ORCL PROJECT 1 — REVISION 2: Q1 BRIDGE / TIME-ANCHOR CHECK')
    print('Historical Aug 31, 2026 reported facts; units USD millions')
    print(f"Assets {report['aug31_balance']['reported_assets']:,.0f}; "
          f"liabilities {report['aug31_reported_liabilities_calculated']:,.0f}; "
          f"equity {report['aug31_balance']['reported_equity']:,.0f}")
    print(f"Unrestricted cash {Q1_ACTUALS['unrestricted_cash_and_equivalents_end']:,.0f}; "
          f"restricted cash implied {report['restricted_cash_implied_from_cash_flow_end_vs_balance_sheet']:,.0f}")
    print(f"Q1 revenue {Q1_ACTUALS['revenue']:,.0f}; CFO {Q1_ACTUALS['operating_cash_flow']:,.0f}; "
          f"capex {Q1_ACTUALS['capital_expenditures']:,.0f}; CFO-capex {report['reported_q1_cfo_minus_capex']:,.0f}")
    print(f"Q1 ATM equity funding {Q1_ACTUALS['net_common_share_issuance_proceeds_atm']:,.0f}: "
          'already occurred and is already reflected in Aug31 balances')
    print('Original FY27 annual forecast less reported Q1, ONLY an arithmetic diagnostic:')
    for key in ('revenue','operating_income','net_income','operating_cash_flow','capital_expenditures'):
        print(f"  {key}: {report['q2_through_q4_arithmetic_remaining_targets_NOT_validated_forecasts'][key]:,.2f}")
    for item in report['accounting_validation']:
        print(f"{item['status']}: {item['name']}")
    print('STATUS: no revised post-Q1 forecast and no defensible per-share valuation yet.')

if __name__ == '__main__':
    main()
