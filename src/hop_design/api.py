"""Stable public operations for HOP Design."""

from __future__ import annotations

from hop_design.design.basal import evaluate_basal_pairing
from hop_design.design.bundle import load_verified_bundle, verify_bundle
from hop_design.design.compile import check_spec, compile_spec, create_catalog_spec
from hop_design.design.design_space import plan_design_space
from hop_design.design.foldback import evaluate_foldback
from hop_design.design.loading import load_spec
from hop_design.design.payloads import (
    collect_payloads,
    expand_payload,
    load_csv_payloads,
    load_fasta_payloads,
)
from hop_design.design.processing import project_released_strand_state
from hop_design.design.result import Compilation
from hop_design.design.stem import evaluate_paired_stem_extension
from hop_design.models.diagnostics import CheckReport
from hop_design.models.spec import DesignSpec, HopSpec

__all__ = [
    "check",
    "collect_payloads",
    "compile",
    "create_spec",
    "evaluate_basal_pairing",
    "evaluate_foldback",
    "evaluate_paired_stem_extension",
    "expand_payload",
    "load_csv_payloads",
    "load_fasta_payloads",
    "load_spec",
    "load_verified_bundle",
    "plan_design_space",
    "project_released_strand_state",
    "verify_bundle",
]


def create_spec(*, sequence: str, design_id: str | None = None) -> HopSpec:
    """Expand one input sequence into a strict spec with a visible generic default."""
    return create_catalog_spec(sequence=sequence, design_id=design_id)


def check(spec: DesignSpec) -> CheckReport:
    """Return all expected feasibility diagnostics for one valid specification."""
    return check_spec(spec)


def compile(
    spec: DesignSpec | None = None,
    *,
    sequence: str | None = None,
    design_id: str | None = None,
) -> Compilation:
    """Compile either one explicit spec or one convenience sequence."""
    if (spec is None) == (sequence is None):
        raise TypeError("Provide exactly one of spec or sequence.")
    if spec is not None:
        if design_id is not None:
            raise TypeError("design_id is only valid with the sequence convenience input.")
        resolved_spec = spec
    else:
        assert sequence is not None
        resolved_spec = create_spec(sequence=sequence, design_id=design_id)
    return compile_spec(resolved_spec)
