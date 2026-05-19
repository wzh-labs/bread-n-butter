---
name: monitor-macro
description: Refresh the macro-economy snapshot under ~/knowledge/macro/ — pull the latest readings for the indicators in the catalog, write a dated snapshot, and surface what changed since the prior run. Use when the user asks to "monitor macro", "refresh macro", "update the macro snapshot", "check the macro tape", "where are we macro-wise", "/monitor-macro", or otherwise wants the macro layer brought up to date. Idempotent — re-running on the same day shows the existing snapshot unless explicitly forced. Designed to be invoked manually or wired into the daily routine.
---

# Monitor macro

Goal: keep `~/knowledge/macro/` current so any equity-research session has a fresh, dated read of the macro backdrop. The skill walks the indicator catalog, pulls the latest values, writes a new snapshot, and outputs a *delta-focused* summary — not the full snapshot — so the user sees what changed without re-reading what didn't.

This is the macro counterpart to [`research-public-company`](../research-public-company/SKILL.md). That skill tracks individual tickers; this one tracks the regime they all trade against.

## Inputs

All optional:
- **Force** — re-run even if today's snapshot exists. Default: read the existing snapshot and report it instead.
- **Event** — optional tag for a tier-1 release that triggered this run (e.g. `CPI`, `NFP`, `FOMC`, `PCE`, `ISM`). When set, the snapshot is named `YYYY-MM-DD-<event>.md` and the writeup emphasizes that release.

## Storage layout

Everything lives under `~/knowledge/macro/` (override with `$KNOWLEDGE_ROOT/macro`):

```
~/knowledge/macro/
  README.md                     # purpose, structure, refresh cadence
  indicators.md                 # CATALOG — source of truth for what to fetch (do not skip)
  calendar.md                   # rolling release calendar, ~30 days out
  snapshots/
    YYYY-MM-DD.md               # one per refresh; sometimes YYYY-MM-DD-<event>.md
```

**Always read `indicators.md` first.** It's the catalog of every series in the snapshot, grouped by mechanism (policy, rates, inflation, growth, labor, credit, FX/cross-asset, geopolitics, earnings). Adding or removing indicators is a catalog edit, not a skill edit — this keeps the skill stable as the user's interests evolve.

## Modes

### Initial mode (first time — empty `snapshots/`)

This is unusual; the macro layer was bootstrapped with a first snapshot. But if `snapshots/` is empty:
1. Run the full method.
2. Write `snapshots/<today>.md` from the snapshot template (see *Snapshot schema* below).
3. **Commit and push** (see *Git workflow*).
4. Output the full snapshot to the user.

### Delta mode (normal — at least one prior snapshot)

1. Locate the most recent file under `snapshots/` (lexicographic max — date-named files sort correctly).
2. Load its frontmatter and section tables — these are the *previous* values.
3. Run the full method, refreshing every indicator in `indicators.md`.
4. Compose the new snapshot with `prev → curr` inline in each table cell when the value changed (e.g. `4.55% → 4.61%`). If unchanged, just write the current value.
5. Update `calendar.md`: drop releases whose date is before today; append any new releases in the next ~30 days.
6. Compute the delta vs. the prior snapshot:
   - **Tier-1 changes:** any move in Fed funds target, a new FOMC statement, a new CPI/PCE/NFP/ISM print, a >10 bp move in 10Y yield or HY OAS, a >2% move in DXY, a regime-shift in the curve (inversion ↔ normalization), a new tier-1 geopolitical event.
   - **Tier-2 changes:** any *other* updated indicator value that materially shifts the regime read.
   - **No change:** if nothing tier-1 or tier-2 moved, output one line: *"No material macro changes since YYYY-MM-DD."* and **do not** write a new snapshot file or commit.
7. If delta is non-empty:
   - Write `snapshots/<today>.md` (or `snapshots/<today>-<event>.md` if `--event` is set).
   - Set the new snapshot's frontmatter `prev_snapshot: <prior file's date>` so the lineage is explicit.
   - **Commit and push** (see *Git workflow*).
   - Output the *delta brief* (see *Output formats*) — not the full snapshot. Mention the snapshot path so the user can open it.

## Idempotency

Before running anything:
1. Check whether `snapshots/<today>.md` exists (or `snapshots/<today>-<event>.md` for event runs).
2. If it exists and `--force` is not set: print one line — `Snapshot for <today> already exists at <path>. Regime: <regime from frontmatter>. Run with --force to refresh.` — then stop. Do not re-run web searches.
3. If `--force` is set: archive the existing file as `snapshots/<today>__superseded-<HH-MM>.md` before proceeding. Do not silently overwrite.

## Method

### 1. Read the catalog

Read `indicators.md` end to end. Build a working list of every indicator across all 8 groups. Note which ones are flagged ★ tier-1 — those *must* have a current value in every snapshot.

### 2. Load the prior snapshot

In delta mode, parse the most recent snapshot under `snapshots/`. Extract:
- Each indicator's value and `as of` date
- The prior regime call
- Any "key tensions" list (for narrative continuity in the new snapshot)

### 3. Fetch in parallel

Issue web searches and fetches in parallel — never serialize them. Group by indicator group; one batch per group. Reasonable search queries:

**Policy & rates**
- `Fed funds target range current` + `FOMC meeting [latest month] [year] decision`
- `CME FedWatch implied probability next FOMC`
- `10 year treasury yield [today/latest]` + `2 year treasury yield`
- `10Y TIPS real yield latest`

**Inflation**
- `US CPI [latest month] [year] year over year`
- `US core PCE [latest month] [year]`
- `US PPI [latest month] [year]`
- `5y5y forward inflation expectations latest`

**Growth & activity**
- `ISM manufacturing PMI [latest month] [year]`
- `ISM services PMI [latest month] [year]`
- `GDP advance estimate [quarter] [year]` + `Atlanta Fed GDPNow current`
- `US retail sales [latest month] [year]`
- `Conference Board LEI [latest month] [year]`

**Labor**
- `nonfarm payrolls [latest month] [year] unemployment rate`
- `JOLTS job openings [latest month] [year]`
- `initial jobless claims latest week`
- `labor force participation rate [latest month]`

**Credit & consumer**
- `ICE BofA high yield OAS latest` + `investment grade OAS latest`
- `SLOOS senior loan officer survey latest` (quarterly)
- `consumer credit G19 delinquencies latest`
- `UMich consumer sentiment latest` + `Conference Board consumer confidence latest`

**FX, cross-asset, volatility**
- `DXY dollar index level today`
- `VIX index today` + `MOVE index today`
- `WTI crude oil price today` + `gold price today`
- `copper gold ratio today`

**Global**
- `China NBS PMI [latest month] [year]` + `Caixin PMI`
- `ECB BOJ policy rate latest`
- `Baltic Dry Index latest`

**Earnings & equity internals**
- `S&P 500 forward EPS estimate latest FactSet`
- `S&P 500 forward PE ratio latest`
- `S&P 500 Q[n] [year] earnings season blended growth beat rate`

**Geopolitics**
- Current significant conflicts/sanctions/tariff regimes — search for headlines in the last 7 days touching oil supply, semiconductor exports, trade policy.

Prefer authoritative primaries when fetching (FRED, BLS, BEA, Federal Reserve releases, Treasury direct, ISM, BEA PCE page, FactSet Insight). Use commentary outlets (CNBC, TradingEconomics, Advisor Perspectives, Kiplinger) for color and context — never as the *only* source for a headline number.

### 4. Cross-check tier-1 numbers

For every ★ indicator, require **two independent sources** for the headline value, or label it `(reported by <source>, unverified)`. Be alert to:
- Reported vs. revised (e.g. NFP often gets significant revisions — note both)
- m/m vs YoY — never quote one without saying which
- SA (seasonally adjusted) vs NSA
- Headline vs core

### 5. Note what's missing or stale

If a release was expected by now but hasn't printed (government shutdowns, BLS delays, etc.), say so explicitly. If a source is rate-limited or paywalled, fall back and note the gap. Missing data is itself a signal.

### 6. Compose the new snapshot

Use the **exact section structure** of the most recent snapshot. Per cell, when the value changed:

```
| 10Y Treasury | 4.55% → **4.61%** | 2026-05-18 | 16-month high; touched 4.7% intraday. |
```

When unchanged, just write the current value with no arrow. Bold the new value when the change is tier-1.

Update the **regime read** at the top with a fresh 4–6 sentence paragraph. The regime read should explicitly call out *what changed since the last snapshot* — don't restate the prior read verbatim.

Update the **key tensions** list — keep tensions that are still live, retire ones that resolved, add new ones.

### 7. Refresh the calendar

Open `calendar.md`. Remove rows whose date is before today. Append any newly scheduled releases extending the horizon back out to ~30 days. Tier-1 releases stay marked ★.

### 8. Compute the delta

Side-by-side compare the new snapshot to the prior one. For each indicator group, build a bullet list of what changed. If a group has zero changes, drop that bullet entirely.

### 9. Write & commit

If the delta is non-empty:
1. Write `snapshots/<today>.md` (or event-tagged variant).
2. Save the calendar update.
3. Commit and push.

## What counts as a material change

**Always material (tier-1):**
- Any FOMC meeting outcome (rate move, statement language change, SEP/dot-plot revision)
- A new monthly CPI, core PCE, NFP, ISM-M, ISM-S print
- A new GDP advance/second/final estimate
- A new JOLTS or PPI print
- Yield curve inversion ↔ normalization
- A new SLOOS report (quarterly)
- A new earnings-season blended-growth update from FactSet
- A new geopolitical event affecting oil supply, China trade, or Fed credibility
- A >10 bp move in 10Y yield since the last snapshot
- A >25 bp move in HY OAS since the last snapshot

**Sometimes material (tier-2 — judgment call):**
- DXY move >2%
- VIX move >20% (e.g. 18 → 22)
- A new earnings revision >1% to forward CY EPS
- A notable Fed-speaker comment that moves rate-cut probabilities by >10 pp

**Never material (don't write a snapshot):**
- Intra-day market noise without a corresponding economic release
- Re-running on a weekend with no fresh prints
- Minor (<5 bp) yield moves
- Sentiment-only commentary without a data anchor

## Snapshot schema

`snapshots/<date>.md` matches the structure of the bootstrap snapshot. Frontmatter:

```yaml
---
date: 2026-05-19
prev_snapshot: 2026-05-12          # null in initial mode; otherwise prior snapshot's date
event: null                        # null | "CPI" | "NFP" | "FOMC" | "PCE" | "ISM" | "geopolitical"
regime: stagflation-tilt           # one short label: e.g. "risk-on", "stagflation-tilt", "soft-landing", "hard-landing-tilt", "deflation-scare"
---
```

Body sections (in order, mirror the bootstrap snapshot):
1. Regime read (4–6 sentences; call out what changed since `prev_snapshot`)
2. Monetary policy
3. Rates & yield curve
4. Inflation
5. Growth & activity
6. Labor
7. Credit & consumer
8. FX, cross-asset, volatility
9. Geopolitics
10. Earnings & equity internals
11. Key tensions for the next 2–4 weeks
12. Upcoming releases (next 30 days)

Tables use `| Indicator | Value | Date | Note |` columns. Sources go inline under each section as a `**Sources:**` line of markdown links.

## Output formats

### Delta brief (delta mode — the normal case)

After writing the snapshot, output to the user:

```
# Macro update — <YYYY-MM-DD>

**Regime:** <prior regime> → **<new regime>** (or "unchanged: <regime>")
**Snapshot:** [snapshots/<date>.md](snapshots/<date>.md)
**Prev:** [snapshots/<prev>.md](snapshots/<prev>.md)

## What changed
- **Monetary policy:** <changes, with prev → curr and one-line interpretation>
- **Inflation:** <…>
- **Labor:** <…>
- **Rates & curve:** <…>
- **Credit:** <…>
- **FX & vol:** <…>
- **Geopolitics:** <…>
- **Earnings:** <…>

(Drop any bullet whose answer is "no change".)

## Implications
2–4 sentences on what the changes mean for broad-market risk-on/off positioning. Concrete, not platitudes.

## Watch list — next 2 weeks
| Date | Release | Why it matters now |
|---|---|---|
| YYYY-MM-DD | <release> | <single sentence> |
```

If the delta is empty: output exactly one line — `No material macro changes since <YYYY-MM-DD>.` — and exit.

### Initial brief (initial mode)

Same as the bootstrap snapshot output: render the full new snapshot, then a one-line pointer to the file.

## Sources policy

**Headline numbers must come from primary sources:**
- BLS — CPI, PPI, NFP, ECI, JOLTS, productivity
- BEA — GDP, PCE, personal income
- Federal Reserve — FOMC statements, H.4.1 (balance sheet), H.15 (selected rates), SLOOS, G.17 (industrial production), G.19 (consumer credit)
- Treasury — daily par yield curve
- FRED — clean historical series for everything above + ICE BofA OAS
- ISM — Manufacturing and Services PMI
- Census — retail sales, durable goods
- Conference Board — LEI, consumer confidence
- UMich — consumer sentiment
- DOL — weekly UI claims
- CME — FedWatch implied probabilities
- ICE / BofA via FRED — OAS spreads
- FactSet Earnings Insight — forward EPS, beat rates, blended growth

**Acceptable for color/context (never as the sole source for a headline):**
CNBC, TradingEconomics, Advisor Perspectives, Yahoo Finance, Bloomberg, Reuters, WSJ, FT, Kiplinger, TD Economics.

**Always cite inline.** Every non-trivial value gets a source link in the section's `**Sources:**` line.

## Git workflow

`~/knowledge` is a git repo. Every successful run that *changes files* must be committed and pushed.

```bash
git add macro/
git commit -m "<message>"
git push
```

Commit message format:
- **Initial mode:** `monitor-macro: initial snapshot`
- **Delta mode (no event):** `monitor-macro: YYYY-MM-DD — <one-line summary of biggest delta>` (e.g. `monitor-macro: 2026-05-19 — 10Y at 4.61% (16-mo high), HY OAS still tight`)
- **Delta mode (event):** `monitor-macro: YYYY-MM-DD — <EVENT> print: <one-line summary>` (e.g. `monitor-macro: 2026-06-10 — CPI: May 4.0% YoY, core 2.9%`)

Rules:
- **Stage explicitly** — `git add macro/`. Never `git add -A` or `git add .`.
- **No commit on empty delta.** If the run produced no file changes (delta was empty), do not commit.
- **One commit per run.** Don't bundle other knowledge-base changes.
- **If `git push` fails** (no upstream, network, conflict), report it and stop. Do not force-push. The local commit remains.
- **Never** run destructive git operations as part of this skill.

## Style rules

- **Cite every number.** No phantom citations — only cite pages actually fetched this run.
- **Always name the period.** "CPI 3.8%" is meaningless without "(Apr 2026, YoY)".
- **Headline vs. core.** Always say which.
- **Reported vs. revised.** NFP especially — name the revision when relevant.
- **No marketing language.** "Sticky", "hot", "robust" are fine; "unprecedented", "historic" are usually not. State the number.
- **No editorializing.** "Stocks look expensive" — no. "Forward P/E 21.0 vs 10-yr avg 18.9" — yes.
- **No fabrication.** If a value can't be sourced this run, label it `(stale: last seen YYYY-MM-DD)` and move on.
- **Be terse in delta mode.** The full data is in the file; the chat output is the diff.
- **Use prev → curr inline.** Don't make the reader subtract.

## What to skip

- Don't explain what an indicator measures (the catalog already does).
- Don't include a generic "Why this matters" or "Conclusion" section.
- Don't speculate on what the Fed *should* do — surface what futures price.
- Don't restate the prior regime read verbatim — say what changed.
- Don't re-output the full snapshot in delta mode.
- Don't make stock picks — this skill is about the regime, not single names. (For tickers, defer to [`research-public-company`](../research-public-company/SKILL.md).)

## Integration with the daily routine

This skill can be added to `~/knowledge/daily-routine/config.yaml` as another task so the macro snapshot refreshes alongside trending GitHub, private companies, and public companies. The recommended schedule is **weekly on Fridays after the close**, plus event-triggered runs on tier-1 release days (CPI, NFP, FOMC, PCE, ISM). The daily routine can call this skill in plain delta mode and let the empty-delta short-circuit avoid noise on data-light days.
