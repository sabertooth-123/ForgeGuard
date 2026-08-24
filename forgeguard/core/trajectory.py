"""Normalizes TrueForge's raw event log into a Trajectory.

Field names and event shapes here are taken directly from a real captured run via
`GET /sessions/{id}/turns/{id}/events` (see scripts/inspect_events.py), not assumed.

Important, non-obvious API quirk found the hard way: this persisted/REST events
endpoint uses **snake_case** field names (`tool_calls`, `thread_id`, `tool_call_id`)
and returns each tool call as one complete, consolidated `model.message` event -- this
is a *different* wire format from the live SSE stream used by the TypeScript SDK, which
is **camelCase** and fragments each tool call across many `model.message.delta` chunks
that must be reassembled. forgeguard's Python client deliberately avoids SSE (see
trueforge_client/client.py) and only ever reads the REST endpoint, so this module only
needs to handle the snake_case, consolidated shape -- do not merge in camelCase/delta
handling without re-verifying against a real captured event log first.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from forgeguard.core.models import ToolCallRecord, Trajectory


def build_trajectory(
    run_id: str,
    scenario_id: str,
    started_at: datetime,
    raw_events: list[dict[str, Any]],
    approval_decisions: dict[str, str] | None = None,
) -> Trajectory:
    """Build a Trajectory from the full raw event log of every turn in a scenario run.

    approval_decisions: tool_call_id -> "allow"/"deny", supplied by the caller (the
    client is the one making that decision, so it isn't recoverable from the events
    alone -- TrueForge only records our decision as the *input* to the next turn, not
    as an event on the trajectory itself).
    """
    approval_decisions = approval_decisions or {}

    calls_by_id: dict[str, ToolCallRecord] = {}
    ordered_call_ids: list[str] = []
    final_response: str | None = None
    errors: list[str] = []

    for event in raw_events:
        etype = event.get("type")

        if etype == "model.message":
            for tc in event.get("tool_calls") or []:
                func = tc.get("function") or {}
                try:
                    arguments = json.loads(func.get("arguments") or "{}")
                except json.JSONDecodeError:
                    arguments = {"_unparsed": func.get("arguments")}

                record = ToolCallRecord(
                    id=tc["id"],
                    name=func.get("name", ""),
                    mcp_server=arguments.get("mcp_server"),
                    tool_name=arguments.get("tool_name"),
                    arguments=arguments,
                )
                calls_by_id[record.id] = record
                ordered_call_ids.append(record.id)

        elif etype == "tool.response":
            record = calls_by_id.get(event.get("tool_call_id"))
            if record is not None:
                record.result = event.get("content")

        elif etype == "tool.approval_required":
            # Deliberately NOT merged with tool.response_required: that one just means
            # the model called ask_user_question (a clarifying question, no safety
            # implication). Only this event means TrueForge's actual approval gate
            # fired -- conflating the two would make require_approval_for checks lie.
            for ref in event.get("tool_calls", []):
                record = calls_by_id.get(ref.get("id"))
                if record is not None:
                    record.approval_required = True

        elif etype == "turn.done":
            state = event.get("state", {})
            status = state.get("status")
            if status == "error":
                errors.append(state.get("message", "unknown error"))
            elif status == "done":
                output = state.get("output")
                if output and output.get("content"):
                    final_response = output["content"]

    for call_id, decision in approval_decisions.items():
        record = calls_by_id.get(call_id)
        if record is not None:
            record.approval_decision = decision  # type: ignore[assignment]

    return Trajectory(
        run_id=run_id,
        scenario_id=scenario_id,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        tool_calls=[calls_by_id[cid] for cid in ordered_call_ids],
        final_response=final_response,
        errors=errors,
        raw_events=raw_events,
    )
