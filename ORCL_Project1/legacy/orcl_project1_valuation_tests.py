"""Revision 4 standard-library checks. Run: py -m unittest -v orcl_project1_valuation_tests.py"""
import copy
import unittest

import orcl_project1_post_q1_proforma as proforma
import orcl_project1_valuation_bridge as valuation


class OracleRevision4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=proforma.project()

    def test_historical_ties_10q(self):
        b=valuation.source_bridge()
        self.assertAlmostEqual(b["reported_assets"],303259)
        self.assertAlmostEqual(b["reported_equity"],67196)
        self.assertAlmostEqual(b["restricted_cash_EXCLUDED"],2565)
        self.assertAlmostEqual(b["senior_notes_and_borrowings"],125337)

    def test_original_model_unchanged_result(self):
        p=proforma.build_result()
        self.assertEqual(p["fy2027_full_year_revenue_implied"],90000)
        self.assertAlmostEqual(p["fy2027_full_year_capex_implied"],92500)
        self.assertEqual(p["independent_total_accounting_checks"],52)

    def test_early_negative_fcff_retained(self):
        c=valuation.discounted_case(self.rows,.114,.03)
        self.assertTrue(c["used_signed_negative_cash_flows"])
        self.assertLess(self.rows[0]["fcff"],0)
        self.assertLess(self.rows[1]["fcff"],0)

    def test_wacc_g_boundaries_fail_loudly(self):
        for w,g in [(0.03,0.03),(.02,.04),(-.1,.01),(float('nan'),.03)]:
            with self.assertRaises(ValueError): valuation.discounted_case(self.rows,w,g)

    def test_bridge_mutually_exclusive_preferred(self):
        claim=valuation.discounted_case(self.rows,.114,.03,preferred_policy="outstanding_claim")["equity_bridge"]
        converted=valuation.discounted_case(self.rows,.114,.03,preferred_policy="if_converted")["equity_bridge"]
        self.assertEqual(claim["minus_preferred_claim"],4954)
        self.assertEqual(converted["minus_preferred_claim"],0)
        self.assertGreater(converted["shares_millions"],claim["shares_millions"])
        self.assertAlmostEqual(claim["bridge_gap"],0)
        self.assertAlmostEqual(converted["bridge_gap"],0)

    def test_excess_cash_vs_total_cash(self):
        a=valuation.discounted_case(self.rows,.114,.03,"excess")["equity_bridge"]
        b=valuation.discounted_case(self.rows,.114,.03,"total")["equity_bridge"]
        self.assertAlmostEqual(b["estimated_common_equity"]-a["estimated_common_equity"],10000)
        self.assertAlmostEqual(b["indicative_dollars_per_share_NOT_FINAL"] - a["indicative_dollars_per_share_NOT_FINAL"],10000/3023.736)

    def test_wacc_and_growth_monotonic_on_specific_base(self):
        checks=valuation.maths_tests(self.rows)
        self.assertEqual(len(checks),6)
        self.assertTrue(all(c["status"]=="PASS" for c in checks))

    def test_corrupt_finance_lease_split_is_caught(self):
        b=copy.deepcopy(proforma.OPEN)
        b["finance_lease_liabilities"]+=1
        with self.assertRaisesRegex(ValueError,"finance-lease bridge"):
            valuation.source_bridge(b)

    def test_corrupt_cashflow_is_caught(self):
        rows=copy.deepcopy(self.rows)
        rows[1]["cash_from_operations"]+=1
        with self.assertRaises(ValueError):proforma.audit_independently(rows)

    def test_not_final_and_no_operating_sensitivity(self):
        o=valuation.build_result()
        self.assertIsNone(o["final_value_per_share"])
        self.assertIsNone(o["recommendation"])
        self.assertFalse(o["new_operating_input_sensitivity_executed"])
        self.assertFalse(o["student_AI_off_operating_prediction_submitted"])
        self.assertGreater(o["terminal_dependency_pct"],80)

if __name__=='__main__':
    unittest.main()
