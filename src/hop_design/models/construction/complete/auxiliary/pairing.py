"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/auxiliary/pairing.py

Resolves explicit distal adapter constraints against invariant source bases.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.basal.pairing import derive_basal_pair_class
from hop_design.models.construction.targets import BasalPairAllowance, BasalPairConstraint

from ..pcr.pairing import complete_adapter_pairing
from ..preparation_diagnostics import PreparationConstraintDiagnostic


class FixedAdapterSequenceMismatch(ValueError):
    """An exact fixed adapter fails the already resolved annealing requirement."""

    def __init__(self, *, requested: str, available: str) -> None:
        message = "Fixed adapter sequence must start with the required pairing prefix."
        super().__init__(message)
        self.diagnostic = PreparationConstraintDiagnostic(
            code="fixed-adapter-sequence-mismatch",
            stage="endpoint-auxiliary-preparation",
            field="materialization.endpoint_auxiliaries.adapter.material.sequence_5prime",
            requirement="starts-with",
            requested=requested,
            available=available,
            message=message,
        )


class AdapterPairingPolicyError(ValueError):
    """The caller must refine an ambiguous or out-of-scope distal policy."""


def resolve_adapter_pairing_sequence(
    basal: BasalRealizationRecord,
    *,
    source_prefix: str,
    constraints: tuple[BasalPairConstraint, ...],
    fixed_sequence: str | None,
) -> str:
    """Resolve one exact distal arm; ambiguous unpinned domains require refinement."""
    canonical = complete_adapter_pairing(basal, source_prefix=source_prefix)
    local = basal.projection.pairing_state
    required = len(canonical.pairs)
    for declared in constraints:
        if not len(local.pairs) <= declared.position_from_ligation < required:
            raise AdapterPairingPolicyError(
                "Distal pairing constraints must lie outside the local junction "
                "within the required annealing span."
            )
    by_position = {item.position_from_ligation: item for item in constraints}
    adapter = list(canonical.adapter_sequence_5prime)
    action = basal.future_release_action
    end_bases = (
        {}
        if action is None
        else dict(
            action.adapter_end_bases(
                nick_offset_nt=basal.payload_source_map.segments[0].source_span.start.offset
                - basal.basal_nick.boundary.offset
            )
        )
    )
    for position in range(len(local.pairs), required):
        constraint = by_position.get(position)
        if constraint is None and position not in end_bases:
            continue
        source_base = canonical.pairs[position].source_base
        choices = (
            (adapter[position],)
            if constraint is None
            else tuple(
                base
                for base in constraint.allowed_adapter_bases
                if source_base in constraint.allowed_source_bases
                and (
                    constraint.allowed_class is BasalPairAllowance.ANY
                    or derive_basal_pair_class(source_base, base).value
                    == constraint.allowed_class.value
                )
            )
        )
        if position in end_bases:
            choices = tuple(base for base in choices if base == end_bases[position])
            if not choices:
                raise ValueError("Distal pairing constraints conflict with the exact future end.")
        if fixed_sequence is not None:
            if position >= len(fixed_sequence) or fixed_sequence[position] not in choices:
                raise ValueError("Fixed adapter violates a declared distal pairing constraint.")
            adapter[position] = fixed_sequence[position]
        elif len(choices) == 1:
            adapter[position] = choices[0]
        elif not choices:
            raise ValueError("No adapter base satisfies a declared distal pairing constraint.")
        else:
            raise AdapterPairingPolicyError(
                "Distal pairing is ambiguous; constrain the adapter base or supply a fixed adapter."
            )
    sequence = "".join(adapter)
    if fixed_sequence is not None and not fixed_sequence.startswith(sequence):
        raise FixedAdapterSequenceMismatch(requested=fixed_sequence, available=sequence)
    return sequence
