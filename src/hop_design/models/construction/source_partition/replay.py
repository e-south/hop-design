"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/source_partition/replay.py

Replays one enzyme subset into exact nicks, fragments, and survivor selection.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass

from hop_design.models.catalog import ResolvedNickSite
from hop_design.models.construction.source_partition.request import (
    SourcePartitionDiscoveryRequest,
)
from hop_design.models.construction.source_partition.types import (
    PartitionNickFunction,
    SourcePartitionFailure,
    SourcePartitionNickFunction,
)
from hop_design.models.enzymes import EnzymeRole
from hop_design.models.junction import Strand
from hop_design.models.method_states import (
    DenaturedFragmentSet,
    LengthSelectedFragmentSet,
    MultiSiteNickedDuplex,
)
from hop_design.models.molecular_replay import (
    build_denatured_fragments,
    strand_from_sequence,
)
from hop_design.models.molecular_state import LineageStrand
from hop_design.models.reaction_replay import scan_actionable_sites
from hop_design.models.reactions import ReactionMolecule, ReactionState
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.models.strand_state import NickEvent


@dataclass(frozen=True)
class SourcePartitionCandidateReplay:
    """Pure replay outcome for one canonical enzyme subset."""

    enzyme_ids: tuple[str, ...]
    failure_codes: tuple[SourcePartitionFailure, ...]
    nicked_duplex: MultiSiteNickedDuplex | None = None
    denatured: DenaturedFragmentSet | None = None
    selected: LengthSelectedFragmentSet | None = None
    nick_functions: tuple[SourcePartitionNickFunction, ...] = ()


def _resolved_sites(
    request: SourcePartitionDiscoveryRequest,
    *,
    enzyme_ids: tuple[str, ...],
) -> tuple[tuple[ResolvedNickSite, ...], tuple[SourcePartitionFailure, ...]]:
    source = request.source
    sequence = source.top_sequence_5prime
    state = ReactionState(
        state_id="source-duplex",
        molecules=(
            ReactionMolecule(
                molecule_id=source.material_id,
                reference_sequence_5prime=sequence,
                complement_sequence_5prime=reverse_complement_iupac(sequence),
            ),
        ),
    )
    failures: set[SourcePartitionFailure] = set()
    sites: list[ResolvedNickSite] = []
    for enzyme_id in enzyme_ids:
        enzyme = request.enzyme_provisioning.catalog.by_id(enzyme_id)
        if not request.enzyme_provisioning.permits(
            enzyme_id,
            role=EnzymeRole.STRAND_EXPOSURE,
        ):
            raise ValueError("Source-partition replay received an unprovisioned enzyme.")
        bindings = scan_actionable_sites(state=state, enzyme=enzyme)
        if not bindings:
            failures.add(SourcePartitionFailure.NO_ACTIONABLE_SITES)
            continue
        for binding in bindings:
            if binding.reference_cut is not None:
                strand = Strand.TOP
                boundary = binding.reference_cut
            elif binding.complement_cut is not None:
                strand = Strand.BOTTOM
                boundary = binding.complement_cut
            else:
                raise ValueError("A replayed nickase binding must contain one cut.")
            sites.append(
                ResolvedNickSite(
                    agent_id=enzyme_id,
                    site_span=binding.recognition_span,
                    orientation=binding.orientation,
                    matched_sequence=sequence[
                        binding.recognition_span.start.offset : binding.recognition_span.end.offset
                    ],
                    nick=NickEvent(boundary=boundary, strand=strand),
                )
            )
    site_keys = tuple((site.nick.strand, site.nick.boundary.offset) for site in sites)
    if any(site.nick.boundary.offset in {0, len(sequence)} for site in sites):
        failures.add(SourcePartitionFailure.NONPARTITIONING_TERMINAL_CUT)
    if len(site_keys) != len(set(site_keys)):
        failures.add(SourcePartitionFailure.CONFLICTING_CUT_BOUNDARIES)
    operation_limit = request.enzyme_provisioning.max_operations
    if operation_limit is not None and len(sites) > operation_limit:
        failures.add(SourcePartitionFailure.OPERATION_LIMIT_EXCEEDED)
    return (
        tuple(
            sorted(
                sites,
                key=lambda site: (
                    site.nick.boundary.offset,
                    site.nick.strand.value,
                    site.agent_id,
                    site.site_span.start.offset,
                ),
            )
        ),
        tuple(sorted(failures, key=lambda item: item.value)),
    )


def _strand_matches_required_survivor(
    request: SourcePartitionDiscoveryRequest,
    *,
    precursor_strand: Strand,
    start: int,
    end: int,
) -> bool:
    return any(
        survivor.precursor_strand is precursor_strand
        and survivor.source_span.start.offset == start
        and survivor.source_span.end.offset == end
        for survivor in request.constraints.required_survivors
    )


def replay_source_partition_candidate(
    request: SourcePartitionDiscoveryRequest,
    *,
    enzyme_ids: tuple[str, ...],
) -> SourcePartitionCandidateReplay:
    """Replay all actionable sites for one enzyme subset against one exact source."""
    if not enzyme_ids or enzyme_ids != tuple(sorted(set(enzyme_ids))):
        raise ValueError("Source-partition enzyme ids must be unique and canonical.")
    sites, failures = _resolved_sites(request, enzyme_ids=enzyme_ids)
    if failures:
        return SourcePartitionCandidateReplay(
            enzyme_ids=enzyme_ids,
            failure_codes=failures,
        )

    source = request.source
    sequence = source.top_sequence_5prime
    top = strand_from_sequence(
        strand_id="source-top",
        sequence=sequence,
        five_prime_end=source.top_five_prime_end,
        three_prime_end=source.top_three_prime_end,
        origin_id=source.material_id,
        origin_strand=LineageStrand.PRIMARY,
        origin_indexes=range(len(sequence)),
    )
    bottom = strand_from_sequence(
        strand_id="source-bottom",
        sequence=reverse_complement_iupac(sequence),
        five_prime_end=source.bottom_five_prime_end,
        three_prime_end=source.bottom_three_prime_end,
        origin_id=source.material_id,
        origin_strand=LineageStrand.COMPLEMENTARY,
        origin_indexes=range(len(sequence) - 1, -1, -1),
    )
    nicked = MultiSiteNickedDuplex(top_strand=top, bottom_strand=bottom, sites=sites)
    top_cuts = tuple(
        sorted(site.nick.boundary.offset for site in sites if site.nick.strand is Strand.TOP)
    )
    bottom_cuts = tuple(
        sorted(site.nick.boundary.offset for site in sites if site.nick.strand is Strand.BOTTOM)
    )
    fragments = build_denatured_fragments(
        source_id=source.material_id,
        source_top_sequence=sequence,
        top_cut_boundaries=top_cuts,
        bottom_cut_boundaries=bottom_cuts,
        top_five_prime_end=source.top_five_prime_end,
        top_three_prime_end=source.top_three_prime_end,
        bottom_five_prime_end=source.bottom_five_prime_end,
        bottom_three_prime_end=source.bottom_three_prime_end,
    )
    denatured = DenaturedFragmentSet(
        precursor_top_sequence=sequence,
        fragments=fragments,
    )
    selection = request.constraints.selection
    retained = tuple(
        fragment
        for fragment in fragments
        if len(fragment.sequence) >= selection.min_length_nt
        and (selection.max_length_nt is None or len(fragment.sequence) <= selection.max_length_nt)
    )
    excluded = tuple(fragment for fragment in fragments if fragment not in retained)
    selected = LengthSelectedFragmentSet(
        selection=selection,
        retained_fragment_ids=tuple(fragment.fragment_id for fragment in retained),
        excluded_fragment_ids=tuple(fragment.fragment_id for fragment in excluded),
    )
    retained_matches = tuple(
        _strand_matches_required_survivor(
            request,
            precursor_strand=fragment.precursor_strand,
            start=fragment.precursor_span.start.offset,
            end=fragment.precursor_span.end.offset,
        )
        for fragment in retained
    )
    if len(retained) != len(request.constraints.required_survivors) or not all(retained_matches):
        return SourcePartitionCandidateReplay(
            enzyme_ids=enzyme_ids,
            failure_codes=(SourcePartitionFailure.RETAINED_FRAGMENT_SET_MISMATCH,),
        )

    functions = tuple(
        SourcePartitionNickFunction(
            enzyme_id=site.agent_id,
            recognition_span=site.site_span,
            orientation=site.orientation,
            strand=site.nick.strand,
            boundary=site.nick.boundary,
            function=(
                PartitionNickFunction.RETAINED_FRAGMENT_BOUNDARY
                if any(
                    survivor.precursor_strand is site.nick.strand
                    and site.nick.boundary.offset
                    in {
                        survivor.source_span.start.offset,
                        survivor.source_span.end.offset,
                    }
                    for survivor in request.constraints.required_survivors
                )
                else PartitionNickFunction.EXCLUDED_FRAGMENT_CLEANUP
            ),
        )
        for site in sites
    )
    return SourcePartitionCandidateReplay(
        enzyme_ids=enzyme_ids,
        failure_codes=(),
        nicked_duplex=nicked,
        denatured=denatured,
        selected=selected,
        nick_functions=functions,
    )


__all__ = ["SourcePartitionCandidateReplay", "replay_source_partition_candidate"]
