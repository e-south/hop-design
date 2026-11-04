"""Bind context projection to an exact local source, association and endpoint frame."""

from dataclasses import dataclass

from hop_design.kernel.construction.release_context import admit_release_contexts
from hop_design.kernel.construction.source_context import protected_context_suffix_nt
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
    UpstreamSequenceLengthRange,
)
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.sequence_sets import SequenceSet, SequenceSpaceLimits
from hop_design.models.physical import Strand

from ..coordinates import coordinate_at
from ..partitions import ProductParts
from .domains import ContextCompletionPlan


@dataclass(frozen=True)
class ContextProtection:
    scope: str
    protected_suffix_nt: int
    local_prefix_nt: int | None = None
    nick_offset_nt: int | None = None
    required_association_nt: int | None = None
    left_footprint_nt: int | None = None


@dataclass(frozen=True)
class BoundContextCompletion:
    protection: ContextProtection
    plan: ContextCompletionPlan


def bind_context_completion(
    product: ProductRequest,
    parts: ProductParts,
    *,
    page: int,
    limits: SequenceSpaceLimits,
    preferred_contexts: tuple[str, ...] = (),
    handle_seed: str = "",
) -> BoundContextCompletion:
    """Protect both paired context and context reaching the requested left end.

    In this frame the source context precedes the exact local basal prefix. Its
    suffix supplies any association beyond the local prefix. The copied left
    interface is anchored relative to the supplied stem, so the paired gap plus
    protruding word bounds any context retained by release. Fixed primer handles
    do not introduce free context variables. PCR copying preserves sequence
    dependence even when the physical origin changes to a primer.

    The scope permits differences in unpaired context at the hairpin stage;
    it never asserts complete hairpin identity. Site and fixed-material checks
    still decide whether each auxiliary completion works. Unknown source frames
    retain every context base instead of extrapolating the bound.
    """
    if parts.conflict is not None or parts.empty_candidates:
        raise ValueError("A local exclusion has no context-completion population.")
    assert parts.basal_candidates is not None and parts.foldback is not None
    _, basal_rank = coordinate_at((parts.foldback.parts, parts.basal_candidates.parts), page)
    support, member = parts.basal_candidates.member_at(basal_rank)
    source = product.materialization.source_preparation.source_ssdna
    maximum = 0
    if isinstance(source, ConstrainedSourceSsdnaPolicy):
        spec = source.upstream_sequence_spec
        maximum = spec.max_length_nt if isinstance(spec, UpstreamSequenceLengthRange) else len(spec)
    protection = ContextProtection("all_context_positions", maximum)
    target = support.index.domain.target
    prefix = member.payload_span.start.offset
    association = (
        None if product.basal is None else product.basal.geometry.minimum_adapter_annealing_nt
    )
    known = (
        product.ends is not None
        and product.release is not None
        and product.release.basal_projection.product_end == "right"
        and target.nick_strand is Strand.BOTTOM
        and association is not None
        and member.payload_span.end.offset == len(member.source_precursor_sequence)
        and member.source_precursor_sequence[prefix:] == product.stem_arm
        and support.index.domain.source_span.end.offset == prefix - target.nick_offset_nt
    )
    if known:
        assert association is not None and product.ends is not None
        required = max(association, support.index.domain.source_span.length.value)
        footprint = product.ends.left.payload_end_offset_bp + len(
            product.ends.left.cohesive_end_sequence
        )
        count = protected_context_suffix_nt(
            local_prefix_nt=prefix,
            nick_offset_nt=target.nick_offset_nt,
            adapter_annealing_nt=required,
            left_paired_gap_bp=product.ends.left.payload_end_offset_bp,
            left_end_nt=len(product.ends.left.cohesive_end_sequence),
        )
        protection = ContextProtection(
            "basal_pairing_and_released_insert",
            count,
            prefix,
            target.nick_offset_nt,
            required,
            footprint,
        )

    def condition(pattern: str) -> SequenceSet | None:
        if not known or member.adapter_sequence is None:
            return None
        return admit_release_contexts(
            product=product,
            pattern=pattern,
            local_prefix=member.source_precursor_sequence[:prefix],
            local_adapter=member.adapter_sequence,
            nick_offset_nt=target.nick_offset_nt,
            required_association_nt=required,
            limits=limits,
        )

    plan = ContextCompletionPlan.create(
        source,
        protected_suffix_nt=protection.protected_suffix_nt,
        limits=limits,
        condition=condition,
        preferred_contexts=preferred_contexts,
        handle_seed=handle_seed,
    )
    return BoundContextCompletion(protection, plan)
