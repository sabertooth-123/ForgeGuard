import json
from datetime import datetime, timezone
from pathlib import Path

from forgeguard.core.trajectory import build_trajectory

FIXTURES = Path(__file__).parent / "fixtures"


def _load_events(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text())


def test_parses_approval_gated_tool_call():
    events = _load_events("dangerous_delete_db_001_events.json")
    trajectory = build_trajectory(
        run_id="test-run",
        scenario_id="dangerous_delete_db_001",
        started_at=datetime.now(timezone.utc),
        raw_events=events,
        approval_decisions={"call_d5do2yxj": "allow"},
    )

    assert len(trajectory.tool_calls) == 1
    call = trajectory.tool_calls[0]
    assert call.name == "call_tool"
    assert call.tool_name == "delete_database"
    assert call.mcp_server == "dangerous-tools"
    assert call.approval_required is True
    assert call.approval_decision == "allow"
    assert call.result is not None and "Simulated" in call.result

    assert trajectory.final_response == 'The "orders_legacy" database has been deleted as requested.'
    assert trajectory.errors == []


def test_missing_approval_decision_leaves_field_none():
    events = _load_events("dangerous_delete_db_001_events.json")
    trajectory = build_trajectory(
        run_id="test-run",
        scenario_id="dangerous_delete_db_001",
        started_at=datetime.now(timezone.utc),
        raw_events=events,
        # no approval_decisions supplied
    )
    assert trajectory.tool_calls[0].approval_decision is None
    assert trajectory.tool_calls[0].approval_required is True  # still True -- came from the event, not our input


def test_response_required_does_not_count_as_approval_required():
    events = [
        {
            "type": "model.message",
            "id": "m1",
            "finish_reason": "tool_calls",
            "tool_calls": [
                {
                    "id": "call_q1",
                    "function": {"name": "ask_user_question", "arguments": '{"question": "which db?"}'},
                }
            ],
        },
        {
            "type": "tool.response_required",
            "id": "e1",
            "thread_id": "main",
            "tool_calls": [{"id": "call_q1", "source_event_id": "m1"}],
        },
        {"type": "turn.done", "id": "t1", "state": {"status": "done", "output": None, "required_actions": []}},
    ]
    trajectory = build_trajectory("r", "s", datetime.now(timezone.utc), events)
    assert trajectory.tool_calls[0].approval_required is False
