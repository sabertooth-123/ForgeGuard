from pathlib import Path

from forgeguard.core.scenario import ScenarioLoadError, load_scenarios

SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


def test_loads_all_scenarios():
    scenarios = load_scenarios(SCENARIOS_DIR)
    assert len(scenarios) >= 2
    ids = {s.id for s in scenarios}
    assert "injection_readme_001" in ids
    assert "dangerous_delete_db_001" in ids


def test_filters_by_category():
    injection_only = load_scenarios(SCENARIOS_DIR, category="injection")
    assert all(s.category == "injection" for s in injection_only)
    assert len(injection_only) >= 1


def test_dangerous_scenario_has_approval_check():
    scenarios = load_scenarios(SCENARIOS_DIR, category="dangerous")
    scenario = next(s for s in scenarios if s.id == "dangerous_delete_db_001")
    assert scenario.risk_level == "CRITICAL"
    assert len(scenario.checks.require_approval_for) == 1
    assert scenario.checks.require_approval_for[0].tool == "call_tool"


def test_duplicate_scenario_id_raises(tmp_path):
    cat_dir = tmp_path / "normal"
    cat_dir.mkdir()
    scenario_json = """{
        "id": "dup_001", "name": "a", "category": "normal", "description": "d",
        "task": "t", "risk_level": "SAFE"
    }"""
    (cat_dir / "a.json").write_text(scenario_json)
    (cat_dir / "b.json").write_text(scenario_json)

    try:
        load_scenarios(tmp_path)
        assert False, "expected ScenarioLoadError"
    except ScenarioLoadError as exc:
        assert "duplicate scenario id" in str(exc)
