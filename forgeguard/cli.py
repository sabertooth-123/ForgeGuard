"""ForgeGuard CLI.

    forgeguard run
    forgeguard run --category injection
    forgeguard run --scenario injection_readme_001
    forgeguard list-scenarios
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import click
import httpx

# Windows consoles default to cp1252, which can't encode the box-drawing/checkmark
# characters below -- reconfigure to UTF-8 where possible (Python 3.7+), matching the
# same class of Windows-specific issue already hit with TrueForge itself today.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

from forgeguard.core.models import Trajectory
from forgeguard.core.scenario import ScenarioLoadError, load_scenarios
from forgeguard.evaluation.evaluator import evaluate
from forgeguard.reporting.json_report import write_json_report
from forgeguard.reporting.markdown_report import render_markdown_report
from forgeguard.scoring.scorer import compute_report
from forgeguard.trueforge_client.client import ScenarioRunError, TrueForgeClient

SCENARIOS_DIR = Path("scenarios")
REPORTS_DIR = Path("reports")


@click.group()
def main() -> None:
    """ForgeGuard -- stress-tests an AI agent inside TrueForge and scores the result."""


@main.command()
@click.option("--category", default=None, help="Only run scenarios in this category.")
@click.option("--scenario", "scenario_id", default=None, help="Only run this scenario id.")
@click.option("--agent", default="dev-agent", help="TrueForge agent name to test.")
@click.option(
    "--runs",
    default=1,
    type=click.IntRange(min=1),
    help="Run each scenario N times and report consistency across runs. A single run "
    "is a weak signal -- the same scenario has been observed to produce different "
    "tool-call choices run to run against a local model. Defaults to 1 to keep "
    "`forgeguard run` fast by default; pass --runs 3 or more for a trustworthy score.",
)
def run(category: str | None, scenario_id: str | None, agent: str, runs: int) -> None:
    """Run scenarios against a TrueForge agent and produce a report."""
    try:
        scenarios = load_scenarios(SCENARIOS_DIR, category=category)
    except ScenarioLoadError as exc:
        raise click.ClickException(str(exc)) from exc

    if scenario_id:
        scenarios = [s for s in scenarios if s.id == scenario_id]
        if not scenarios:
            raise click.ClickException(f"no scenario with id {scenario_id!r}")

    if not scenarios:
        raise click.ClickException("no scenarios matched")

    click.echo("ForgeGuard")
    click.echo("─" * 32)
    click.echo(f"Agent: {agent}")
    click.echo(f"Tests: {len(scenarios)}" + (f" x {runs} runs each" if runs > 1 else ""))
    click.echo()
    click.echo("Running...")
    click.echo()

    results = []
    with TrueForgeClient() as client:
        for scenario in scenarios:
            run_marks = []
            for _ in range(runs):
                try:
                    trajectory = client.run_scenario(scenario, agent_name=agent)
                    result = evaluate(scenario, trajectory)
                except httpx.TransportError as exc:
                    # A genuine connectivity loss (server down, port unreachable) means
                    # every remaining run would fail identically -- stop now with a
                    # clear diagnostic instead of grinding through the rest for nothing.
                    raise click.ClickException(
                        f"lost connection to TrueForge while running {scenario.id!r} ({exc}). "
                        f"Is it still running? {len(results)} run(s) were completed before "
                        f"this -- re-run with --scenario to resume individually."
                    ) from exc
                except (ScenarioRunError, httpx.HTTPStatusError) as exc:
                    empty_trajectory = Trajectory(
                        run_id="unknown",
                        scenario_id=scenario.id,
                        started_at=datetime.now(timezone.utc),
                        completed_at=datetime.now(timezone.utc),
                        errors=[str(exc)],
                    )
                    result = evaluate(scenario, empty_trajectory)
                results.append(result)
                run_marks.append("✓" if result.passed else "✗")

            passed_runs = run_marks.count("✓")
            suffix = f" ({passed_runs}/{runs})" if runs > 1 else ""
            click.echo(f"{''.join(run_marks)} {scenario.id}{suffix}")

    report = compute_report(agent, results)

    click.echo()
    click.echo("─" * 32)
    click.echo()
    for label, value in [
        ("Overall Score", report.overall_score),
        ("Task Completion", report.task_completion_score),
        ("Safety", report.safety_score),
        ("Tool Usage", report.tool_usage_score),
        ("Recovery", report.recovery_score),
    ]:
        if value is not None:
            click.echo(f"{label + ':':<16} {value}/100")
    click.echo()
    click.echo(f"Critical Findings: {len(report.critical_findings)}")
    if runs > 1:
        inconsistent = [s.scenario_id for s in report.scenario_summaries if not s.consistent]
        if inconsistent:
            click.echo(f"Inconsistent across runs: {', '.join(inconsistent)}")

    REPORTS_DIR.mkdir(exist_ok=True)
    json_path = REPORTS_DIR / "latest.json"
    md_path = REPORTS_DIR / "latest.md"
    write_json_report(report, json_path)
    md_path.write_text(render_markdown_report(report), encoding="utf-8")
    click.echo()
    click.echo(f"Full report: {json_path} / {md_path}")


@main.command(name="list-scenarios")
@click.option("--category", default=None, help="Only list scenarios in this category.")
def list_scenarios(category: str | None) -> None:
    """List available scenarios."""
    try:
        scenarios = load_scenarios(SCENARIOS_DIR, category=category)
    except ScenarioLoadError as exc:
        raise click.ClickException(str(exc)) from exc

    for scenario in scenarios:
        click.echo(f"{scenario.id:<28} [{scenario.category:<10}] risk={scenario.risk_level:<8} {scenario.name}")


@main.command()
def report() -> None:
    """Print the most recent report (from `forgeguard run`)."""
    md_path = REPORTS_DIR / "latest.md"
    if not md_path.exists():
        raise click.ClickException("no report yet -- run `forgeguard run` first")
    click.echo(md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
