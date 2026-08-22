"""State builders used by the bounded linear-source method compiler."""

from __future__ import annotations

from pydantic import JsonValue

from hop_design.kernel.molecular_states import (
    build_lineage,
    observe_pair,
    reindex_lineage,
    strand_from_sequence,
)
from hop_design.kernel.site_scanning import scan_release_agent
from hop_design.models.catalog import SiteOrientation
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.diagnostics import Diagnostic, Severity
from hop_design.models.linear_source_method import (
    LinearSourceMultinickHairpinPcrRequest,
    LinearSourceMultinickHairpinPcrResult,
)
from hop_design.models.method import (
    BindingOrientation,
    MethodImplementationStatus,
    MethodOutcome,
    MethodResolutionStatus,
    OligoModification,
    ProcessMaterial,
    ProcessMaterialRole,
)
from hop_design.models.method_states import (
    HairpinPcrDuplex,
    RestrictionDigestProduct,
    SourcePcrDuplex,
)
from hop_design.models.molecular_state import (
    EndChemistry,
    Fragment,
    LineageStrand,
    MolecularStrand,
    PrimerBinding,
    SequenceProjection,
    StrandPairObservation,
)
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.serialization import sha256_digest


def material_by_role(
    materials: tuple[ProcessMaterial, ...], role: ProcessMaterialRole
) -> ProcessMaterial:
    return next(material for material in materials if material.role is role)


def five_prime_chemistry(material: ProcessMaterial) -> EndChemistry:
    return (
        EndChemistry.PHOSPHATE
        if OligoModification.FIVE_PRIME_PHOSPHATE in material.modifications
        else EndChemistry.HYDROXYL
    )


def primer_binding(
    binding_id: str,
    primer_id: str,
    strand_id: str,
    span: Span,
    orientation: BindingOrientation,
) -> PrimerBinding:
    return PrimerBinding(
        binding_id=binding_id,
        primer_id=primer_id,
        template_strand_id=strand_id,
        template_span=span,
        orientation=orientation,
    )


def infeasible_result(
    request: LinearSourceMultinickHairpinPcrRequest,
    *,
    code: str,
    path: str,
    message: str,
    evidence: dict[str, JsonValue],
    suggestion: str,
) -> LinearSourceMultinickHairpinPcrResult:
    diagnostic = Diagnostic(
        code=code,
        severity=Severity.ERROR,
        path=path,
        message=message,
        evidence=evidence,
        suggestions=(suggestion,),
    )
    return LinearSourceMultinickHairpinPcrResult(
        request_id=request.request_id,
        outcome=MethodOutcome(
            implementation_status=MethodImplementationStatus.AVAILABLE,
            resolution_status=MethodResolutionStatus.INFEASIBLE,
            diagnostics=(diagnostic,),
        ),
        plan=None,
    )


def build_source_pcr_duplex(
    request: LinearSourceMultinickHairpinPcrRequest,
) -> SourcePcrDuplex:
    spec = request.materials
    source = spec.source_oligo.sequence
    top = strand_from_sequence(
        strand_id="source-top",
        sequence=source,
        five_prime_end=(
            EndChemistry.PHOSPHATE
            if OligoModification.FIVE_PRIME_PHOSPHATE
            in spec.source_pcr_forward_primer.modifications
            else EndChemistry.HYDROXYL
        ),
        three_prime_end=EndChemistry.HYDROXYL,
        origin_id=spec.source_oligo.material_id,
        origin_strand=LineageStrand.PRIMARY,
        origin_indexes=range(len(source)),
    )
    bottom = strand_from_sequence(
        strand_id="source-bottom",
        sequence=reverse_complement_iupac(source),
        five_prime_end=(
            EndChemistry.PHOSPHATE
            if OligoModification.FIVE_PRIME_PHOSPHATE
            in spec.source_pcr_reverse_primer.modifications
            else EndChemistry.HYDROXYL
        ),
        three_prime_end=EndChemistry.HYDROXYL,
        origin_id=spec.source_oligo.material_id,
        origin_strand=LineageStrand.COMPLEMENTARY,
        origin_indexes=range(len(source) - 1, -1, -1),
    )
    forward_nt = len(spec.source_pcr_forward_primer.sequence)
    reverse_nt = len(spec.source_pcr_reverse_primer.sequence)
    return SourcePcrDuplex(
        top_strand=top,
        bottom_strand=bottom,
        primer_bindings=(
            primer_binding(
                "source-pcr-forward",
                spec.source_pcr_forward_primer.material_id,
                top.strand_id,
                Span(start=Boundary(offset=0), end=Boundary(offset=forward_nt)),
                BindingOrientation.SAME_5TO3,
            ),
            primer_binding(
                "source-pcr-reverse",
                spec.source_pcr_reverse_primer.material_id,
                top.strand_id,
                Span(
                    start=Boundary(offset=len(source) - reverse_nt),
                    end=Boundary(offset=len(source)),
                ),
                BindingOrientation.REVERSE_COMPLEMENT_5TO3,
            ),
        ),
    )


def resolve_selected_pairs(
    top: Fragment,
    bottom: Fragment,
    adapter: MolecularStrand,
    request: LinearSourceMultinickHairpinPcrRequest,
) -> tuple[StrandPairObservation, ...] | None:
    overlap_start = max(top.precursor_span.start.offset, bottom.precursor_span.start.offset)
    overlap_end = min(top.precursor_span.end.offset, bottom.precursor_span.end.offset)
    if overlap_start >= overlap_end:
        return None
    retained_pairs = tuple(
        observe_pair(
            left_strand_id=top.fragment_id,
            right_strand_id=bottom.fragment_id,
            left_index=coordinate - top.precursor_span.start.offset,
            right_index=bottom.precursor_span.end.offset - 1 - coordinate,
            left_base=top.sequence[coordinate - top.precursor_span.start.offset],
            right_base=bottom.sequence[bottom.precursor_span.end.offset - 1 - coordinate],
        )
        for coordinate in range(overlap_start, overlap_end)
    )
    arm = request.adapter_annealing.adapter_span
    adapter_start = overlap_start - arm.length.value
    if adapter_start < top.precursor_span.start.offset:
        return None
    adapter_pairs = tuple(
        observe_pair(
            left_strand_id=top.fragment_id,
            right_strand_id=adapter.strand_id,
            left_index=adapter_start + position - top.precursor_span.start.offset,
            right_index=arm.end.offset - 1 - position,
            left_base=top.sequence[adapter_start + position - top.precursor_span.start.offset],
            right_base=adapter.sequence[arm.end.offset - 1 - position],
        )
        for position in range(arm.length.value)
    )
    return retained_pairs + adapter_pairs


def build_restriction_product(
    request: LinearSourceMultinickHairpinPcrRequest,
    duplex: HairpinPcrDuplex,
) -> RestrictionDigestProduct | None:
    sites = scan_release_agent(duplex.top_strand.sequence, agent=request.restriction_agent)
    if len(sites) != 2 or tuple(site.orientation for site in sites) != (
        SiteOrientation.FORWARD,
        SiteOrientation.REVERSE,
    ):
        return None
    left, right = sites
    top_start, top_end = left.cut.top.offset, right.cut.top.offset
    bottom_start, bottom_end = left.cut.bottom.offset, right.cut.bottom.offset
    if not (top_start < top_end and bottom_start < bottom_end):
        return None
    union = Span(
        start=Boundary(offset=min(top_start, bottom_start)),
        end=Boundary(offset=max(top_end, bottom_end)),
    )
    primary = MolecularStrand(
        strand_id="restriction-primary",
        sequence=duplex.top_strand.sequence[top_start:top_end],
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=reindex_lineage((duplex.top_strand.lineage[top_start:top_end],)),
    )
    complementary = MolecularStrand(
        strand_id="restriction-complementary",
        sequence=reverse_complement_iupac(duplex.top_strand.sequence[bottom_start:bottom_end]),
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=build_lineage(
            origin_id=duplex.top_strand.strand_id,
            origin_strand=LineageStrand.COMPLEMENTARY,
            origin_indexes=range(bottom_end - 1, bottom_start - 1, -1),
        ),
    )
    union_sequence = duplex.top_strand.sequence[union.start.offset : union.end.offset]
    projected = (
        union_sequence
        if request.hairpin_encoding_projection_orientation is BindingOrientation.SAME_5TO3
        else reverse_complement_iupac(union_sequence)
    )
    return RestrictionDigestProduct(
        agent_id=request.restriction_agent.agent_id,
        sites=sites,
        primary_strand=primary,
        complementary_strand=complementary,
        primary_union_span=union,
        hairpin_encoding_projection=SequenceProjection(
            sequence=projected,
            sequence_digest=sha256_digest(projected.encode()),
            source_span=union,
            orientation=request.hairpin_encoding_projection_orientation,
        ),
    )


__all__ = [
    "build_restriction_product",
    "build_source_pcr_duplex",
    "five_prime_chemistry",
    "infeasible_result",
    "material_by_role",
    "primer_binding",
    "resolve_selected_pairs",
]
