"""Necessary release footprints on shared symbolic source/adapter expressions."""

from typing import Literal, cast

from hop_design.models.construction.basal_release import (
    BasalFutureReleaseAction,
    BasalFutureReleaseRequirement,
)
from hop_design.models.construction.complete.auxiliary.policy import (
    ConstrainedAdapterPolicy,
    ConstrainedEndpointPrimerPolicy,
    DerivedAdapterPolicy,
    DerivedEndpointPrimerPolicy,
    EndpointPrimerResolutionPolicy,
    FixedEndpointPrimerPolicy,
)
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.sequence_sets import SequenceSet, SequenceSpaceLimits
from hop_design.models.enzymes import CharacterizedEnzyme, EnzymeProvisioningPolicy, EnzymeRole
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac

from .basal.programs import resolve_future_release_action
from .foldback.domains import SequenceExpression, reverse_complement_expression
from .sequence_sets import SequenceSetBuilder


def _primer_handle(policy: EndpointPrimerResolutionPolicy) -> str:
    if isinstance(policy, DerivedEndpointPrimerPolicy):
        return ""
    if isinstance(policy, ConstrainedEndpointPrimerPolicy):
        return policy.five_prime_handle_sequence
    assert isinstance(policy, FixedEndpointPrimerPolicy)
    return policy.primer.five_prime_handle


def release_frame_supported(product: ProductRequest) -> bool:
    """Whether default distal pairing and endpoint obligations can be translated."""
    auxiliary = product.materialization.endpoint_auxiliaries
    return (
        product.ends is not None
        and product.release is not None
        and auxiliary is not None
        and isinstance(auxiliary.adapter, (DerivedAdapterPolicy, ConstrainedAdapterPolicy))
        and not auxiliary.adapter.distal_pairing_constraints
    )


def release_flanks(
    product: ProductRequest,
    prefix: SequenceExpression,
    local_adapter: SequenceExpression,
    *,
    nick_offset_nt: int,
    required_association_nt: int,
) -> tuple[SequenceExpression, SequenceExpression] | None:
    """Project copying, default distal pairing, adapter and primer-added handles.

    Caller establishes payload-forward source, bottom nick and sufficient source
    span. The folded interior is deliberately absent, so footprint translation
    must fall back when an operation reaches it.
    """
    if not release_frame_supported(product):
        return None
    auxiliary = product.materialization.endpoint_auxiliaries
    assert auxiliary is not None
    assert isinstance(auxiliary.adapter, (DerivedAdapterPolicy, ConstrainedAdapterPolicy))
    nick = len(prefix) - nick_offset_nt
    if not 0 < len(local_adapter) <= required_association_nt <= nick:
        raise ValueError("Release frame requires a complete local and distal association span.")
    adapter = local_adapter + reverse_complement_expression(
        prefix[nick - required_association_nt : nick - len(local_adapter)]
    )
    if isinstance(auxiliary.adapter, ConstrainedAdapterPolicy):
        adapter += tuple(auxiliary.adapter.three_prime_handle_sequence)
    forward, reverse = (
        _primer_handle(auxiliary.forward_primer),
        _primer_handle(auxiliary.reverse_primer),
    )
    return (
        tuple(forward) + prefix,
        reverse_complement_expression(prefix[nick:])
        + adapter
        + tuple(reverse_complement_iupac(reverse) if reverse else ""),
    )


def _window_masks(
    domains: tuple[tuple[str, ...], ...],
    expression: SequenceExpression,
    windows: tuple[tuple[int, str], ...],
) -> tuple[tuple[str, ...], ...] | None:
    """Conjoin unary recognition obligations, retaining shared variable aliases."""
    masks = [set(bases) for bases in domains]
    if any(not bases for bases in masks):
        return None
    for start, word in windows:
        if start < 0 or start + len(word) > len(expression):
            return None
        for base, symbol in zip(expression[start : start + len(word)], word, strict=True):
            allowed = iupac_bases(symbol)
            if isinstance(base, str):
                if base not in allowed:
                    return None
            else:
                masks[base.index].intersection_update(
                    {reverse_complement_iupac(b) for b in allowed} if base.complemented else allowed
                )
                if not masks[base.index]:
                    return None
    return tuple(tuple(sorted(bases)) for bases in masks)


def _window_domain(
    builder: SequenceSetBuilder,
    domains: tuple[tuple[str, ...], ...],
    expression: SequenceExpression,
    windows: tuple[tuple[int, str], ...],
) -> int:
    masks = _window_masks(domains, expression, windows)
    return 0 if masks is None else builder.from_domains(masks)


def required_release_windows(
    requirement: BasalFutureReleaseRequirement,
    enzyme: CharacterizedEnzyme,
    expression: SequenceExpression,
) -> tuple[tuple[int, str], tuple[int, str]] | None:
    """Recognition and end windows in one PCR flank; None means unproved frame."""
    action = resolve_future_release_action(enzyme, requirement)
    return release_action_windows(action, expression)


def release_action_windows(
    action: BasalFutureReleaseAction | None,
    expression: SequenceExpression,
) -> tuple[tuple[int, str], tuple[int, str]] | None:
    """Place a resolved cut program without deriving it again for each flank."""
    if action is None:
        return None
    requirement = action.requirement
    side = requirement.product_end
    width = len(requirement.cohesive_end_sequence)
    start = (
        len(expression) - requirement.payload_end_offset_bp - width
        if side == "left"
        else requirement.payload_end_offset_bp
    )
    site = start + (0 if side == "left" else width) + action.recognition_start_from_release_boundary
    word = action.recognition_pattern_5prime
    if (side == "left" and site + len(word) > len(expression)) or (side == "right" and site < 0):
        return None
    return (site, word), (start, requirement.endpoint_reference_sequence)


def admit_release_flanks(
    product: ProductRequest,
    domains: tuple[tuple[str, ...], ...],
    flanks: tuple[SequenceExpression, SequenceExpression],
    limits: SequenceSpaceLimits,
) -> SequenceSet | None:
    """Conjoin required ends/sites; preserve all variable aliases and disjunctions.

    These are necessary conditions, not complete reaction admission. Unknown
    action frames return None. Resource exhaustion raises, never an empty set.
    """
    assert product.ends is not None and product.release is not None
    builder = SequenceSetBuilder(
        length_nt=len(domains),
        max_nodes=limits.max_decisions,
        max_operations=limits.max_set_operations,
    )
    provisioning = EnzymeProvisioningPolicy(
        **product.release.enzymes.model_dump(), catalog=product.enzyme_catalog
    )
    enzymes = tuple(
        e
        for e in product.enzyme_catalog.enzymes
        if provisioning.permits(e.enzyme_id, role=EnzymeRole.END_GENERATION)
    )
    admitted = builder.from_domains(domains)
    left, right = flanks
    for side, end, expression in (
        ("left", product.ends.left, left),
        ("right", product.ends.right, right),
    ):
        requirement = BasalFutureReleaseRequirement(
            **end.model_dump(),
            product_end=cast(Literal["left", "right"], side),
            recognition_material="endpoint_material",
        )
        permitted = 0
        for enzyme in enzymes:
            windows = required_release_windows(requirement, enzyme, expression)
            if windows is None:
                return None
            permitted = builder.union(
                permitted, _window_domain(builder, domains, expression, windows)
            )
        admitted = builder.intersection(admitted, permitted)
    return builder.freeze(admitted)
