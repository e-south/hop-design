"""Machine-readable design diagnostics."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, JsonValue

from hop_design.models.base import HopModel


class Severity(StrEnum):
    """Diagnostic severity."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Diagnostic(HopModel):
    """One stable, actionable finding about an expected design condition."""

    code: str = Field(pattern=r"^HOP-[A-Z]+-[0-9]{3}$")
    severity: Severity
    path: str = Field(min_length=1)
    message: str = Field(min_length=1)
    evidence: dict[str, JsonValue] = Field(default_factory=dict)
    suggestions: tuple[str, ...] = ()


class CheckReport(HopModel):
    """Aggregate expected design diagnostics without masking software errors."""

    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def has_errors(self) -> bool:
        """Return whether any diagnostic prevents compilation."""
        return any(item.severity is Severity.ERROR for item in self.diagnostics)

    @property
    def status(self) -> Literal["valid", "infeasible"]:
        """Summarize whether the design can proceed."""
        return "infeasible" if self.has_errors else "valid"

    def raise_for_errors(self) -> None:
        """Raise a typed exception when this report is infeasible."""
        if self.has_errors:
            raise InfeasibleDesignError(self)


class InfeasibleDesignError(ValueError):
    """Raised only when a caller elects to convert diagnostics into an exception."""

    def __init__(self, report: CheckReport) -> None:
        self.report = report
        codes = ", ".join(
            item.code for item in report.diagnostics if item.severity is Severity.ERROR
        )
        super().__init__(f"HOP design is infeasible: {codes}")
