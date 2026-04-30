---
name: research-public-company
description: Produce a structured intelligence brief on a public company from fundamentals to industry trends, or a delta if the company has been researched before. Use when the user asks to research, analyze, or profile a public company by ticker symbol (e.g. "$GOOGL", "$AAPL", "$NVDA") or company name. Covers financials, business segments, management, competitive position, industry trends, analyst sentiment, and risk factors.
---

# Research a public company

Goal: produce a dense, well-sourced intelligence brief on a publicly traded company, from financial fundamentals to industry positioning — OR, if the company has been researched before, a *delta* showing only what changed since the last run. Prioritize accuracy and recency over comprehensiveness; call out stale or unverified data explicitly.

## Inputs

Required (one of):
- Ticker symbol — `$GOOGL`, `NVDA`, `MSFT` (strip the `$` prefix if present; normalize to uppercase)
- Company name — resolve to the primary ticker before proceeding

**Ticker resolution**: if the user gives a company name without a ticker, do a quick web search (`<company> stock ticker`) and confirm before proceeding. If the ticker maps to multiple share classes (e.g. GOOG vs GOOGL), use the more liquid class and note the other.

## Storage layout

All findings live under `~/knowledge/public-companies/` (override with `$KNOWLEDGE_ROOT`). One directory per ticker:

```
~/knowledge/public-companies/<TICKER>/
  brief.md          # current canonical brief: YAML frontmatter + narrative
  changelog.md      # append-only delta log, newest on top
  snapshots/
    YYYY-MM-DD.md   # frozen point-in-time copies of brief.md
  sources.jsonl     # every cited URL with first-seen date and content hash
  filings/          # SEC primary documents, committed to git
    10-K-YYYY-MM-DD.htm
    10-Q-YYYY-MM-DD.htm
    8-K-YYYY-MM-DD.htm
    index.json      # accession numbers, form types, filing dates, local paths, source URLs
  transcripts/      # earnings call transcripts, committed to git
    Q<n>-YYYY.txt   # plain text, stripped of HTML/ads
    index.json      # period, call date, source URL, local path
```

`<TICKER>` is the uppercase ticker symbol (e.g. `GOOGL`, `NVDA`). **If `brief.md` exists, run in delta mode. Otherwise run in initial mode.** Always check with `ls` or equivalent before deciding.

## Modes

### Initial mode (first time researching)

1. Run the full method (below).
2. Download SEC filings into `filings/` (see *SEC filings* below): latest 10-K, last 4 10-Qs, 8-Ks from the past 90 days. Write `filings/index.json`.
   Then download the last 4 earnings call transcripts into `transcripts/` (see *Earnings call transcripts* below). Write `transcripts/index.json`.
3. Write `brief.md` with frontmatter + narrative.
4. Copy it to `snapshots/<today>.md`.
5. Create `changelog.md` with one entry: `## <today>\n- Initial brief.`
6. Write every cited URL into `sources.jsonl` with today's date.
7. **Commit and push** (see *Git workflow* below).
8. Output the full brief to the user.

### Delta mode (re-researching)

1. Load `brief.md`'s frontmatter and `sources.jsonl`.
2. Run the full method, biasing searches toward recency (e.g. add `after:<last_researched>` or the current quarter as a qualifier). Goal: find what's new, not re-confirm what's known.
3. Compute the delta:
   - **Frontmatter diffs:** revenue or earnings revision, guidance change, new segment, CEO/CFO change, M&A announcement, material dividend/buyback change, rating change, index inclusion/exclusion.
   - **New sources:** any cited URL not already in `sources.jsonl`.
   - **Content drift:** if a previously-cited page still resolves and its content hash changed materially (e.g. IR page updated guidance), note it.
4. If the delta is empty, output one line: *"No material changes since YYYY-MM-DD."* Do not modify any files.
5. If the delta is non-empty:
   - Update `brief.md` frontmatter to current values; update narrative sections that materially changed.
   - Download any new SEC filings since the last `filings/index.json` entry (compare by accession number). Add them to `filings/` and update `index.json`.
   - Download any new earnings call transcripts since the last `transcripts/index.json` entry (compare by `period`). Add them to `transcripts/` and update `index.json`.
   - Freeze a new `snapshots/<today>.md` copy.
   - Prepend a new dated entry to `changelog.md` with the deltas.
   - Append new cited URLs to `sources.jsonl`; update `cited_in` arrays for re-cited URLs.
   - **Commit and push** (see *Git workflow* below).
   - Output **only the changelog entry** to the user — not the full brief. Mention the brief path so they can open it for context.

Defaults for what counts as a change:
- **Strict frontmatter fields**: revenue, eps, guidance, market cap, price, dividend, buyback, key executives, segment mix, rating consensus, next earnings date. Always reported.
- **Cited-only source ledger**: only URLs actually cited in the brief land in `sources.jsonl`. Keeps it small and meaningful.
- **New SEC filings** since the last run always count as a delta — even if no other field changed, a freshly filed 8-K or 10-Q is a material event worth recording.

## Git workflow

`~/knowledge` is a git repository. Every successful research run must be committed and pushed.

Run from `$KNOWLEDGE_ROOT` (default `~/knowledge`):

```bash
git add public-companies/<TICKER>/
git commit -m "<message>"
git push
```

Commit message format:
- **Initial mode:** `research($TICKER): initial brief`
- **Delta mode:** `research($TICKER): <YYYY-MM-DD> — <one-line delta summary>` (e.g. `research($NVDA): 2026-04-28 — Q1 beat, raised FY guidance, Jensen interview`)

Rules:
- **Stage explicitly** — `git add public-companies/<TICKER>/`. Never `git add -A` or `git add .`. The recursive add picks up `filings/` automatically.
- **No commit on empty delta.** If the run produced no file changes, do not create a commit. New filings count as a change.
- **One commit per ticker per run.** Don't bundle multiple companies in one commit.
- **SEC filings are committed.** They can be 1–10MB each — that's expected. Don't gitignore `filings/`. If a filing is unusually large (>25MB), still commit it; flag it in the changelog.
- **Transcripts are committed.** Plain-text transcripts are small (~50–150KB). Don't gitignore `transcripts/`.
- **If `git push` fails** (no upstream, network, conflict), report it and stop. Do not force-push or rewrite history. The local commit remains on disk.
- **Never** run destructive git operations as part of this skill.

## Method

### 1. Resolve and orient

Confirm the ticker. Check what exchange it trades on, what index it's in (S&P 500, Nasdaq 100, Russell 2000, …), and what sector/industry classification it carries (GICS preferred). This frames the peer group for the rest of the research.

### 2. Gather in parallel

Issue web searches and fetches in parallel — do not serialize them. 10–15 searches in the first batch covering distinct angles:

**Fundamentals**
- `<ticker> OR <company> revenue earnings EPS latest quarter`
- `<ticker> annual report 10-K fiscal year`
- `<ticker> guidance outlook <current year>`
- `<ticker> free cash flow margin operating income`
- `<ticker> balance sheet debt cash`
- `<ticker> secondary offering equity raise convertible notes debt issuance <current year>`
- `<ticker> IPO history OR initial public offering date`

**Business & strategy**
- `<ticker> business segments revenue breakdown`
- `<ticker> product roadmap strategy`
- `<company> CEO CFO leadership`
- `<ticker> M&A acquisition partnership <current year>`
- `<ticker> investor day presentation`

**People & operations**
- `<company> employee count headcount <current year>`
- `<company> layoffs hiring workforce <current year>`

**Industry & competition**
- `<company> market share competitors <current year>`
- `<company> industry trends headwinds tailwinds`
- `<ticker> vs <peer> comparison`

**Sentiment & risk**
- `<ticker> analyst rating price target <current year>`
- `<ticker> risk factors lawsuit regulatory`
- `<ticker> news <current month and year>`

**Earnings calendar**
- `<ticker> next earnings date <current year>`
- `<company> Q<n> earnings call schedule`
- Cross-check against the IR page's events/calendar section — companies usually publish the date 3–6 weeks ahead. Resolve to an exact `YYYY-MM-DD` and note the time/timezone if disclosed (e.g. `after market close ET`). If no date is announced yet, set `next_earnings_date: null` and note the expected window in narrative.

Then `WebFetch` the highest-value pages:
- Company Investor Relations page (earnings releases, presentations)
- SEC EDGAR: latest 10-K and most recent 10-Q (`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=<ticker>&type=10-K`)
- Yahoo Finance or similar for live fundamentals snapshot
- Recent earnings call transcript or summary
- Reputable analyst coverage (Seeking Alpha, Bloomberg, Reuters, WSJ)

### 3. Cross-check financials

Quantitative claims (revenue, EPS, margin, market cap) require **two independent sources** or get labeled `(reported by <source>, unverified)`. Be alert to:
- Reported vs. adjusted (non-GAAP) figures — always name which metric you're quoting
- TTM (trailing twelve months) vs. latest quarter vs. fiscal year — always specify the period
- Consensus estimates vs. company guidance vs. actuals — distinguish them clearly
- Analyst price targets are opinions, not facts — present the range and consensus

### 4. Note what's missing

Call out unknowns explicitly (e.g. "segment-level margins not disclosed", "no granular geographic breakdown", "guidance paused due to macro uncertainty"). Missing data is itself a signal.

### 5. Download SEC filings

Pull the company's primary documents from EDGAR into `filings/`. These are the canonical source for everything else and worth keeping locally.

**What to download:**
- Latest **10-K** (annual report)
- Last 4 **10-Q**s (quarterly reports)
- All **8-K**s with `filingDate` within the past 90 days

Primary document only — skip exhibits (`EX-*`), XBRL files, and graphics. This keeps the repo lean while preserving the readable filing.

**How to fetch:**

1. **Resolve CIK from ticker.** Fetch `https://www.sec.gov/files/company_tickers.json` once and grep for the ticker; record the 10-digit zero-padded `cik_str`. Cache the value in `filings/index.json` so subsequent runs skip this step.

2. **List recent filings.** Fetch the submissions feed:
   ```
   https://data.sec.gov/submissions/CIK<10-digit-cik>.json
   ```
   The `filings.recent` object has parallel arrays — `accessionNumber[]`, `form[]`, `filingDate[]`, `primaryDocument[]`. Iterate them together. Filter to the forms above and the date windows above.

3. **Compute the document URL.** For each kept filing:
   ```
   https://www.sec.gov/Archives/edgar/data/<CIK-no-padding>/<accession-no-dashes>/<primaryDocument>
   ```
   where `<accession-no-dashes>` is the accession number with dashes stripped (e.g. `0001193125-26-012345` → `000119312526012345`).

4. **Download with a proper User-Agent.** SEC requires a contact header. Use:
   ```bash
   curl -A "claude-research-skill thomas.wang@vercel.com" -s -o "filings/<form>-<filingDate>.htm" "<url>"
   ```
   Throttle to <=10 req/sec (SEC's published limit). For ~6 files this is not a concern; just don't parallelize aggressively.

5. **Skip already-downloaded filings.** Before downloading, check `filings/index.json` for the accession number. If present, skip.

6. **Write/update `filings/index.json`.** Schema:
   ```json
   {
     "cik": "0001652044",
     "ticker": "GOOGL",
     "filings": [
       {
         "accession": "0001652044-26-000012",
         "form": "10-Q",
         "filing_date": "2026-04-25",
         "period_of_report": "2026-03-31",
         "primary_document": "goog10q1q26.htm",
         "local_path": "filings/10-Q-2026-04-25.htm",
         "source_url": "https://www.sec.gov/Archives/edgar/data/1652044/000165204426000012/goog10q1q26.htm",
         "downloaded_at": "2026-04-29"
       }
     ]
   }
   ```
   Sort `filings[]` by `filing_date` descending. On a re-run, merge: keep existing entries, add new ones.

7. **Filename collisions.** If two 8-Ks share a filing date, append a short accession suffix: `8-K-2026-04-25-12.htm`.

If EDGAR is unreachable or returns errors, log the failure in the changelog (`- **Filings:** EDGAR fetch failed (<reason>) — retry on next run`) and continue. Don't block the brief on filings.

### 6. Download earnings call transcripts

Pull the last **4 earnings call transcripts** into `transcripts/`. Cover the same window as the 10-Qs so the prepared remarks and Q&A line up with the financials.

**Source priority (try in order, stop at the first working source per quarter):**

1. **Company IR page** — many companies post a PDF or HTML transcript with the webcast replay. Search `<company> investor relations earnings call transcript Q<n> <year>`. Most authoritative when available.
2. **Motley Fool** — search `site:fool.com <company> earnings call transcript Q<n> <year>`. Free, broad, generally accurate prepared-remarks-and-Q&A format.
3. **Seeking Alpha** — `site:seekingalpha.com <company> earnings call transcript Q<n> <year>`. Increasingly gated; only use if the page renders the full transcript without login.
4. **8-K Item 2.02 / 7.01 prepared remarks** — already in `filings/`. If no transcript source has the Q&A, at minimum extract the prepared remarks from the relevant 8-K and save those, labeled `prepared-remarks-only`.

**How to fetch and store:**

1. For each of the last 4 fiscal quarters, identify the call date (usually the day of or after the earnings release).
2. `WebFetch` the source URL. If the page returns HTML with ads/nav, strip it down to the transcript text (intro → prepared remarks → Q&A → close). Save as plain UTF-8 text.
3. Filename: `Q<n>-<fiscal_year>.txt` (e.g. `Q1-2026.txt`). Use the company's fiscal calendar, not the calendar quarter, when they differ — check the 10-Q's "period of report" to disambiguate.
4. If only prepared remarks are available, suffix the filename: `Q1-2026-prepared-only.txt`.
5. **Skip already-downloaded transcripts.** Before fetching, check `transcripts/index.json` for the `period`. If present, skip.

**`transcripts/index.json` schema:**

```json
{
  "ticker": "GOOGL",
  "transcripts": [
    {
      "period": "Q1 2026",
      "call_date": "2026-04-25",
      "source": "fool.com",
      "source_url": "https://www.fool.com/earnings/call-transcripts/...",
      "local_path": "transcripts/Q1-2026.txt",
      "completeness": "full",
      "downloaded_at": "2026-04-29"
    }
  ]
}
```

`completeness` is one of `full` (prepared remarks + Q&A), `prepared-only`, or `partial` (paywalled or truncated — note in the field).

If no public transcript exists for a recent quarter (sometimes true for small caps or very recent calls), record an entry with `local_path: null` and `completeness: "unavailable"` so future runs don't re-attempt the same dead ends. Re-attempt unavailable ones once per delta run in case a transcript has since been published.

If a transcript fetch fails, log it in the changelog (`- **Transcripts:** Q<n> <year> fetch failed (<reason>)`) and continue.

## Frontmatter schema

`brief.md` starts with this YAML block. Keep field names stable across tickers.

```yaml
---
ticker: GOOGL
name: Alphabet Inc.
exchange: NASDAQ
sector: Communication Services      # GICS sector
industry: Interactive Media & Services
indices: [S&P 500, Nasdaq 100]
hq: Mountain View, CA, USA
founded: 1998
last_researched: YYYY-MM-DD

market_cap_usd: 2100000000000       # as of last_researched
price_usd: 170.00                   # as of last_researched
price_date: YYYY-MM-DD

financials:
  fiscal_year_end: December
  latest_annual:
    period: FY2025
    revenue_usd: 350000000000
    operating_income_usd: null
    net_income_usd: null
    eps_diluted: null
    free_cash_flow_usd: null
    gross_margin_pct: null
    operating_margin_pct: null
  latest_quarter:
    period: Q1 2026
    revenue_usd: null
    eps_diluted: null
    eps_beat_miss: null             # beat | miss | inline
    revenue_beat_miss: null
  guidance:
    period: Q2 2026
    revenue_low_usd: null
    revenue_high_usd: null
    notes: null
  next_earnings_date: null            # YYYY-MM-DD; null if not yet announced
  next_earnings_period: null          # e.g. Q2 2026
  next_earnings_time: null            # e.g. "after market close ET"; null if undisclosed

segments:
  - name: Google Services
    revenue_share_pct: null
  - name: Google Cloud
    revenue_share_pct: null
  - name: Other Bets
    revenue_share_pct: null

dividend:
  annual_usd: null                  # null if no dividend
  yield_pct: null

buyback:
  authorized_usd: null
  ttm_usd: null

capital_raises:                       # secondary offerings, debt, convertibles since IPO
  ipo_date: null
  ipo_price_usd: null
  recent:
    - type: null                      # secondary-offering | debt | convertible | other
      date: null
      amount_usd: null
      notes: null

executives:
  - name: Sundar Pichai
    role: CEO
    since: 2015
  - name: Anat Ashkenazi
    role: CFO
    since: 2024

headcount:
  value: null
  as_of: null
  source: null                        # press-release | SEC-filing | linkedin | self-reported

analyst_consensus:
  rating: Buy                       # Strong Buy | Buy | Hold | Underperform | Sell
  price_target_low_usd: null
  price_target_high_usd: null
  price_target_median_usd: null
  as_of: YYYY-MM-DD

competitors: [Meta, Microsoft, Amazon, Apple]
---
```

Use `null` for unknown numerics. Omit list fields entirely when actively unknown rather than writing `[]`.

## Output formats

### Initial brief (initial mode)

After the frontmatter, the narrative `brief.md` body:

```
# <Company Name> (<TICKER>)

**One-liner:** <what the business does, in one sentence — no marketing language>
**Sector:** <GICS sector> · **Exchange:** <NASDAQ/NYSE/…> · **Indices:** <S&P 500, Nasdaq 100, …>
**Market Cap:** $<X>T/B · **Price:** $<price> (as of <date>)
**Website / IR:** <url>

## Snapshot
5–7 bullets: the most important things a smart reader needs first (recent quarter result, guidance, next earnings date, big strategic move, key risk, analyst view).

## Business & segments
What the company does, revenue breakdown by segment, geographic mix, pricing model, major products.

## Financials
| Metric | Latest Quarter | Prior Quarter | YoY | Latest FY | Prior FY |
|--------|---------------|---------------|-----|-----------|----------|
| Revenue | | | | | |
| Gross Margin | | | | | |
| Operating Margin | | | | | |
| EPS (diluted) | | | | | |
| Free Cash Flow | | | | | |

Guidance for next period. Balance sheet highlights (cash, debt, net cash position).
Capital return (dividend yield, buyback authorization and pace).
Capital raises: IPO date/price, any secondary offerings, debt issuances, or convertible notes since IPO.
Next earnings call: date, period covered, time/timezone if disclosed; note "not yet announced" if missing.

## Management
CEO, CFO, and key operational leaders. Tenure, prior-company signal, any recent changes. Headcount (value, as-of date, source) and any notable workforce trends (layoffs, hiring plans).

## Competitive position & moat
Named competitors. Market share where available. Durable advantages (network effects, switching costs, scale, IP, regulatory moat). Positioning vs. peers.

## Industry trends
Tailwinds and headwinds for the sector/industry. Macro factors relevant to this company. Regulatory environment. Technology shifts.

## Analyst sentiment
Consensus rating (Buy/Hold/Sell split), price target range and median, notable upgrades/downgrades since last quarter. Street expectations for next quarter.

## Recent news & catalysts
Last 3–6 months: earnings, M&A, product launches, leadership changes, regulatory actions, activist investors, macro events that moved the stock.

## Risks & open questions
Top 3–5 concrete risks: regulatory, competitive, macro, execution, governance. Things that couldn't be verified and why they matter.

## Sources
Numbered list of URLs actually used, with one-line annotation each.
```

### Changelog entry (delta mode)

Prepend to `changelog.md`:

```
## <YYYY-MM-DD>
- **Earnings:** <quarter, beat/miss on revenue and EPS, key metrics>
- **Next earnings:** <prev date → new date, or "newly announced: <date>", or "still <date>" if unchanged but worth confirming>
- **Guidance:** <updated guidance vs. prior, if changed>
- **Financials:** <material changes to margin, FCF, balance sheet, capital raises>
- **Management:** <hires, departures, role changes, headcount prev → curr>
- **Strategy:** <M&A, new products, pivots, investor day highlights>
- **Analyst:** <consensus shift, notable upgrades/downgrades, target changes>
- **Industry:** <material macro or sector developments affecting the company>
- **News:** <1–3 most material items, with [n] citations>
- **Risks:** <new risks or risks resolved>
- **Filings:** <list new SEC filings since last run by form + date, e.g. "8-K 2026-04-22 (CFO transition), 10-Q 2026-04-25">
- **Transcripts:** <new transcripts saved this run, e.g. "Q1 2026 (fool.com, full)"; or fetch failures>
- **Sources added:** <n> new URLs — summarize what they say, don't just count
```

Drop any bullet whose answer is "no change". User-facing output in delta mode is exactly this entry plus: *"Full brief at `<path>`. Snapshot frozen at `<snapshot-path>`."*

### sources.jsonl format

One JSON object per line:

```json
{"url": "https://...", "first_seen": "2026-04-28", "cited_in": ["2026-04-28"], "content_hash": "<sha256-prefix>", "note": "Alphabet Q1 2026 earnings release"}
```

## Style rules

- **Cite inline** with `[1]`, `[2]`, … matching the Sources list. Every non-trivial claim gets a citation.
- **Always name the period.** Never say "revenue was $X" — say "Q1 2026 revenue was $X" or "FY2025 revenue was $X".
- **GAAP vs. non-GAAP.** Always state which you're quoting. When both exist, quote GAAP first, non-GAAP second.
- **No marketing language.** Strip adjectives like "revolutionary", "industry-leading", "transformative". State what the product actually does.
- **No fabrication.** If a figure isn't sourced, say so. Never invent earnings estimates or price targets.
- **Confidence labels:** `(high confidence)`, `(reported, unverified)`, `(estimate)`.
- **Analyst opinions are opinions.** Present price targets as a range + consensus; don't state them as fact.
- **Be concise.** A useful brief is 600–1,200 words of narrative plus the financials table.
- **Frontmatter is the source of truth for trends.** Mirror every key fact from narrative into frontmatter so future queries can roll up the corpus.

## What to skip

- Don't explain how stock markets work or what a P/E ratio is.
- Don't include a generic "Why this matters" or "Conclusion" section.
- Don't speculate on acquisition targets unless the user asks.
- Don't pull from sources you didn't actually fetch (no phantom citations).
- In delta mode, don't re-output the full brief — the user wants the diff.
- Don't editorialize about whether the stock is a "buy" — surface the analyst consensus and let the user decide.
