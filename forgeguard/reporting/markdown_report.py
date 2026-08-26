"""Human-readable Markdown report -- adapted from the spec's example format. Each
failed scenario's violations and evidence are pulled straight from its TestResult
rather than from the flat critical_findings strings, since that's the more complete,
directly useful version of the same information."""

from __future__ import annotations

from forgeguard.core.models import EvaluationReport


def _score_line(label: str, value: float | None) -> str | None:
    if value is None:
        return None
    return f"**{label}:** {value}/100"


def render_markdown_report(report: EvaluationReport) -> str:
    lines: list[str] = ["# ForgeGuard Report", "", f"**Agent:** {report.agent_name}", ""]

    for label, value in [
        ("Overall", report.overall_score),
        ("Task Completion", report.task_completion_score),
        ("Safety", report.safety_score),
        ("Tool Usage", report.tool_usage_score),
        ("Recovery", report.recovery_score),
    ]:
        line = _score_line(label, value)
        if line:
            lines.append(line)
    lines.append("")

    lines.append("## Sub-scores")
    lines.append("")
    for label, value in [
        ("Prompt Injection Defense", report.injection_defense_score),
        ("Dangerous Action Handling", report.dangerous_action_handling_score),
        ("Tool Reliability", report.tool_reliability_score),
        ("Human Oversight", report.human_oversight_score),
    ]:
        if value is not None:
            lines.append(f"- {label}: {value}/100")
    lines.append("")

    lines.append(f"## Tests: {report.passed_tests}/{report.total_tests} runs passed")
    lines.append("")
    for summary in report.scenario_summaries:
        if summary.total_runs > 1:
            status = f"{summary.passed_runs}/{summary.total_runs}" + ("" if summary.consistent else " (inconsistent)")
        else:
            status = "PASS" if summary.passed_runs else "FAIL"
        lines.append(f"- [{status}] `{summary.scenario_id}` ({summary.category}, risk={summary.risk_level})")
    lines.append("")

    failing = [s for s in report.scenario_summaries if s.passed_runs < s.total_runs]
    if failing:
        lines.append("## Critical Findings")
        lines.append("")
        for summary in failing:
            note = "" if summary.total_runs == 1 else f" -- {summary.passed_runs}/{summary.total_runs} runs passed"
            lines.append(f"### [{summary.risk_level}] {summary.scenario_id}{note}")
            lines.append("")
            for violation in summary.sample_violations:
                lines.append(f"- {violation}")
            if summary.sample_evidence:
                lines.append("")
                lines.append("**Evidence:**")
                lines.append("")
                for item in summary.sample_evidence:
                    lines.append(f"```\n{item}\n```")
            lines.append("")

    if report.recommendations:
        lines.append("## Recommendations")
        lines.append("")
        for rec in report.recommendations:
            lines.append(f"- {rec}")
        lines.append("")

    return "\n".join(lines)
