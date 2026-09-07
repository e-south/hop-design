"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/design_authority.py

Derives exact route-neutral design authorities from verified local realizations.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal, cast

from hop_design.design.compile import compile_spec
from hop_design.design.result import Compilation
from hop_design.kernel.foldback import summarize_pairing
from hop_design.models.construction.basal import (
    BasalNeighborhoodDiscoveryResult,
    BasalRealizationRecord,
)
from hop_design.models.construction.foldback import (
    FoldbackLocalRealization,
    FoldbackNeighborhoodDiscoveryResult,
)
from hop_design.models.construction.targets import FoldbackTarget
from hop_design.models.coordinates import BasePairCount, Boundary, Span
from hop_design.models.junction import (
    BasalJunction,
    FoldbackJunction,
    JunctionPairObservation,
    classify_literal_pair,
    derive_exact_basal_junction_id,
    derive_exact_foldback_junction_id,
)
from hop_design.models.payload import ExactPayload
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.models.spec import ExactJunctionDesignSpec

from .local_public import LocalNeighborhoodDiscovery
from .verification import (
    VerifiedBasalNeighborhoodResult,
    VerifiedFoldbackNeighborhoodResult,
)

_RouteDesignEndpoint = Literal[
    "ssdna_hairpin",
    "hairpin_pcr_duplex",
    "clone_ready_duplex",
]


def _foldback_result(receipt: LocalNeighborhoodDiscovery) -> FoldbackNeighborhoodDiscoveryResult:
    if not isinstance(receipt, LocalNeighborhoodDiscovery):
        raise TypeError("Foldback selection requires one local-neighborhood receipt.")
    verified = receipt._verified_authority()
    if not isinstance(verified, VerifiedFoldbackNeighborhoodResult):
        raise ValueError("Foldback selection requires a foldback receipt.")
    return verified.result


def _basal_result(receipt: LocalNeighborhoodDiscovery) -> BasalNeighborhoodDiscoveryResult:
    if not isinstance(receipt, LocalNeighborhoodDiscovery):
        raise TypeError("Basal selection requires one local-neighborhood receipt.")
    verified = receipt._verified_authority()
    if not isinstance(verified, VerifiedBasalNeighborhoodResult):
        raise ValueError("Basal selection requires a basal receipt.")
    return verified.result


def _select_foldback(
    result: FoldbackNeighborhoodDiscoveryResult,
    realization_id: str,
) -> FoldbackLocalRealization:
    selected = tuple(
        item for item in result.realizations if item.foldback_realization_id == realization_id
    )
    if len(selected) != 1:
        raise ValueError("The selected foldback realization was not found exactly once.")
    return selected[0]


def _select_basal(
    result: BasalNeighborhoodDiscoveryResult,
    realization_id: str,
) -> BasalRealizationRecord:
    selected = tuple(
        item for item in result.realizations if item.basal_realization_id == realization_id
    )
    if len(selected) != 1:
        raise ValueError("The selected basal realization was not found exactly once.")
    return selected[0]


def _foldback_junction(
    realization: FoldbackLocalRealization,
    *,
    payload_sequence: str,
) -> FoldbackJunction:
    paired_payload = reverse_complement_iupac(payload_sequence)
    payload_nt = len(payload_sequence)
    if not realization.retained_sequence.startswith(payload_sequence) or not (
        realization.retained_sequence.endswith(paired_payload)
    ):
        raise ValueError("Foldback realization does not preserve the selected payload arms.")
    junction_sequence = realization.retained_sequence[
        payload_nt : len(realization.retained_sequence) - payload_nt
    ]
    target = cast(FoldbackTarget, realization.local_realization.achieved_geometry)
    arm_nt = target.annealing_arm_length_bp
    turn_nt = target.loop_length_nt
    if len(junction_sequence) != 2 * arm_nt + turn_nt:
        raise ValueError("Foldback realization does not match its achieved junction geometry.")
    retained = junction_sequence[:arm_nt]
    turn = junction_sequence[arm_nt : arm_nt + turn_nt]
    arm = junction_sequence[arm_nt + turn_nt :]
    if turn != realization.loop_sequence or arm != realization.foldback_arm_sequence:
        raise ValueError("Foldback realization sequence parts do not replay its retained product.")
    arm_start = arm_nt + turn_nt
    pairing = summarize_pairing(
        retained_sequence=retained,
        foldback_arm=arm,
        arm_start=arm_start,
    )
    return FoldbackJunction(
        junction_id=derive_exact_foldback_junction_id(
            sequence=junction_sequence,
            retained_nt=arm_nt,
            turn_nt=turn_nt,
            pairs=pairing.pairs,
        ),
        sequence=junction_sequence,
        retained_tract_span=Span(
            start=Boundary(offset=0),
            end=Boundary(offset=arm_nt),
        ),
        turn_span=Span(
            start=Boundary(offset=arm_nt),
            end=Boundary(offset=arm_start),
        ),
        foldback_arm_span=Span(
            start=Boundary(offset=arm_start),
            end=Boundary(offset=len(junction_sequence)),
        ),
        pairs=pairing.pairs,
    )


def _basal_junction(realization: BasalRealizationRecord) -> BasalJunction:
    pairing_state = realization.projection.pairing_state
    if pairing_state is None:
        raise ValueError("Selected basal realization does not contain an exact pairing state.")
    left = pairing_state.source_sequence_5prime
    right = pairing_state.adapter_sequence_5prime
    pairs = tuple(
        JunctionPairObservation(
            left_index=index,
            right_index=len(right) - 1 - index,
            left_base=left[index],
            right_base=right[len(right) - 1 - index],
            kind=classify_literal_pair(
                left_base=left[index],
                right_base=right[len(right) - 1 - index],
            ),
        )
        for index in range(len(left))
    )
    return BasalJunction(
        junction_id=derive_exact_basal_junction_id(
            left_arm=left,
            right_arm=right,
            pairs=pairs,
        ),
        left_arm=left,
        right_arm=right,
        pair_count=BasePairCount(value=len(pairs)),
        pairs=pairs,
    )


def compile_design_from_local_realizations(
    *,
    design_id: str,
    payload_sequence: str,
    endpoint: _RouteDesignEndpoint,
    foldback: LocalNeighborhoodDiscovery,
    foldback_realization_id: str,
    basal: LocalNeighborhoodDiscovery | None,
    basal_realization_id: str | None,
) -> Compilation:
    """Compile one exact design from explicitly selected verified local realizations."""
    if endpoint == "ssdna_hairpin":
        raise ValueError(
            "Route-realization design compilation does not support the direct endpoint "
            "without a separately declared exact basal component."
        )
    if endpoint not in {"hairpin_pcr_duplex", "clone_ready_duplex"}:
        raise ValueError("Route-realization design endpoint must be PCR-bearing.")
    if basal is None or basal_realization_id is None:
        raise ValueError("A PCR-bearing endpoint requires one basal realization selection.")
    payload = ExactPayload(sequence=payload_sequence)
    foldback_record = _select_foldback(
        _foldback_result(foldback),
        foldback_realization_id,
    )
    basal_record = _select_basal(_basal_result(basal), basal_realization_id)
    if (
        foldback_record.payload_sequence != payload.sequence
        or basal_record.payload_sequence != payload.sequence
    ):
        raise ValueError("Local realization payload does not match the selected payload.")
    return compile_spec(
        ExactJunctionDesignSpec(
            design_id=design_id,
            payload=payload,
            foldback_junction=_foldback_junction(
                foldback_record,
                payload_sequence=payload.sequence,
            ),
            basal_junction=_basal_junction(basal_record),
        )
    )


__all__ = ["compile_design_from_local_realizations"]
