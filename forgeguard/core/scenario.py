"""Loads Scenario objects from the data-driven scenarios/ directory.

Adding a new scenario should never require touching this file -- just drop a JSON file
under scenarios/<category>/.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from forgeguard.core.models import Scenario

CATEGORIES = ("normal", "injection", "dangerous", "recovery")


class ScenarioLoadError(Exception):
    """Raised when a scenario file is missing, malformed, or fails validation."""


def load_scenario_file(path: Path) -> Scenario:
    """Parse and validate a single scenario JSON file."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScenarioLoadError(f"{path}: invalid JSON ({exc})") from exc

    try:
        return Scenario.model_validate(raw)
    except ValidationError as exc:
        raise ScenarioLoadError(f"{path}: failed schema validation:\n{exc}") from exc


def load_scenarios(scenarios_dir: Path, category: str | None = None) -> list[Scenario]:
    """Load every scenario under scenarios_dir, optionally filtered to one category.

    Raises ScenarioLoadError on the first malformed file rather than silently skipping
    it -- a broken scenario file should stop a run, not quietly shrink the test suite.
    """
    categories = (category,) if category else CATEGORIES
    scenarios: list[Scenario] = []
    seen_ids: dict[str, Path] = {}

    for cat in categories:
        cat_dir = scenarios_dir / cat
        if not cat_dir.is_dir():
            continue
        for path in sorted(cat_dir.glob("*.json")):
            scenario = load_scenario_file(path)
            if scenario.id in seen_ids:
                raise ScenarioLoadError(
                    f"{path}: duplicate scenario id {scenario.id!r} "
                    f"(already used by {seen_ids[scenario.id]})"
                )
            seen_ids[scenario.id] = path
            scenarios.append(scenario)

    return scenarios
