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

    lines.append(f"## Tests: {report.passed_tests}/{report.total_tests} passed")
    lines.append("")
    for result in report.results:
        mark = "PASS" if result.passed else "FAIL"
        lines.append(f"- [{mark}] `{result.scenario_id}` ({result.category}, risk={result.risk_level})")
    lines.append("")

    failed = [r for r in report.results if not r.passed]
    if failed:
        lines.append("## Critical Findings")
        lines.append("")
        for result in failed:
            lines.append(f"### [{result.risk_level}] {result.scenario_id}")
            lines.append("")
            for violation in result.violations:
                lines.append(f"- {violation}")
            if result.evidence:
                lines.append("")
                lines.append("**Evidence:**")
                lines.append("")
                for item in result.evidence:
                    lines.append(f"```\n{item}\n```")
            lines.append("")

    if report.recommendations:
        lines.append("## Recommendations")
        lines.append("")
        for rec in report.recommendations:
            lines.append(f"- {rec}")
        lines.append("")

    return "\n".join(lines)
