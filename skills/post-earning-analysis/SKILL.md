---
name: post-earning-analysis
description: Analyze a public company's just-reported earnings against its history and consensus expectations. Pulls the earnings 8-K and 10-Q from SEC EDGAR, the earnings call transcript, and trailing quarterly metrics, then layers in market reaction, analyst response, and qualitative themes from the call. Use when the user asks to "analyze earnings for $TICKER", "post-earnings analysis on NVDA", "how did GOOGL's earnings go", "break down AAPL's latest quarter", or similar — the company should have just reported (within ~10 trading days). Distinct from research-public-company, which produces a full-company brief; this skill is narrowly focused on the single earnings event.
---

# Post-earnings analysis

Goal: produce a tight, well-sourced analysis of a public company's most recent earnings report — the actuals vs. consensus and history, the call commentary, and the market/analyst response — and persist it for future reference. Treat the just-reported quarter as the unit of work; do not re-do a full company brief.

## Inputs

Required:
- Ticker symbol — `$NVDA`, `GOOGL`, `MSFT` (strip the `$` prefix; normalize to uppercase).

If the user gives a company name, do a quick web search (`<company> stock ticker`) and confirm before proceeding. If multiple share classes exist (GOOG vs GOOGL), use the more liquid class and note the other.

**Recency check.** Confirm earnings actually shipped recently. Search `<ticker> earnings <current month and year>` and look for a press release dated within the last ~10 trading days. If the latest earnings are older than that, ask the user whether they meant a prior report or want to re-analyze regardless. Don't silently analyze stale earnings.

## Storage layout

Reuses the `research-public-company` layout under `~/knowledge/public-companies/` (override with `$KNOWLEDGE_ROOT`). One directory per ticker:

```
~/knowledge/public-companies/<TICKER>/
  brief.md               # owned by research-public-company; read-only here
  filings/               # shared
    8-K-YYYY-MM-DD.htm
    10-Q-YYYY-MM-DD.htm
    index.json
  transcripts/           # shared
    Q<n>-YYYY.txt
    index.json
  earnings/              # owned by THIS skill
    Q<n>-YYYY.md         # one analysis per quarter, the canonical artifact
    index.json           # period, report date, beat/miss summary, stock reaction
    Q<n>-YYYY-followup.md  # optional: follow-up analysis if the user re-runs days later
```

If `~/knowledge/public-companies/<TICKER>/` does not exist, create it and proceed — this skill does NOT write `brief.md` or run the full company brief. If the user wants a full brief, suggest they run `/research-public-company` separately afterward.

If `earnings/Q<n>-YYYY.md` already exists for the just-reported quarter, run in **follow-up mode** (see *Modes* below) instead of overwriting.

## Modes

### Initial earnings analysis (first run for this quarter)

The default mode. Produces `earnings/Q<n>-YYYY.md` from scratch.

### Follow-up mode (re-running on the same quarter)

If `earnings/Q<n>-YYYY.md` already exists, the user is asking for an updated take — typically a few days after the report when more analyst notes and post-earnings drift data are available. Write `earnings/Q<n>-YYYY-followup-<YYYY-MM-DD>.md` with only what's new (analyst rating changes, T+1/T+5 stock drift, follow-on filings, management interviews). Do not overwrite the original analysis.

## Method

### 1. Resolve ticker and orient

- Normalize ticker, identify exchange and GICS sector/industry. Confirm the company actually reported.
- Identify the **just-reported period**: company fiscal quarter (e.g. "Q1 FY2026") and the **report date** (the day the press release dropped). Disambiguate fiscal vs. calendar quarter using the 10-Q's "period of report".

### 2. Pull SEC filings

Reuse the EDGAR fetch pattern from `research-public-company` (see that skill for full mechanics — CIK resolution, submissions feed, document URLs, User-Agent, throttling, `filings/index.json` schema). For this skill, download:

- The **8-K** filed on or near the report date — it contains the earnings press release as Exhibit 99.1 (Item 2.02). This is the canonical source for headline numbers and is usually filed within minutes of the press release.
- The **10-Q** for the just-reported quarter, if filed. (10-Qs often lag the 8-K by 1–4 weeks; if not yet filed, note it and rely on the 8-K + transcript.)
- For comparison: the prior **4 quarterly filings** (10-Qs and the latest 10-K covering the year-ago period). If `filings/` already has them from a prior `research-public-company` run, reuse — do not re-download.

Skip already-downloaded filings (check `filings/index.json` by accession number). Append new filings to `index.json`.

If EDGAR is unreachable, log it in the analysis and continue with web sources for headline numbers.

### 3. Pull the earnings call transcript

Use the source priority and storage convention from `research-public-company` (IR page → fool.com → seekingalpha.com → 8-K prepared remarks). Save as `transcripts/Q<n>-<fiscal_year>.txt` and update `transcripts/index.json`.

Transcripts often appear within 24 hours of the call. If the user runs this skill the same day as the report and no transcript is up yet, extract prepared remarks from the 8-K's Exhibit 99.x and save as `Q<n>-<fiscal_year>-prepared-only.txt`. Re-attempt the full transcript on follow-up runs.

### 4. Extract historical metrics

Build a quarterly time series from the prior 10-Qs and the latest 10-K. Pull each metric **directly from the filing**, not from analyst summaries — analyst sites often round, restate non-GAAP definitions, or mix segments.

Required series (last 5–8 quarters, plus year-ago quarter):
- **Revenue** (GAAP, total)
- **Revenue by segment** (if disclosed)
- **Gross profit** and **gross margin %** (GAAP)
- **Operating income** and **operating margin %** (GAAP and non-GAAP if reported)
- **Net income** (GAAP)
- **EPS, diluted** (GAAP **and** non-GAAP / "adjusted" — both, always labeled)
- **Free cash flow** (operating cash flow − capex)
- **Cash & equivalents** and **total debt** (latest balance sheet)
- **Share count, diluted** (for tracking dilution / buybacks)

For each metric in the just-reported quarter, compute:
- **QoQ %** change vs. immediate prior quarter
- **YoY %** change vs. same quarter last year
- **vs. consensus** (beat / miss / inline, with $ and % delta) — use Wall Street consensus from the search step below

Capture **guidance** explicitly:
- Prior guidance for the just-reported quarter (what the company said 90 days ago) → actual → was guidance beat/met/missed?
- New guidance for the next quarter and full year → vs. prior consensus for that period

### 5. Research online — earnings performance

Issue these searches in parallel. Bias toward the report date and the days following it.

**Pre-earnings expectations (consensus before the print)**
- `<ticker> earnings preview Q<n> <year>` (Zacks, Yahoo Finance, Seeking Alpha, Reuters)
- `<ticker> consensus revenue EPS estimate Q<n> <year>`
- `<ticker> whisper number Q<n> <year>` (optional, if covered)

**The print itself**
- `<ticker> Q<n> <year> earnings results beat miss`
- `<ticker> earnings press release <report-date>`
- `<ticker> guidance Q<n+1> outlook` (look for the company's forward guidance language)

**Market reaction**
- `<ticker> stock reaction after earnings <report-date>` — capture intraday move on report day, after-hours move (if reported AMC), and T+1 close. Note T+5 drift if available.
- `<ticker> stock price <report-date>` for the post-earnings session

**Analyst response (the most valuable signal)**
- `<ticker> analyst price target raised lowered <report-date>` (typically arrives T+1 to T+3)
- `<ticker> upgrade downgrade <month> <year>`
- `<ticker> analyst note Q<n> earnings`

**Themes from the call**
- `<ticker> earnings call <topic>` for any topic the prepared remarks emphasized (AI, margin, China, hyperscaler capex, AV, ad load, etc.)
- `<ticker> CEO CFO commentary Q<n> <year>` for soundbites that moved the stock during the call

**Peer / sector context**
- `<peer1 ticker> <peer2 ticker> earnings <month> <year>` if a peer reported the same week — investors will read the prints together.
- `<sector> earnings season <month> <year>` for sector-wide read-through.

Then `WebFetch` the highest-value pages: company IR earnings release page, 1–2 reputable analyst recap articles (Bloomberg, Reuters, WSJ, Barron's, FT), and the most-cited bull/bear takes.

### 6. Cross-check and mark unknowns

- Headline figures (revenue, EPS) require **two independent sources** or get labeled `(reported by <source>, unverified)`.
- Always specify GAAP vs. non-GAAP. When companies lead with "adjusted" numbers, quote GAAP first.
- Always specify the period (`Q1 FY2026`, not "this quarter").
- Mark unknowns explicitly: "segment margins not disclosed", "guidance withheld", "no analyst coverage on price target shifts yet (run follow-up in 3 days)".

### 7. Write the analysis

Write to `~/knowledge/public-companies/<TICKER>/earnings/Q<n>-<fiscal_year>.md`. Schema below.

### 8. Update the index

Append (or merge) an entry to `earnings/index.json`:

```json
{
  "ticker": "NVDA",
  "analyses": [
    {
      "period": "Q1 FY2026",
      "report_date": "2026-05-22",
      "report_time": "after market close ET",
      "revenue_actual_usd": 26000000000,
      "revenue_consensus_usd": 24650000000,
      "revenue_beat_miss": "beat",
      "eps_adjusted_actual": 5.98,
      "eps_adjusted_consensus": 5.59,
      "eps_beat_miss": "beat",
      "guide_next_q_revenue_low_usd": 28000000000,
      "guide_next_q_revenue_high_usd": 28500000000,
      "guide_vs_consensus": "above",
      "stock_reaction_t0_pct": 7.4,
      "stock_reaction_t1_pct": -1.2,
      "stock_reaction_t5_pct": null,
      "analyst_target_changes": "median PT raised $145 → $158 across 22 analysts",
      "local_path": "earnings/Q1-2026.md",
      "analyzed_at": "2026-05-23"
    }
  ]
}
```

Sort `analyses[]` by `report_date` descending.

### 9. Commit and push

`~/knowledge` is a git repo. Stage and commit:

```bash
git add public-companies/<TICKER>/
git commit -m "post-earnings($TICKER): <period> — <one-line headline>"
git push
```

Examples:
- `post-earnings($NVDA): Q1 FY2026 — beat top/bottom, raised next-Q guide, stock +7%`
- `post-earnings($GOOGL): Q1 2026 — Cloud accel offset by Search miss, flat reaction`
- `post-earnings($META): Q4 2025 follow-up — analyst PTs caught up, stock recovered T+5`

Rules carry over from `research-public-company`: stage explicitly (no `git add -A`), one commit per ticker per run, no commit on a no-op run, never destructive, stop and report if `git push` fails.

### 10. Output to user

Produce the **summary** described in *Output* below — keep it tight; the canonical detail lives in the file.

## Analysis file schema (`earnings/Q<n>-YYYY.md`)

```markdown
---
ticker: NVDA
name: NVIDIA Corporation
period: Q1 FY2026
report_date: 2026-05-22
report_time: after market close ET
analyzed_at: 2026-05-23
fiscal_year_end: January

headline:
  revenue_usd: 26000000000
  revenue_consensus_usd: 24650000000
  revenue_yoy_pct: 262.0
  revenue_qoq_pct: 18.0
  revenue_beat_miss: beat
  revenue_surprise_pct: 5.5
  eps_gaap_diluted: 5.16
  eps_adjusted_diluted: 5.98
  eps_consensus_adjusted: 5.59
  eps_beat_miss: beat
  gross_margin_gaap_pct: 78.4
  gross_margin_adjusted_pct: 78.9
  operating_margin_gaap_pct: 64.9
  free_cash_flow_usd: 14900000000

guidance:
  prior_q_guide_revenue_midpoint_usd: 24000000000   # what they said 90 days ago for the just-reported quarter
  prior_q_guide_outcome: beat                       # beat | met | missed
  next_q_revenue_low_usd: 28000000000
  next_q_revenue_high_usd: 28500000000
  next_q_revenue_consensus_usd: 26800000000
  next_q_guide_vs_consensus: above                  # above | inline | below
  fy_revenue_guide_change: raised                   # raised | maintained | lowered | withdrawn | not-given

market_reaction:
  pre_print_close_usd: 949.50
  after_hours_pct: 6.8
  t1_close_pct: 7.4
  t5_close_pct: null                                # fill on follow-up
  options_implied_move_pct: 8.5                     # if known

analyst_response:
  pt_changes_count: 22
  pt_median_before_usd: 145
  pt_median_after_usd: 158
  upgrades_count: 1
  downgrades_count: 0
  notable_calls:
    - firm: Morgan Stanley
      action: raised PT $130 → $160
      thesis: data center demand visibility extended into FY2027
    - firm: Bernstein
      action: maintained Hold, PT $120
      thesis: gross margin compression risk in next 2 quarters

themes_from_call:
  - data-center revenue concentration in top-3 hyperscalers
  - Blackwell ramp commentary
  - sovereign AI demand
  - China export-control headwind

risks_called_out:
  - gross margin to compress sequentially as Blackwell ramps
  - inventory build ahead of demand
  - customer concentration

sources_count: 14
---

# NVIDIA (NVDA) — Q1 FY2026 post-earnings analysis

**Report:** 2026-05-22 after market close · **Analyzed:** 2026-05-23

## Bottom line
2–3 sentence headline. What was the print, did it beat, did the stock move, and what's the single most important takeaway for someone who only reads this paragraph.

## Headline numbers vs. consensus and history

| Metric | Q1 FY26 actual | Consensus | Surprise | YoY | QoQ | Q1 FY25 |
|--------|---------------|-----------|----------|-----|-----|---------|
| Revenue | | | | | | |
| Gross margin (GAAP) | | | | | | |
| Operating margin (GAAP) | | | | | | |
| EPS, diluted (GAAP) | | | | | | |
| EPS, diluted (adjusted) | | | | | | |
| Free cash flow | | | | | | |

(All figures from <8-K accession #> and <10-Q accession # if filed>.)

## Trailing trend
A 5–8 quarter view of the metrics that matter most for this company. Markdown table or short prose. Highlight inflections (margin reversal, growth deceleration, capex step-up).

## Segment results
For each disclosed segment: revenue, YoY, QoQ, what management attributed it to. Call out any segment that diverged from the headline.

## Guidance
- What they said about the just-reported quarter 90 days ago → actual → outcome.
- New guidance for next quarter and FY (if given). Vs. consensus.
- Tone shift in guidance language ("strong demand visibility" → "moderating demand"), if any.

## What management emphasized on the call
3–6 bullets of the most important commentary. Quote sparingly, paraphrase mostly. Distinguish prepared remarks from Q&A — analyst questions often expose the real concerns.

## Market reaction
- Stock move: after-hours, T+1, T+5 (if known).
- vs. options-implied move (was the move bigger or smaller than priced in?).
- vs. peer reactions (did peers move sympathetically?).

## Analyst response
- Median price target before → after.
- Notable rating actions (with firm, action, thesis).
- Bull case summary (1–2 sentences).
- Bear case summary (1–2 sentences).

## Risks and watch-items
What this print introduced or amplified. What the next print needs to show to keep the thesis intact.

## Open questions
Things that couldn't be answered from the filings + transcript + analyst response. What additional disclosure or follow-up data would resolve them. Used as the agenda for follow-up runs.

## Sources
Numbered list of URLs actually used. Each gets a one-line annotation.
```

## Summary output to the user

After writing the file, output to chat — keep it tight. The canonical artifact lives in the file.

```
# <Company> (<TICKER>) — <period> earnings

**Headline:** <one line: beat/miss on revenue, EPS, plus the stock move>
**Revenue:** $<X>B (<beat/miss> consensus by <Y>%, <YoY>% YoY)
**EPS (adjusted):** $<X> (<beat/miss> by $<Y>)
**Guidance:** <above/inline/below> consensus for next Q; <raised/maintained/lowered> FY
**Stock:** <T0 / T+1 move>; <peer-relative note if relevant>
**Analyst response:** <median PT change, count of upgrades/downgrades>

## What's new vs. prior quarters
3–5 bullets. Inflections in growth, margin, FCF, guidance tone, segment mix.

## Themes from the call
3–5 bullets — what management emphasized, what analysts pressed on.

## Bull / bear after the print
- **Bull:** 1 sentence
- **Bear:** 1 sentence

## What to watch into next quarter
2–3 concrete items.

Full analysis: `~/knowledge/public-companies/<TICKER>/earnings/Q<n>-<fiscal_year>.md`
```

In follow-up mode, replace this with a tighter delta:

```
# <Company> (<TICKER>) — <period> follow-up (<YYYY-MM-DD>)

- **Stock:** T+5 drift, vs. peers
- **Analyst:** new PT/rating actions since initial analysis
- **Filings:** any 10-Q or 8-K that landed since
- **Disclosures:** management interviews, conferences, or new commentary

Follow-up at: `<path>`
```

## Style rules

- **Cite inline** with `[1]`, `[2]`, … matching the Sources list. Headline figures get a citation tied to a specific filing or press release.
- **Always name the period.** "Q1 FY2026 revenue", not "this quarter".
- **GAAP vs. non-GAAP.** Always state which. When both exist, GAAP first, non-GAAP second. The press release usually leads with non-GAAP — don't mirror that bias.
- **Quote consensus precisely.** Cite the source and the date as of (consensus drifts hour by hour into earnings).
- **Beat / miss is binary, surprise % is signed.** A 0.1% beat is a beat — but flag thin beats explicitly. A "miss with raised guidance" is more bullish than a "beat with cut guidance" — surface that combination clearly.
- **Stock reaction is multi-window.** Always report at least the T+0 (after-hours or close-of-print-day) and T+1 close. T+5 is preferred but often unavailable on day-of.
- **Analyst reactions matter more than analyst opinions.** A median PT shift is a signal; one firm's Hold is noise.
- **No fabrication.** If consensus or a price target isn't sourced, say so. Never invent.
- **Confidence labels:** `(high confidence)`, `(reported by <source>, unverified)`, `(estimate)`.
- **Be concise.** A useful analysis is 600–1,000 words of narrative plus the metrics table.

## What to skip

- Don't re-do the full company brief — that's `research-public-company`. Reference `brief.md` if it exists and only update fields directly tied to this print.
- Don't editorialize "buy / sell" — surface analyst consensus and the bull/bear cases, let the reader decide.
- Don't speculate on stock direction beyond what analysts and the options market are saying.
- Don't pull from sources you didn't actually fetch.
- Don't include a generic "Why this matters" or "Conclusion" section.
- Don't analyze stale earnings without the user's explicit confirmation.
