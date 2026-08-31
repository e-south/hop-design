"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_endpoint_materialization.py

Tests endpoint-owned PCR primer and clone-release materialization contracts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import tracemalloc

import pytest
from pydantic import ValidationError

from hop_design.models.construction import BasalTarget
from hop_design.models.construction.complete import (
    CompositionEnumerationPolicy,
    ConstructionCompositionExecution,
    ExactConstructionMaterial,
    MaterialOrigin,
    PcrPrimer,
    ReleaseSideRequirement,
    TypeIisReleaseRequest,
)
from hop_design.models.construction.complete.clone import discover_endpoint_release
from hop_design.models.construction.complete.pcr.products import pcr_products
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    CharacterizedEnzymeCatalog,
    EnzymeClass,
    EnzymeProvisioningPolicy,
    EnzymeRole,
    EnzymeRoleRestriction,
    RecognitionOrientationSemantics,
    ResultingEndModel,
    SubstrateRequirement,
    TargetMolecule,
)
from hop_design.models.junction import Strand
from hop_design.models.molecular_state import (
    EndChemistry,
    LineageStrand,
    MaterialBaseLineage,
    MolecularStrand,
    StrandEnd,
)
from hop_design.models.physical import SiteOrientation
from hop_design.models.references import ExternalRef
from hop_design.models.sequence import reverse_complement_iupac


def _material(sequence: str) -> ExactConstructionMaterial:
    return ExactConstructionMaterial(
        material_id="forward-primer",
        origin=MaterialOrigin.SYNTHESIZED,
        sequence_5prime=sequence,
        five_prime_end=EndChemistry.HYDROXYL,
        three_prime_end=EndChemistry.HYDROXYL,
    )


def _template(sequence: str) -> MolecularStrand:
    return MolecularStrand(
        strand_id="template",
        sequence=sequence,
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=tuple(
            MaterialBaseLineage(
                product_index=index,
                origin_id="template",
                origin_strand=LineageStrand.PRIMARY,
                origin_index=index,
            )
            for index in range(len(sequence))
        ),
    )


def _type_iis() -> CharacterizedEnzyme:
    return CharacterizedEnzyme(
        enzyme_id="example:enzyme/type-iis@1",
        canonical_name="Type IIS example",
        enzyme_class=EnzymeClass.DUPLEX_RESTRICTION,
        target_molecule=TargetMolecule.DNA,
        recognition_pattern="GGTCTC",
        recognition_orientation_semantics=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
        recognition_length=6,
        substrate_requirement=SubstrateRequirement.DUPLEX_DNA,
        cut_offset_reference_strand=7,
        cut_offset_complement_strand=11,
        resulting_end_model=ResultingEndModel.DUPLEX_BREAK,
        characterization_source=ExternalRef(
            system="literature",
            kind="synthetic-characterization-fixture",
            id="type-iis",
        ),
    )


def _release_policy() -> EnzymeProvisioningPolicy:
    enzyme = _type_iis()
    return EnzymeProvisioningPolicy(
        catalog=CharacterizedEnzymeCatalog(
            catalog_id="example:catalog/release@1",
            enzymes=(enzyme,),
        ),
        allowed_enzyme_ids=(enzyme.enzyme_id,),
        forbidden_enzyme_ids=(),
        reserved_enzyme_ids=(),
        role_restrictions=(
            EnzymeRoleRestriction(
                role=EnzymeRole.END_GENERATION,
                allowed_enzyme_ids=(enzyme.enzyme_id,),
            ),
        ),
    )


def _release_policy_with_two_enzymes() -> EnzymeProvisioningPolicy:
    first = _type_iis()
    second = first.model_copy(
        update={
            "enzyme_id": "example:enzyme/type-iis-second@1",
            "canonical_name": "Type IIS second example",
        }
    )
    return EnzymeProvisioningPolicy(
        catalog=CharacterizedEnzymeCatalog(
            catalog_id="example:catalog/release-pair@1",
            enzymes=(first, second),
        ),
        allowed_enzyme_ids=(first.enzyme_id, second.enzyme_id),
        forbidden_enzyme_ids=(),
        reserved_enzyme_ids=(),
        role_restrictions=(
            EnzymeRoleRestriction(
                role=EnzymeRole.END_GENERATION,
                allowed_enzyme_ids=(first.enzyme_id, second.enzyme_id),
            ),
        ),
    )


def test_primer_contract_separates_terminal_annealing_from_five_prime_handle() -> None:
    primer = PcrPrimer(
        oligo=_material("GGTCTCACGT"),
        annealing_length_nt=4,
    )

    assert primer.five_prime_handle == "GGTCTC"
    assert primer.annealing_sequence == "ACGT"

    with pytest.raises(ValidationError, match="annealing length"):
        PcrPrimer(oligo=_material("ACGT"), annealing_length_nt=5)


def test_pcr_product_retains_both_complete_primers_with_exact_lineage() -> None:
    template_sequence = "ACGTAAAACCGT"
    template = MolecularStrand(
        strand_id="template",
        sequence=template_sequence,
        five_prime_end=EndChemistry.PHOSPHATE,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=tuple(
            MaterialBaseLineage(
                product_index=index,
                origin_id="template",
                origin_strand=LineageStrand.PRIMARY,
                origin_index=index,
            )
            for index in range(len(template_sequence))
        ),
    )
    forward = PcrPrimer(oligo=_material("GGTCTCACGT"), annealing_length_nt=4)
    reverse = PcrPrimer(
        oligo=_material("GAGACCACGG").model_copy(update={"material_id": "reverse-primer"}),
        annealing_length_nt=4,
    )

    top, bottom = pcr_products(template, forward, reverse)

    assert top.sequence == "GGTCTCACGTAAAACCGTGGTCTC"
    assert bottom.sequence == reverse_complement_iupac(top.sequence)
    assert len(top.lineage) == len(top.sequence)
    assert tuple(item.origin_id for item in top.lineage[:10]) == ("forward-primer",) * 10
    assert tuple(item.origin_index for item in top.lineage[-10:]) == tuple(reversed(range(10)))
    assert tuple(item.origin_id for item in top.lineage[-10:]) == ("reverse-primer",) * 10


def test_pcr_primer_annealing_spans_may_meet_but_must_not_overlap() -> None:
    forward = PcrPrimer(oligo=_material("GGACGT"), annealing_length_nt=4)
    reverse = PcrPrimer(
        oligo=_material("TTACGG").model_copy(update={"material_id": "reverse-primer"}),
        annealing_length_nt=4,
    )

    top, bottom = pcr_products(_template("ACGTCCGT"), forward, reverse)

    assert top.sequence == "GGACGTCCGTAA"
    assert bottom.sequence == reverse_complement_iupac(top.sequence)

    overlapping_reverse = reverse.model_copy(
        update={"oligo": reverse.oligo.model_copy(update={"sequence_5prime": "TTACGA"})}
    )
    with pytest.raises(ValueError, match="annealing spans must not overlap"):
        pcr_products(_template("ACGTCGT"), forward, overlapping_reverse)


def test_release_request_preserves_oriented_left_and_right_requirements() -> None:
    request = TypeIisReleaseRequest(
        enzyme_provisioning=_release_policy(),
        left=ReleaseSideRequirement(
            orientation=SiteOrientation.FORWARD,
            cohesive_end_sequence="AATG",
            overhang_end=StrandEnd.FIVE_PRIME,
        ),
        right=ReleaseSideRequirement(
            orientation=SiteOrientation.REVERSE,
            cohesive_end_sequence="CGCT",
            overhang_end=StrandEnd.FIVE_PRIME,
        ),
        max_site_pairs=16,
    )

    assert request.left.cohesive_end_sequence == "AATG"
    assert request.right.cohesive_end_sequence == "CGCT"
    assert request.left.orientation is SiteOrientation.FORWARD
    assert request.right.orientation is SiteOrientation.REVERSE


def test_release_request_requires_one_exact_end_generation_enzyme() -> None:
    with pytest.raises(ValidationError, match="exactly one provisioned"):
        TypeIisReleaseRequest(
            enzyme_provisioning=_release_policy_with_two_enzymes(),
            left=ReleaseSideRequirement(
                orientation=SiteOrientation.FORWARD,
                cohesive_end_sequence="AATG",
                overhang_end=StrandEnd.FIVE_PRIME,
            ),
            right=ReleaseSideRequirement(
                orientation=SiteOrientation.REVERSE,
                cohesive_end_sequence="CGCT",
                overhang_end=StrandEnd.FIVE_PRIME,
            ),
            max_site_pairs=16,
        )


def test_release_request_requires_a_type_iis_cleavage_definition() -> None:
    enzyme = _type_iis().model_copy(
        update={
            "cut_offset_reference_strand": 1,
            "cut_offset_complement_strand": 5,
        }
    )
    policy = _release_policy().model_copy(
        update={
            "catalog": CharacterizedEnzymeCatalog(
                catalog_id="example:catalog/type-ii@1",
                enzymes=(enzyme,),
            )
        }
    )

    with pytest.raises(ValidationError, match="outside its recognition site"):
        TypeIisReleaseRequest(
            enzyme_provisioning=policy,
            left=ReleaseSideRequirement(
                orientation=SiteOrientation.FORWARD,
                cohesive_end_sequence="AATG",
                overhang_end=StrandEnd.FIVE_PRIME,
            ),
            right=ReleaseSideRequirement(
                orientation=SiteOrientation.REVERSE,
                cohesive_end_sequence="CGCT",
                overhang_end=StrandEnd.FIVE_PRIME,
            ),
            max_site_pairs=16,
        )


def test_complete_construction_execution_identifies_endpoint_contract_v3() -> None:
    execution = ConstructionCompositionExecution(
        problem_id=f"hop:construction-problem/{'a' * 64}@1",
        hop_version="0.1.0a8",
        enumeration=CompositionEnumerationPolicy(
            max_combinations=1,
            max_realizations=1,
        ),
    )

    assert execution.route_implementation_version == "complete-construction/4"


def test_basal_target_rejects_endpoint_release_fields() -> None:
    with pytest.raises(ValidationError, match="end_generation"):
        BasalTarget.model_validate(
            {
                "nick_strand": Strand.BOTTOM,
                "nick_offset_nt": 0,
                "pairing_constraints": (),
                "ligation_proximal_match_required": False,
                "end_generation": {
                    "type_iis_cut_offset_nt": 0,
                    "requested_overhangs": (),
                },
            }
        )


def test_release_search_recovers_the_oriented_pair_that_retains_the_design_union() -> None:
    design = "AACCGGTT"
    pcr_top = f"GGTCTCA{design}AGAGACC"
    request = TypeIisReleaseRequest(
        enzyme_provisioning=_release_policy(),
        left=ReleaseSideRequirement(
            orientation=SiteOrientation.FORWARD,
            cohesive_end_sequence=design[:4],
            overhang_end=StrandEnd.FIVE_PRIME,
        ),
        right=ReleaseSideRequirement(
            orientation=SiteOrientation.REVERSE,
            cohesive_end_sequence=reverse_complement_iupac(design[-4:]),
            overhang_end=StrandEnd.FIVE_PRIME,
        ),
        max_site_pairs=1,
    )

    result = discover_endpoint_release(
        request=request,
        pcr_top=pcr_top,
        design_sequence=design,
    )

    assert result.bindings is not None
    assert result.examined_site_pairs == 1
    assert result.truncated is False


def test_release_search_reports_truncation_before_unique_pair_is_established() -> None:
    design = "AACCGGTT"
    pcr_top = f"GGTCTCA{design}AGAGACCAGAGACC"
    request = TypeIisReleaseRequest(
        enzyme_provisioning=_release_policy(),
        left=ReleaseSideRequirement(
            orientation=SiteOrientation.FORWARD,
            cohesive_end_sequence=design[:4],
            overhang_end=StrandEnd.FIVE_PRIME,
        ),
        right=ReleaseSideRequirement(
            orientation=SiteOrientation.REVERSE,
            cohesive_end_sequence=reverse_complement_iupac(design[-4:]),
            overhang_end=StrandEnd.FIVE_PRIME,
        ),
        max_site_pairs=1,
    )

    result = discover_endpoint_release(
        request=request,
        pcr_top=pcr_top,
        design_sequence=design,
    )

    assert result.bindings is None
    assert result.examined_site_pairs == 1
    assert result.truncated is True


def test_release_search_consumes_only_the_bounded_cartesian_prefix() -> None:
    design = "AACCGGTT"
    repeated_sites = 1_024
    pcr_top = "GGTCTC" * repeated_sites + "A" + design + "A" + "GAGACC" * repeated_sites
    request = TypeIisReleaseRequest(
        enzyme_provisioning=_release_policy(),
        left=ReleaseSideRequirement(
            orientation=SiteOrientation.FORWARD,
            cohesive_end_sequence=design[:4],
            overhang_end=StrandEnd.FIVE_PRIME,
        ),
        right=ReleaseSideRequirement(
            orientation=SiteOrientation.REVERSE,
            cohesive_end_sequence=reverse_complement_iupac(design[-4:]),
            overhang_end=StrandEnd.FIVE_PRIME,
        ),
        max_site_pairs=1,
    )

    tracemalloc.start()
    result = discover_endpoint_release(
        request=request,
        pcr_top=pcr_top,
        design_sequence=design,
    )
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert result.examined_site_pairs == 1
    assert result.truncated is True
    assert peak_bytes < 20_000_000


def test_release_search_reports_ambiguous_and_zero_match_outcomes() -> None:
    design = "AACCGGTT"
    request = TypeIisReleaseRequest(
        enzyme_provisioning=_release_policy(),
        left=ReleaseSideRequirement(
            orientation=SiteOrientation.FORWARD,
            cohesive_end_sequence=design[:4],
            overhang_end=StrandEnd.FIVE_PRIME,
        ),
        right=ReleaseSideRequirement(
            orientation=SiteOrientation.REVERSE,
            cohesive_end_sequence=reverse_complement_iupac(design[-4:]),
            overhang_end=StrandEnd.FIVE_PRIME,
        ),
        max_site_pairs=4,
    )

    ambiguous = discover_endpoint_release(
        request=request,
        pcr_top=f"GGTCTCA{design}AGAGACCGGTCTCA{design}AGAGACC",
        design_sequence=design,
    )
    zero = discover_endpoint_release(
        request=request,
        pcr_top="A" * 32,
        design_sequence=design,
    )

    assert ambiguous.bindings is None
    assert ambiguous.examined_site_pairs == 4
    assert ambiguous.truncated is False
    assert ambiguous.ambiguous is True
    assert zero.bindings is None
    assert zero.examined_site_pairs == 0
    assert zero.truncated is False
    assert zero.ambiguous is False
