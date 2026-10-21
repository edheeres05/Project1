# Validation and AI Use - ORCL Project 1 | 2026-10-19

**Educational AI-assisted work. Decision user:** Buy-side committee; **current decision:** WATCH/DEFER initiation (conditional). **Analysis boundary:** Oracle Q1 actual as of Aug31, 2026 (filing later), forecast Q2-Q4 FY27 through FY2031; the Oct19 closing quote is only an out-of-period reference. USD millions, share counts millions. See source ledger.

## Run evidence and tests

Run from extracted folder:

```powershell
py orcl_project1_application.py --tests
py orcl_project1_application.py --demo-failure
py orcl_project1_application.py --export
```

**Observed:** 12/12 workbench unit tests PASS. Original pro forma is unchanged. Independent sourced Aug31 opening checks = 7; per forecast year 9 independent checks; total **52 checks** in base. Accounting balance, cash-flow changes, debt roll-forward, contract liability roll-forward, preferred conversion equity transfer, and signed FCFF reconcile to input statements. Source EV bridge rebalances exactly; restricted cash excluded, $10bn operational cash reserved, neither operating leases nor deferred revenue double-counted as debt. Deliberately breaking cash by $1bn raises a ValueError instead of a new value. Tests also reject invalid bounds and WACC <= terminal growth; WACC up reduces illustrative value, growth up raises it.

**Known-answer fixture:** Original revision1 DCF training case $27.4974/share reproduced to published tolerance; direct numerical self-check compares EBIT-based FCFF with CFO-derived FCFF. **Independent source/definition check:** reported Aug31 total assets $303,259m and equity $67,196m to Oracle 10-Q; notes/finance/operating leases and restricted cash separately defined. FY2026 $2.7bn Ampere disposal gain flagged as nonoperating, not recurring EBIT. Source periods and exact links in `source-ledger.md`.

## One-at-a-time operating sensitivity (new workbench)

All tests return to the *same* base and leave original assumptions unchanged; no invalid case is assigned a fictitious DCF. Each result is provisional and does not establish a new independently human precommitted lock.

| Scenario | FY2031 operating profit ($m) | FY2031 FCFF ($m) | Indicative share | Result |
|---|---:|---:|---:|---|
| Base | 59,944.46 | 37,482.05 | $57.72 | PASS |
| Growth -2 pp FY28-31 | 54,264.94 | 33,634.43 | $46.70 | PASS |
| Growth +2 pp FY28-31 | 65,921.98 | 41,500.67 | $69.20 | PASS |
| FY2028 CapEx -10% | 60,464.85 | 37,258.28 | $58.92 | PASS |
| FY2028 CapEx +10% | — | — | — | **INVALID funding floor** |
| Margin -1 pp | 58,578.26 | 36,361.77 | $54.13 | PASS |
| Margin +1 pp | 61,310.66 | 38,602.34 | $61.30 | PASS |

Revenue growth has the largest change in FY2031 operating profit and modeled value across these particular usable bounds; CapEx directly reduces FY2028 cash flow and may violate available funding even if terminal FY2031 operating income is largely unchanged. Driver rankings depend on chosen bounds. **The failed +10% CapEx endpoint must not be treated as a usable data point.**

## Low/base/high and rate-by-growth check

With the *same unverified* 11.4% WACC, 3% growth and terminal formula, the three combined **causal** scenarios show low **$50.42/share** (FY28-FY31 growth -1pp and pre-D&A gross margin -0.5pp); base **$57.72**; high **$71.70** (+2pp growth, +0.5pp pre-D&A margin, FY2028 CapEx -5%). The severe downside (-2pp growth, -1pp margin, FY2028 CapEx +10%) fails FY2028 liquidity constraints, so there is no usable low-end market valuation for that stress. None of these are probability intervals or a recommendation.

| WACC / terminal growth | 2.0% | 3.0% | 4.0% |
|---|---:|---:|---:|
| 10.4% | $61.27 | $75.03 | $93.09 |
| 11.4% | $47.24 | $57.72 | $71.02 |
| 12.4% | $36.01 | $44.19 | $54.32 |

**Partner fresh-eyes:** Lab 11 colleague **Aidan Murrin** questioned growth assumption sustainability and relative effect versus CapEx. Lab 12 colleague **Nicole Yu** asked why high market valuation could coexist with low DCF and whether Oracle would need additional debt for data-center construction. Student's cited original responses are in the course Lab11/Lab12 GitHub repository and drive the funding-research and cloud-to-cash monitoring priorities.

## Locked changed-input history (student evidence; DO NOT claim a new lock)

Lab 11 from **September 29, 2026** contains a locked, **student-authored** AI-off prediction before running the **growth** sensitivity on the **earlier** original Lab 10 model; it is not a new locked test for this revision.

- Snapshot time (student Lab 11): **2026-09-29 16:53:07.498015 -04:00**; prediction SHA-256 `9057466cef65443ce394b5952238d56e175e9939864fba4ff58351fa87787f5a`. An independently verified Git commit timestamp associated with this exact file is **not established**.
- One driver: FY2027-FY2031 *annual revenue growth* old [33.6164,25,20,15,10]% to new [35.6164,27,22,17,12]%; +2 percentage points each year, original CapEx and other inputs held base.
- Student prediction: FY2031 operating profit and signed FCFE both rise; estimated **$66,174.6957m EBIT** and **$26,495.6902m FCFE** from base $59,936.4607m/$21,777.5260m.
- Executed Lab 11 result: **$67,281.5518m EBIT** and **$27,097.5816m FCFE**, positive directions match; predictions understated increases by **$1,106.8561m EBIT** and **$601.8914m FCFE**. No new Lab 11 share-price outcome because original FCFE terminal policy was unsupported. Link: https://github.com/edheeres05/Proforma/blob/main/lab11_orcl_EthanHeeres.md.
- Diagnosis: Compounded revenue carries through operating expenses and working capital differently than the student's percentage estimates. The same lab demonstrated funding limitations for high CapEx. Student-authored explanation is preserved in the archived lab, not rewritten.
- Current conversation's separate belief (extra servers may create future cloud revenue) is an **AI-assisted discussion**, not independently certified AI-off and **not** falsely dated before this application's scenario runs. Confirm professor accepts carried-forward Lab11 evidence or complete a new supervised lock.

## AI use, verification and limits

**AI system:** OpenAI ChatGPT GPT-6 (2026-10-19); earlier revision coding is AI-assisted, specific prior model/version not recorded. **Material contributions:** Rev1 signed FCFF connection (**modify/accept** only after CFO recon); Rev2 filing balances and financing separation (**accept** after SEC 10-Q tie-out); Rev3 nine-month forecast (**qualify**: no Sep-Oct actual stub); Rev4 EV/equity bridge and desktop user controls (**qualify**: WACC/dilution/terminal not verified); this application, sensitivity table and draft writing (**qualify**: student finance and wording review pending). In each case the validation is independent accounting identity, SEC 10-Q comparison or math boundary where indicated, **not** an external second-model vote.

**Rejected:** Calling $57.72 a fair price/strong short thesis; the model's terminal share is 95.8%, tax/WACC and cash-flow dates remain unverified. **Not resolved:** true FY2032 maintenance capex, current treasury yields/equity beta/cost of debt, future financing commitments, SBC dilution, forecast lease schedule, full base-year one-off adjustments, Sep-Oct stub, fully reproducible cold run on another Windows PC, instructor access / final video artifacts. Current script checks are NOT proof those economic issues are solved.

## Cold-run note

Local test logs saved in `output/validation_log.txt`; these do **not** constitute a fresh-environment Windows run. On independent machine: extract ZIP -> `py orcl_project1_application.py --tests` -> `--export` -> open GUI -> reset -> stress FY2028 CapEx 10% -> capture fail state -> restore -> compare output. Record date, OS/Python version, first failure and fix. The student should verify the published repo and submission file accessibility.
