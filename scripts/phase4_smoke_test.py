"""One-off manual smoke test for the Python trueforge_client, run against the live
local TrueForge server. Not a pytest test (needs a running server + local model) --
Phase 4's actual pytest coverage will use recorded fixtures instead (see Phase 5/6)."""

import logging
from pathlib import Path

from forgeguard.core.scenario import load_scenarios
from forgeguard.evaluation.evaluator import evaluate
from forgeguard.trueforge_client.client import TrueForgeClient

logging.basicConfig(level=logging.INFO)

scenarios = load_scenarios(Path("scenarios"))
scenario = next(s for s in scenarios if s.id == "dangerous_delete_db_001")

with TrueForgeClient() as client:
    trajectory = client.run_scenario(scenario)

print(f"\nrun_id: {trajectory.run_id}")
print(f"tool_calls: {len(trajectory.tool_calls)}")
for call in trajectory.tool_calls:
    print(
        f"  - {call.name} tool_name={call.tool_name!r} "
        f"approval_required={call.approval_required} decision={call.approval_decision} "
        f"result={(call.result or '')[:80]!r}"
    )
print(f"final_response: {trajectory.final_response!r}")
print(f"errors: {trajectory.errors}")
print(f"raw_events captured: {len(trajectory.raw_events)}")

result = evaluate(scenario, trajectory)
print(f"\npassed: {result.passed}")
print(f"violations: {result.violations}")
print(f"evidence: {result.evidence}")
