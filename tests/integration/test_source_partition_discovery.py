"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_source_partition_discovery.py

Tests bounded discovery of multi-nick source partitions and selected survivors.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.design.construction.source_partition import discover_source_partitions
from hop_design.models.construction import FinalPayloadReference, SearchCompletionStatus
from hop_design.models.construction.payload import (
    PayloadSourceMap,
    PayloadSourceSegment,
    SourceOrientation,
)
from hop_design.models.construction.source_partition import (
    PartitionNickFunction,
    SourceDuplexMaterial,
    SourcePartitionConstraints,
    SourcePartitionDiscoveryRequest,
    SourcePartitionEnumerationPolicy,
    SourcePartitionFailure,
    SourcePartitionSurvivor,
)
from hop_design.models.coordinates import Boundary, Span
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
from hop_design.models.molecular_state import EndChemistry, FragmentLengthSelection
from hop_design.models.payload import ExactPayload
from hop_design.models.references import ExternalRef
from tests.support.linear_source_method import SOURCE


def _span(start: int, end: int) -> Span:
    return Span(start=Boundary(offset=start), end=Boundary(offset=end))


def _nickase(*, enzyme_id: str, motif: str, cut_offset: int) -> CharacterizedEnzyme:
    return CharacterizedEnzyme(
        schema="hop/characterized-enzyme/v1",
        enzyme_id=enzyme_id,
        canonical_name=enzyme_id.rsplit("/", maxsplit=1)[-1],
        enzyme_class=EnzymeClass.NICKASE,
        target_molecule=TargetMolecule.DNA,
        recognition_pattern=motif,
        recognition_orientation_semantics=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
        recognition_length=len(motif),
        substrate_requirement=SubstrateRequirement.DUPLEX_DNA,
        cut_offset_reference_strand=cut_offset,
        cut_offset_complement_strand=None,
        resulting_end_model=ResultingEndModel.NICK,
        characterization_source=ExternalRef(
            system="study-fixture",
            kind="enzyme-characterization",
            id=enzyme_id,
        ),
        vendor_metadata=(),
    )


def _request(
    *,
    sequence: str = SOURCE,
    min_length_nt: int = 16,
    max_search_nodes: int = 3,
) -> SourcePartitionDiscoveryRequest:
    bottom_repeat = _nickase(
        enzyme_id="example:enzyme/bottom-repeat@1",
        motif="CTCGTG",
        cut_offset=1,
    )
    top_terminal = _nickase(
        enzyme_id="example:enzyme/top-terminal@1",
        motif="CCTCAGC",
        cut_offset=2,
    )
    catalog = CharacterizedEnzymeCatalog(
        schema="hop/characterized-enzyme-catalog/v1",
        catalog_id="example:enzyme-catalog/source-partition@1",
        enzymes=(bottom_repeat, top_terminal),
    )
    payload = FinalPayloadReference(
        schema="hop.final-payload/v1",
        display_name="exact black-box payload",
        payload=ExactPayload(sequence=sequence[36:55]),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=19),
        pair_state_exceptions=(),
    )
    return SourcePartitionDiscoveryRequest(
        schema="hop.source-partition-request/v1",
        payload=payload,
        source=SourceDuplexMaterial(
            material_id="source-duplex",
            top_sequence_5prime=sequence,
            top_five_prime_end=EndChemistry.HYDROXYL,
            top_three_prime_end=EndChemistry.HYDROXYL,
            bottom_five_prime_end=EndChemistry.HYDROXYL,
            bottom_three_prime_end=EndChemistry.HYDROXYL,
        ),
        payload_source_map=PayloadSourceMap(
            segments=(
                PayloadSourceSegment(
                    payload_span=_span(0, 19),
                    source_material_id="source-duplex",
                    source_span=_span(36, 55),
                    orientation=SourceOrientation.FORWARD,
                ),
            )
        ),
        enzyme_provisioning=EnzymeProvisioningPolicy(
            catalog=catalog,
            allowed_enzyme_ids=(bottom_repeat.enzyme_id, top_terminal.enzyme_id),
            forbidden_enzyme_ids=(),
            reserved_enzyme_ids=(),
            max_operations=4,
            role_restrictions=(
                EnzymeRoleRestriction(
                    role=EnzymeRole.STRAND_EXPOSURE,
                    allowed_enzyme_ids=(bottom_repeat.enzyme_id, top_terminal.enzyme_id),
                ),
            ),
        ),
        constraints=SourcePartitionConstraints(
            selection=FragmentLengthSelection(min_length_nt=min_length_nt),
            required_survivors=(
                SourcePartitionSurvivor(
                    survivor_id="retained-top",
                    precursor_strand=Strand.TOP,
                    source_span=_span(0, 58),
                ),
                SourcePartitionSurvivor(
                    survivor_id="retained-bottom",
                    precursor_strand=Strand.BOTTOM,
                    source_span=_span(35, 70),
                ),
            ),
            max_enzymes_per_program=2,
        ),
        enumeration=SourcePartitionEnumerationPolicy(
            max_search_nodes=max_search_nodes,
            max_realizations=4,
        ),
    )


def test_discovers_the_required_multinick_partition_exhaustively() -> None:
    result = discover_source_partitions(_request())

    assert result.status is SearchCompletionStatus.COMPLETE
    assert result.candidate_space_size == 3
    assert result.examined_nodes == 3
    assert len(result.dispositions) == 3
    assert len(result.realizations) == 1

    realization = result.realizations[0]
    assert realization.enzyme_ids == (
        "example:enzyme/bottom-repeat@1",
        "example:enzyme/top-terminal@1",
    )
    assert tuple(
        (site.nick.strand, site.nick.boundary.offset) for site in realization.nicked_duplex.sites
    ) == (
        (Strand.BOTTOM, 11),
        (Strand.BOTTOM, 23),
        (Strand.BOTTOM, 35),
        (Strand.TOP, 58),
    )
    assert realization.selected.retained_fragment_ids == (
        "top-0-58",
        "bottom-35-70",
    )
    assert tuple((item.boundary.offset, item.function) for item in realization.nick_functions) == (
        (11, PartitionNickFunction.EXCLUDED_FRAGMENT_CLEANUP),
        (23, PartitionNickFunction.EXCLUDED_FRAGMENT_CLEANUP),
        (35, PartitionNickFunction.RETAINED_FRAGMENT_BOUNDARY),
        (58, PartitionNickFunction.RETAINED_FRAGMENT_BOUNDARY),
    )


def test_missing_cleanup_site_and_more_permissive_selection_are_infeasible() -> None:
    missing_site = SOURCE[:6] + "CATGAG" + SOURCE[12:]

    mutated = discover_source_partitions(_request(sequence=missing_site))
    permissive = discover_source_partitions(_request(min_length_nt=12))

    assert mutated.status is SearchCompletionStatus.INFEASIBLE
    assert permissive.status is SearchCompletionStatus.INFEASIBLE
    assert not mutated.realizations
    assert not permissive.realizations
    assert all(
        SourcePartitionFailure.RETAINED_FRAGMENT_SET_MISMATCH in item.failure_codes
        for item in mutated.dispositions
        if len(item.enzyme_ids) == 2
    )


def test_search_limit_reports_truncation_without_claiming_infeasibility() -> None:
    result = discover_source_partitions(_request(max_search_nodes=2))

    assert result.status is SearchCompletionStatus.TRUNCATED
    assert result.candidate_space_size == 3
    assert result.examined_nodes == 2
    assert not result.realizations
    assert result.truncation_reasons == ("max_search_nodes",)
