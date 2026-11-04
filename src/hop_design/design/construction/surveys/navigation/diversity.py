"""Stratify existing geometry streams without changing their canonical addresses."""

from typing import TYPE_CHECKING, Any

from hop_design.models.construction.targets import FoldbackTarget
from hop_design.models.construction.variants.objective import DesignSearchObjective

from ...search.diversity import stratified_costs
from ..coordinates import coordinate_at
from ..geometry_order import GeometryOrder

if TYPE_CHECKING:
    from ..branches import SurveyBranches
    from ..partitions import ProductParts


def factor_costs(
    rows: list[dict[str, Any]], ordinary: tuple[int, ...], objective: DesignSearchObjective
) -> tuple[int, ...]:
    """Rank one factor's requested classes before or after local admission."""
    parameters = objective.parameters
    if (
        "loop_word" in parameters
        and rows
        and all(row.get("loop_word") is None and row.get("loop_nt") is not None for row in rows)
    ):
        # Length partitions unknown words; exact words still determine result diversity.
        parameters = tuple("loop_nt" if key == "loop_word" else key for key in parameters)
    return stratified_costs(rows, ordinary, parameters)


def diversity_order(branches: "SurveyBranches", objective: DesignSearchObjective) -> GeometryOrder:
    return GeometryOrder(
        tuple(
            factor_costs(rows, ordinary, objective)
            for rows, ordinary in zip(
                _factors(branches), branches.geometry_order.costs, strict=True
            )
        )
    )


def foldback_values(case: FoldbackTarget) -> dict[str, Any]:
    return {
        "foldback_arm_bp": case.annealing_arm_length_bp,
        "join_offset_nt": case.junction_offset_nt,
        "loop_nt": case.loop_length_nt,
        "loop_word": case.loop_sequence,
        "foldback_strand": case.nick_strand.value,
    }


def _factors(branches: "SurveyBranches") -> tuple[list[dict[str, Any]], ...]:
    return (
        [{"left_gap": p.left_bp, "right_gap": p.right_bp} for p in branches.placements],
        [{"basal_nick_offset_nt": n} for n in branches.request.basal.geometry.nick_offsets_nt],
        [{"adapter_annealing_min_nt": n} for n in branches.request.basal.annealing_lengths_nt],
        [{"release_method": method} for method in branches.release_methods],
        [foldback_values(case) for case in branches.foldback_cases],
        [{} for _ in branches.request.release.basal_projections],
    )


def local_page_values(
    parts: "ProductParts", page: int, parameters: tuple[str, ...]
) -> dict[str, Any]:
    """Read known page coordinates; local support is not a complete witness."""
    if parts.conflict is not None or parts.empty_candidates:
        return {}
    assert parts.foldback is not None and parts.basal_candidates is not None
    foldback, basal = coordinate_at((parts.foldback.parts, parts.basal_candidates.parts), page)
    values: dict[str, Any] = {}
    if "foldback_method" in parameters:
        values["foldback_method"] = parts.foldback.method_at(foldback)
    if "basal_method" in parameters:
        values["basal_method"] = parts.basal_candidates.method_at(basal)
    if "loop_word" in parameters:
        values["loop_word"] = parts.foldback.loop_sequence(foldback)
    return values


def geometry_values(branches: "SurveyBranches", geometry: tuple[int, ...]) -> dict[str, Any]:
    return {
        key: value
        for factor, index in zip(_factors(branches), geometry, strict=True)
        for key, value in factor[index].items()
    }
