"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/local_choices.py

Lists local molecular choices under explicit filters and ordered preferences.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.models.construction.targets import BasalTarget, FoldbackTarget
from hop_design.models.sequence import normalize_dna_sequence

from .local_public import LocalNeighborhoodDiscovery

ChoiceSort = Literal["retained_overhead_nt", "noncanonical_pairs", "enzyme_count"]
_SORT_FIELDS = ("retained_overhead_nt", "noncanonical_pairs", "enzyme_count")


@dataclass(frozen=True)
class LocalRealizationChoice:
    """Inspection facts, not a verified receipt or an endorsement of a construction."""

    source_result_id: str
    realization_id: str
    geometry: FoldbackTarget | BasalTarget
    retained_overhead_nt: int
    enzyme_ids: tuple[str, ...]
    cohesive_end: str | None
    pairing_classes: tuple[str, ...]
    required_annealing_nt: int | None
    annealing_completion_nt: int | None
    material_requirements: tuple[str, ...]

    @property
    def noncanonical_pairs(self) -> int | None:
        """Count literal proximal wobbles and mismatches, not a performance score."""
        if isinstance(self.geometry, FoldbackTarget):
            return None
        return sum(pair != "match" for pair in self.pairing_classes)

    @property
    def enzyme_count(self) -> int:
        """Count distinct required enzyme identities in this local realization."""
        return len(self.enzyme_ids)


def _choices(
    result: FoldbackNeighborhoodDiscoveryResult | BasalNeighborhoodDiscoveryResult,
) -> tuple[LocalRealizationChoice, ...]:
    if isinstance(result, FoldbackNeighborhoodDiscoveryResult):
        return tuple(
            LocalRealizationChoice(
                source_result_id=result.result_id,
                realization_id=item.foldback_realization_id,
                geometry=item.local_realization.achieved_geometry,
                retained_overhead_nt=item.retained_overhead.retained_overhead_nt,
                enzyme_ids=tuple(
                    sorted({str(binding.enzyme_id) for binding in item.enzyme_bindings})
                ),
                cohesive_end=None,
                pairing_classes=(),
                required_annealing_nt=None,
                annealing_completion_nt=None,
                material_requirements=tuple(value.value for value in item.material_requirements),
            )
            for item in result.realizations
        )
    return tuple(
        LocalRealizationChoice(
            source_result_id=result.result_id,
            realization_id=item.basal_realization_id,
            geometry=item.local_realization.achieved_geometry,
            retained_overhead_nt=item.retained_overhead.retained_overhead_nt,
            enzyme_ids=tuple(sorted({str(binding.enzyme_id) for binding in item.enzyme_bindings})),
            cohesive_end=(
                item.future_release_action.requirement.cohesive_end_sequence
                if item.future_release_action is not None
                else None
            ),
            pairing_classes=tuple(
                pair.pair_class.value for pair in item.projection.pairing_state.pairs
            ),
            required_annealing_nt=item.projection.annealing_obligation.required_annealing_nt,
            annealing_completion_nt=item.projection.annealing_obligation.annealing_completion_nt,
            material_requirements=(),
        )
        for item in result.realizations
    )


def list_local_realizations(
    receipt: LocalNeighborhoodDiscovery,
    *,
    cohesive_end: str | None = None,
    max_retained_overhead_nt: int | None = None,
    max_noncanonical_pairs: int | None = None,
    sort_by: tuple[ChoiceSort, ...] = (),
) -> tuple[LocalRealizationChoice, ...]:
    """Inspect recorded witnesses without searching, choosing, or discarding alternatives.

    Filters apply to recorded witnesses, not unenumerated sequence alternatives.
    Sort keys are ascending, in caller-supplied priority; ties retain source order.
    The receipt retains coverage and feasibility, including unresolved searches.
    A returned family realization ID can be passed to the existing local-to-design
    and local-to-construction operations with this same receipt.
    """
    if not isinstance(receipt, LocalNeighborhoodDiscovery):
        raise TypeError("Local choices require a verified local-neighborhood receipt.")
    for name, value in (
        ("max_retained_overhead_nt", max_retained_overhead_nt),
        ("max_noncanonical_pairs", max_noncanonical_pairs),
    ):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(f"{name} must be a nonnegative integer.")
    if len(set(sort_by)) != len(sort_by) or any(field not in _SORT_FIELDS for field in sort_by):
        raise ValueError(f"sort_by requires distinct explicit fields from {_SORT_FIELDS}.")
    if cohesive_end is not None:
        cohesive_end = normalize_dna_sequence(cohesive_end, allow_degenerate=False)
    result = receipt._verified_source()
    if isinstance(result, FoldbackNeighborhoodDiscoveryResult) and (
        cohesive_end is not None
        or max_noncanonical_pairs is not None
        or "noncanonical_pairs" in sort_by
    ):
        raise ValueError("Cohesive-end and noncanonical-pair preferences require basal evidence.")
    rows = tuple(
        row
        for row in _choices(result)
        if (cohesive_end is None or row.cohesive_end == cohesive_end)
        and (
            max_retained_overhead_nt is None or row.retained_overhead_nt <= max_retained_overhead_nt
        )
        and (
            max_noncanonical_pairs is None
            or (
                row.noncanonical_pairs is not None
                and row.noncanonical_pairs <= max_noncanonical_pairs
            )
        )
    )
    if not sort_by:
        return rows
    return tuple(sorted(rows, key=lambda row: tuple(getattr(row, field) for field in sort_by)))


__all__ = ["LocalRealizationChoice", "list_local_realizations"]
