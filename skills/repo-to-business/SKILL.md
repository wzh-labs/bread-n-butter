---
name: repo-to-business
description: Evaluate GitHub repos for business potential and synthesize cross-repo stack opportunities — either for a specific repo or a batch scan of the latest trending brief from research-trending-github. Use when the user asks to "evaluate repo X as a business", "what repos could I build a business on", "scan trending repos for opportunities", "could these repos work together as a business", "find stack opportunities in trending repos", or similar. Produces per-repo opportunity briefs AND a synthesis layer that identifies which repos combine into a more compelling product than any single one alone.
---

# Repo to business

Goal: given one or more GitHub repos, do two things:

1. **Per-repo**: evaluate whether each repo represents a real business opportunity on its own.
2. **Synthesis**: look across all evaluated repos and identify combinations — stacks, bundles, or "glue" ideas — where two or more repos together form a more compelling product than any single one alone.

The synthesis pass is the more important output. Individual repos are inputs; the interesting question is what product emerges when you combine the right pieces.

Do not produce generic "here's how to monetize open source" advice. Every claim about market size, competition, or monetization should be grounded in research.

## Inputs

Required (one of):
- A GitHub repo URL or `owner/repo` slug
- The keyword `trending` or `latest` — scan repos from the most recent `research-trending-github` brief

Optional:
- A filter: language, topic, or minimum star threshold
- A focus angle: `saas`, `managed-hosting`, `enterprise`, `services`, `marketplace`, `developer-tools`
- A constraint: solo founder, small team, bootstrapped, VC-backable

If the user says "trending repos" with no other input, default to the latest daily brief, top 15 repos by star velocity.

## Storage layout

All findings live under `~/knowledge/repo-to-business/` (override with `$KNOWLEDGE_ROOT`).

```
~/knowledge/repo-to-business/
  scans/
    YYYY-MM-DD.md           # batch scan brief: ranked individual opportunities + synthesis summary
  stacks/
    <stack-slug>.md         # individual stack brief: current canonical version
    <stack-slug>--YYYY-MM-DD.md  # frozen snapshot per revision
  <owner>--<repo>/
    opportunity.md          # current evaluation: YAML frontmatter + narrative
    changelog.md            # append-only revision log, newest on top
    snapshots/
      YYYY-MM-DD.md         # frozen copies of opportunity.md
```

`<owner>--<repo>` uses double-dash to separate owner and repo (e.g. `vercel--next.js`). **If `opportunity.md` exists, run in revision mode.**

`<stack-slug>` is a kebab-case name for the business concept (e.g. `ai-ops-platform`, `local-first-sync-stack`). Stack briefs are updated in place when the constituent repos change; snapshots track revisions.

## Modes

### Single-repo mode

1. Fetch the repo's README, GitHub page, and star history.
2. Run the full evaluation method (below).
3. Write `opportunity.md`.
4. Copy to `snapshots/<today>.md`.
5. Create `changelog.md` with one entry: `## <today>\n- Initial evaluation.`
6. Write cited URLs to `research.jsonl` (same format as other skills).
7. **Commit and push** (see *Git workflow*).
8. Output the full evaluation.

### Batch / trending mode

1. Locate the most recent brief under `~/knowledge/github-trending/briefs/` — use the latest file by date.
2. Extract the repo list (parse the brief's repo cards). Apply any language/topic/star filters from input.
3. For each repo, check if `opportunity.md` already exists:
   - If yes and last evaluated within 14 days: skip (include in "already evaluated" list).
   - If yes and older than 14 days: run revision mode.
   - If no: run initial single-repo mode.
4. Run individual evaluations in parallel (up to 5 at a time) — do not serialize.
5. **Run the synthesis pass** (see *Synthesis method* below) across all evaluated repos, including previously-evaluated ones that were skipped in step 3. The synthesis pass always runs on the full pool, not just new additions.
6. Write `scans/<today>.md` — ranked individual opportunities + synthesis section (see output format).
7. Write or update `stacks/<stack-slug>.md` for each identified stack (new or changed).
8. **Commit and push** for the scan file, any new/updated `opportunity.md` files, and any stack briefs.
9. Output the scan brief.

### Revision mode

1. Load existing `opportunity.md` frontmatter.
2. Re-fetch the repo (check for star growth, new releases, README changes, forks, issues).
3. Run targeted research: what's changed in the competitive landscape since last evaluation?
4. If no material changes: output one line and stop. Do not modify files.
5. If changes: update `opportunity.md`, freeze snapshot, prepend changelog entry, commit and push. Output the changelog entry only.

## Git workflow

`~/knowledge` is a git repository. Every successful run must be committed and pushed.

```bash
git add repo-to-business/
git commit -m "<message>"
git push
```

Commit message format:
- **Single initial:** `repo-to-business(<owner>--<repo>): initial evaluation`
- **Single revision:** `repo-to-business(<owner>--<repo>): <YYYY-MM-DD> — <one-line delta>`
- **Batch scan:** `repo-to-business: scan <YYYY-MM-DD> — <n> repos, <k> individual opportunities, <j> stacks`
- **Stack update:** `repo-to-business(stack/<stack-slug>): <YYYY-MM-DD> — <one-line change>`

Rules: stage explicitly, no commit on empty delta, one commit per run, no force-push, no destructive operations.

## Evaluation method

### 1. Understand what the repo actually is

Read the README, recent releases, and open issues. Do not rely on the GitHub description alone — it is often stale or vague. Identify:
- What problem it solves, for whom
- Whether it's a library, framework, CLI tool, service, dataset, or something else
- How it's currently used (check dependent repos, forks, integrations)
- Who is contributing (solo maintainer, small team, company-backed)

### 2. Research the commercial landscape in parallel

Issue searches in parallel:

- `<repo topic> commercial alternatives SaaS`
- `<repo topic> market size TAM <current year>`
- `<repo topic> startup funding crunchbase`
- `<repo topic> enterprise pricing`
- `<repo name> competitors`
- `<repo name> hosted service`
- `<repo maintainer or org> company funding`
- Recent news: `<repo name> <current year>`

Fetch the homepages or Crunchbase profiles of 2–3 closest commercial competitors.

### 3. Identify the business angle

For each repo, test these angles in order — most repos fit one or two clearly:

| Angle | Fits when | Example |
|-------|-----------|---------|
| **Managed hosting** | Self-hosting is painful; devs want it running, not maintained | Supabase → hosted Postgres |
| **SaaS wrapper** | The raw tool needs UX, auth, billing, teams | Metabase → hosted BI |
| **Enterprise features** | OSS core is solid; companies need SSO, audit logs, SLA | GitLab, HashiCorp model |
| **Vertical SaaS** | The tool solves a general problem; a specific industry needs it packaged | generic RAG → legal discovery |
| **Developer tools / platform** | The repo is infrastructure; tooling around it is the business | dbt → dbt Cloud |
| **Services / consulting** | Complexity is the moat; implementation beats productization | Kubernetes → managed K8s consulting |
| **Marketplace / ecosystem** | The repo enables plugins, models, or integrations others will sell | LangChain → agent marketplace |

Dismiss angles that don't fit — don't list all seven if only one or two are real.

### 4. Stress-test the opportunity

Before scoring, explicitly answer:
- **Why hasn't this been built yet?** (If it has, who built it and why might a new entrant still win?)
- **Who pays, and how much?** (Estimate willingness-to-pay from comparable tools.)
- **What is the moat?** Network effects, data, switching costs, distribution — be specific.
- **What's the hardest thing?** Distribution, trust, enterprise sales cycle, regulatory, etc.
- **Founder fit requirements:** What background, network, or credibility does the founder need?

### 5. Score

Use a simple 3-point rubric per dimension — not a made-up decimal score:

| Dimension | 1 | 2 | 3 |
|-----------|---|---|---|
| **Market pull** | Niche / hobbyist | Real pain, limited addressable market | Large, growing, underserved |
| **Monetization clarity** | Unclear who pays or how much | Plausible model, needs validation | Clear buyers, comparable pricing exists |
| **Competitive window** | Crowded or large incumbent owns it | Some competition, differentiation possible | Open field or weak incumbents |
| **Build feasibility** | Deep moat to replicate / defend | Moderate complexity | Lean team can execute in months |
| **OSS leverage** | OSS is incidental | OSS gives some distribution | OSS community is the GTM |

Total: 5–15. Flag as **Strong (12–15)**, **Worth exploring (8–11)**, **Pass (5–7)**.

## Synthesis method

Run this after all individual evaluations are complete. The goal is to find combinations of repos that form a product more defensible, complete, or compelling than any single repo alone.

### 1. Build the pool

Collect all repos with a verdict of **Strong** or **Worth exploring** from the current scan, plus any previously evaluated repos in `~/knowledge/repo-to-business/` with those verdicts. Pass-rated repos are excluded unless you have a specific reason to include one as supporting infrastructure.

### 2. Identify combination patterns

For each pair or small group of repos in the pool, test these patterns:

| Pattern | Signal | Example |
|---------|--------|---------|
| **Vertical stack** | Repos solve adjacent layers of the same problem (data, compute, API, UI) | inference engine + prompt router + observability = AI ops platform |
| **Core + distribution** | One repo is powerful but hard to use; another provides the UX, SDK, or workflow that makes it accessible | headless search engine + embeddable UI components = hosted search-as-a-service |
| **Shared user + adjacent pain** | Two repos target the same persona solving different but related problems — bundle reduces switching cost | local-first sync lib + CRDT conflict resolver = collaboration infrastructure |
| **Glue opportunity** | Two strong repos don't integrate with each other; the missing connector is the product | ETL framework + vector store = data pipeline for RAG applications |
| **Data flywheel** | Combining two repos generates a proprietary dataset neither alone could produce | web scraper + structured extraction model = training data marketplace |
| **Enterprise bundle** | Multiple OSS tools that enterprises want managed under one SLA, one support contract | identity + secrets + audit logging = compliance infrastructure platform |

Dismiss patterns that don't fit — do not force combinations that lack a real synthesis thesis.

### 3. For each identified stack

Answer these questions before writing the brief:
- **What is the product?** One sentence a customer could understand — not a list of repos.
- **What does each repo contribute?** Be specific: which layer, which capability.
- **What is still missing?** Gaps in the stack (repos, proprietary data, distribution, sales motion) that the team must build or acquire.
- **Why is this better than each repo alone?** If the answer is just "more features," it's not a stack — it's a bundle. A real stack has emergent properties: stickiness, data, defensibility that didn't exist in the parts.
- **Who is the natural builder?** Someone already deep in one of the communities? An OSS maintainer? A company that uses all of them?
- **What's the fastest path to $1M ARR?** Forces specificity about the go-to-market.

### 4. Score the stack

Same 3-point rubric, plus a **Synthesis strength** dimension:

| Dimension | 1 | 2 | 3 |
|-----------|---|---|---|
| **Market pull** | Niche / hobbyist | Real pain, limited market | Large, growing, underserved |
| **Monetization clarity** | Unclear who pays | Plausible model | Clear buyers, comparable pricing |
| **Competitive window** | Crowded or incumbents own it | Some competition, differentiation possible | Open field |
| **Build feasibility** | Deep complexity, large team required | Moderate | Lean team, months not years |
| **OSS leverage** | Repos are incidental | Community gives some GTM | Combined communities = powerful GTM |
| **Synthesis strength** | Parts work fine independently, bundling adds little | Combination is meaningfully better | Emergent properties: data, stickiness, or moat that didn't exist in the parts |

Total: 6–18. **Strong stack (15–18)**, **Worth exploring (10–14)**, **Pass (6–9)**.

### 5. Rank and filter

Output at most 3–5 stacks. Rank by total score. If fewer than 3 real stacks exist, output what you have and note that the pool didn't yield more — do not invent weak combinations to fill the list.

## Stack frontmatter schema

`stacks/<stack-slug>.md` starts with:

```yaml
---
name: <Business concept name>
slug: <kebab-case>
last_updated: <YYYY-MM-DD>
pattern: <vertical-stack | core-plus-distribution | shared-user | glue | data-flywheel | enterprise-bundle>

repos:
  - repo: <owner/repo>
    contributes: <what this repo provides to the stack>
  - repo: <owner/repo>
    contributes: <what this repo provides to the stack>

gaps: [<what still needs to be built or acquired>]

target_customer: <who pays>
pricing_model: <subscription | usage | seat | services>
closest_analog: <company that built something similar>

score:
  market_pull: <1|2|3>
  monetization_clarity: <1|2|3>
  competitive_window: <1|2|3>
  build_feasibility: <1|2|3>
  oss_leverage: <1|2|3>
  synthesis_strength: <1|2|3>
  total: <6-18>
  verdict: <strong | worth-exploring | pass>
---
```

## Frontmatter schema

```yaml
---
repo: <owner/repo>
slug: <owner>--<repo>
url: https://github.com/<owner/repo>
stars: <int>
language: <primary language>
description: <one-line from GitHub>
last_evaluated: <YYYY-MM-DD>

topic: <what it is in plain English>
target_user: <who uses the OSS project today>

business_angle: <managed-hosting | saas-wrapper | enterprise | vertical-saas | devtools | services | marketplace>
target_customer: <who would pay>
pricing_model: <subscription | usage | seat | one-time | services>

score:
  market_pull: <1|2|3>
  monetization_clarity: <1|2|3>
  competitive_window: <1|2|3>
  build_feasibility: <1|2|3>
  oss_leverage: <1|2|3>
  total: <5-15>
  verdict: <strong | worth-exploring | pass>

competitors: [<Co>, <Co>]
closest_analog: <company that did something similar>
---
```

## Output formats

### Single-repo evaluation

```
# <owner/repo>

**What it is:** <one sentence — what the project actually does>
**Business angle:** <angle> · **Verdict:** <Strong | Worth exploring | Pass> (<score>/15)

## The opportunity in one paragraph
What gap does this prove exists? Who has the pain? Why now?

## Business model
Who pays, how much, why. Show comparable pricing if it exists.
Include a rough napkin math: e.g. "1,000 dev teams × $500/mo = $6M ARR at scale."

## Competition
| Company | Approach | Weakness | Your edge |
|---------|----------|----------|-----------|
Be honest about incumbents. If Vercel, AWS, or Datadog already owns this, say so.

## What makes this hard
The single biggest obstacle. Not a list of risks — the one thing that determines if this works.

## Founder fit
What background, network, or credibility gives someone a real shot here? Who is the ideal founder?

## Score breakdown
| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| Market pull | <1-3> | ... |
| Monetization clarity | <1-3> | ... |
| Competitive window | <1-3> | ... |
| Build feasibility | <1-3> | ... |
| OSS leverage | <1-3> | ... |
| **Total** | **<n>/15** | |

## Next steps to validate
3 concrete actions to test the riskiest assumption before building anything.

## Sources
Numbered list of URLs used, with one-line annotations.
```

### Stack brief

`stacks/<stack-slug>.md` body after frontmatter:

```
# <Business Concept Name>

**What it is:** <one sentence — the product, not the repo list>
**Pattern:** <pattern> · **Verdict:** <Strong | Worth exploring | Pass> (<score>/18)

## The synthesis thesis
Why these repos together form something more compelling than each alone.
What emergent property — stickiness, data, moat, distribution — appears only in the combination?

## The stack
| Repo | What it contributes | Maturity |
|------|---------------------|----------|
What each repo provides. Be specific about layers: data, compute, API, UX, auth, observability, etc.

## What's missing
Gaps the team must build or acquire. Be concrete: "an auth layer", "enterprise SSO", "a managed hosting layer", "a sales motion into mid-market".

## Business model
Who pays, how much, via what model. Napkin math to $1M ARR.

## Competition
| Company | Approach | Why the stack wins |
|---------|----------|--------------------|
Who else is assembling this or adjacent. What's the differentiation.

## The hardest thing
One paragraph. The single constraint that determines whether this works.

## Natural builder
Who is best positioned to build this — and why. Existing maintainer? OSS-adjacent company? Newcomer with distribution?

## Next steps
3 concrete validations before building. Each should produce a yes/no answer to a specific risk.
```

### Batch scan brief

```
# Repo-to-business scan — <YYYY-MM-DD>
Source: ~/knowledge/github-trending/briefs/<source-brief>

**Evaluated:** <n> repos · **Individual — Strong:** <k> · **Worth exploring:** <j> · **Pass:** <m>
**Stacks identified:** <n> · **Strong:** <k> · **Worth exploring:** <j>

## Stack opportunities  ← lead with this
For each stack (Strong first, then Worth exploring):
  ### <Business Concept Name> (<score>/18)
  <synthesis thesis in 2–3 sentences>
  **Repos:** <owner/repo>, <owner/repo>, ...
  **Missing:** <gaps>
  Full brief: ~/knowledge/repo-to-business/stacks/<slug>.md

## Individual opportunities
### Strong
For each: one-paragraph summary + score + path.
### Worth exploring
For each: two-sentence summary + score + path.

## Pass
One line per repo: `<owner/repo> — <why>`.

## Already evaluated (skipped)
`<owner/repo> (last evaluated <date>)` — one line each.
```

The scan brief leads with stacks because that's the more interesting signal.

## Style rules

- **Lead with stacks.** The synthesis output is the headline finding. Individual repo evals are supporting evidence.
- **No generic OSS monetization advice.** Every brief should reflect the specific repos, their communities, and their actual competitive landscape.
- **The synthesis thesis must be specific.** "These repos complement each other" is not a thesis. "Combining repo A's inference engine with repo B's observability layer creates a feedback loop that makes the product stickier than either alone" is.
- **Show the math.** Napkin math to $1M ARR — even rough — is more useful than adjectives like "large market."
- **Name the incumbents.** If there's already a company doing this, name it and explain the differentiation thesis.
- **One honest paragraph on why it's hard** beats three bullets of "risks."
- **Cite inline** with `[1]`, `[2]`, ... matching Sources.
- **Pass is a valid outcome.** Most repos and stacks are passes. Say so quickly and move on.
- **Verdict drives action.** Strong stack → worth spending a week validating with potential customers. Worth exploring → one customer conversation. Pass → skip.
- **Don't force stacks.** Three weak combinations are worse than one strong one. If the pool doesn't yield good stacks, say so.

## What to skip

- Don't explain how open source business models work in general — get to the specific repos.
- Don't include every business angle if only one or two are real.
- Don't pad Pass verdicts with "on the other hand, if you really wanted to..."
- Don't cite sources you didn't fetch.
- In revision mode, don't re-output the full evaluation.
- Don't list every possible repo pair as a "potential stack" — only write up combinations with a real synthesis thesis.
