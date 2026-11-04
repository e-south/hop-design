"""Translate admitted preferred candidates into existing completion groups."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hop_design.models.construction.surveys.completion import PreferredCompletionGroup
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits

from ..branches import SurveyBranches
from ..coordinates import coordinate_at, interleaved_rank
from ..navigation.diversity import geometry_values
from .group_preference import preferred_group_position
from .page_order import program_page_depth

if TYPE_CHECKING:
    from ..evaluate import LocalReceipts


def preferred_groups_for(
    locals_: LocalReceipts, branches: SurveyBranches, limits: SurveyEvaluationLimits, target: int
) -> tuple[PreferredCompletionGroup, ...]:
    from .execute import _frame

    result = []
    for candidate in locals_.preferred_candidates(branches, limits):
        if candidate.target != target:
            continue
        product, parts, bound = _frame(
            locals_, branches, limits, target, candidate.geometry_rank, candidate.page
        )
        if bound is None:
            raise ValueError("Preferred candidate has no admitted completion group.")
        plan = bound.plan
        group_position = None
        if not plan.populations:
            group_position = 0
        for i, population in enumerate(plan.populations):
            if len(candidate.source_context) != population.sequences.length_nt:
                continue
            canonical = population.group_of(candidate.source_context)
            policy = branches.request.materialization.source_preparation.source_ssdna
            order = locals_.partitions.context_priority(product, candidate.page, policy)._order(
                len(candidate.source_context)
            )
            preferred = None if order is None else order.preferred.sequences
            position = (
                canonical
                if preferred is None
                else preferred_group_position(
                    population, canonical, preferred, limits=limits.sequence_space_limits
                )
            )
            group_position = interleaved_rank(
                tuple(p.group_count for p in plan.populations), i, position
            )
            domain = plan.group_at(group_position, preferred=preferred)
            if domain.member_at(0)[1] != candidate.context_rank:
                raise ValueError("Preferred source context is not the group's first completion.")
            break
        if group_position is None:
            raise ValueError("Preferred context does not belong to the admitted length domain.")
        geometry = coordinate_at(branches.geometry_sizes, candidate.geometry_rank)
        depth = parts.depth(candidate.page)
        if limits.objective is not None:
            assert parts.foldback is not None and parts.basal_candidates is not None
            frame = (
                (target, geometry)
                if limits.objective.varies_foldback_members
                and geometry_values(branches, geometry)["loop_word"] is None
                else None
            )
            depth = program_page_depth(
                parts.foldback.program_cardinalities,
                parts.basal_candidates.program_cardinalities,
                candidate.page,
                foldback_frame=frame,
            )
        group = PreferredCompletionGroup.model_validate(
            {
                "geometry": geometry,
                "page": candidate.page,
                "group": group_position,
                "depth": depth,
            }
        )
        if group not in result:
            result.append(group)
    return tuple(result)


def has_preferred_work(address: dict[str, Any] | None, branches: SurveyBranches) -> bool:
    """Only bounded prefix introductions and their first pair attempts get priority."""
    if address is None:
        return False
    if "completion" in address:
        work = address["completion"]
        cursor = work["after"]
        geometry = coordinate_at(branches.geometry_sizes, work["geometry_rank"])
        return work["iteration"] == 0 and any(
            (tuple(g["geometry"]), g["page"], g["group"]) == (geometry, work["page"], work["group"])
            for g in cursor.get("preferred_groups", ())
        )
    cursor = address.get("completion_seek", {})
    groups = cursor.get("preferred_groups", ())
    if cursor.get("preferred_next", 0) < len(groups):
        return True
    addresses = {(tuple(g["geometry"]), g["page"], g["group"]) for g in groups}
    return any(
        e["work"] is not None
        and e["work"]["iteration"] == 0
        and (tuple(e["geometry"]), e["page"], e["group"]) in addresses
        for e in cursor.get("frontier", ())
    )
