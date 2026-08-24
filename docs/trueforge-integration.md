# TrueForge Integration Notes (Phase 0 — pre-hackathon survey)

Status: **preliminary**, based on a README-level review of
[truefoundry/trueforge](https://github.com/truefoundry/trueforge) done on 2026-08-18,
before the hackathon window (Aug 22–30, 2026) opens. This is NOT a substitute for
reading the actual API reference at trueforge.dev or running the SDK locally — treat
everything below as "confirmed to exist" but "signatures/exact usage TBD" until Phase 0
is redone for real on day one.

## What TrueForge is

An open-source agent execution *harness* (their word) — the runtime layer between an
LLM and the outside world. It owns: model orchestration, tool/MCP management, sandboxed
execution, human approval checkpoints, sessions, and subagents. MIT licensed, ~1.2k
stars, 388 commits — a real, maintained SDK, not a hackathon scaffold.

## Install / runtime

- **Language: Node.js >= 22.13.** SDK is TypeScript (`@truefoundry/trueforge`,
  `@truefoundry/trueforge-sdk`, `@truefoundry/trueforge-ui`, `@truefoundry/trueforge-core`
  on npm).
- Local dev: `npx @truefoundry/trueforge` (SQLite-backed).
- Hosted: Docker Compose or Helm (Postgres + Redis).
- Also exposes a generic **HTTP API** — this is what lets a non-TS client (our Python
  evaluator) drive it without the TS SDK.

**Consequence for ForgeGuard:** the target agent under test (DevAgent) should be built
natively with the TS SDK so it's genuinely harness-native, not a wrapper — this maps
directly to the "harness centrality" judging criterion. ForgeGuard's orchestration/
evaluation/scoring layer talks to TrueForge over the HTTP API from Python. See
[architecture.md](./architecture.md) for the full split.

## Capabilities confirmed to exist (need exact API surface on day one)

| Capability | Status | ForgeGuard use |
|---|---|---|
| MCP tool integration (remote servers, header/OAuth auth) | confirmed | DevAgent tool access |
| Sandboxed code/file execution ("sandbox as a tool", Daytona-backed) | confirmed | DevAgent's repo/shell environment |
| Tool approval workflow / ask-user-question / generative UI | confirmed | Category 3 (dangerous actions → human approval) |
| Subagents (delegation) | confirmed | not needed for MVP; relevant to future Attacker Agent |
| Sessions / turns / events | confirmed | **likely our trajectory data source** — need exact event schema |
| Skills (git-backed `SKILL.md`, sandbox-loaded) | confirmed | optional, not MVP-critical |
| Context compaction / large-result offloading / deferred tool loading | confirmed | not MVP-relevant |
| Multiple model providers (OpenAI, Anthropic, Gemini, OpenAI-compatible) | confirmed | pick one for DevAgent |

## Open questions to resolve on day one (before writing any Phase 1 code)

1. Exact shape of a "session" / "turn" / "event" object via the HTTP API — this
   determines the `Trajectory` model in `forgeguard/core/trajectory.py` almost
   one-to-one. Do NOT invent a schema; mirror TrueForge's.
2. Does the HTTP API expose approval requests/decisions as first-class events, or do we
   need to poll a separate endpoint?
3. How is a sandbox environment seeded with a starting repo state (for scenario
   `initial_state`)? Per-run sandbox provisioning semantics (Daytona) — cost/latency of
   spinning up a fresh sandbox per scenario run matters for a 20-scenario suite.
4. Auth model for the HTTP API when called from a separate Python process (API key?
   session token?).
5. Whether tool-call arguments and raw tool output are captured verbatim in events (we
   need this for deterministic pattern-matching, e.g. detecting `rm -rf` in a shell tool
   call).

## Explicit non-goals

Per "do not recreate TrueForge functionality unnecessarily": ForgeGuard will NOT build
its own sandboxing, its own approval UI, or its own MCP integration. If something in the
original spec implied reimplementing one of these, it's been dropped in favor of driving
TrueForge's real implementation.
