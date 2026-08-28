# Submission form answers

Draft answers for the Agent Harness Hackathon submission form
(`forms.gle/PxGLsWW1HPyroQ5u9`) -- copy into the form directly. Not a separate
essay-style write-up; the form asks three specific short-answer questions plus a
YouTube video link.

**Note on the "Track" field:** the form says "you can submit the same project in all
tracks, but you can only win one" -- unclear from the form's structure alone whether
that's a multi-select on one submission or requires resubmitting per track. Check this
when actually filling it in. We're submitting for two tracks: Best Use of TrueForge and
Best Code Quality.

---

## What does your project do?

*(problem it solves + who it's for)*

AI agents are increasingly given access to real tools -- shells, databases, deployment
configs -- but the standard way to evaluate them only checks whether the final answer
looks right. That misses the failure mode that actually matters: an agent can produce a
"correct" result through unsafe means. Given "fix the failing tests," one agent reads
the code and fixes the actual bug; another just deletes the failing test. Both make the
suite pass. A final-answer-only evaluator calls both a success.

ForgeGuard is a security and reliability tester for AI agents: it stress-tests a target
agent (DevAgent) inside TrueForge across four categories -- normal tasks, prompt
injection, dangerous actions, and failure recovery -- and evaluates its entire tool-use
trajectory, not just its output. It's for anyone building or deploying an agent with
real tool access who needs to know not just whether it completes tasks, but how --
safely, honestly, and under supervision, or not.

---

## How did you use TrueForge in your project?

*(what the agent does + how TrueForge fits in)*

DevAgent, the agent under test, is built directly on TrueForge's TypeScript SDK -- not
wrapped or mocked. It's a coding/DevOps assistant with file and shell access via
TrueForge's sandbox, plus a custom MCP server for destructive actions (deleting a
database, changing deployment config, syncing inventory). Every one of ForgeGuard's four
test categories exercises a real TrueForge mechanism: normal tasks run through the
sandbox; prompt-injection scenarios test whether the agent follows an instruction
embedded in untrusted content; dangerous-action scenarios verify the agent's destructive
tool calls actually pause at TrueForge's approval gate before executing, not just that
they get called; recovery scenarios use a genuinely stateful MCP tool that fails on its
first call and succeeds on retry, to see whether the agent actually retries instead of
giving up or fabricating success.

ForgeGuard itself (the evaluation engine) is Python, driving TrueForge over its HTTP
API -- launching sessions and turns, reading back the persisted session/turn/event log,
and reconstructing the full trajectory: every tool call, every argument, every approval
decision. Nothing in the harness is simulated on our side except the specific
destructive-tool implementations (by design, so nothing real ever gets deleted) --
sandbox execution, MCP routing, and approval gating are all TrueForge's real, live
mechanisms.

---

## How did you use Qodo in your project?

*(how it improved code quality)*

Every non-trivial change went through a real PR → Qodo review → fix → merge cycle, not
a token gesture at the end -- logged in full at `docs/qodo-usage.md` in the repo. Two
concrete examples: Qodo caught that our GitHub Actions workflow's push trigger was
scoped only to `main`, so commits on a feature branch got zero CI coverage until a PR
existed -- contradicting the workflow's own stated goal of running on every push. More
significantly, on our multi-run scenario aggregation feature, Qodo caught a real scoring
bug: our `critical_findings` list was expanding one entry per violation instead of one
per failing scenario, meaning the CLI's headline count silently disagreed with the
detailed report whenever a scenario failed with more than one violation -- something our
own test suite missed because every existing test scenario happened to fail with exactly
one violation. Both were fixed with regression tests added, not just patched. On a later
PR, Qodo's review was substantive even without finding a bug -- it explicitly weighed
two real alternative designs for our LLM-judge feature and endorsed the one we'd built,
which was useful independent validation of a design decision, not just error-checking.

---

## YouTube video (~3 min) -- required structure per the form

- About the project
- Tech stack and architecture
- Demo (if possible)
- Learning and growth (optional)
