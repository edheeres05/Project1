# Oracle (ORCL) - FIN 439 Project 1: Pro Forma Research Workbench

**AI-assisted educational analysis; human investment judgment required. This is not investment advice.**

**Decision user:** Buy-side analyst committee, no ORCL position per course mandate. **Status:** WATCH/DEFER initiation pending a date-aligned, independently supported valuation. **Prepared:** 2026-10-19. **Unit convention:** USD millions unless stated otherwise. **Shares:** millions of Sept 7, 2026 cover shares, **not** a fully diluted market share count.

## What it does

- Five linked forecast periods: remaining 9 months of FY2027 (Q2-Q4) plus full FY2028-FY2031. Reports FY2027 actual Q1 separately. Anchors reported balances at 2026-08-31. Links income, cash flow, balance sheet and signed FCFF. Frozen source accounting rules; changes are made only through scenario drivers.
- Bounded **six-driver panel**: FY2028-FY2031 growth shift, FY2028 CapEx, pre-depreciation gross margin, WACC, terminal growth, additional FY2032 reinvestment. Reset restores base. A check-break demonstration changes only a temporary **copy**, raises a meaningful error, and permits reset.
- Base, directional one-at-a-time sensitivities, WACC/terminal-growth changes, synthetic known-answer check (legacy revision), enterprise-to-common bridge, reverse DCF, and September 10 archived MSFT/CRM peer policy and multiples.
- **Warning:** This is a research workbench, not a verified intrinsic valuation: reported Q1 balances were published after Aug 31; a September-October cash-flow stub, fully diluted shares, cost of capital and FY2032 maintenance/reinvestment are unresolved.

## Windows VS Code quickstart

Extract the **entire** ZIP so `.py` files remain in the same folder. Install Python 3 from python.org and in VS Code choose Terminal > New Terminal:

```powershell
py orcl_project1_application.py                # graphical app, no extra package
py orcl_project1_application.py --summary      # terminal-only mode
py orcl_project1_application.py --tests        # 12 reproducible tests
py orcl_project1_application.py --demo-failure # intentionally detects broken cash
py orcl_project1_application.py --export       # refreshes output/visible_output.json
```

No `pip install` is required (Python standard library, including Tkinter desktop GUI). On a Python distribution without Tkinter or in a headless environment use `--summary`, `--tests` and `--export`.

## Interpreting results - do not conceal failed checks

| Output | Base-case result | Qualification |
|---|---:|---|
| Illustrative per-share model diagnostic | $57.72 | Not a tradable date-aligned or verified target |
| Illustrative terminal share of EV | 95.8% | Extremely high, alerts on >80% |
| Signed FCFF FY2027 remainder / FY2028 | $-31,645m / $-8,720m | Negative periods are included in DCF |
| FY2028 CapEx +10% | **INVALID** | Fails liquidity/financing constraints - cannot assign a valuation |
| Committee action | **WATCH/DEFER** | Conditional, not an asserted market mispricing |

The current model uses **FY2027-FY2031** ending forecasts but its Q1 balance anchor is August 31, 2026. Comparison to the **Oct 19 closing ORCL quote $129.59** is a scale diagnostic only: it is *not* a time-consistent investment return or forecast. Market source: https://stockanalysis.com/stocks/orcl/history/.

## Files

| Path | Purpose |
|---|---|
| `orcl_project1_application.py` | Command line, JSON export, validation, and adjustable desktop workbench |
| `orcl_project1_post_q1_proforma.py` | Forecast and accounting invariant engine (Rev 3, unchanged) |
| `orcl_project1_valuation_bridge.py` | DCF and source-cash, debt and claims bridge (Rev 4, unchanged) |
| `orcl_project1_q1_bridge.py` | Q1 financial filing reconciliation (Rev 2, unchanged) |
| `orcl_proforma_EthanHeeres.py` | Original Lab 10 pro forma, unchanged |
| `orcl_project1_fcff.py` | First signed FCFF revision and known-answer fixture |
| `output/visible_output.json` | Fully serialized audit and scenarios (view without code) |
| `output/validation_log.txt` | 12 automated tests run 2026-10-19 |
| `docs/` | Committee memo, source ledger, assumptions, validation, Edition B draft and manifest |
| `legacy/` | Earlier revisions/results for audit trail |

**Submission integrity:** The earlier `Project_1_Edition_A_ORCL.md` was recovered unchanged (SHA-256 `f5a7443624ddd7bec59e5f65fd702e2f62c828b850cff2249c0caba84ef9e6af`). `Research-Evolution.pdf` contains a new *rendered copy*, not proof of the original Brightspace PDF or receipt. Confirm those prior submission records. Videos and corrected transcripts still require genuine recordings. All finance documents need student review and verification.

**Prepared written files:** `Research-Evolution.pdf`, `Decision-Memo.pdf`, `Validation-and-AI-Use.pdf`, `Edition-B-REVIEW-DRAFT.pdf`.  
**Other materials:** `docs/research-evolution.md` (A-to-B table), `docs/edition-b.md`, `docs/submission-manifest.md`, `docs/video-recording-guide.md` (not actual transcripts), and the original `.md` Edition A source.  
**Student actions:** confirm original Edition A receipt/PDF, review numbers and attribution, push repository, record three videos, transcribe each actual recording and submit Brightspace.
