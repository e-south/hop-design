"""Propagate endpoint obligations through a coupled local sequence population."""

from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
    SourceSsdnaPolicy,
    UpstreamSequenceLengthRange,
)
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.sequence_sets import SequenceSet, SequenceSpaceLimits
from hop_design.models.physical import Strand
from hop_design.models.sequence import iupac_bases

from .basal.sequence_population import BasalSequencePopulation
from .foldback.domains import SequenceVariable
from .release_constraints import admit_release_flanks, release_flanks
from .sequence_sets import SequenceSetBuilder


def admit_release_population(
    product: ProductRequest,
    support: BasalSequencePopulation,
    policy: SourceSsdnaPolicy,
    limits: SequenceSpaceLimits,
) -> SequenceSet | None:
    """Existentially complete authored handles without expanding their words.

    Returned variables retain the original source+adapter domain. Source reaction
    admission and conditional pairing still belong to BasalSequencePopulation;
    this set only adds necessary endpoint obligations. None preserves ordinary
    evaluation for every program whose frame/policy has not been translated.
    """
    d = support.index.domain
    if (
        not isinstance(policy, ConstrainedSourceSsdnaPolicy)
        or product.release is None
        or product.ends is None
        or product.basal is None
        or product.basal.geometry.minimum_adapter_annealing_nt is None
        or product.release.basal_projection.product_end != "right"
        or d.target.nick_strand is not Strand.BOTTOM
        or d.payload_span.end.offset != d.adapter_span.start.offset
        or d.payload_sequence != product.stem_arm
        or d.source_span.end.offset != d.payload_span.start.offset - d.target.nick_offset_nt
    ):
        return None
    k = len(d.base_domains)
    builder = SequenceSetBuilder(
        length_nt=k, max_nodes=limits.max_decisions, max_operations=limits.max_set_operations
    )
    spec = policy.upstream_sequence_spec
    patterns = (
        tuple(spec.base_spec * n for n in range(spec.min_length_nt, spec.max_length_nt + 1))
        if isinstance(spec, UpstreamSequenceLengthRange)
        else (spec,)
    )
    masks = support.index.source_domains() + d.base_domains[d.adapter_span.start.offset :]
    local = tuple(
        SequenceVariable(i) for i in range(d.adapter_span.start.offset, d.adapter_span.end.offset)
    )
    required = max(product.basal.geometry.minimum_adapter_annealing_nt, len(local))
    union = 0
    for pattern in patterns:
        prefix = tuple(SequenceVariable(k + i) for i in range(len(pattern))) + tuple(
            SequenceVariable(i) for i in range(d.payload_span.start.offset)
        )
        # Local source length always accommodates the local pairing span. A
        # shorter total prefix cannot satisfy the authored distal requirement.
        if len(prefix) - d.target.nick_offset_nt < required:
            if (
                release_flanks(
                    product,
                    prefix,
                    local,
                    nick_offset_nt=d.target.nick_offset_nt,
                    required_association_nt=len(local),
                )
                is None
            ):
                return None
            continue
        flanks = release_flanks(
            product,
            prefix,
            local,
            nick_offset_nt=d.target.nick_offset_nt,
            required_association_nt=required,
        )
        if flanks is None:
            return None
        domains = masks + tuple(tuple(sorted(iupac_bases(b))) for b in pattern)
        permitted = admit_release_flanks(product, domains, flanks, limits)
        if permitted is None:
            return None
        union = builder.union(union, builder.project_window(permitted, start=0, end=k))
    return builder.freeze(union)
