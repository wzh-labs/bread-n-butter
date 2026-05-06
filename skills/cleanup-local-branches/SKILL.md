---
name: cleanup-local-branches
description: Find and delete local git branches whose work has already landed on main — including squash- and rebase-merged branches that `git branch --merged` misses. Use when the user asks to "clean up branches", "delete merged branches", "prune local branches", "remove old branches", or similar. Lists candidates with age and merge reason, asks before deleting, and optionally cleans up matching git worktrees.
---

# Cleanup local branches

Goal: surface local branches whose changes already exist on `main` (whether via merge commit, squash, or rebase), present them to the user with enough context to judge, and delete only what the user confirms. Squash- and rebase-merged branches are the main thing this skill exists to catch — `git branch --merged` does not find them.

## Inputs

All optional:
- `base` — base branch to compare against (default `main`; fall back to `master` if `main` does not exist locally)
- `protect` — additional branch names to never offer for deletion (always protected: `main`, `master`, current branch, plus any branch listed in `~/.config/branch-cleanup/protected` if present)

## Method

### 1. Refresh remote refs

Always run first so detection is accurate:

```bash
git fetch --prune
```

If the repo has no remote, skip without error.

### 2. Resolve base branch

```bash
base=main
git show-ref --verify --quiet "refs/heads/$base" || base=master
git show-ref --verify --quiet "refs/heads/$base" || { echo "no main/master branch found"; exit 1; }
```

### 3. Build the candidate list

Collect every local branch except protected ones, then classify each as **merged**, **squash/rebase-merged**, or **not merged** (skip the last category — out of scope).

```bash
current=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
protected=("$base" "$current" main master)
# plus user-supplied names from ~/.config/branch-cleanup/protected if present

# Plain merged (reachable from base)
git branch --merged "$base" --format='%(refname:short)'

# Squash/rebase-merged detection — the standard "is the diff already in main" trick:
for b in $(git for-each-ref --format='%(refname:short)' refs/heads/); do
  # skip protected and already-in-merged-list
  mb=$(git merge-base "$base" "$b") || continue
  # If the branch tip equals the merge base, branch has no unique commits — it's already in base.
  [ "$mb" = "$(git rev-parse "$b")" ] && continue
  # Create an ephemeral squash-commit object representing the branch's diff against the merge base,
  # then ask git cherry whether base already contains a commit with that same patch-id.
  tree=$(git rev-parse "$b^{tree}")
  squash=$(git commit-tree "$tree" -p "$mb" -m _)
  if [ "$(git cherry "$base" "$squash" | head -1 | cut -c1)" = "-" ]; then
    echo "$b"  # squash/rebase-merged
  fi
done
```

Notes:
- The `commit-tree` object is dangling and harmless — git GC will reap it. Do not push or otherwise reference it.
- This detection works for both squash merges and rebase-and-merge: in both cases the branch's net diff against the merge base appears as one or more patches already on main.
- `git cherry` matches by patch-id, so it tolerates rebases that shift line numbers but not changes that conflict-resolved differently. Branches where conflict resolution diverged will show as "not merged" — correctly excluded.

### 4. Per-branch metadata

For every candidate, gather:

- last commit date (`%cs` — short ISO date)
- last commit author (`%an`)
- age in days (today − last commit date)
- merge reason: `merged` (from --merged) or `squash` (from the cherry check)
- worktree path, if any (`git worktree list --porcelain` → match by branch)

```bash
git log -1 --format='%cs%x09%an%x09%s' "$b"
git worktree list --porcelain | awk '/^worktree /{wt=$2} /^branch refs\/heads\/'"$b"'$/{print wt}'
```

### 5. Show the list and ask

Present a table sorted by age descending (oldest first), then ask which to delete. Offer:
- **all** — delete every candidate
- **pick** — let user list specific branches (comma-separated or numbered)
- **none / cancel** — exit without changes

```
## Local branch cleanup  (base: main · 7 candidates)

 #  Branch                          Age    Last commit   Author        Reason  Worktree
 1  feat/old-auth-flow              63d    2026-03-04    thomas.wang   squash  —
 2  fix/typo-in-readme              41d    2026-03-26    thomas.wang   merged  —
 3  spike/edge-runtime-bench        22d    2026-04-14    thomas.wang   squash  .claude/worktrees/edge-bench
 ...

Protected (skipped): main, master, <current-branch>

Delete which? [all / 1,3,5 / none]
```

### 6. Delete

For each confirmed branch:

```bash
# Plain merged: safe delete
git branch -d "$b"
# Squash/rebase-merged: -d will refuse, use -D after the cherry check has confirmed safety
git branch -D "$b"
```

If the branch has a worktree, ask once whether to also remove worktrees, then for each:

```bash
git worktree remove "$wt"   # add --force only if it has uncommitted changes AND user re-confirms
```

Do not auto-force. If `git worktree remove` fails because of dirty state, surface the error and ask before retrying with `--force`.

### 7. Report

```
Deleted 4 branches:
  feat/old-auth-flow            (squash)
  fix/typo-in-readme            (merged)
  spike/edge-runtime-bench      (squash, worktree removed)
  chore/bump-eslint             (merged)

Skipped 1:
  hotfix/payment-retry          (worktree dirty — not removed)
```

## Safety rules

- **Never delete the current branch.** Detect via `git symbolic-ref --short HEAD`. If user happens to be on a candidate branch, exclude it and say so.
- **Never delete `main` or `master`**, even if the user names it explicitly. If they insist, refuse and tell them to do it manually.
- **Never use `git branch -D` on a branch the cherry check did not classify as squash-merged.** If `-d` refuses a "merged" branch (rare — usually means upstream changed), surface the error rather than escalating to `-D`.
- **Do not push, force-push, or delete remote branches.** This skill is local-only. If the user asks for remote cleanup, tell them to use `gh` or the GitHub UI.
- **No `git gc`, no `reflog expire`.** Deleted branches stay in reflog for 90 days by default — this is the user's safety net.

## Failure modes

- **Detached HEAD:** `git symbolic-ref` fails. Treat current branch as "none", run normally — but warn at the top of the output.
- **No `main` or `master`:** stop with a clear error; do not guess (e.g. `develop`, `trunk`).
- **No remote configured:** skip `git fetch --prune` silently — squash detection still works against the local base.
- **Repo has 0 candidates:** print "Nothing to clean up." and exit. Do not show an empty table.

## Style

- Be terse. This is a maintenance tool — show the table, the prompt, and the result. No preamble, no recap.
- Show absolute dates (`2026-03-04`), not relative (`2 months ago`) — relative dates rot in saved transcripts.
- When uncertain about a branch's status, exclude it. False negatives (leaving a branch alone) are cheap; false positives (deleting unmerged work) are not.
