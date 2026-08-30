"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/clone/release.py

Discovers an exact bounded Type IIS site pair for a clone endpoint.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice, product

from hop_design.models.construction.enzyme_binding import (
    ConstructionEnzymeBinding,
    derive_cohesive_end,
)
from hop_design.models.enzymes import EnzymeRole
from hop_design.models.reaction_replay import scan_actionable_sites
from hop_design.models.reactions import ActionableEnzymeBinding, ReactionMolecule, ReactionState
from hop_design.models.sequence import reverse_complement_iupac

from ..request import TypeIisReleaseRequest
from .geometry import CloneEndGenerationError, derive_clone_cut_geometry


@dataclass(frozen=True, slots=True)
class EndpointReleaseDiscovery:
    """One accepted site pair or a truthful bounded-search outcome."""

    bindings: tuple[ConstructionEnzymeBinding, ConstructionEnzymeBinding] | None
    examined_site_pairs: int
    truncated: bool
    ambiguous: bool = False


def _binding(site: ActionableEnzymeBinding) -> ConstructionEnzymeBinding:
    return ConstructionEnzymeBinding.create(
        enzyme_id=site.enzyme_id,
        role=EnzymeRole.END_GENERATION,
        strand=None,
        recognition_span=site.recognition_span,
        orientation=site.orientation,
        reference_cut=site.reference_cut,
        complement_cut=site.complement_cut,
    )


def discover_endpoint_release(
    *,
    request: TypeIisReleaseRequest,
    pcr_top: str,
    design_sequence: str,
) -> EndpointReleaseDiscovery:
    """Return one unique exact site pair after bounded exhaustive assessment."""
    state = ReactionState(
        state_id="endpoint-release-search",
        molecules=(
            ReactionMolecule(
                molecule_id="complete-hairpin-pcr",
                reference_sequence_5prime=pcr_top,
                complement_sequence_5prime=reverse_complement_iupac(pcr_top),
            ),
        ),
    )
    sites = tuple(
        site
        for enzyme in sorted(
            request.enzyme_provisioning.catalog.enzymes,
            key=lambda item: item.enzyme_id,
        )
        if request.enzyme_provisioning.permits(
            enzyme.enzyme_id,
            role=EnzymeRole.END_GENERATION,
        )
        for site in scan_actionable_sites(state=state, enzyme=enzyme)
    )
    left_sites = tuple(site for site in sites if site.orientation is request.left.orientation)
    right_sites = tuple(site for site in sites if site.orientation is request.right.orientation)
    total_site_pairs = len(left_sites) * len(right_sites)
    bounded_pairs = islice(product(left_sites, right_sites), request.max_site_pairs)
    matches: list[tuple[ConstructionEnzymeBinding, ConstructionEnzymeBinding]] = []
    examined = 0
    for left_site, right_site in bounded_pairs:
        examined += 1
        if left_site.recognition_span.start.offset >= right_site.recognition_span.start.offset:
            continue
        bindings = (_binding(left_site), _binding(right_site))
        try:
            derive_clone_cut_geometry(
                bindings=bindings,
                parent_length=len(pcr_top),
                template_sequence=pcr_top,
                design_sequence=design_sequence,
            )
            left_end = derive_cohesive_end(
                side="left",
                top_sequence=pcr_top,
                binding=bindings[0],
                primary_strand_id="complete-clone-primary",
                complementary_strand_id="complete-clone-complementary",
            )
            right_end = derive_cohesive_end(
                side="right",
                top_sequence=pcr_top,
                binding=bindings[1],
                primary_strand_id="complete-clone-primary",
                complementary_strand_id="complete-clone-complementary",
            )
        except (CloneEndGenerationError, ValueError):
            continue
        if (
            left_end.sequence == request.left.cohesive_end_sequence
            and left_end.overhang_end is request.left.overhang_end
            and right_end.sequence == request.right.cohesive_end_sequence
            and right_end.overhang_end is request.right.overhang_end
        ):
            matches.append(bindings)
    if total_site_pairs > examined:
        return EndpointReleaseDiscovery(
            bindings=None,
            examined_site_pairs=examined,
            truncated=True,
        )
    if len(matches) == 1:
        return EndpointReleaseDiscovery(
            bindings=matches[0],
            examined_site_pairs=examined,
            truncated=False,
        )
    return EndpointReleaseDiscovery(
        bindings=None,
        examined_site_pairs=examined,
        truncated=False,
        ambiguous=len(matches) > 1,
    )


__all__ = ["EndpointReleaseDiscovery", "discover_endpoint_release"]
