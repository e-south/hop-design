"""Necessary endpoint constraints on an exact source/adapter completion frame."""

from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.sequence_sets import SequenceSet, SequenceSpaceLimits
from hop_design.models.sequence import iupac_bases

from .foldback.domains import SequenceVariable
from .release_constraints import admit_release_flanks, release_flanks, release_frame_supported
from .sequence_sets import SequenceSetBuilder


def admit_release_contexts(
    *,
    product: ProductRequest,
    pattern: str,
    local_prefix: str,
    local_adapter: str,
    nick_offset_nt: int,
    required_association_nt: int,
    limits: SequenceSpaceLimits,
) -> SequenceSet | None:
    """Intersect necessary left/right footprints with one authored context domain.

    Caller establishes a payload-forward prefix, bottom basal nick and terminal
    local adapter segment. Unknown frames return None; computing limits raise.
    Empty sets exclude only this local source/adapter and context length, never
    the whole scaffold or another permitted auxiliary completion.
    """
    if not release_frame_supported(product):
        return None
    if not pattern or not 0 <= nick_offset_nt <= len(local_prefix):
        raise ValueError("Release propagation requires a nonempty context and embedded nick.")
    if not 0 < len(local_adapter) <= required_association_nt:
        raise ValueError("Local adapter must fit the required association span.")
    prefix = tuple(SequenceVariable(i) for i in range(len(pattern))) + tuple(local_prefix)
    if len(prefix) - nick_offset_nt < required_association_nt:
        return SequenceSetBuilder(
            length_nt=len(pattern),
            max_nodes=limits.max_decisions,
            max_operations=limits.max_set_operations,
        ).freeze(0)
    flanks = release_flanks(
        product,
        prefix,
        tuple(local_adapter),
        nick_offset_nt=nick_offset_nt,
        required_association_nt=required_association_nt,
    )
    if flanks is None:
        return None
    return admit_release_flanks(
        product, tuple(tuple(iupac_bases(b)) for b in pattern), flanks, limits
    )
