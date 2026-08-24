"""Captures one real approval-flow run's raw events to a fixture file for unit tests.
Run manually against the live server when we want to refresh the fixture -- not run in
CI, since it depends on the live server and local model."""

import json
from pathlib import Path

from forgeguard.core.scenario import load_scenarios
from forgeguard.trueforge_client.client import TrueForgeClient

scenarios = load_scenarios(Path("scenarios"))
scenario = next(s for s in scenarios if s.id == "dangerous_delete_db_001")

with TrueForgeClient() as client:
    session_id = client.create_session("dev-agent")
    input_items = [{"type": "user.message", "content": scenario.task}]
    all_events = []
    for _ in range(6):
        turn = client._run_turn_with_backoff(session_id, input_items)
        all_events.extend(client.get_turn_events(session_id, turn["id"]))
        required_actions = turn["state"].get("required_actions") or []
        if not required_actions:
            break
        next_input = []
        for action in required_actions:
            for tc in action["tool_calls"]:
                if action["type"] == "tool.approval_required":
                    next_input.append(
                        {
                            "type": "user.tool_approval",
                            "thread_id": action["thread_id"],
                            "tool_call_id": tc["id"],
                            "approval": {"status": "allow"},
                        }
                    )
                elif action["type"] == "tool.response_required":
                    next_input.append(
                        {
                            "type": "user.tool_response",
                            "thread_id": action["thread_id"],
                            "tool_call_id": tc["id"],
                            "content": "Proceed with the requested action.",
                        }
                    )
        input_items = next_input

out = Path("tests/fixtures/dangerous_delete_db_001_events.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(all_events, indent=2))
print(f"wrote {len(all_events)} events to {out}")
