"""Visit existing local pairs by requested contrasts without expanding their product."""

from collections.abc import Iterator
from heapq import heappop, heappush
from itertools import product
from typing import Any

from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.targets import FoldbackTarget
from hop_design.models.construction.variants.objective import DesignSearchObjective

from ..local_choices import LocalRealizationChoice
from ..search.diversity import stratified_costs

LOCAL_PARAMETERS = frozenset(
    {
        "foldback_arm_bp",
        "join_offset_nt",
        "loop_nt",
        "loop_word",
        "foldback_strand",
        "basal_nick_offset_nt",
        "adapter_annealing_min_nt",
        "foldback_method",
        "basal_method",
    }
)


def validate_options_objective(
    request: ProductRequest,
    objective: DesignSearchObjective | None,
) -> None:
    if objective is None:
        return
    unsupported = set(objective.parameters) - LOCAL_PARAMETERS
    if unsupported:
        raise ValueError(f"Local-pair diversity does not target {sorted(unsupported)}.")
    if request.basal is None and set(objective.parameters) & {
        "basal_nick_offset_nt",
        "adapter_annealing_min_nt",
        "basal_method",
    }:
        raise ValueError("This direct-hairpin route has no basal association search.")


def _facts(choice: LocalRealizationChoice | None) -> dict[str, Any]:
    if choice is None:
        return {}
    geometry = choice.geometry
    if isinstance(geometry, FoldbackTarget):
        return {
            "foldback_arm_bp": geometry.annealing_arm_length_bp,
            "join_offset_nt": geometry.junction_offset_nt,
            "loop_nt": geometry.loop_length_nt,
            "loop_word": geometry.loop_sequence,
            "foldback_strand": geometry.nick_strand.value,
            "foldback_method": choice.nick_enzyme_id,
        }
    return {
        "basal_nick_offset_nt": geometry.nick_offset_nt,
        "adapter_annealing_min_nt": choice.required_annealing_nt,
        "basal_method": choice.nick_enzyme_id,
    }


def ordered_pairs(
    choices: dict[str, tuple[LocalRealizationChoice, ...]],
    objective: DesignSearchObjective | None,
) -> Iterator[tuple[LocalRealizationChoice, LocalRealizationChoice | None]]:
    foldback = choices["foldback"]
    basal = choices.get("basal", (None,))
    if objective is None:
        yield from product(foldback, basal)
        return
    if not foldback or not basal:
        return
    ranked = []
    factor_costs = []
    for factor in (foldback, basal):
        costs = stratified_costs(
            [_facts(choice) for choice in factor], tuple(range(len(factor))), objective.parameters
        )
        ranked.append(sorted(range(len(factor)), key=lambda i: (costs[i], i)))
        factor_costs.append(costs)
    # Stream the diagonal of two sorted factors. At most one frontier item per
    # visited pair; the potentially large Cartesian product is never allocated.
    costs_f, costs_b = factor_costs
    queue = [(costs_f[ranked[0][0]] + costs_b[ranked[1][0]], 0, 0)]
    seen = {(0, 0)}
    while queue:
        _, i, j = heappop(queue)
        yield foldback[ranked[0][i]], basal[ranked[1][j]]
        for ni, nj in ((i + 1, j), (i, j + 1)):
            if ni < len(foldback) and nj < len(basal) and (ni, nj) not in seen:
                seen.add((ni, nj))
                heappush(queue, (costs_f[ranked[0][ni]] + costs_b[ranked[1][nj]], ni, nj))
