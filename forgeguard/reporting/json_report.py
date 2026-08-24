"""Machine-readable JSON report -- just the EvaluationReport's own schema, since
Pydantic already gives us a stable, typed serialization for free."""

from __future__ import annotations

from pathlib import Path

from forgeguard.core.models import EvaluationReport


def write_json_report(report: EvaluationReport, path: Path) -> None:
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
