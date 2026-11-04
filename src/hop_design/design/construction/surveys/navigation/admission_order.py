"""Defer proven-empty foldback cases without removing canonical search addresses."""

from heapq import nsmallest
from typing import TYPE_CHECKING

from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction.product_pairing import ProductConstraintConflict
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits

from ..coordinates import coordinate_rank
from ..geometry_order import GeometryOrder
from .diversity import factor_costs, foldback_values

if TYPE_CHECKING:
    from ..branches import SurveyBranches
    from ..partitions import PartitionPlans

MAX_FOLDBACK_PROBES = 128


def admitted_geometry_order(
    branches: "SurveyBranches", limits: SurveyEvaluationLimits, partitions: "PartitionPlans"
) -> GeometryOrder:
    """Use existing local admission as a bounded priority, never an exclusion.

    Unknown or unexamined cases keep their ordinary priority. Full construction
    still decides support, including for locally admitted foldbacks. This probe
    is request-owned and shares replayable population authorities with execution.
    """
    ordinary = branches.search_order(limits)
    if branches.request.source_context_objective != "paired_scaffold_completions":
        return ordinary
    costs = ordinary.costs[4]
    candidates = nsmallest(
        min(MAX_FOLDBACK_PROBES, limits.navigation_nodes),
        range(len(costs)),
        key=lambda index: (costs[index], index),
    )
    empty = set()
    admitted = []
    for foldback in candidates:
        try:
            product = branches.product(
                0,
                branch=coordinate_rank(branches.geometry_sizes, (0, 0, 0, 0, foldback, 0)),
                limits=limits,
            )
            if partitions.foldback_population(product).parts == 0:
                empty.add(foldback)
            else:
                admitted.append(foldback)
        except (ProductConstraintConflict, SequenceSetLimitError):
            # A conflict in this representative basal frame or a stopped local
            # proof cannot establish that the foldback itself is empty.
            continue
    if not empty:
        return ordinary
    # Impossible earlier members must not postpone a shape's first admitted
    # representative. Unknown and unexamined cases keep their ordinary costs.
    ranked = (
        tuple(costs[i] for i in admitted)
        if limits.objective is None
        else factor_costs(
            [foldback_values(branches.foldback_cases[i]) for i in admitted],
            tuple(costs[i] for i in admitted),
            limits.objective,
        )
    )
    penalty = ordinary.maximum + 1
    reordered = list(costs)
    for i, rank in zip(admitted, ranked, strict=True):
        reordered[i] = rank
    for i in empty:
        reordered[i] += penalty
    return GeometryOrder((*ordinary.costs[:4], tuple(reordered), ordinary.costs[5]))
