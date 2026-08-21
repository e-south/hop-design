"""Deterministic one-design compiler."""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.catalog.defaults import (
    BASAL_REF,
    CATALOG_REF,
    CONSTRAINT_PROFILE_REF,
    DEFAULTS_REF,
    FOLDBACK_REF,
    PROCESSING_ROUTE_REF,
    generic_direct_synthesis_route,
)
from hop_design.design.assembly import assemble_compilation
from hop_design.design.basal import evaluate_basal_pairing
from hop_design.design.foldback import evaluate_foldback
from hop_design.design.processing import project_released_strand_state
from hop_design.design.result import Compilation
from hop_design.design.views import (
    build_basal_pairing_view,
    build_basal_view,
    build_foldback_junction_view,
    build_foldback_view,
    build_released_workflow_view,
)
from hop_design.export.svg import render_workflow_svg
from hop_design.models.basal import BasalEvaluation, BasalPolicyStatus
from hop_design.models.diagnostics import CheckReport, Diagnostic, Severity
from hop_design.models.foldback import FoldbackEvaluation
from hop_design.models.processing import (
    ComponentAssemblyRoute,
    PlanProcessingRoute,
    ProcessingRoute,
    ResolvedMechanicsRoute,
    ResolvedMechanicsStep,
)
from hop_design.models.spec import DesignSpec, HopSpec, ResolvedHopSpec
from hop_design.models.strand_state import ReleasedStrandState
from hop_design.serialization import canonical_json_bytes


class UnknownCatalogReferenceError(ValueError):
    """Raised when a spec names a reference absent from the locked public catalog."""


@dataclass(frozen=True)
class _ResolvedMechanics:
    report: CheckReport
    foldback: FoldbackEvaluation
    basal: BasalEvaluation
    released_state: ReleasedStrandState | None


def _evaluate_resolved_spec(spec: ResolvedHopSpec) -> _ResolvedMechanics:
    foldback = evaluate_foldback(spec.foldback)
    basal = evaluate_basal_pairing(spec.basal.pairing, constraints=spec.basal.constraints)
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
    return _ResolvedMechanics(
        report=CheckReport(diagnostics=tuple(diagnostics)),
        foldback=foldback,
        basal=basal,
        released_state=released_state,
    )


def check_spec(spec: DesignSpec) -> CheckReport:
    """Check expected design feasibility for one supported specification."""
    if isinstance(spec, ResolvedHopSpec):
        return _evaluate_resolved_spec(spec).report
    _resolve_route(spec)
    return CheckReport()


def compile_spec(spec: DesignSpec) -> Compilation:
    """Compile one generic or explicit-mechanics specification."""
    if isinstance(spec, ResolvedHopSpec):
        resolved = _evaluate_resolved_spec(spec)
        resolved.report.raise_for_errors()
        foldback_ref = resolved.foldback.junction.junction_id
        basal_ref = resolved.basal.junction.junction_id
        steps: list[ResolvedMechanicsStep] = []
        if resolved.released_state is not None:
            steps.extend(
                (
                    ResolvedMechanicsStep(
                        step_id="nick",
                        operation="nick",
                        input_states=("precursor_duplex",),
                        output_state="nicked_precursor",
                    ),
                    ResolvedMechanicsStep(
                        step_id="duplex-release",
                        operation="duplex_release",
                        input_states=("nicked_precursor",),
                        output_state="released_active_strand",
                    ),
                )
            )
            foldback_input = "released_active_strand"
        else:
            foldback_input = "authored_foldback_precursor"
        steps.extend(
            (
                ResolvedMechanicsStep(
                    step_id="foldback",
                    operation="foldback",
                    input_states=(foldback_input,),
                    output_state="foldback_junction",
                ),
                ResolvedMechanicsStep(
                    step_id="basal-pairing",
                    operation="basal_pairing",
                    input_states=("authored_basal_arms",),
                    output_state="basal_junction",
                ),
            )
        )
        terminal_nick = spec.basal.terminal_nick
        if terminal_nick is None:
            steps.append(
                ResolvedMechanicsStep(
                    step_id="insert-assembly",
                    operation="assemble_insert",
                    input_states=(
                        "foldback_junction",
                        "basal_junction",
                        "authored_payload",
                    ),
                    output_state="hairpin_encoding_insert",
                )
            )
            route: PlanProcessingRoute = ComponentAssemblyRoute(
                route_id=spec.processing_route_ref,
                description=(
                    "Validated caller-supplied foldback and basal components assembled "
                    "without a discovery or processing-route claim."
                ),
                catalog_ref=spec.catalog_ref,
                foldback=resolved.foldback,
                basal=resolved.basal,
                steps=tuple(steps),
            )
        else:
            steps.extend(
                (
                    ResolvedMechanicsStep(
                        step_id="terminal-nick",
                        operation="terminal_nick",
                        input_states=("basal_junction",),
                        output_state="terminal_nicked_basal_junction",
                    ),
                    ResolvedMechanicsStep(
                        step_id="insert-assembly",
                        operation="assemble_insert",
                        input_states=(
                            "foldback_junction",
                            "terminal_nicked_basal_junction",
                            "authored_payload",
                        ),
                        output_state="hairpin_encoding_insert",
                    ),
                )
            )
            route = ResolvedMechanicsRoute(
                route_id=spec.processing_route_ref,
                description=(
                    "Caller-resolved nick, release, foldback, and basal-junction events; "
                    "catalog eligibility remains caller-owned."
                ),
                catalog_ref=spec.catalog_ref,
                foldback=resolved.foldback,
                basal=resolved.basal,
                terminal_nick=terminal_nick,
                released_state=resolved.released_state,
                steps=tuple(steps),
            )
        intermediates = canonical_json_bytes(
            {
                "schema": "hop.expected-intermediates/v1",
                "foldback": resolved.foldback.model_dump(mode="json"),
                "basal": resolved.basal.model_dump(mode="json"),
                "released_state": (
                    None
                    if resolved.released_state is None
                    else resolved.released_state.model_dump(mode="json")
                ),
            }
        )
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
            route=route,
            catalog_ref=spec.catalog_ref,
            foldback_ref=foldback_ref,
            basal_ref=basal_ref,
            foldback_sequence=resolved.foldback.junction_sequence,
            basal_left_arm=resolved.basal.profile.left_arm,
            basal_right_arm=resolved.basal.profile.right_arm,
            route_source_sequence=(
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
    route = _resolve_route(spec)
    return assemble_compilation(
        spec=spec,
        report=report,
        route=route,
        catalog_ref=CATALOG_REF,
        foldback_ref=route.foldback_junction.junction_id,
        basal_ref=route.basal_junction.junction_id,
        foldback_sequence=route.foldback_junction.sequence,
        basal_left_arm=route.basal_junction.left_arm,
        basal_right_arm=route.basal_junction.right_arm,
        route_source_sequence=None,
        additional_artifacts={},
    )


def _resolve_route(spec: HopSpec) -> ProcessingRoute:
    expected = {
        "defaults": (spec.defaults_ref, DEFAULTS_REF),
        "foldback junction": (spec.junction.foldback.ref, FOLDBACK_REF),
        "basal junction": (spec.junction.basal.ref, BASAL_REF),
        "processing route": (spec.processing_route_ref, PROCESSING_ROUTE_REF),
        "constraint profile": (spec.constraint_profile_ref, CONSTRAINT_PROFILE_REF),
    }
    for label, (actual, supported) in expected.items():
        if actual != supported:
            raise UnknownCatalogReferenceError(
                f"Unknown {label} reference {actual!r}; locked catalog supports {supported!r}."
            )
    return generic_direct_synthesis_route()
