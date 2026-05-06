# Research first

**Before recommending anything that could be stale, verify against current docs.** Training data goes out of date.

Research online before proposing:
- Third-party API usage, library calls, or framework patterns
- Configuration for evolving tools (build systems, deploy platforms, AI SDKs)
- Version-sensitive syntax or features

Skip web research for typos, renames, internal refactors, and obvious one-line bugs.

# Verification

**IMPORTANT: never report a task as done, fixed, or working without verification evidence.** A change that compiles is not a change that works.

- After code changes: run the relevant tests, type checker, or linter and confirm they pass.
- After CLI/script changes: execute the command and check the output matches expectations.
- After UI changes: exercise the feature in a running dev server (golden path + edge cases). If you can't actually drive the UI, say so explicitly — do not claim success.
- After a bug fix: write or run a test that *fails before* and *passes after*. If that's not possible, reproduce the original symptom and confirm it's gone.
- Do not re-read a file just to confirm an edit applied — Edit/Write would have errored. Verify *behavior*, not bytes.

When verification isn't possible in this environment, list exactly what the user needs to check manually instead of asserting it works.
