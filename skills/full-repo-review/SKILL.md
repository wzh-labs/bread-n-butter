---
name: full-repo-review
description: Review the repository at the current working directory end-to-end and produce a structured, actionable assessment in chat. Covers architecture, code quality, security, dependencies, tests, CI/CD, and documentation — grounded in the actual code, not vibes. Persists a per-repo profile under `~/knowledge/repos/<slug>/` so re-runs detect repo drift (what changed in the code) and ecosystem drift (what changed in the wider world — deprecations, CVEs, official successors — even if the repo didn't). Takes no arguments and always operates on pwd. Output stays in chat (plus the knowledge-base writes); never opens PRs, posts issues, or writes files into the repo under review. Use when the user asks to "review this repo", "audit this codebase", "do a full repo review", "/full-repo-review", or otherwise wants a holistic read of the repo they're currently in. Distinct from `review-pr` (single PR diff) and the built-in `/review` (local uncommitted changes only).
---

# Full Repo Review

Goal: read the whole repository at `pwd` — not just a diff — and produce a review the user can act on. What's solid, what's weak, what's risky, where to look first. Grounded in the actual code, manifests, and history. Re-runs surface what changed in the repo *and* what changed in the wider ecosystem (deprecations, CVEs, official successors) since the last review. Chat-only output for the review; persistent state is written to `~/knowledge/repos/<slug>/` — never into the repo under review.

## Persistence

State lives under `~/knowledge/repos/<slug>/` and mirrors the existing knowledge-base layout (see `~/knowledge/private-companies/<name>/`):

- **`brief.md`** — the most recent review, in the same structured shape as the chat output.
- **`state.json`** — machine-diffable facts: stack (language, framework, runtime versions), key dependencies + versions, build system, deploy target, default branch, license, last-reviewed commit SHA, last-reviewed timestamp (ISO-8601 UTC). This is what drives drift detection.
- **`changelog.md`** — append-only log of deltas across runs. Each entry: timestamp, *repo drift* lines (what changed in the code), *ecosystem drift* lines (what changed in the world).
- **`snapshots/<YYYY-MM-DDTHHMM>.md`** — timestamped copy of `brief.md` at each run, so old reviews aren't lost when `brief.md` is overwritten.
- **`sources.jsonl`** — one JSON object per line, capturing the URLs hit during ecosystem-drift research (release notes, deprecation announcements, CVE advisories). `{ "url": "...", "title": "...", "fetched_at": "...", "purpose": "..." }`.

**Slug derivation:**
1. If `git remote get-url origin` matches `github.com[:/]<owner>/<repo>(\.git)?` → `<owner>-<repo>` (lowercase, kebab — matches the `private-companies` convention).
2. Else → `basename "$(git rev-parse --show-toplevel)"` (lowercase, kebab).
3. If a collision is plausible (common name like `web` or `api`), prefix with parent directory name.

Create `~/knowledge/repos/<slug>/` (and `snapshots/`) on first run. Never delete existing state — even if the user re-runs and the new review looks different, append to changelog and snapshot the old brief rather than overwriting silently.

## Inputs

**None.** This skill always runs against the current working directory. Do not ask for a path, URL, or repo identifier — if the user offers one, point them at `cd` and re-run from there.

## Prerequisites

- `pwd` must be inside a git repo (`git rev-parse --show-toplevel`). If not, stop with a one-line note.
- `gh` CLI authenticated (`gh auth status`) is **optional** — used for issues, PRs, releases, and CI signal when there's a GitHub remote. If not authenticated or no remote, skip those sections and say so in the output. Do not fail.
- For very large repos: be prepared to sample rather than read every file (see §5).

## Method

### 0. Load prior profile (if any)

Compute the slug per the rules above. Check `~/knowledge/repos/<slug>/state.json`:

- **First run** (no `state.json`): note this — the review will write a fresh profile and there will be no drift sections.
- **Re-run** (`state.json` exists): load it. Record `prior.last_reviewed_sha`, `prior.last_reviewed_at`, `prior.stack`, `prior.dependencies`. You'll use these in §7 and §8.

### 1. Snapshot the repo

Confirm `pwd` is a git repo with `git rev-parse --show-toplevel`. Operate from the repo root regardless of where inside the tree `pwd` is.

Gather a fast snapshot — run these in parallel, they're independent:

```bash
git log --oneline -50                                      # recent activity
git log --format='%an' | sort -u | wc -l                   # contributor count
git log --format='%ad' --date=short | head -1              # last commit date
git log --format='%ad' --date=short | tail -1              # first commit date
git ls-files | wc -l                                        # tracked file count
git ls-files | awk -F. '{print $NF}' | sort | uniq -c | sort -rn | head -10   # file extensions
tokei . 2>/dev/null || cloc . 2>/dev/null || true          # LOC by language if available
```

If the repo has a GitHub remote (`git remote get-url origin` returns a `github.com` URL) and `gh` is authenticated, also fetch repo-health signal — these are optional, skip silently if `gh` errors:

```bash
gh repo view --json name,description,stargazerCount,forkCount,defaultBranchRef,licenseInfo,isArchived,pushedAt,openIssuesCount,languages,topics
gh issue list  --state open --limit 20 --json number,title,labels,createdAt
gh pr list     --state open --limit 20 --json number,title,isDraft,createdAt
gh release list --limit 5 2>/dev/null
```

(`gh` infers `--repo` from the cwd's remote — no need to pass `owner/repo`.)

### 2. Read intent before judging code

Before scanning for issues, read:

- **README** (and `docs/` index, if present) — what is this trying to be?
- **Top-level manifests** — `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`, etc. They reveal language, framework, target runtime, and stated dependencies.
- **`CHANGELOG.md` / recent releases** — what's been shipping?
- **`CONTRIBUTING.md`, `CODEOWNERS`, `.github/`** — what conventions does the project expect?
- **Recent commits + open issues/PRs** — what's the team currently fighting?

A "missing feature" or "weird abstraction" that the README explains away is not a finding. Many bad reviews come from skipping this step.

### 3. Map the architecture

Walk the top-level directory and identify:

- **Entry points** — `main.*`, `index.*`, `app/`, `cmd/`, `bin/`, `pages/`, `server/`.
- **Layers** — frontend, backend, infra, shared libs, generated code.
- **Build system** — `Makefile`, `turbo.json`, `nx.json`, `pnpm-workspace.yaml`, `tsconfig*.json`, `vite.config.*`, `next.config.*`, etc.
- **Runtime / deploy target** — Vercel, Docker, k8s manifests, serverless framework, GitHub Actions workflows.

Sketch the architecture in 2–4 sentences. If you can't, that itself is a finding — the repo's structure is unclear without an architecture doc.

### 4. Verify unfamiliar APIs and frameworks against current docs

If the repo uses third-party APIs, framework patterns, or config you don't recognize confidently from training, **look them up before flagging anything as wrong or outdated**. Training data goes stale. Use `WebFetch` or `WebSearch` against the library's current docs. Only flag a misuse after confirming the current shape of the API.

Skip this for plainly internal code, typos, renames, and obvious one-line issues.

### 5. Scan focus areas

For each area, note issues with `file:line` (or `dir/`) precision. Be specific — vague findings are noise.

**Sampling strategy for large repos.** Don't try to read every file. Cover:
- All top-level entry points and manifests.
- The 10–20 largest non-generated source files (`git ls-files | xargs wc -l | sort -rn | head -30` — filter out lockfiles/vendored).
- 1–2 files per significant subdirectory.
- Files touched in the last 20 commits (recent activity is where bugs live).
- Test directories — sample, don't exhaust.

Note coverage explicitly at the end (§8).

**Architecture & organization**
- Unclear module boundaries; circular dependencies; "kitchen sink" utility files.
- Layering violations (UI reaching into DB, etc.).
- Generated code mixed with hand-written code without clear separation.
- Public surface that leaks internals.

**Code quality & maintainability**
- Dead code, commented-out blocks, TODO/FIXME debt — count and spot-check.
- Functions/files that are far too long; obvious duplication.
- Error handling: swallowed exceptions, generic catches, missing context.
- Inconsistent patterns across similar files (e.g. some routes do auth, others don't).
- Tests that exist but don't actually assert the behavior they claim to.

**Security**
- Secrets in the repo or git history (`git log -p -S 'API_KEY' -S 'SECRET' -S 'PASSWORD' | head -200`, plus a scan of `.env*` files that aren't gitignored).
- Injection sinks reachable from user input (SQL, shell, template, SSRF).
- Authn/authz gaps: missing checks, IDOR patterns, overly broad tokens.
- Unsafe deserialization, path traversal, unsafe `eval`/`exec`/dynamic require.
- Crypto misuse: hardcoded keys, weak primitives, custom crypto.
- CORS / CSP / cookie flags on web endpoints.
- Dependency CVEs — run `npm audit`, `pnpm audit`, `pip-audit`, `cargo audit`, or `gh api /repos/<o>/<r>/dependabot/alerts` if available. Summarize counts; cite the worst.

**Dependencies & supply chain**
- Unmaintained packages (last published >2 years, no recent commits upstream).
- Typosquats or suspicious package names you can't verify on the registry.
- Pinning hygiene: `^` vs exact pins, lockfile committed, multiple lockfiles in conflict.
- License compatibility — surface anything in `node_modules`/manifests that's GPL/AGPL/SSPL when the repo's own license is permissive (or vice versa).
- Native deps / postinstall scripts on packages with low download counts.

**Performance**
- N+1 queries, sync I/O on hot paths, unbounded loops over remote calls.
- Bundle-size red flags on the client (heavy top-level imports, no code-splitting).
- Missing indexes hinted at by query shapes in the data layer.
- Memory: reading whole files when streaming would do, unbounded caches.

**Tests & CI**
- Test coverage by directory (which areas are tested, which aren't). Don't quote a coverage % unless one is generated — eyeball the test/source ratio.
- Are tests run in CI? Required for merge? Look at `.github/workflows/`, `.gitlab-ci.yml`, `circleci/`, etc.
- Flaky-looking tests (network calls without mocks, time-based assertions).
- E2E / integration coverage vs. unit-only.

**Documentation**
- Is the README enough to get someone running locally?
- Are public APIs / exported types documented?
- Are architectural decisions captured anywhere (ADRs, `docs/`)?
- Stale docs — references to removed features, outdated install commands.

**Conventions & consistency**
- Linter/formatter configured + enforced in CI?
- Type checking enforced?
- Commit message / PR template discipline (look at recent commits).
- Naming consistency across the codebase.

### 6. Check repo-health signal (remote only)

From `gh` queries in §1:
- Is the repo archived? Last push date.
- Open issue / PR backlog — count and oldest.
- Release cadence — gaps between recent releases.
- CI: do recent commits on the default branch show green? (`gh run list --branch <default> --limit 10`)

Don't rephrase what `gh` already says — but flag a stale repo, a red default branch, or a months-old open PR backlog as findings.

### 7. Detect drift (re-runs only)

Skip if §0 found no prior profile.

**Repo drift** — diff the prior `state.json` against what you just measured. Surface only meaningful deltas, not cosmetic noise:
- Stack changes: language version bumps, framework major-version bumps, new/removed runtime targets.
- Dependency changes: added/removed top-level deps, version bumps that cross a major boundary, lockfile churn that suggests an upgrade attempt.
- Architecture changes: new top-level directories, abandoned directories, switched build system or deploy target.
- Default branch / license / activity: archived, license changed, default branch renamed.

For each, name the *what changed* and *when* (use `git log -- <path>` if useful).

**Ecosystem drift** — for each significant stored stack item (language, framework, major deps), check the world *now* against where the repo is. This is the part that needs fresh web research — do not rely on training data. Use `WebFetch` / `WebSearch` against official sources:
- Is the version the repo uses **EOL** or past official support? (Cite the vendor's support-matrix page.)
- Does the version have a **known CVE** that's fixed in a later release? (Cite the advisory.)
- Has the upstream project been **deprecated**, **renamed**, **archived**, or **transferred** to a different maintainer? (Cite the announcement.)
- Is there an **official successor or migration guide** published by the same maintainer? (Cite the migration doc — community alternatives don't count.)

Filter discipline: only flag the four categories above. Do NOT flag "there's a newer minor version", "library X is more popular now", or "you could refactor to Y". Those are noise. The bar is *the maintainer or a CVE database told you this matters*.

Record every URL hit during this step for `sources.jsonl`.

### 8. Produce the review

Print one structured block. No preamble.

```
## Repo review — <name> (<pwd>)

**Stack:** <primary language(s) + framework(s)> · **Size:** <LOC or file count> · **Age:** <first commit → last commit>
**Activity:** <commits last 30d> · <contributors total> · <open issues / open PRs if available>
**License:** <license or —> · **Default branch CI:** <green/red/unknown>
**Stated purpose:** <1 sentence from README>
**Profile:** <fresh — first review> | <updated — last reviewed YYYY-MM-DD at SHA <short-sha>>

### Architecture (2–4 sentences)
<What this repo is, how it's laid out, what the major moving parts are.>

### Repo drift (re-runs only; omit section entirely on first run)
<What changed in this repo since the last review. One line per change, with the prior → current values and a citation (`<path>` or commit SHA). Empty section → omit.>

### Ecosystem drift (re-runs only; omit section entirely on first run)
<What changed in the wider world that now matters for this repo's stack. One line per finding: **<tech> <current version>** — <EOL | CVE | deprecated | successor available> per <cited source>. Strict filter per §7. Empty section → omit.>

### Blockers
<Issues that should be fixed before this repo is used / shipped / merged-from. Each: **[area] file:line or dir/** — what's wrong + suggested fix. Empty section if none.>

### Should-fix
<Real issues, not blockers. Same format.>

### Nits & questions
<Style nits, questions for the maintainer, things worth clarifying. Mark questions with `?`.>

### Strengths
<Short. Non-obvious decisions that were clearly right. Skip if nothing stands out — no praise theater.>

### Out of scope (noted, not flagged)
<Things you noticed but won't pursue — pre-existing issues, intentional per the docs, etc. Keep short.>

### Coverage
Read: <N> files across <M> directories. Sampled: <list of areas>. Skipped: <list>.

---
_Profile written to `~/knowledge/repos/<slug>/` — `brief.md`, `state.json`, `changelog.md`, `snapshots/<timestamp>.md`._
```

Each issue line should be one sentence (two if the fix is non-obvious). Cite `file:line` always — no vague "in the auth code". Quote the offending snippet only when the line number alone is ambiguous.

If you couldn't fetch part of the data (e.g. `gh` not authed, no CI configured, empty README), say so explicitly in the relevant section rather than omitting it silently.

### 9. Persist the profile

After printing the chat output, write to `~/knowledge/repos/<slug>/`:

1. **`snapshots/<YYYY-MM-DDTHHMM>.md`** — copy of the chat output (without the footer line). Create the `snapshots/` directory if needed.
2. **`brief.md`** — overwrite with the new chat output. This is always the latest review.
3. **`state.json`** — overwrite with the structured facts you measured:
   ```json
   {
     "slug": "<slug>",
     "last_reviewed_at": "<ISO-8601 UTC>",
     "last_reviewed_sha": "<git rev-parse HEAD>",
     "default_branch": "...",
     "license": "...",
     "archived": false,
     "stack": { "language": "...", "language_version": "...", "framework": "...", "framework_version": "...", "runtime": "...", "deploy_target": "..." },
     "build_system": "...",
     "dependencies": { "<name>": "<version>", ... },
     "size": { "loc": 0, "files": 0 }
   }
   ```
   Include only fields you actually determined — omit unknowns rather than writing `null`.
4. **`changelog.md`** — append (don't overwrite) a new entry:
   ```
   ## <YYYY-MM-DD HH:MM UTC> · <short-sha>

   **Repo drift:**
   - <one line per change, or "—" if none>

   **Ecosystem drift:**
   - <one line per finding, or "—" if none>

   **New findings:** <count of Blockers + Should-fix new since last run, or "first run">
   ```
5. **`sources.jsonl`** — append one JSON line per URL hit during §7's ecosystem-drift research. Skip on first run (no §7).

All writes go to `~/knowledge/repos/<slug>/`. Nothing is written into the repo under review.

## Style

- **Be specific.** "Consider refactoring" is noise. Either say what to change or don't say it.
- **Severity discipline.** Most findings are nits; very few are blockers. If everything is a blocker, nothing is.
- **No praise theater.** The user wants problems and a plan, not affirmation. Strengths section is optional and short.
- **Don't speculate.** If you're unsure whether something is a bug, frame it as a question, not a Blocker.
- **Diff what's in front of you.** Don't compare against a hypothetical "ideal" repo. Compare against the project's own stated intent and the conventions visible inside the repo.

## Output destination

The chat output is the review. The **only** files this skill writes are under `~/knowledge/repos/<slug>/` (see §9). Never:
- Run `gh issue create`, `gh pr create`, `gh pr comment`, or any other write command against the repo.
- Write files into the repo under review — this skill is read-only on the target repo.
- Push, branch, or commit anywhere.

The user reads the review, decides what to act on, and posts/files anything themselves. If they explicitly ask you to open issues for the findings afterward, that's a separate request — confirm exactly what to file and where before running any write command.

## Failure modes

- **`pwd` is not inside a git repo:** stop with a one-line note pointing them at `cd`.
- **`gh` not authenticated or no GitHub remote:** proceed with local-only signal; skip issue/PR/CI sections and say so in the output. Do not fail.
- **Empty repo / no commits:** stop with a one-line note. Nothing to review.
- **Monorepo with many independent packages:** ask the user whether to review the whole tree or scope to one package before diving in. (If they pick a package, prefix the slug with the package name so it gets its own profile.)
- **Archived / read-only repo (per `gh repo view`):** review anyway, but note the archived state at the top.
- **`state.json` exists but is malformed:** treat as first run for drift purposes, but back up the broken file to `state.json.bak.<timestamp>` instead of overwriting it silently.
