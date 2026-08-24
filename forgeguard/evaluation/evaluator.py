"""Turns a (Scenario, Trajectory) pair into a TestResult.

Deliberately just a thin wrapper around the deterministic evaluator right now -- no
llm_judge.py exists yet. Per engineering principle "no half-finished implementations":
none of the current scenarios need semantic judgment, so a judge module would just be
dead code. Add it when a scenario actually requires one (Phase 9), not before.
"""

from __future__ import annotations

from forgeguard.core.models import Scenario, TestResult, Trajectory
from forgeguard.evaluation.deterministic import evaluate_deterministic


def evaluate(scenario: Scenario, trajectory: Trajectory) -> TestResult:
    violations, evidence = evaluate_deterministic(scenario, trajectory)

    execution_time_s = 0.0
    if trajectory.completed_at is not None:
        execution_time_s = (trajectory.completed_at - trajectory.started_at).total_seconds()

    return TestResult(
        scenario_id=scenario.id,
        category=scenario.category,
        passed=len(violations) == 0,
        risk_level=scenario.risk_level,
        violations=violations,
        evidence=evidence,
        trajectory=trajectory,
        execution_time_s=execution_time_s,
    )
