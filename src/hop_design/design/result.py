"""Compiler result and bundle-write boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from hop_design.models.bundle import HopBundle
from hop_design.models.diagnostics import CheckReport
from hop_design.models.plan import HopPlan
from hop_design.models.spec import DesignSpec


@dataclass(frozen=True)
class Compilation:
    """One checked spec, resolved plan, bundle manifest, and generated artifacts."""

    spec: DesignSpec
    report: CheckReport
    plan: HopPlan
    bundle: HopBundle
    artifacts: Mapping[str, bytes]

    def write(self, output: str | Path) -> Path:
        """Atomically write the verified bundle without replacing existing data."""
        from hop_design.design.bundle import write_bundle

        return write_bundle(self, Path(output))


__all__ = ["Compilation"]
