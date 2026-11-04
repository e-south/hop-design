"""Bounded target suggestions from joint relations; never an exclusion authority."""

from collections.abc import Iterator
from dataclasses import dataclass
from itertools import islice, product, zip_longest

from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder, SequenceSetLimitError
from hop_design.models.construction.product_pairing import ProductConstraintConflict
from hop_design.models.construction.sequence_sets import SequenceSet, SequenceSpaceLimits
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.targets import FOUR_BASE_WORDS, InterfaceTargetDomain

from ...search.diversity import diversity_class
from ..branches import SurveyBranches
from ..completion.interfaces import EndPairRelations
from ..coordinates import coordinate_rank
from .diversity import geometry_values

MAX_SEED_FRAMES = 256
MAX_FRAMES_PER_PLACEMENT = 16


def _seed_frames(sizes: tuple[int, ...]) -> Iterator[tuple[int, ...]]:
    """Spread a short probe across factor values before lexicographic repeats.

    These are independent basal factors, not independently chosen end words.
    The subsequent molecular relation still supplies only jointly allowed pairs.
    The original full product remains a lazy fallback, without duplicate frames.
    """
    if not sizes or any(size == 0 for size in sizes):
        return
    introduced = set()
    for index in range(max(sizes)):
        frame = tuple(index % size for size in sizes)
        if frame not in introduced:
            introduced.add(frame)
            yield frame
    for frame in product(*(range(size) for size in sizes)):
        if frame not in introduced:
            yield frame


@dataclass(frozen=True)
class TargetSeeds:
    targets: tuple[int, ...]
    examined_frames: int
    unknown_frames: int
    resource_stopped: bool
    candidate_classes: dict[int, frozenset[str]]


def _builder(limits: SequenceSpaceLimits) -> SequenceSetBuilder:
    return SequenceSetBuilder(
        length_nt=8, max_nodes=limits.max_decisions, max_operations=limits.max_set_operations
    )


def _permissions(domain: InterfaceTargetDomain, limits: SequenceSpaceLimits) -> SequenceSet:
    builder = _builder(limits)
    allowed = 1
    for side, words in enumerate((domain.left_words, domain.right_words)):
        if words is None:
            continue
        side_set = 0
        for word in words:
            pattern = word + "NNNN" if side == 0 else "NNNN" + word
            side_set = builder.union(side_set, builder.from_iupac(pattern))
        allowed = builder.intersection(allowed, side_set)
    return builder.freeze(allowed)


def propose_interface_targets(
    branches: SurveyBranches, limits: SurveyEvaluationLimits
) -> TargetSeeds:
    """Sample members of allowed joint relations without enumerating the word space.

    Unsupported or budget-stopped frames leave ordinary search intact. This small
    deterministic probe changes preference, not permissions or completeness. The
    fixed frame cap is a compute bound, not a molecular length/geometry limit.
    """
    domain = branches.request.targets
    left = {word: i for i, word in enumerate(domain.left_words or FOUR_BASE_WORDS)}
    right = {word: i for i, word in enumerate(domain.right_words or FOUR_BASE_WORDS)}
    relation_cache = EndPairRelations(
        branches.request.materialization.source_preparation.source_ssdna,
        limits.sequence_space_limits,
    )
    proposals: list[list[int]] = [[] for _ in branches.placements]
    classes: dict[int, set[str]] = {}
    examined = unknown = 0
    stopped = False
    try:
        permitted = _permissions(domain, limits.sequence_space_limits)
        # Interleave placements so a small probe budget does not scan only the
        # first gap. Foldback is absent from this necessary basal relation.
        frames = islice(
            _seed_frames(tuple(branches.geometry_sizes[i] for i in (1, 2, 3, 5))),
            MAX_FRAMES_PER_PLACEMENT,
        )
        for n, a, method, projection in frames:
            for p in range(len(branches.placements)):
                if examined >= min(MAX_SEED_FRAMES, limits.navigation_nodes):
                    break
                examined += 1
                geometry = (p, n, a, method, 0, projection)
                try:
                    candidate = branches.product(
                        0, branch=coordinate_rank(branches.geometry_sizes, geometry), limits=limits
                    )
                    relation = relation_cache.relation(candidate)
                except ProductConstraintConflict:
                    relation = None
                if relation is None:
                    unknown += 1
                    continue
                builder = _builder(limits.sequence_space_limits)
                allowed = builder.freeze(
                    builder.intersection(
                        builder.import_set(relation), builder.import_set(permitted)
                    )
                )
                if not allowed.cardinality:
                    continue
                for rank in sorted({0, allowed.cardinality // 2, allowed.cardinality - 1}):
                    word = allowed.member_at(rank)
                    target = left[word[:4]] * domain.right_count + right[word[4:]]
                    if target not in proposals[p]:
                        proposals[p].append(target)
                    values = {
                        **geometry_values(branches, geometry),
                        "left_end_word": word[:4],
                        "right_end_word": word[4:],
                    }
                    objective = limits.objective
                    if objective is not None and all(
                        values.get(key) is not None for key in objective.parameters
                    ):
                        classes.setdefault(target, set()).add(diversity_class(objective, values))
            if examined >= min(MAX_SEED_FRAMES, limits.navigation_nodes):
                break
    except SequenceSetLimitError:
        stopped = True
    ordered = dict.fromkeys(t for row in zip_longest(*proposals) for t in row if t is not None)
    return TargetSeeds(
        tuple(ordered),
        examined,
        unknown,
        stopped,
        {target: frozenset(values) for target, values in classes.items()},
    )
