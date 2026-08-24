import json
from pathlib import Path

from forgeguard.core.scenario import load_scenarios
from forgeguard.trueforge_client.client import TrueForgeClient

scenarios = load_scenarios(Path("scenarios"))
scenario = next(s for s in scenarios if s.id == "dangerous_delete_db_001")

with TrueForgeClient() as client:
    session_id = client.create_session("dev-agent")
    turn = client._create_turn(session_id, [{"type": "user.message", "content": scenario.task}])
    turn = client._wait_for_turn(session_id, turn["id"])
    events = client.get_turn_events(session_id, turn["id"])

print(f"turn status: {turn['state']['status']}")
print(f"event count: {len(events)}\n")
for e in events:
    print(json.dumps(e)[:400])
