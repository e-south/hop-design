"""Closed contracts for linear-source multi-nick hairpin-PCR resolution."""

from __future__ import annotations

from itertools import pairwise
from typing import Final, Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.catalog import (
    NickingAgent,
    ReleaseAgent,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.method import (
    BindingOrientation,
    LigationEndPreparation,
    LinearSourceHairpinPcrMaterialsPlan,
    LinearSourceHairpinPcrMaterialsSpec,
    MethodOutcome,
    OligoModification,
    ProcessMaterialRole,
)
from hop_design.models.method_states import (
    AdapterAnnealedComplex,
    DenaturedFragmentSet,
    HairpinPcrDuplex,
    LengthSelectedFragmentSet,
    LigatedHairpin,
    MultiSiteNickedDuplex,
    RestrictionDigestProduct,
    SourcePcrDuplex,
)
from hop_design.models.molecular_state import (
    AdapterAnnealingRequest,
    EndChemistry,
    FragmentLengthSelection,
    StrandEnd,
)
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import (
    EXACT_DNA_ALPHABET,
    SequenceValidationError,
    normalize_dna_sequence,
    reverse_complement_iupac,
)

LinearSourceMethodKind = Literal["linear-source-multinick-size-selection-hairpin-pcr@1"]
LINEAR_SOURCE_METHOD_KIND: Final[LinearSourceMethodKind] = (
    "linear-source-multinick-size-selection-hairpin-pcr@1"
)


class LinearSourceMultinickHairpinPcrRequest(HopModel):
    schema_id: Literal["hop.linear-source-multinick-hairpin-pcr-request/v1"] = Field(
        default="hop.linear-source-multinick-hairpin-pcr-request/v1", alias="schema"
    )
    request_id: ReferenceId
    method_kind: LinearSourceMethodKind = LINEAR_SOURCE_METHOD_KIND
    materials: LinearSourceHairpinPcrMaterialsSpec
    nicking_agents: tuple[NickingAgent, ...] = Field(min_length=1)
    fragment_selection: FragmentLengthSelection
    adapter_annealing: AdapterAnnealingRequest
    restriction_agent: ReleaseAgent
    hairpin_encoding_projection_orientation: BindingOrientation = (
        BindingOrientation.REVERSE_COMPLEMENT_5TO3
    )
    expected_hairpin_encoding: str | None = None

    @field_validator("expected_hairpin_encoding", mode="before")
    @classmethod
    def normalize_expected_encoding(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=False)

    @model_validator(mode="after")
    def validate_request(self) -> LinearSourceMultinickHairpinPcrRequest:
        source = self.materials.source_oligo.sequence
        if not set(source) <= EXACT_DNA_ALPHABET:
            raise ValueError("The linear-source method requires one exact source oligo.")
        ids = tuple(agent.agent_id for agent in self.nicking_agents)
        if len(ids) != len(set(ids)):
            raise ValueError("Linear-source nicking-agent ids must be unique.")
        if self.adapter_annealing.adapter_span.end.offset > len(
            self.materials.ligation_adapter.sequence
        ):
            raise ValueError("Adapter annealing span must stay inside the adapter sequence.")
        return self


class LinearSourceMultinickHairpinPcrPlan(HopModel):
    schema_id: Literal["hop.linear-source-multinick-hairpin-pcr-plan/v1"] = Field(
        default="hop.linear-source-multinick-hairpin-pcr-plan/v1", alias="schema"
    )
    request_id: ReferenceId
    request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    method_kind: LinearSourceMethodKind = LINEAR_SOURCE_METHOD_KIND
    materials: LinearSourceHairpinPcrMaterialsPlan
    source_pcr_duplex: SourcePcrDuplex
    multi_site_nicked_duplex: MultiSiteNickedDuplex
    denatured_fragment_set: DenaturedFragmentSet
    length_selected_fragment_set: LengthSelectedFragmentSet
    adapter_annealing: AdapterAnnealingRequest
    adapter_annealed_complex: AdapterAnnealedComplex
    ligated_hairpin: LigatedHairpin
    hairpin_pcr_duplex: HairpinPcrDuplex
    restriction_digest_product: RestrictionDigestProduct

    @model_validator(mode="after")
    def validate_transition_identity(self) -> LinearSourceMultinickHairpinPcrPlan:
        source = self.source_pcr_duplex
        nicked = self.multi_site_nicked_duplex
        if source.top_strand != nicked.top_strand or source.bottom_strand != nicked.bottom_strand:
            raise ValueError("Multi-site nicking must preserve both source-PCR strands.")
        if self.denatured_fragment_set.precursor_top_sequence != source.top_strand.sequence:
            raise ValueError("Denatured fragments must retain source-duplex identity.")
        if source.bottom_strand.sequence != reverse_complement_iupac(source.top_strand.sequence):
            raise ValueError("Source-PCR strands must be reverse complements.")
        length = len(source.top_strand.sequence)
        top_cuts = sorted(
            site.nick.boundary.offset for site in nicked.sites if site.nick.strand == "top"
        )
        bottom_cuts = sorted(
            site.nick.boundary.offset for site in nicked.sites if site.nick.strand == "bottom"
        )
        expected_fragments = tuple(
            [("top", start, end) for start, end in pairwise((0, *top_cuts, length))]
            + [
                ("bottom", start, end)
                for start, end in reversed(tuple(pairwise((0, *bottom_cuts, length))))
            ]
        )
        fragments = self.denatured_fragment_set.fragments
        observed_fragments = tuple(
            (
                fragment.precursor_strand,
                fragment.precursor_span.start.offset,
                fragment.precursor_span.end.offset,
            )
            for fragment in fragments
        )
        if observed_fragments != expected_fragments:
            raise ValueError("Denatured fragments must partition every nicked strand.")
        for fragment in fragments:
            start = fragment.precursor_span.start.offset
            end = fragment.precursor_span.end.offset
            expected_sequence = source.top_strand.sequence[start:end]
            if fragment.precursor_strand == "bottom":
                expected_sequence = reverse_complement_iupac(expected_sequence)
            expected_five_prime = (
                source.top_strand.five_prime_end
                if fragment.precursor_strand == "top" and start == 0
                else source.bottom_strand.five_prime_end
                if fragment.precursor_strand == "bottom" and end == length
                else EndChemistry.PHOSPHATE
            )
            if (
                fragment.sequence != expected_sequence
                or fragment.five_prime_end is not expected_five_prime
                or fragment.three_prime_end is not EndChemistry.HYDROXYL
            ):
                raise ValueError("Fragment sequence and end chemistry must replay nicking.")
        selected = self.length_selected_fragment_set
        fragment_ids = tuple(item.fragment_id for item in fragments)
        selected_ids = selected.retained_fragment_ids + selected.excluded_fragment_ids
        if len(selected_ids) != len(fragment_ids) or set(selected_ids) != set(fragment_ids):
            raise ValueError("Length selection must partition every denatured fragment.")
        retained = tuple(
            fragment
            for fragment in fragments
            if fragment.fragment_id in selected.retained_fragment_ids
        )
        should_retain = tuple(
            fragment
            for fragment in fragments
            if len(fragment.sequence) >= selected.selection.min_length_nt
            and (
                selected.selection.max_length_nt is None
                or len(fragment.sequence) <= selected.selection.max_length_nt
            )
        )
        retained_strands = {fragment.precursor_strand for fragment in retained}
        if retained != should_retain or len(retained) != 2 or retained_strands != {"top", "bottom"}:
            raise ValueError("Retained fragments must derive only from the length rule.")
        top = next(fragment for fragment in retained if fragment.precursor_strand == "top")
        bottom = next(fragment for fragment in retained if fragment.precursor_strand == "bottom")
        adapter = next(
            material
            for material in self.materials.materials
            if material.role is ProcessMaterialRole.LIGATION_ADAPTER
        )
        strand_sequences = {
            top.fragment_id: top.sequence,
            bottom.fragment_id: bottom.sequence,
            adapter.material_id: adapter.sequence,
        }
        pairs = self.adapter_annealed_complex.pairs
        for pair in pairs:
            if (
                pair.left_strand_id not in strand_sequences
                or pair.right_strand_id not in strand_sequences
                or strand_sequences[pair.left_strand_id][pair.left_index] != pair.left_base
                or strand_sequences[pair.right_strand_id][pair.right_index] != pair.right_base
            ):
                raise ValueError("Annealing pairs must reference the selected literal strands.")
        overlap_start = max(top.precursor_span.start.offset, bottom.precursor_span.start.offset)
        overlap_end = min(top.precursor_span.end.offset, bottom.precursor_span.end.offset)
        arm = self.adapter_annealing.adapter_span
        adapter_start = overlap_start - arm.length.value
        expected_pair_indexes = tuple(
            (
                top.fragment_id,
                bottom.fragment_id,
                coordinate,
                bottom.precursor_span.end.offset - 1 - coordinate,
            )
            for coordinate in range(overlap_start, overlap_end)
        ) + tuple(
            (
                top.fragment_id,
                adapter.material_id,
                adapter_start + position,
                arm.end.offset - 1 - position,
            )
            for position in range(arm.length.value)
        )
        observed_pair_indexes = tuple(
            (pair.left_strand_id, pair.right_strand_id, pair.left_index, pair.right_index)
            for pair in pairs
        )
        if observed_pair_indexes != expected_pair_indexes:
            raise ValueError("Annealing pairs must cover both declared antiparallel interfaces.")
        components = (top.fragment_id, bottom.fragment_id, adapter.material_id)
        if self.ligated_hairpin.component_strand_ids != components:
            raise ValueError("Ligated-hairpin components must follow physical traversal order.")
        expected_bonds = (
            (top.fragment_id, StrandEnd.THREE_PRIME, bottom.fragment_id, StrandEnd.FIVE_PRIME),
            (bottom.fragment_id, StrandEnd.THREE_PRIME, adapter.material_id, StrandEnd.FIVE_PRIME),
        )
        observed_bonds = tuple(
            (
                bond.upstream_strand_id,
                bond.upstream_end,
                bond.downstream_strand_id,
                bond.downstream_end,
            )
            for bond in self.ligated_hairpin.bonds
        )
        ligation_ends_ready = (
            bottom.five_prime_end is EndChemistry.PHOSPHATE
            and OligoModification.FIVE_PRIME_PHOSPHATE in adapter.modifications
        ) or (self.materials.ligation_end_preparation is LigationEndPreparation.KINASE_STEP)
        ligated_sequence = top.sequence + bottom.sequence + adapter.sequence
        if (
            observed_bonds != expected_bonds
            or self.ligated_hairpin.strand.sequence != ligated_sequence
            or not ligation_ends_ready
        ):
            raise ValueError("Ligation bonds and sequence must join the selected strand chain.")
        duplex = self.hairpin_pcr_duplex
        if (
            duplex.top_strand.sequence != ligated_sequence
            or duplex.bottom_strand.sequence != reverse_complement_iupac(ligated_sequence)
        ):
            raise ValueError(
                "Hairpin PCR must produce a complementary duplex of the ligated strand."
            )
        hairpin_forward = next(
            material
            for material in self.materials.materials
            if material.role is ProcessMaterialRole.HAIRPIN_PCR_FORWARD_PRIMER
        )
        hairpin_reverse = next(
            material
            for material in self.materials.materials
            if material.role is ProcessMaterialRole.HAIRPIN_PCR_REVERSE_PRIMER
        )
        expected_binding_spans = (
            (
                hairpin_forward.material_id,
                0,
                len(hairpin_forward.sequence),
                BindingOrientation.SAME_5TO3,
            ),
            (
                hairpin_reverse.material_id,
                len(ligated_sequence) - len(hairpin_reverse.sequence),
                len(ligated_sequence),
                BindingOrientation.REVERSE_COMPLEMENT_5TO3,
            ),
        )
        observed_binding_spans = tuple(
            (
                binding.primer_id,
                binding.template_span.start.offset,
                binding.template_span.end.offset,
                binding.orientation,
            )
            for binding in duplex.primer_bindings
        )
        if observed_binding_spans != expected_binding_spans:
            raise ValueError("Hairpin-PCR primer boundaries must match the resolved materials.")
        product = self.restriction_digest_product
        left, right = product.sites
        top_start, top_end = left.cut.top.offset, right.cut.top.offset
        bottom_start, bottom_end = left.cut.bottom.offset, right.cut.bottom.offset
        union = Span(
            start=Boundary(offset=min(top_start, bottom_start)),
            end=Boundary(offset=max(top_end, bottom_end)),
        )
        union_sequence = ligated_sequence[union.start.offset : union.end.offset]
        projected = (
            union_sequence
            if product.hairpin_encoding_projection.orientation is BindingOrientation.SAME_5TO3
            else reverse_complement_iupac(union_sequence)
        )
        if (
            product.primary_strand.sequence != ligated_sequence[top_start:top_end]
            or product.complementary_strand.sequence
            != reverse_complement_iupac(ligated_sequence[bottom_start:bottom_end])
            or product.primary_union_span != union
            or product.hairpin_encoding_projection.sequence != projected
        ):
            raise ValueError("Restriction product must derive from its facing cut boundaries.")
        return self


class LinearSourceMultinickHairpinPcrResult(HopModel):
    schema_id: Literal["hop.linear-source-multinick-hairpin-pcr-result/v1"] = Field(
        default="hop.linear-source-multinick-hairpin-pcr-result/v1", alias="schema"
    )
    request_id: ReferenceId
    method_kind: LinearSourceMethodKind = LINEAR_SOURCE_METHOD_KIND
    outcome: MethodOutcome
    plan: LinearSourceMultinickHairpinPcrPlan | None

    @model_validator(mode="after")
    def validate_result(self) -> LinearSourceMultinickHairpinPcrResult:
        is_complete = self.outcome.resolution_status == "complete"
        if is_complete != (self.plan is not None):
            raise ValueError("A method plan exists exactly when resolution is complete.")
        return self
