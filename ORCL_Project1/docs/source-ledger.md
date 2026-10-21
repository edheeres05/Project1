# Oracle research source ledger and timing

| Input | Observed value / use | Period & source | Adjustment / status |
|---|---|---|---|
| FY2026 Oracle revenue / reported net income | $67,357m / $17,087m | Fiscal ended May 31, 2026; [Oracle 10-K](https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm) | Reported history; no retroactive rewrite |
| FY2026 Oracle CapEx / D&A | $55,663m CapEx / $7,623m depreciation from prior base | Same 10-K | Reported, user Lab 10; classify provider cash-flow definition before comparison |
| FY2026 Ampere gain | Approximately $2.7bn non-operating sale gain | Same FY2026 10-K, FY26 nonoperating income narrative | Illustrative after-tax earnings normalized proxy: 17,087 - 2,700*(1-.18) = $14,873m. 18% is model tax assumption, not measured incremental tax rate; do NOT substitute into EBIT/forecast without corroboration. |
| Q1 FY2027 revenue / CapEx | $19,345m / $28,499m | Quarter ended Aug 31, 2026; [10-Q](https://www.sec.gov/Archives/edgar/data/1341439/000119312526389274/orcl-20260831.htm), income and cash-flow statements | Used as separately reported first quarter; forecast Q2-Q4 only |
| Q1 FY2027 shares issuance | $19,909m ATM financing cash inflow | Same 10-Q, shareholder/equity and cash-flow notes | Reflected in Aug31 opening balance once; **never** forecast again |
| Aug31 opening assets and equity | $303,259m assets / $67,196m equity | Same 10-Q, balance sheet | Source splits reconcile and model fails loudly if altered |
| Unrestricted and restricted cash | $36,369m + $2,565m restricted | Same 10-Q cash/balance notes | Exclude restricted from excess-cash bridge |
| Debt and leases | $125,337m notes; $9,185m finance leases; $34,621m operating leases | Same 10-Q, balance sheet and lease footnote | Finance leases in financing debt; operating lease obligations kept in EBIT/operating forecast, not also subtracted as debt |
| Preferred / NCI | $4,954m / $424m | Same 10-Q | Deduct claims under outstanding preferred policy; fully diluted conversion alternative provisional |
| Common share count | 3,023.736m | 10-Q Sept 7, 2026 cover | Current shares, NOT diluted EPS count or full SBC model |
| FY2027 and FY2028-31 assumptions | FY2027 revenue $90bn; FY2027 CapEx $92.5bn, FY2028 CapEx $70bn; future growth 25/20/15/10% | User's unchanged [Lab 10](https://github.com/edheeres05/Proforma), carried to Q1-aware revision | Forecasts, not Oracle guidance; future Q2-Q4 = annual budget less actual Q1 |
| Archived Sept 10 peer pricing | MSFT $492.44, CRM $243.00, Oracle $152.94; diluted GAAP EPS MSFT $17.95, CRM $7.80, Oracle $5.83 | Student [Lab 08](https://github.com/edheeres05/ORCL_Research/blob/main/lab08_oracle.md), historical price feeds | Equity P/E archival comparison, not October quotes |
| EV/revenue peer inputs | MSFT revenue $331,839m, debt contractual principal $46,136m, liquidity $76,843m, cover shares 7,425.545m; CRM revenue $41,525m, debt principal ~$14,500m, liquidity $9,565m, cover shares ~923m | [MSFT FY2026 10-K](https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm); [CRM FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1108524/000110852426000060/crm-20260131.htm) | EV = Sep10 price * reported outstanding shares + financial debt - cash/short-term securities. MSFT debt principal not necessarily GAAP carrying; share counts not same day. Exclude operating leases consistently; only qualified comparisons. |
| ORCL closing stock price | $129.59 | [Stock Analysis](https://stockanalysis.com/stocks/orcl/history/), Oct 19, 2026 unadjusted closing row | Out-of-period market benchmark; NOT a defensible dated intrinsic comparison to Aug31 anchored DCF |

**Timestamp discipline:** The FY27 Q1 10-Q was not public on Aug 31. No source is described as if already known then; the workbench is a retrospective research diagnostic prepared October 19. Analyst adjustments, financial statement facts, and model assumptions remain labeled separately.
