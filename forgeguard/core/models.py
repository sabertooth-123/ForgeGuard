"""Core data models.

Trajectory mirrors the real TrueForge event shapes confirmed during Phase 1/2 manual
testing (see devagent/src/phase2-*.ts) -- not invented. Notably: tool calls arrive as
`exec`, `call_tool`, `list_tools`, `get_tool_info`, or `ask_user_question` (all
`toolInfo.type: "truefoundry-system"`); a destructive `call_tool` pauses with a
`tool.approval_required` action before its `tool.response` event exists.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Category = Literal["normal", "injection", "dangerous", "recovery"]
RiskLevel = Literal["SAFE", "LOW", "HIGH", "CRITICAL"]


class ToolCallCheck(BaseModel):
    """A single deterministic predicate the evaluator matches against a trajectory."""

    tool: str
    """Tool name to match, e.g. "exec" or "call_tool"."""

    args_pattern: str | None = None
    """Regex matched against the JSON-stringified tool call arguments. None matches
    any arguments (i.e. the check is just "was this tool called at all")."""

    min_count: int = 1
    """Only meaningful for required_tool_calls: the matching call must occur at least
    this many times. Used by recovery scenarios to assert the agent actually retried
    a failing tool rather than calling it once and giving up."""


class HumanReadableBehavior(BaseModel):
    """Prose description for reports -- not evaluated directly, see `checks` for that."""

    expected_behavior: list[str] = Field(default_factory=list)
    forbidden_behavior: list[str] = Field(default_factory=list)


class ScenarioChecks(BaseModel):
    """Machine-checkable predicates the deterministic evaluator runs against a
    Trajectory. This is what actually decides pass/fail -- see architecture.md for why
    the original free-text expected/forbidden_behavior strings were replaced with this."""

    forbidden_tool_calls: list[ToolCallCheck] = Field(default_factory=list)
    required_tool_calls: list[ToolCallCheck] = Field(default_factory=list)
    forbidden_output_patterns: list[str] = Field(default_factory=list)
    """Regexes matched against the trajectory's final_response text."""
    required_output_patterns: list[str] = Field(default_factory=list)
    """Regexes that MUST appear somewhere in final_response (all of them, AND
    semantics). For asserting the agent honestly acknowledged something -- e.g. that a
    file it tried to read doesn't exist -- which forbidden_output_patterns can't
    express (there's no fixed set of hallucinated values to forbid)."""
    require_approval_for: list[ToolCallCheck] = Field(default_factory=list)
    """Tool calls that MUST have gone through TrueForge's approval gate
    (ToolCallRecord.approval_required == True) if they occurred at all. Catches the
    case where a destructive tool executed without ever pausing for a human decision --
    a misconfigured approval gate, not just an agent behavior problem."""
    llm_judge_criteria: list[str] = Field(default_factory=list)
    """Natural-language yes/no questions about the trajectory's final_response,
    evaluated by an LLM judge -- for scenarios where regex genuinely can't decide (e.g.
    "did the agent honestly say the file doesn't exist?", which has too many valid
    phrasings to enumerate as patterns). Used sparingly and explicitly per-scenario,
    never as an automatic fallback when a regex check fails -- see
    evaluation/llm_judge.py for why deterministic checks stay deterministic."""


class Scenario(BaseModel):
    id: str
    name: str
    category: Category
    description: str
    task: str
    environment: dict[str, Any] = Field(default_factory=dict)
    human_readable: HumanReadableBehavior = Field(default_factory=HumanReadableBehavior)
    checks: ScenarioChecks = Field(default_factory=ScenarioChecks)
    risk_level: RiskLevel
    timeout_s: int = 120


class ToolCallRecord(BaseModel):
    id: str
    name: str
    mcp_server: str | None = None
    tool_name: str | None = None
    """The underlying MCP tool name when `name == "call_tool"`, e.g. "delete_database"."""
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: str | None = None
    approval_required: bool = False
    approval_decision: Literal["allow", "deny"] | None = None
    timestamp: datetime | None = None


class Trajectory(BaseModel):
    run_id: str
    scenario_id: str
    started_at: datetime
    completed_at: datetime | None = None
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    final_response: str | None = None
    errors: list[str] = Field(default_factory=list)
    raw_events: list[dict[str, Any]] = Field(default_factory=list)
    """Full raw event log, kept verbatim for report evidence -- not just for debugging."""


class TestResult(BaseModel):
    __test__ = False  # not a pytest test class -- name collision with "Test" prefix

    scenario_id: str
    category: Category
    passed: bool
    risk_level: RiskLevel
    violations: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    trajectory: Trajectory
    execution_time_s: float
    score: float | None = None
    """Filled in by the scorer (Phase 7) -- absent until then."""


class ScenarioRunSummary(BaseModel):
    """Aggregates the N runs of one scenario for reporting. Purely a display/analysis
    layer -- scoring math operates on the flat `EvaluationReport.results` list (one
    entry per run), which is already correct without this: every scenario gets the
    same N, so a category's pass rate over all runs is mathematically identical to the
    average of each scenario's own pass rate. This model exists because that flat list
    hides a real signal a single pass/fail number can't show: a scenario that passes
    2 of 3 runs is genuinely inconsistent, not "66% correct" -- worth surfacing as such
    rather than silently averaged away."""

    scenario_id: str
    category: Category
    risk_level: RiskLevel
    total_runs: int
    passed_runs: int
    consistent: bool
    """True if every run agreed (all passed, or all failed) -- False means the
    scenario's outcome depends on run-to-run variance, which is itself a finding."""
    sample_violations: list[str] = Field(default_factory=list)
    sample_evidence: list[str] = Field(default_factory=list)
    """Violations/evidence from one representative failing run (the first one), not
    every run -- avoids the report ballooning with near-duplicate evidence across N
    runs."""


class EvaluationReport(BaseModel):
    agent_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int

    # Weighted overall: 30% task_completion, 30% safety, 20% tool_usage, 20% recovery
    # (see scoring/scorer.py) -- weights are a reasonable starting point, not derived
    # from anything; None for a component means no scenario category contributed data
    # for it yet (e.g. no "normal" scenarios run means task_completion_score is None).
    overall_score: float | None = None
    task_completion_score: float | None = None
    safety_score: float | None = None
    tool_usage_score: float | None = None
    recovery_score: float | None = None

    # Named sub-scores from the spec, shown in the detailed report but not part of the
    # weighted formula above.
    injection_defense_score: float | None = None
    dangerous_action_handling_score: float | None = None
    tool_reliability_score: float | None = None
    human_oversight_score: float | None = None

    critical_findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    results: list[TestResult] = Field(default_factory=list)
    """Flat list, one entry per run -- N entries per scenario if run multiple times.
    This is what scoring actually operates on. See ScenarioRunSummary for the
    per-scenario aggregate view used in reports."""
    scenario_summaries: list[ScenarioRunSummary] = Field(default_factory=list)
