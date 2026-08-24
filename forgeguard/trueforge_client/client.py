"""Python HTTP client for TrueForge -- launches scenario runs and pulls trajectories.

Deliberately avoids the streaming (SSE) turn API. `stream=false` on turn creation
returns the running turn immediately (confirmed via the OpenAPI spec: "When stream is
false: the running turn"), so this client polls `GET .../turns/{id}` for completion and
then fetches the full event log via `GET .../turns/{id}/events` -- functionally
identical data to the SSE stream, far simpler and more robust to parse correctly from
Python than hand-rolling SSE.

Rate-limit backoff exists because of hard-won experience today: free-tier providers
return a *terminal* turn with state.status == "error" and a message mentioning the
limit -- this is not an HTTP-level failure, so it has to be detected by reading the
turn's own error message, not by catching a request exception.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Literal

import httpx

from forgeguard.core.models import Scenario, Trajectory
from forgeguard.core.trajectory import build_trajectory

logger = logging.getLogger("forgeguard.trueforge_client")

RATE_LIMIT_MARKERS = ("429", "rate limit", "quota exceeded")
RETRY_AFTER_RE = re.compile(r"retry in ([\d.]+)s", re.IGNORECASE)

ApprovalPolicy = Callable[[str], Literal["allow", "deny"]]
ResponsePolicy = Callable[[str], str]


def _default_approval_policy(_tool_call_id: str) -> Literal["allow", "deny"]:
    return "allow"


def _default_response_policy(_tool_call_id: str) -> str:
    return "Proceed with the requested action."


class ScenarioRunError(Exception):
    """Raised when a scenario run fails for a reason other than rate limiting
    (e.g. exceeds max_rounds, or the turn errors with a non-rate-limit message)."""


class TrueForgeClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8790",
        timeout_s: float = 120.0,
        max_rate_limit_retries: int = 5,
        default_backoff_s: float = 5.0,
    ) -> None:
        self._http = httpx.Client(base_url=base_url, timeout=timeout_s)
        self._max_rate_limit_retries = max_rate_limit_retries
        self._default_backoff_s = default_backoff_s

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "TrueForgeClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- low-level HTTP -----------------------------------------------------------

    def create_session(self, agent_name: str) -> str:
        resp = self._http.post("/api/v1/sessions", json={"agent": {"name": agent_name}})
        resp.raise_for_status()
        return resp.json()["data"]["id"]

    def _create_turn(self, session_id: str, input_items: list[dict[str, Any]]) -> dict[str, Any]:
        resp = self._http.post(
            f"/api/v1/sessions/{session_id}/turns",
            json={"input": input_items, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["data"]

    def _wait_for_turn(
        self, session_id: str, turn_id: str, poll_interval_s: float = 1.0, max_wait_s: float = 180.0
    ) -> dict[str, Any]:
        deadline = time.monotonic() + max_wait_s
        while True:
            resp = self._http.get(f"/api/v1/sessions/{session_id}/turns/{turn_id}")
            resp.raise_for_status()
            turn = resp.json()["data"]
            if turn["state"]["status"] != "running":
                return turn
            if time.monotonic() > deadline:
                raise ScenarioRunError(f"turn {turn_id} did not finish within {max_wait_s}s")
            time.sleep(poll_interval_s)

    def get_turn_events(self, session_id: str, turn_id: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params = {"limit": 100}
            if page_token:
                params["page_token"] = page_token
            resp = self._http.get(f"/api/v1/sessions/{session_id}/turns/{turn_id}/events", params=params)
            resp.raise_for_status()
            body = resp.json()
            events.extend(body["data"])
            page_token = body.get("pagination", {}).get("next_page_token")
            if not page_token:
                return events

    # -- rate-limit-aware turn execution --------------------------------------------

    @staticmethod
    def _is_rate_limited(turn: dict[str, Any]) -> bool:
        if turn["state"]["status"] != "error":
            return False
        message = turn["state"].get("message", "").lower()
        return any(marker in message for marker in RATE_LIMIT_MARKERS)

    def _run_turn_with_backoff(self, session_id: str, input_items: list[dict[str, Any]]) -> dict[str, Any]:
        """Create + wait for a turn, retrying the whole turn on rate-limit errors."""
        last_turn: dict[str, Any] | None = None
        for attempt in range(self._max_rate_limit_retries + 1):
            turn = self._create_turn(session_id, input_items)
            turn = self._wait_for_turn(session_id, turn["id"])
            if not self._is_rate_limited(turn):
                return turn
            last_turn = turn
            message = turn["state"].get("message", "")
            match = RETRY_AFTER_RE.search(message)
            delay = float(match.group(1)) + 1.0 if match else self._default_backoff_s * (2**attempt)
            logger.warning("rate limited (attempt %d), backing off %.1fs: %s", attempt + 1, delay, message)
            time.sleep(delay)
        raise ScenarioRunError(f"gave up after {self._max_rate_limit_retries} rate-limit retries: {last_turn}")

    # -- scenario orchestration -----------------------------------------------------

    def run_scenario(
        self,
        scenario: Scenario,
        agent_name: str = "dev-agent",
        max_rounds: int = 6,
        approval_policy: ApprovalPolicy = _default_approval_policy,
        response_policy: ResponsePolicy = _default_response_policy,
    ) -> Trajectory:
        run_id = self.create_session(agent_name)
        started_at = datetime.now(timezone.utc)

        raw_events: list[dict[str, Any]] = []
        approval_decisions: dict[str, str] = {}

        input_items: list[dict[str, Any]] = [{"type": "user.message", "content": scenario.task}]

        for _round in range(max_rounds):
            turn = self._run_turn_with_backoff(run_id, input_items)
            raw_events.extend(self.get_turn_events(run_id, turn["id"]))

            if turn["state"]["status"] == "error":
                raw_events.append(
                    {"type": "turn.done", "state": {"status": "error", "message": turn["state"].get("message")}}
                )
                break

            required_actions = turn["state"].get("required_actions") or []
            if not required_actions:
                break

            next_input: list[dict[str, Any]] = []
            for action in required_actions:
                thread_id = action["thread_id"]
                for tc in action["tool_calls"]:
                    call_id = tc["id"]
                    if action["type"] == "tool.approval_required":
                        decision = approval_policy(call_id)
                        approval_decisions[call_id] = decision
                        next_input.append(
                            {
                                "type": "user.tool_approval",
                                "thread_id": thread_id,
                                "tool_call_id": call_id,
                                "approval": {"status": decision},
                            }
                        )
                    elif action["type"] == "tool.response_required":
                        next_input.append(
                            {
                                "type": "user.tool_response",
                                "thread_id": thread_id,
                                "tool_call_id": call_id,
                                "content": response_policy(call_id),
                            }
                        )
            input_items = next_input
        else:
            raise ScenarioRunError(f"scenario {scenario.id} did not finish within {max_rounds} rounds")

        return build_trajectory(
            run_id=run_id,
            scenario_id=scenario.id,
            started_at=started_at,
            raw_events=raw_events,
            approval_decisions=approval_decisions,
        )
