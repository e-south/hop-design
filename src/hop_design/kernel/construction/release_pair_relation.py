"""Share necessary endpoint reasoning across exact receiving-end requests."""

from functools import cache
from typing import Literal

from hop_design.models.construction.basal_release import (
    BasalFutureReleaseAction,
    BasalFutureReleaseRequirement,
)
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
    UpstreamSequenceLengthRange,
)
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.sequence_sets import SequenceSet, SequenceSpaceLimits
from hop_design.models.enzymes import CharacterizedEnzyme
from hop_design.models.physical import Strand
from hop_design.models.sequence import iupac_bases

from .basal.domains import BasalSequenceDomain
from .basal.programs import resolve_future_release_action
from .basal.sequence_index import BasalSequenceIndex
from .foldback.domains import SequenceExpression, SequenceVariable, reverse_complement_expression
from .release_constraints import _window_masks, release_action_windows, release_flanks
from .release_pair_projection import project_end_pairs
from .sequence_sets import SequenceSetBuilder


def _program_relation(
    product: ProductRequest,
    domain: BasalSequenceDomain,
    pattern: str,
    builder: SequenceSetBuilder,
    limits: SequenceSpaceLimits,
    actions: tuple[BasalFutureReleaseAction | None, ...],
) -> int | None:
    d = domain
    assert product.release is not None and product.ends is not None and product.basal is not None
    if (
        not d.deferred_end_sequence
        or d.target.nick_strand is not Strand.BOTTOM
        or d.payload_sequence != product.stem_arm
        or d.payload_span.end.offset != d.adapter_span.start.offset
        or d.source_span.end.offset != d.payload_span.start.offset - d.target.nick_offset_nt
        or d.program.future_release_enzyme is None
    ):
        return None
    k = len(d.base_domains)
    prefix = tuple(SequenceVariable(k + i) for i in range(len(pattern))) + tuple(
        SequenceVariable(i) for i in range(d.payload_span.start.offset)
    )
    local = tuple(
        SequenceVariable(i) for i in range(d.adapter_span.start.offset, d.adapter_span.end.offset)
    )
    assert product.basal.geometry.minimum_adapter_annealing_nt is not None
    required = max(product.basal.geometry.minimum_adapter_annealing_nt, len(local))
    if len(prefix) - d.target.nick_offset_nt < required:
        return 0
    flanks = release_flanks(
        product,
        prefix,
        local,
        nick_offset_nt=d.target.nick_offset_nt,
        required_association_nt=required,
    )
    if flanks is None:
        return None
    masks = (
        BasalSequenceIndex.create(d).source_domains()
        + d.base_domains[d.adapter_span.start.offset :]
        + tuple(tuple(sorted(iupac_bases(c))) for c in pattern)
    )
    # Validate frame length and limit values without allocating an intermediate
    # graph. The joint output projection still enforces its own resource budget.
    SequenceSetBuilder(
        length_nt=len(masks),
        max_nodes=limits.max_decisions,
        max_operations=limits.max_set_operations,
    )
    placed_masks: tuple[tuple[str, ...], ...] | None = masks
    ends: SequenceExpression = ()
    sides: tuple[Literal["left", "right"], ...] = ("left", "right")
    for side, action, expression in zip(sides, actions, flanks, strict=True):
        windows = release_action_windows(action, expression)
        if windows is None:
            return None
        site, footprint = windows
        start, word = footprint
        if start < 0 or start + len(word) > len(expression):
            return 0
        if placed_masks is not None:
            placed_masks = _window_masks(placed_masks, expression, (site,))
        exposed = expression[start : start + len(word)]
        # Admission currently translates forward-left/reverse-right 5-prime ends.
        ends += reverse_complement_expression(exposed) if side == "right" else exposed
    if placed_masks is None:
        return 0
    return project_end_pairs(d, placed_masks, ends, builder)


def necessary_end_pairs(
    product: ProductRequest,
    domains: tuple[BasalSequenceDomain, ...],
    policy: ConstrainedSourceSsdnaPolicy,
    limits: SequenceSpaceLimits,
) -> SequenceSet | None:
    """All possible end pairs under these necessary conditions, without word scans.

    Does not establish source reaction admission, primer admission, foldback
    compatibility or a complete construction. Unsupported frames return None;
    resource exhaustion raises and cannot certify any absence.
    """
    spec = policy.upstream_sequence_spec
    patterns = (
        tuple(spec.base_spec * n for n in range(spec.min_length_nt, spec.max_length_nt + 1))
        if isinstance(spec, UpstreamSequenceLengthRange)
        else (spec,)
    )
    assert product.ends is not None
    sides: tuple[Literal["left", "right"], ...] = ("left", "right")
    requirements = tuple(
        BasalFutureReleaseRequirement(
            **end.model_dump(), product_end=side, recognition_material="endpoint_material"
        )
        for side, end in zip(sides, (product.ends.left, product.ends.right), strict=True)
    )

    @cache
    def actions(enzyme: CharacterizedEnzyme | None) -> tuple[BasalFutureReleaseAction | None, ...]:
        # Bound to this call's ends and full enzyme definitions. Its size cannot
        # exceed the distinct definitions in the supplied finite domains.
        return tuple(
            resolve_future_release_action(enzyme, requirement) if enzyme is not None else None
            for requirement in requirements
        )

    builder = SequenceSetBuilder(
        length_nt=len(product.ends.left.cohesive_end_sequence)
        + len(product.ends.right.cohesive_end_sequence),
        max_nodes=limits.max_decisions,
        max_operations=limits.max_set_operations,
    )
    result = 0
    for domain in domains:
        program_actions = actions(domain.program.future_release_enzyme)
        for pattern in patterns:
            relation = _program_relation(product, domain, pattern, builder, limits, program_actions)
            if relation is None:
                return None
            result = builder.union(result, relation)
    return builder.freeze(result)
