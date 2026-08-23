"""Foldback-junction evaluation and bounded deterministic search use cases."""

from __future__ import annotations

from typing import Literal

from pydantic import JsonValue

from hop_design.kernel.foldback import (
    enumerate_foldback_arms,
    foldback_arm_candidate_count,
    summarize_pairing,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.diagnostics import CheckReport, Diagnostic, Severity
from hop_design.models.foldback import (
    FoldbackEvaluation,
    FoldbackEvaluationRequest,
    FoldbackSearchLimits,
    FoldbackSearchRequest,
    FoldbackSearchResult,
)
from hop_design.models.junction import FoldbackJunction
from hop_design.serialization import canonical_json_bytes, sha256_digest


def _error(
    code: str,
    *,
    path: str,
    message: str,
    evidence: dict[str, JsonValue],
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        path=path,
        message=message,
        evidence=evidence,
    )


def evaluate_foldback(request: FoldbackEvaluationRequest) -> FoldbackEvaluation:
    """Derive one foldback geometry and report all independent infeasibilities."""
    retained = request.precursor_sequence[
        request.retained_tract_span.start.offset : request.retained_tract_span.end.offset
    ]
    source_turn = request.precursor_sequence[
        request.source_turn_span.start.offset : request.source_turn_span.end.offset
    ]
    effective_turn = f"{source_turn}{request.turn_extension}"
    junction_sequence = f"{retained}{effective_turn}{request.foldback_arm}"
    arm_start = len(retained) + len(effective_turn)
    pairing = summarize_pairing(
        retained_sequence=retained,
        foldback_arm=request.foldback_arm,
        arm_start=arm_start,
    )
    added_nt = len(request.turn_extension) + len(request.foldback_arm)
    junction_seed = {
        "sequence": junction_sequence,
        "retained_nt": len(retained),
        "turn_nt": len(effective_turn),
        "pairs": [pair.model_dump(mode="json") for pair in pairing.pairs],
    }
    junction_digest = sha256_digest(canonical_json_bytes(junction_seed)).removeprefix("sha256:")
    junction = FoldbackJunction(
        junction_id=f"hop:foldback-junction/inline-{junction_digest[:16]}@1",
        sequence=junction_sequence,
        retained_tract_span=Span(start=Boundary(offset=0), end=Boundary(offset=len(retained))),
        turn_span=Span(start=Boundary(offset=len(retained)), end=Boundary(offset=arm_start)),
        foldback_arm_span=Span(
            start=Boundary(offset=arm_start),
            end=Boundary(offset=len(junction_sequence)),
        ),
        pairs=pairing.pairs,
    )
    diagnostics: list[Diagnostic] = []
    constraints = request.constraints

    if len(pairing.non_watson_crick_positions) > constraints.max_non_watson_crick_pairs:
        diagnostics.append(
            _error(
                "HOP-FOLD-001",
                path="foldback_arm",
                message="The foldback arm exceeds the non-Watson-Crick pair limit.",
                evidence={
                    "non_watson_crick_count": len(pairing.non_watson_crick_positions),
                    "max_non_watson_crick_pairs": constraints.max_non_watson_crick_pairs,
                },
            )
        )
    protected_non_watson_crick = tuple(
        position
        for position in pairing.non_watson_crick_positions
        if request.protected_region.contains_index(
            request.retained_tract_span.start.offset + position
        )
    )
    if protected_non_watson_crick and not constraints.allow_protected_region_non_watson_crick_pairs:
        diagnostics.append(
            _error(
                "HOP-FOLD-002",
                path="protected_region",
                message="A non-Watson-Crick pair overlaps the protected region.",
                evidence={
                    "retained_local_non_watson_crick_positions": list(protected_non_watson_crick)
                },
            )
        )
    if not (
        constraints.terminal_watson_crick_bp_min
        <= pairing.terminal_watson_crick_bp
        <= constraints.terminal_watson_crick_bp_max
    ):
        diagnostics.append(
            _error(
                "HOP-FOLD-003",
                path="constraints.terminal_watson_crick_bp",
                message="The terminal Watson-Crick run lies outside the declared range.",
                evidence={
                    "observed": pairing.terminal_watson_crick_bp,
                    "minimum": constraints.terminal_watson_crick_bp_min,
                    "maximum": constraints.terminal_watson_crick_bp_max,
                },
            )
        )
    if pairing.max_uninterrupted_watson_crick_bp > constraints.max_uninterrupted_watson_crick_bp:
        diagnostics.append(
            _error(
                "HOP-FOLD-004",
                path="constraints.max_uninterrupted_watson_crick_bp",
                message="The longest Watson-Crick run exceeds the declared maximum.",
                evidence={
                    "observed": pairing.max_uninterrupted_watson_crick_bp,
                    "maximum": constraints.max_uninterrupted_watson_crick_bp,
                },
            )
        )
    if added_nt > constraints.max_added_nt:
        diagnostics.append(
            _error(
                "HOP-FOLD-005",
                path="constraints.max_added_nt",
                message="The authored extension and foldback arm exceed the added-nt budget.",
                evidence={"observed": added_nt, "maximum": constraints.max_added_nt},
            )
        )
    if len(effective_turn) != constraints.required_turn_nt:
        diagnostics.append(
            _error(
                "HOP-FOLD-006",
                path="constraints.required_turn_nt",
                message="The effective turn length differs from the declared requirement.",
                evidence={
                    "observed": len(effective_turn),
                    "required": constraints.required_turn_nt,
                    "source_turn_nt": len(source_turn),
                    "turn_extension_nt": len(request.turn_extension),
                },
            )
        )

    return FoldbackEvaluation(
        precursor_sequence=request.precursor_sequence,
        retained_tract_span=request.retained_tract_span,
        source_turn_span=request.source_turn_span,
        protected_region=request.protected_region,
        turn_extension=request.turn_extension,
        designed_sequence=(
            f"{request.precursor_sequence}{request.turn_extension}{request.foldback_arm}"
        ),
        junction=junction,
        source_turn_sequence=source_turn,
        effective_turn_sequence=effective_turn,
        foldback_arm=request.foldback_arm,
        non_watson_crick_positions=pairing.non_watson_crick_positions,
        terminal_watson_crick_bp=pairing.terminal_watson_crick_bp,
        max_uninterrupted_watson_crick_bp=pairing.max_uninterrupted_watson_crick_bp,
        added_nt=added_nt,
        report=CheckReport(diagnostics=tuple(diagnostics)),
    )


def search_foldback_arms(
    request: FoldbackSearchRequest,
    *,
    limits: FoldbackSearchLimits,
) -> FoldbackSearchResult:
    """Enumerate exact-first foldback arms under explicit node and hit budgets."""
    retained = request.precursor_sequence[
        request.retained_tract_span.start.offset : request.retained_tract_span.end.offset
    ]
    candidate_space_size = foldback_arm_candidate_count(
        paired_bp=len(retained),
        max_non_watson_crick_pairs=request.constraints.max_non_watson_crick_pairs,
    )
    hits: list[FoldbackEvaluation] = []
    nodes = 0
    truncated_by: Literal["max_search_nodes", "max_hits"] | None = None

    for foldback_arm in enumerate_foldback_arms(
        retained,
        max_non_watson_crick_pairs=request.constraints.max_non_watson_crick_pairs,
    ):
        if nodes >= limits.max_search_nodes:
            truncated_by = "max_search_nodes"
            break
        evaluation = evaluate_foldback(
            FoldbackEvaluationRequest(
                precursor_sequence=request.precursor_sequence,
                retained_tract_span=request.retained_tract_span,
                source_turn_span=request.source_turn_span,
                protected_region=request.protected_region,
                turn_extension=request.turn_extension,
                foldback_arm=foldback_arm,
                constraints=request.constraints,
            )
        )
        nodes += 1
        if evaluation.report.status == "valid":
            hits.append(evaluation)
            if len(hits) >= limits.max_hits and nodes < candidate_space_size:
                truncated_by = "max_hits"
                break

    if truncated_by is not None:
        status: Literal["complete", "infeasible", "truncated"] = "truncated"
    elif hits:
        status = "complete"
    else:
        status = "infeasible"
    return FoldbackSearchResult(
        status=status,
        hits=tuple(hits),
        candidate_space_size=candidate_space_size,
        search_nodes_examined=nodes,
        truncated_by=truncated_by,
    )


__all__ = ["evaluate_foldback", "search_foldback_arms"]
