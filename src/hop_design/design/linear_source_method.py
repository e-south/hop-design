"""Resolve one linear-source multi-nick, size-selected hairpin-PCR route."""

from __future__ import annotations

from collections import Counter

from hop_design.design.linear_source_states.material import (
    build_source_pcr_duplex,
    five_prime_chemistry,
    infeasible_result,
    material_by_role,
    primer_binding,
)
from hop_design.design.linear_source_states.product import (
    build_restriction_product,
    resolve_selected_pairs,
)
from hop_design.design.method import resolve_linear_source_hairpin_pcr_materials
from hop_design.kernel.molecular_states import (
    build_denatured_fragments,
    reindex_lineage,
    strand_from_sequence,
)
from hop_design.kernel.site_scanning import scan_nicking_agent
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.junction import JunctionPairKind, Strand
from hop_design.models.linear_source_method import (
    LINEAR_SOURCE_METHOD_KIND,
    LinearSourceMultinickHairpinPcrPlan,
    LinearSourceMultinickHairpinPcrRequest,
    LinearSourceMultinickHairpinPcrResult,
)
from hop_design.models.method import (
    BindingOrientation,
    MethodImplementationStatus,
    MethodOutcome,
    MethodResolutionStatus,
    ProcessMaterialRole,
)
from hop_design.models.method_states import (
    AdapterAnnealedComplex,
    DenaturedFragmentSet,
    HairpinPcrDuplex,
    LengthSelectedFragmentSet,
    LigatedHairpin,
    MultiSiteNickedDuplex,
)
from hop_design.models.molecular_state import (
    CovalentBond,
    EndChemistry,
    LineageStrand,
    MolecularStrand,
    StrandEnd,
)
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.serialization import canonical_json_bytes, sha256_digest


def compile_linear_source_multinick_hairpin_pcr(
    request: LinearSourceMultinickHairpinPcrRequest,
) -> LinearSourceMultinickHairpinPcrResult:
    """Resolve every molecular state or return one explicit infeasible outcome."""
    materials = resolve_linear_source_hairpin_pcr_materials(request.materials)
    source_duplex = build_source_pcr_duplex(request)
    sites = tuple(
        sorted(
            (
                site
                for agent in request.nicking_agents
                for site in scan_nicking_agent(source_duplex.top_strand.sequence, agent=agent)
            ),
            key=lambda site: (site.site_span.start.offset, site.agent_id),
        )
    )
    site_keys = tuple((site.nick.strand, site.nick.boundary.offset) for site in sites)
    if not sites or len(site_keys) != len(set(site_keys)):
        return infeasible_result(
            request,
            code="HOP-METHOD-002",
            path="nicking_agents",
            message="Nicking agents did not resolve a unique set of strand boundaries.",
            evidence={"site_count": len(sites)},
            suggestion="Review the supplied nicking-agent motifs and cut offsets.",
        )
    nicked = MultiSiteNickedDuplex(
        top_strand=source_duplex.top_strand,
        bottom_strand=source_duplex.bottom_strand,
        sites=sites,
    )
    top_cuts = tuple(
        sorted(site.nick.boundary.offset for site in sites if site.nick.strand is Strand.TOP)
    )
    bottom_cuts = tuple(
        sorted(site.nick.boundary.offset for site in sites if site.nick.strand is Strand.BOTTOM)
    )
    fragments = build_denatured_fragments(
        source_id=request.materials.source_oligo.material_id,
        source_top_sequence=source_duplex.top_strand.sequence,
        top_cut_boundaries=top_cuts,
        bottom_cut_boundaries=bottom_cuts,
        top_five_prime_end=source_duplex.top_strand.five_prime_end,
        bottom_five_prime_end=source_duplex.bottom_strand.five_prime_end,
    )
    denatured = DenaturedFragmentSet(
        precursor_top_sequence=source_duplex.top_strand.sequence,
        fragments=fragments,
    )
    rule = request.fragment_selection
    retained = tuple(
        fragment
        for fragment in fragments
        if len(fragment.sequence) >= rule.min_length_nt
        and (rule.max_length_nt is None or len(fragment.sequence) <= rule.max_length_nt)
    )
    excluded = tuple(fragment for fragment in fragments if fragment not in retained)
    selected = LengthSelectedFragmentSet(
        selection=rule,
        retained_fragment_ids=tuple(fragment.fragment_id for fragment in retained),
        excluded_fragment_ids=tuple(fragment.fragment_id for fragment in excluded),
    )
    counts = Counter(fragment.precursor_strand for fragment in retained)
    if len(retained) != 2 or counts != Counter({Strand.TOP: 1, Strand.BOTTOM: 1}):
        return infeasible_result(
            request,
            code="HOP-METHOD-001",
            path="fragment_selection",
            message="Length selection did not retain one top and one bottom fragment.",
            evidence={"retained_fragment_ids": [item.fragment_id for item in retained]},
            suggestion="Review the declared length-selection rule.",
        )
    top = next(item for item in retained if item.precursor_strand is Strand.TOP)
    bottom = next(item for item in retained if item.precursor_strand is Strand.BOTTOM)
    adapter_material = material_by_role(materials.materials, ProcessMaterialRole.LIGATION_ADAPTER)
    adapter = strand_from_sequence(
        strand_id=adapter_material.material_id,
        sequence=adapter_material.sequence,
        five_prime_end=five_prime_chemistry(adapter_material),
        three_prime_end=EndChemistry.HYDROXYL,
        origin_id=adapter_material.material_id,
        origin_strand=LineageStrand.PRIMARY,
        origin_indexes=range(len(adapter_material.sequence)),
    )
    pairs = resolve_selected_pairs(top, bottom, adapter, request)
    pair_counts = Counter(pair.kind for pair in pairs or ())
    if (
        pairs is None
        or pair_counts[JunctionPairKind.HARD_MISMATCH]
        > request.adapter_annealing.max_hard_mismatches
        or pair_counts[JunctionPairKind.GT_WOBBLE] > request.adapter_annealing.max_gt_wobbles
    ):
        return infeasible_result(
            request,
            code="HOP-METHOD-003",
            path="adapter_annealing",
            message="Selected fragments and adapter do not form the declared annealed complex.",
            evidence={"pair_counts": {kind.value: pair_counts[kind] for kind in pair_counts}},
            suggestion="Review adapter pairing and fragment-selection constraints.",
        )
    annealed = AdapterAnnealedComplex(
        strand_ids=(top.fragment_id, bottom.fragment_id, adapter.strand_id),
        pairs=pairs,
    )
    bonds = (
        CovalentBond(
            upstream_strand_id=top.fragment_id,
            upstream_end=StrandEnd.THREE_PRIME,
            downstream_strand_id=bottom.fragment_id,
            downstream_end=StrandEnd.FIVE_PRIME,
        ),
        CovalentBond(
            upstream_strand_id=bottom.fragment_id,
            upstream_end=StrandEnd.THREE_PRIME,
            downstream_strand_id=adapter.strand_id,
            downstream_end=StrandEnd.FIVE_PRIME,
        ),
    )
    ligated_sequence = top.sequence + bottom.sequence + adapter.sequence
    ligated_strand = MolecularStrand(
        strand_id="ligated-hairpin-strand",
        sequence=ligated_sequence,
        five_prime_end=top.five_prime_end,
        three_prime_end=adapter.three_prime_end,
        lineage=reindex_lineage((top.lineage, bottom.lineage, adapter.lineage)),
    )
    ligated = LigatedHairpin(
        component_strand_ids=(top.fragment_id, bottom.fragment_id, adapter.strand_id),
        bonds=bonds,
        strand=ligated_strand,
    )
    hairpin_forward = material_by_role(
        materials.materials, ProcessMaterialRole.HAIRPIN_PCR_FORWARD_PRIMER
    )
    hairpin_reverse = material_by_role(
        materials.materials, ProcessMaterialRole.HAIRPIN_PCR_REVERSE_PRIMER
    )
    reverse_nt = len(hairpin_reverse.sequence)
    pcr_bindings = (
        primer_binding(
            "hairpin-pcr-forward",
            hairpin_forward.material_id,
            ligated_strand.strand_id,
            Span(
                start=Boundary(offset=0),
                end=Boundary(offset=len(hairpin_forward.sequence)),
            ),
            BindingOrientation.SAME_5TO3,
        ),
        primer_binding(
            "hairpin-pcr-reverse",
            hairpin_reverse.material_id,
            ligated_strand.strand_id,
            Span(
                start=Boundary(offset=len(ligated_sequence) - reverse_nt),
                end=Boundary(offset=len(ligated_sequence)),
            ),
            BindingOrientation.REVERSE_COMPLEMENT_5TO3,
        ),
    )
    pcr_top = MolecularStrand(
        strand_id="hairpin-pcr-top",
        sequence=ligated_sequence,
        five_prime_end=five_prime_chemistry(hairpin_forward),
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=ligated_strand.lineage,
    )
    pcr_bottom = strand_from_sequence(
        strand_id="hairpin-pcr-bottom",
        sequence=reverse_complement_iupac(ligated_sequence),
        five_prime_end=five_prime_chemistry(hairpin_reverse),
        three_prime_end=EndChemistry.HYDROXYL,
        origin_id=ligated_strand.strand_id,
        origin_strand=LineageStrand.COMPLEMENTARY,
        origin_indexes=range(len(ligated_sequence) - 1, -1, -1),
    )
    duplex = HairpinPcrDuplex(
        top_strand=pcr_top,
        bottom_strand=pcr_bottom,
        primer_bindings=pcr_bindings,
    )
    restriction = build_restriction_product(request, duplex)
    if restriction is None:
        return infeasible_result(
            request,
            code="HOP-METHOD-005",
            path="restriction_agent",
            message="Restriction processing did not resolve one facing site pair.",
            evidence={},
            suggestion="Review the restriction motif, cut offsets, and product sequence.",
        )
    projection = restriction.hairpin_encoding_projection.sequence
    if request.expected_hairpin_encoding is not None and (
        projection != request.expected_hairpin_encoding
    ):
        return infeasible_result(
            request,
            code="HOP-METHOD-006",
            path="expected_hairpin_encoding",
            message="Restriction projection does not equal the expected hairpin encoding.",
            evidence={"observed_sequence_digest": sha256_digest(projection.encode())},
            suggestion="Review method inputs or the expected encoding orientation.",
        )
    plan = LinearSourceMultinickHairpinPcrPlan(
        request_id=request.request_id,
        request_digest=sha256_digest(canonical_json_bytes(request)),
        materials=materials,
        source_pcr_duplex=source_duplex,
        multi_site_nicked_duplex=nicked,
        denatured_fragment_set=denatured,
        length_selected_fragment_set=selected,
        adapter_annealing=request.adapter_annealing,
        adapter_annealed_complex=annealed,
        ligated_hairpin=ligated,
        hairpin_pcr_duplex=duplex,
        restriction_agent=request.restriction_agent,
        restriction_digest_product=restriction,
    )
    return LinearSourceMultinickHairpinPcrResult(
        request_id=request.request_id,
        method_kind=LINEAR_SOURCE_METHOD_KIND,
        outcome=MethodOutcome(
            implementation_status=MethodImplementationStatus.AVAILABLE,
            resolution_status=MethodResolutionStatus.COMPLETE,
        ),
        plan=plan,
    )


__all__ = ["compile_linear_source_multinick_hairpin_pcr"]
