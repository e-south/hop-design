from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.models.diagnostics import (
    CheckReport,
    Diagnostic,
    InfeasibleDesignError,
    Severity,
)


def test_check_report_exposes_expected_design_errors_without_throwing() -> None:
    report = CheckReport(
        diagnostics=(
            Diagnostic(
                code="HOP-SPEC-001",
                severity=Severity.ERROR,
                path="payload.sequence",
                message="The payload is incompatible with the selected route.",
                evidence={"route": "hop:processing-route/example@1"},
                suggestions=("Choose a compatible route.",),
            ),
        )
    )

    assert report.has_errors
    assert report.status == "infeasible"
    with pytest.raises(InfeasibleDesignError, match="HOP-SPEC-001") as error:
        report.raise_for_errors()
    assert error.value.report == report


def test_valid_report_has_no_errors() -> None:
    report = CheckReport()

    assert not report.has_errors
    assert report.status == "valid"
    report.raise_for_errors()


def test_diagnostic_code_is_namespaced_and_stable() -> None:
    with pytest.raises(ValidationError):
        Diagnostic(
            code="bad-code",
            severity=Severity.ERROR,
            path="payload",
            message="Invalid.",
        )
