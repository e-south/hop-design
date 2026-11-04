"""Address source context and basal slices by recorded payload coordinates."""

from hop_design.kernel.construction.basal.domains import BasalSequenceDomain
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
    DerivedSourceSsdnaPolicy,
    FixedSourceSsdnaPolicy,
    SourceSsdnaPolicy,
    UpstreamSequenceLengthRange,
)
from hop_design.models.sequence import iupac_bases

from .types import PreferenceOutOfScope


def source_context_rank(policy: SourceSsdnaPolicy, context: str) -> int:
    """Invert ordinary length-first IUPAC addressing, not scheduling order."""
    if isinstance(policy, FixedSourceSsdnaPolicy):
        return 0
    if isinstance(policy, DerivedSourceSsdnaPolicy):
        if context:
            raise PreferenceOutOfScope("Derived source policy does not permit upstream context.")
        return 0
    assert isinstance(policy, ConstrainedSourceSsdnaPolicy)
    spec, origin = policy.upstream_sequence_spec, 0
    if isinstance(spec, UpstreamSequenceLengthRange):
        if not spec.min_length_nt <= len(context) <= spec.max_length_nt:
            raise PreferenceOutOfScope("Reference context length is outside the source policy.")
        size = len(iupac_bases(spec.base_spec))
        origin = sum(size**n for n in range(spec.min_length_nt, len(context)))
        spec = spec.base_spec * len(context)
    if len(spec) != len(context):
        raise PreferenceOutOfScope("Reference context length is outside the source policy.")
    rank = 0
    for base, symbol in zip(context, spec, strict=True):
        alphabet = tuple(sorted(iupac_bases(symbol)))
        if base not in alphabet:
            raise PreferenceOutOfScope("Reference context bases are outside the source policy.")
        rank = rank * len(alphabet) + alphabet.index(base)
    return origin + rank


def basal_source_slice(
    *,
    domain: BasalSequenceDomain,
    source: str,
    payload_start: int,
    payload_end: int,
) -> tuple[str, str]:
    """Return local source and upstream context without ambiguous substring matching."""
    start = payload_start - domain.payload_span.start.offset
    end = start + domain.adapter_span.start.offset
    if (
        start < 0
        or end > len(source)
        or payload_end - payload_start != domain.payload_span.length.value
        or start + domain.payload_span.end.offset != payload_end
    ):
        raise PreferenceOutOfScope("Reference source cannot supply the candidate basal frame.")
    return source[start:end], source[:start]
