# ForgeGuard — 5-day build schedule

Hackathon window is Aug 22–30 (9 days, deadline Aug 30 8pm PT). This schedule compresses
the MVP (phases 0–9 from the plan) into 5 build days, Aug 22–26, leaving Aug 27–30 as
unscheduled buffer for overruns, the demo video, and the write-up — not padding, actual
slack, since every one of these days is already tightly packed.

Dashboard (phase 11) and Attacker Agent (phase 12) are **cut**, not deferred — there's no
day left for them in this window. If a day finishes early, that time goes to scenario
count or polish, not new features.

## Day 1 — Aug 22 (today): unblock TrueForge, get DevAgent talking to it

- Resolve the Windows local-mode bug (Docker Compose hosted mode, or WSL2 — whichever
  gets a running server fastest).
- Phase 1: minimal TS agent — task → TrueForge → result, streamed. Print raw events.
- Start Phase 2: DevAgent skeleton (file read/edit, shell exec via sandbox).
- Parallel/logistics: create the public GitHub repo, install the Qodo Merge GitHub App,
  get a free Gemini API key, confirm Daytona sandbox access (or its free-tier status).

## Day 2 — Aug 23: DevAgent complete, scenario models

- Finish Phase 2: one MCP tool, plus the custom "dangerous tools" MCP server
  (`delete_database`, `modify_deployment_config`, `run_untrusted_script`) with
  `require_approval_for_tools` wired up. Manually verify approval actually pauses
  execution — this is the riskiest unverified piece in the whole plan.
- Phase 3: `Scenario` / `Trajectory` / `TestResult` / `EvaluationReport` models +
  JSON scenario loader.

## Day 3 — Aug 24: the evaluation pipeline (core IP)

- Phase 4: Python `trueforge_client` — launch a run over HTTP, poll/stream to
  `turn.done`, fetch the trajectory.
- Phase 5: normalize TrueForge's real event shape into the `Trajectory` model.
- Phase 6: deterministic evaluator — `checks`-block predicate matching. Get at least
  one scenario (the malicious-README injection) passing end to end today; that's the
  proof the whole architecture works.

## Day 4 — Aug 25: scoring, reporting, full scenario suite

- Phase 7: scorer (30/30/20/20 + the five sub-scores).
- Phase 8: CLI output + JSON + Markdown report.
- Phase 9: write the remaining scenarios to reach 8 total (2 per category). If Day 3
  ran long, 6 is an acceptable fallback — 2 categories at 2 scenarios, 2 at 1 — don't
  let scenario count crowd out a working pipeline.
- Qodo: first real PR-review pass across everything merged so far, not a one-off — log
  findings in `docs/qodo-usage.md`.

## Day 5 — Aug 26: end-to-end run, fixes, docs

- Full `forgeguard run` across all scenarios; fix whatever breaks — nothing gets called
  done until it's actually been run once, per the working rule.
- README complete (architecture, setup, scoring methodology, security considerations,
  limitations, Qodo usage, AI-assistant disclosure — the full §22 list).
- Record the ~3-minute demo video (script already in the plan: problem → ForgeGuard →
  DevAgent running through TrueForge → injection scenario → dangerous-action approval →
  score/report).
- Write the short technical write-up.

## Aug 27–30: buffer

Unscheduled. Absorbs whatever slipped, or — only if genuinely nothing did — a stretch
item from phase 9 (more scenarios) or phase 11 (a minimal dashboard).
