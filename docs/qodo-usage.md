# Qodo usage log

Running log of what Qodo Merge caught on this project's pull requests, and what changed
in response. Updated as real PRs get reviewed -- this is not filled in retroactively
with fabricated entries.

## Workflow

1. Work happens on a feature branch, never directly on `main`.
2. Open a PR.
3. Qodo reviews automatically (or via `/review`, `/improve`).
4. Findings get addressed -- fixed, or explicitly noted here as a deliberate no-op with
   reasoning if a suggestion isn't taken.
5. Re-review, then merge.

## Log

| PR | What Qodo flagged | What changed |
|---|---|---|
| [#1](https://github.com/sabertooth-123/ForgeGuard/pull/1) -- README, .env.example, AI_ASSISTANCE.md, Qodo log | Clean review: classified as `Documentation` / `Configuration changes` / `Bug fix`, 10-20 min estimated review time. No security concerns or possible-issues sections were raised -- Qodo's own assessment: "Reading endpoint from environment preserves explicit constructor injection without adding dependencies." Consistent with the PR's actual content (mostly markdown, one small env-var fix). | No changes required; merged as-is. |
| [#2](https://github.com/sabertooth-123/ForgeGuard/pull/2) -- GitHub Actions CI | Real bug, correctly caught: `🐞 Bugs (1)`, "Branch pushes skip CI" -- the `push:` trigger was scoped to `branches: [main]`, so a push to a feature branch before a PR exists ran no CI at all (only `pull_request:` events covered it, and only once a PR was open). Contradicted the workflow's own stated goal of running "on every push". | Removed the `branches: [main]` filter from the `push:` trigger so it fires on pushes to any branch, not just `main`. |
| [#3](https://github.com/sabertooth-123/ForgeGuard/pull/3) -- multi-run scenario aggregation | Real, sharp bug: `🐞 Bugs (1)`, "Findings remain per violation" -- `compute_report`'s `critical_findings` comprehension iterated `for v in s.sample_violations` per failing scenario, so a scenario failing with 2+ violations produced 2+ critical_findings entries instead of 1. This silently broke the PR's own stated contract (one entry per failing scenario) and made the CLI's "Critical Findings" count disagree with the Markdown report, which renders one heading per scenario regardless of violation count. Our own test suite didn't catch it because every test scenario happened to fail with exactly one violation. | Collapsed to one `critical_findings` entry per failing scenario by joining `sample_violations` with `"; "` instead of expanding them into separate list entries. Added a regression test with a 3-violation failing scenario asserting exactly one finding is produced. |
| [#4](https://github.com/sabertooth-123/ForgeGuard/pull/4) -- opt-in LLM-judge fallback | Clean review, but substantive, not a rubber stamp -- Qodo explicitly weighed two alternative designs (expanding the deterministic regex pattern list further; auto-invoking the judge whenever a regex check fails) and endorsed the PR's actual approach: "Keep the PR's explicit per-scenario criteria and deterministic-first ordering... while the injected JudgeFn keeps tests deterministic." No bug-findings comment followed the summary, confirming a genuinely clean pass rather than an incomplete review. | No changes required; merged as-is. |
