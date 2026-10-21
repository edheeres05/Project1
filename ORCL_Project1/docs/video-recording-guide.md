# Oracle Project 1 | Recording guide (NOT transcripts)

**Order:** Get repository uploaded and review the model first; film Video 2 and Video 3 with the actual running tool, and Video 1 once `Research-Evolution.pdf` has been read. The finished videos require accurate transcript files, which cannot be produced before the recordings.

## Video 1 - Research Evolution (<= 3 minutes)

**0:00-0:20** Introduce the committee decision and original Edition A: watch/defer because cloud growth was promising but CapEx and debt were risky. Show original source or source PDF.  
**0:20-1:10** Explain Labs 06/08 (initial DCF and MSFT/CRM peer policy) and Labs 10/11 (three statements, stress cases, Aidan's growth questions).  
**1:10-2:05** Explain post-Q1 revisions and how Nicole's finance questions refined the research. Point to the actual A-to-B table.  
**2:05-2:50** The conclusion didn't flip; the reasons are clearer: signed early negative FCFF, cash funding constraints and 95.8% terminal EV. Explain what could change your decision.

## Video 2 - Code & Validation (<= 5 minutes)

Open VS Code with the extracted `ORCL_Project1` folder.  
**0:00-0:45** Explain dated financial inputs, forecast timing, independent/provisional versus filing-based assumptions.  
**0:45-1:35** Run `py orcl_project1_application.py --summary` and point out the $57.72 diagnostic is NOT a validated target.  
**1:35-2:30** Run `py orcl_project1_application.py --tests` (12 software tests) and describe balance/cash/bridge checks.  
**2:30-3:20** Run `py orcl_project1_application.py --demo-failure` and show the deliberate failure is detected.  
**3:20-4:45** Show `output/visible_output.json`, the known-answer DCF reconciliation, locked historical Lab 11 change/prediction, and one AI output you independently checked. Name limitations: WACC, terminal-year reinvestment, mixed as-of bases, fully diluted shares.

## Video 3 - Committee Recommendation (<= 5 minutes, LIVE PRODUCT DEMO FIRST)

**0:00-0:20** Open `py orcl_project1_application.py` live on camera; point to bounded drivers.  
**0:20-0:55** Move FY2028 CapEx to **+10%**. Explain the red invalid financing/check and why no value should be displayed; then use **Reset**.  
**0:55-1:20** Change growth +2 percentage points, compare with $57.72 base and restore. A directionally higher indicative value does not prove the forecast.  
**1:20-2:00** State mandate and **WATCH/DEFER** decision.  
**2:00-3:10** Explain FY2027 remaining signed FCFF -$31.65bn, FY2028 -$8.72bn and terminal share 95.8%. Compare dated P/E peers without averaging.  
**3:10-4:20** Explain funding, debt and why the $57.72 diagnostic cannot justify initiating a position.  
**4:20-4:55** State committee ask, three conditions for re-evaluation and what would make you reject.

## After recording

Use each video's actual words/captions to make a `transcript-video-1.txt`, `transcript-video-2.txt`, and `transcript-video-3.txt`. Correct wrong numbers, spelling and finance terms. Add URLs and durations to `docs/submission-manifest.md`. Do not claim these preparation cues are the video's transcript.
