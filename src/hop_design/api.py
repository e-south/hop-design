"""Stable public operations for HOP Design."""

from __future__ import annotations

import hashlib

from hop_design.catalog.defaults import (
    BASAL_REF,
    CONSTRAINT_PROFILE_REF,
    DEFAULTS_REF,
    FOLDBACK_REF,
    PROCESSING_ROUTE_REF,
)
from hop_design.design.basal import evaluate_basal_pairing
from hop_design.design.basal_candidates import search_basal_candidates
from hop_design.design.basal_processing import search_basal_processing_geometries
from hop_design.design.basal_routes import search_basal_processing_routes
from hop_design.design.bundle import load_verified_bundle, verify_bundle
from hop_design.design.candidates import search_foldback_precursors
from hop_design.design.compile import check_spec, compile_spec
from hop_design.design.design_space import plan_design_space
from hop_design.design.discovery import search_nicking_placements
from hop_design.design.foldback import evaluate_foldback, search_foldback_arms
from hop_design.design.linear_source_method import (
    compile_linear_source_multinick_hairpin_pcr,
)
from hop_design.design.loading import load_spec
from hop_design.design.method import resolve_linear_source_hairpin_pcr_materials
from hop_design.design.method_bundle import (
    compile_linear_source_method_bundle,
    load_verified_method_bundle,
    verify_method_bundle,
)
from hop_design.design.method_views import build_method_trajectory_view
from hop_design.design.payloads import (
    collect_payloads,
    expand_payload,
    load_csv_payloads,
    load_fasta_payloads,
)
from hop_design.design.processing import project_released_strand_state
from hop_design.design.released_foldback import (
    search_released_foldback_geometries,
    search_released_foldback_precursors,
)
from hop_design.design.result import Compilation
from hop_design.design.stem import evaluate_paired_stem_extension
from hop_design.design.views import (
    build_basal_pairing_view,
    build_basal_view,
    build_foldback_junction_view,
    build_foldback_view,
    build_released_workflow_view,
)
from hop_design.export.svg import render_workflow_svg
from hop_design.kernel.site_scanning import (
    classify_motif_presence,
    scan_nicking_agent,
    scan_release_agent,
)
from hop_design.models.diagnostics import CheckReport
from hop_design.models.payload import DegeneratePayload, ExactPayload
from hop_design.models.sequence import EXACT_DNA_ALPHABET, normalize_dna_sequence
from hop_design.models.spec import (
    BasalSelection,
    DesignLimits,
    DesignSpec,
    FoldbackSelection,
    HopSpec,
    JunctionRequest,
)

__all__ = [
    "build_basal_pairing_view",
    "build_basal_view",
    "build_foldback_junction_view",
    "build_foldback_view",
    "build_method_trajectory_view",
    "build_released_workflow_view",
    "check",
    "classify_motif_presence",
    "collect_payloads",
    "compile",
    "compile_linear_source_method_bundle",
    "compile_linear_source_multinick_hairpin_pcr",
    "create_spec",
    "evaluate_basal_pairing",
    "evaluate_foldback",
    "evaluate_paired_stem_extension",
    "expand_payload",
    "load_csv_payloads",
    "load_fasta_payloads",
    "load_spec",
    "load_verified_bundle",
    "load_verified_method_bundle",
    "plan_design_space",
    "project_released_strand_state",
    "render_workflow_svg",
    "resolve_linear_source_hairpin_pcr_materials",
    "scan_nicking_agent",
    "scan_release_agent",
    "search_basal_candidates",
    "search_basal_processing_geometries",
    "search_basal_processing_routes",
    "search_foldback_arms",
    "search_foldback_precursors",
    "search_nicking_placements",
    "search_released_foldback_geometries",
    "search_released_foldback_precursors",
    "verify_bundle",
    "verify_method_bundle",
]


def create_spec(*, sequence: str, design_id: str | None = None) -> HopSpec:
    """Expand one input sequence into a strict spec with a visible generic default."""
    normalized = normalize_dna_sequence(sequence, allow_degenerate=True)
    payload = (
        ExactPayload(sequence=normalized)
        if set(normalized) <= EXACT_DNA_ALPHABET
        else DegeneratePayload(sequence=normalized)
    )
    resolved_design_id = (
        design_id or f"sequence-{hashlib.sha256(normalized.encode()).hexdigest()[:8]}"
    )
    return HopSpec(
        design_id=resolved_design_id,
        payload=payload,
        junction=JunctionRequest(
            foldback=FoldbackSelection(ref=FOLDBACK_REF),
            basal=BasalSelection(ref=BASAL_REF),
        ),
        processing_route_ref=PROCESSING_ROUTE_REF,
        constraint_profile_ref=CONSTRAINT_PROFILE_REF,
        defaults_ref=DEFAULTS_REF,
        constraints=DesignLimits(max_candidates=1),
    )


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
