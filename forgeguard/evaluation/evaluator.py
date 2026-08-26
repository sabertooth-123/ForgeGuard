"""Turns a (Scenario, Trajectory) pair into a TestResult.

Deterministic checks run first, always. LLM-judge criteria (evaluation/llm_judge.py)
only run for scenarios that explicitly declare `checks.llm_judge_criteria` -- most
scenarios have none, so this is a no-op for them, not an extra model call every time.
"""

from __future__ import annotations

from forgeguard.core.models import Scenario, TestResult, Trajectory
from forgeguard.evaluation.deterministic import evaluate_deterministic
from forgeguard.evaluation.llm_judge import JudgeFn, evaluate_llm_judge_criteria, ollama_judge


def evaluate(scenario: Scenario, trajectory: Trajectory, judge_fn: JudgeFn = ollama_judge) -> TestResult:
    violations, evidence = evaluate_deterministic(scenario, trajectory)

    if scenario.checks.llm_judge_criteria:
        judge_violations, judge_evidence = evaluate_llm_judge_criteria(
            scenario.checks.llm_judge_criteria, trajectory.final_response, judge_fn
        )
        violations += judge_violations
        evidence += judge_evidence

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
