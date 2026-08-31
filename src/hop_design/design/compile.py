"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/compile.py

Builds and compiles one deterministic hairpin design specification.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from hop_design.catalog.defaults import (
    BASAL_REF,
    CATALOG_REF,
    CONSTRAINT_PROFILE_REF,
    DEFAULTS_REF,
    DESIGN_DERIVATION_REF,
    FOLDBACK_REF,
    generic_catalog_junction_derivation,
)
from hop_design.design.assembly import assemble_compilation
from hop_design.design.basal import evaluate_basal_pairing
from hop_design.design.foldback import evaluate_foldback
from hop_design.design.processing import project_released_strand_state
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
from hop_design.models.basal_policy import BasalEvaluation, BasalPolicyStatus
from hop_design.models.derivation import (
    CatalogJunctionDerivation,
    EvaluatedComponentDerivation,
    ExactJunctionComponentDerivation,
    PlanDesignDerivation,
    ResolvedJunctionDerivation,
)
from hop_design.models.diagnostics import CheckReport, Diagnostic, Severity
from hop_design.models.foldback import FoldbackEvaluation
from hop_design.models.payload import DegeneratePayload, ExactPayload
from hop_design.models.sequence import EXACT_DNA_ALPHABET, normalize_dna_sequence
from hop_design.models.spec import (
    BasalSelection,
    DesignAuthoritySpec,
    DesignLimits,
    DesignSpec,
    ExactJunctionDesignSpec,
    FoldbackSelection,
    HopSpec,
    JunctionRequest,
    ResolvedHopSpec,
)
from hop_design.models.stem import PairedStemExtension
from hop_design.models.strand_state import ReleasedStrandState
from hop_design.serialization import canonical_json_bytes


class UnknownCatalogReferenceError(ValueError):
    """Raised when a spec names a reference absent from the locked public catalog."""


def create_catalog_spec(*, sequence: str, design_id: str | None = None) -> HopSpec:
    """Build one strict design specification against the locked public catalog."""
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
        design_derivation_ref=DESIGN_DERIVATION_REF,
        constraint_profile_ref=CONSTRAINT_PROFILE_REF,
        defaults_ref=DEFAULTS_REF,
        constraints=DesignLimits(max_candidates=1),
    )


@dataclass(frozen=True)
class _ResolvedComponents:
    report: CheckReport
    foldback: FoldbackEvaluation
    basal: BasalEvaluation
    stem_extension: PairedStemExtension | None
    released_state: ReleasedStrandState | None


def _evaluate_resolved_spec(spec: ResolvedHopSpec) -> _ResolvedComponents:
    foldback = evaluate_foldback(spec.foldback)
    basal = evaluate_basal_pairing(spec.basal.pairing, constraints=spec.basal.constraints)
    stem_extension = (
        None if spec.stem_extension is None else evaluate_paired_stem_extension(spec.stem_extension)
    )
    diagnostics = [*foldback.report.diagnostics, *basal.report.diagnostics]
    released_state: ReleasedStrandState | None = None
    if spec.release is not None:
        release = project_released_strand_state(spec.release)
        diagnostics.extend(release.report.diagnostics)
        released_state = release.projection
        if (
            released_state is not None
            and released_state.active_product_sequence != spec.foldback.precursor_sequence
        ):
            diagnostics.append(
                Diagnostic(
                    code="HOP-ROUTE-001",
                    severity=Severity.ERROR,
                    path="release",
                    message=(
                        "The released active product must equal the foldback precursor input."
                    ),
                    evidence={
                        "released_active_product": released_state.active_product_sequence,
                        "foldback_precursor": spec.foldback.precursor_sequence,
                    },
                )
            )
    if (
        basal.decision.status is BasalPolicyStatus.RESERVE
        and spec.basal.acceptance == "active_only"
    ):
        diagnostics.append(
            Diagnostic(
                code="HOP-BASAL-003",
                severity=Severity.ERROR,
                path="basal.acceptance",
                message="A reserve basal profile requires acceptance='allow_reserve'.",
                evidence={"reason": basal.decision.reason.value},
            )
        )
    return _ResolvedComponents(
        report=CheckReport(diagnostics=tuple(diagnostics)),
        foldback=foldback,
        basal=basal,
        stem_extension=stem_extension,
        released_state=released_state,
    )


def check_spec(spec: DesignSpec) -> CheckReport:
    """Check expected design feasibility for one supported specification."""
    if isinstance(spec, ResolvedHopSpec):
        return _evaluate_resolved_spec(spec).report
    _resolve_derivation(spec)
    return CheckReport()


def compile_spec(spec: DesignAuthoritySpec) -> Compilation:
    """Compile one catalog-backed or explicit-component design specification."""
    if isinstance(spec, ExactJunctionDesignSpec):
        exact_derivation = ExactJunctionComponentDerivation(
            derivation_id=spec.design_derivation_ref,
            description=(
                "Exact caller-selected foldback and basal components used to derive one "
                "hairpin encoding without a production-method claim."
            ),
            catalog_ref=spec.catalog_ref,
            foldback_junction=spec.foldback_junction,
            basal_junction=spec.basal_junction,
        )
        return assemble_compilation(
            spec=spec,
            report=CheckReport(),
            derivation=exact_derivation,
            catalog_ref=spec.catalog_ref,
            foldback_ref=spec.foldback_junction.junction_id,
            basal_ref=spec.basal_junction.junction_id,
            foldback_sequence=spec.foldback_junction.sequence,
            basal_left_arm=spec.basal_junction.left_arm,
            basal_right_arm=spec.basal_junction.right_arm,
            stem_extension=None,
            derivation_source_sequence=None,
            additional_artifacts={},
        )
    if isinstance(spec, ResolvedHopSpec):
        resolved = _evaluate_resolved_spec(spec)
        resolved.report.raise_for_errors()
        foldback_ref = resolved.foldback.junction.junction_id
        basal_ref = resolved.basal.junction.junction_id
        terminal_nick = spec.basal.terminal_nick
        if terminal_nick is None:
            derivation: PlanDesignDerivation = EvaluatedComponentDerivation(
                derivation_id=spec.design_derivation_ref,
                description=(
                    "Evaluated caller-supplied foldback and basal components used to derive "
                    "one hairpin encoding without a production-method claim."
                ),
                catalog_ref=spec.catalog_ref,
                foldback=resolved.foldback,
                basal=resolved.basal,
                stem_extension=resolved.stem_extension,
            )
        else:
            derivation = ResolvedJunctionDerivation(
                derivation_id=spec.design_derivation_ref,
                description=(
                    "Exact strand projection, nick geometry, foldback, and basal components "
                    "used to derive one hairpin encoding."
                ),
                catalog_ref=spec.catalog_ref,
                foldback=resolved.foldback,
                basal=resolved.basal,
                stem_extension=resolved.stem_extension,
                terminal_nick=terminal_nick,
                released_foldback_source=resolved.released_state,
            )
        intermediate_payload = {
            "schema": "hop.expected-intermediates/v1",
            "foldback": resolved.foldback.model_dump(mode="json"),
            "basal": resolved.basal.model_dump(mode="json"),
            "released_state": (
                None
                if resolved.released_state is None
                else resolved.released_state.model_dump(mode="json")
            ),
        }
        if resolved.stem_extension is not None:
            intermediate_payload["stem_extension"] = resolved.stem_extension.model_dump(mode="json")
        intermediates = canonical_json_bytes(intermediate_payload)
        foldback_view = (
            build_foldback_junction_view(resolved.foldback)
            if terminal_nick is None
            else build_foldback_view(resolved.foldback)
        )
        basal_view = (
            build_basal_pairing_view(resolved.basal)
            if terminal_nick is None
            else build_basal_view(resolved.basal, nicked_strand=terminal_nick.strand)
        )
        additional_artifacts: dict[str, tuple[bytes, str]] = {
            "expected-intermediates.json": (intermediates, "application/json"),
            "foldback-view.json": (canonical_json_bytes(foldback_view), "application/json"),
            "foldback-view.svg": (render_workflow_svg(foldback_view), "image/svg+xml"),
            "basal-view.json": (canonical_json_bytes(basal_view), "application/json"),
            "basal-view.svg": (render_workflow_svg(basal_view), "image/svg+xml"),
        }
        if resolved.released_state is not None:
            released_view = build_released_workflow_view(
                resolved.released_state,
                resolved.foldback,
            )
            additional_artifacts.update(
                {
                    "released-workflow-view.json": (
                        canonical_json_bytes(released_view),
                        "application/json",
                    ),
                    "released-workflow-view.svg": (
                        render_workflow_svg(released_view),
                        "image/svg+xml",
                    ),
                }
            )
        return assemble_compilation(
            spec=spec,
            report=resolved.report,
            derivation=derivation,
            catalog_ref=spec.catalog_ref,
            foldback_ref=foldback_ref,
            basal_ref=basal_ref,
            foldback_sequence=resolved.foldback.junction_sequence,
            basal_left_arm=resolved.basal.profile.left_arm,
            basal_right_arm=resolved.basal.profile.right_arm,
            stem_extension=resolved.stem_extension,
            derivation_source_sequence=(
                None
                if terminal_nick is None
                else (
                    spec.foldback.precursor_sequence
                    if spec.release is None
                    else spec.release.precursor_top_strand
                )
            ),
            additional_artifacts=additional_artifacts,
        )

    report = check_spec(spec)
    catalog_derivation = _resolve_derivation(spec)
    return assemble_compilation(
        spec=spec,
        report=report,
        derivation=catalog_derivation,
        catalog_ref=CATALOG_REF,
        foldback_ref=catalog_derivation.foldback_junction.junction_id,
        basal_ref=catalog_derivation.basal_junction.junction_id,
        foldback_sequence=catalog_derivation.foldback_junction.sequence,
        basal_left_arm=catalog_derivation.basal_junction.left_arm,
        basal_right_arm=catalog_derivation.basal_junction.right_arm,
        stem_extension=None,
        derivation_source_sequence=None,
        additional_artifacts={},
    )


def _resolve_derivation(spec: HopSpec) -> CatalogJunctionDerivation:
    expected = {
        "defaults": (spec.defaults_ref, DEFAULTS_REF),
        "foldback junction": (spec.junction.foldback.ref, FOLDBACK_REF),
        "basal junction": (spec.junction.basal.ref, BASAL_REF),
        "design derivation": (spec.design_derivation_ref, DESIGN_DERIVATION_REF),
        "constraint profile": (spec.constraint_profile_ref, CONSTRAINT_PROFILE_REF),
    }
    for label, (actual, supported) in expected.items():
        if actual != supported:
            raise UnknownCatalogReferenceError(
                f"Unknown {label} reference {actual!r}; locked catalog supports {supported!r}."
            )
    return generic_catalog_junction_derivation()
