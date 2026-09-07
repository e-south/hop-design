"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_source_partition_discovery.py

Tests bounded discovery of multi-nick source partitions and selected survivors.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import combinations as itertools_combinations

import pytest

from hop_design.design.construction.source_partition import discover_source_partitions
from hop_design.models.construction import FinalPayloadReference, SearchCompletionStatus
from hop_design.models.construction.payload import (
    PayloadSourceMap,
    PayloadSourceSegment,
    SourceOrientation,
)
from hop_design.models.construction.source_partition import (
    PartitionNickFunction,
    SacrificialFragmentPolicy,
    SourceDuplexMaterial,
    SourcePartitionConstraints,
    SourcePartitionDiscoveryRequest,
    SourcePartitionEnumerationPolicy,
    SourcePartitionFailure,
    SourcePartitionFragmentDisposition,
    SourcePartitionSurvivor,
)
from hop_design.models.construction.source_partition.result import (
    canonical_source_partition_candidates,
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
from hop_design.models.molecular_state import EndChemistry
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
    preferred_maximum_nt: int = 11,
    absolute_maximum_nt: int = 15,
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
        schema="hop.source-partition-request/v2",
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
            fragment_policy=SacrificialFragmentPolicy(
                preferred_maximum_nt=preferred_maximum_nt,
                absolute_maximum_nt=absolute_maximum_nt,
            ),
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


def test_realization_certifies_every_fragment_and_the_inclusive_threshold_ladder() -> None:
    realization = discover_source_partitions(_request()).realizations[0]
    certificate = realization.fragment_certificate

    assert certificate.source_length_nt == 70
    assert certificate.selected_maximum_sacrificial_fragment_nt == 12
    assert [item.maximum_sacrificial_fragment_nt for item in certificate.thresholds] == [
        11,
        12,
        13,
        14,
        15,
    ]
    assert [item.feasible for item in certificate.thresholds] == [
        False,
        True,
        True,
        True,
        True,
    ]
    assert tuple(
        (
            item.precursor_strand,
            item.source_span.start.offset,
            item.source_span.end.offset,
            item.length_nt,
            item.disposition,
            item.left_boundary.kind,
            item.right_boundary.kind,
        )
        for item in certificate.fragments
    ) == (
        (
            Strand.TOP,
            0,
            58,
            58,
            SourcePartitionFragmentDisposition.REQUIRED,
            "physical_end",
            "cleavage",
        ),
        (
            Strand.TOP,
            58,
            70,
            12,
            SourcePartitionFragmentDisposition.SACRIFICIAL,
            "cleavage",
            "physical_end",
        ),
        (
            Strand.BOTTOM,
            0,
            11,
            11,
            SourcePartitionFragmentDisposition.SACRIFICIAL,
            "physical_end",
            "cleavage",
        ),
        (
            Strand.BOTTOM,
            11,
            23,
            12,
            SourcePartitionFragmentDisposition.SACRIFICIAL,
            "cleavage",
            "cleavage",
        ),
        (
            Strand.BOTTOM,
            23,
            35,
            12,
            SourcePartitionFragmentDisposition.SACRIFICIAL,
            "cleavage",
            "cleavage",
        ),
        (
            Strand.BOTTOM,
            35,
            70,
            35,
            SourcePartitionFragmentDisposition.REQUIRED,
            "cleavage",
            "physical_end",
        ),
    )


def test_missing_cleanup_site_and_unmet_fragment_threshold_are_infeasible() -> None:
    missing_site = SOURCE[:6] + "CATGAG" + SOURCE[12:]

    mutated = discover_source_partitions(_request(sequence=missing_site))
    too_strict = discover_source_partitions(
        _request(preferred_maximum_nt=11, absolute_maximum_nt=11)
    )

    assert mutated.status is SearchCompletionStatus.INFEASIBLE
    assert too_strict.status is SearchCompletionStatus.INFEASIBLE
    assert not mutated.realizations
    assert not too_strict.realizations
    assert all(
        SourcePartitionFailure.FRAGMENT_THRESHOLD_INFEASIBLE in item.failure_codes
        for item in mutated.dispositions
        if len(item.enzyme_ids) == 2
    )
    assert all(
        SourcePartitionFailure.FRAGMENT_THRESHOLD_INFEASIBLE in item.failure_codes
        for item in too_strict.dispositions
        if len(item.enzyme_ids) == 2
    )


def test_search_limit_reports_truncation_without_claiming_infeasibility() -> None:
    result = discover_source_partitions(_request(max_search_nodes=2))

    assert result.status is SearchCompletionStatus.TRUNCATED
    assert result.candidate_space_size == 3
    assert result.examined_nodes == 2
    assert not result.realizations
    assert result.truncation_reasons == ("max_search_nodes",)


def test_realization_limit_reports_its_exact_stopping_reason() -> None:
    request = _request(max_search_nodes=6)
    unused = request.enzyme_provisioning.catalog.enzymes[0].model_copy(
        update={
            "enzyme_id": "example:enzyme/z-unused@1",
            "canonical_name": "z-unused",
            "recognition_pattern": "AAAAAC",
        }
    )
    mapping = request.model_dump(mode="python", by_alias=True)
    provisioning = mapping["enzyme_provisioning"]
    provisioning["catalog"]["enzymes"] = (
        *provisioning["catalog"]["enzymes"],
        unused.model_dump(mode="python", by_alias=True),
    )
    provisioning["allowed_enzyme_ids"] = (
        *provisioning["allowed_enzyme_ids"],
        unused.enzyme_id,
    )
    provisioning["role_restrictions"][0]["allowed_enzyme_ids"] = (
        *provisioning["role_restrictions"][0]["allowed_enzyme_ids"],
        unused.enzyme_id,
    )
    mapping["enumeration"]["max_realizations"] = 1
    expanded = SourcePartitionDiscoveryRequest.model_validate(mapping)

    result = discover_source_partitions(expanded)

    assert result.status is SearchCompletionStatus.TRUNCATED
    assert result.examined_nodes == 4
    assert result.candidate_space_size == 6
    assert result.truncation_reasons == ("max_realizations",)


def test_candidate_enumeration_is_lazy_and_stops_at_the_search_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import hop_design.models.construction.source_partition.result as result_module

    def guarded_combinations(values: tuple[str, ...], width: int) -> Iterator[tuple[str, ...]]:
        for index, candidate in enumerate(itertools_combinations(values, width)):
            if index > 0:
                raise AssertionError("candidate enumeration crossed the search bound")
            yield candidate

    monkeypatch.setattr(result_module, "combinations", guarded_combinations)
    request = _request(max_search_nodes=1)

    candidates = canonical_source_partition_candidates(request)
    assert iter(candidates) is candidates
    result = discover_source_partitions(request)

    assert result.candidate_space_size == request.candidate_space_size == 3
    assert result.examined_nodes == 1
    assert result.status is SearchCompletionStatus.TRUNCATED


def test_large_candidate_domain_retains_exact_symbolic_accounting() -> None:
    request = _request(max_search_nodes=1)
    template = request.enzyme_provisioning.catalog.enzymes[0]
    added = tuple(
        template.model_copy(
            update={
                "enzyme_id": f"example:enzyme/scale-{index:02d}@1",
                "canonical_name": f"scale-{index:02d}",
            }
        )
        for index in range(18)
    )
    mapping = request.model_dump(mode="python", by_alias=True)
    provisioning = mapping["enzyme_provisioning"]
    added_mappings = tuple(enzyme.model_dump(mode="python", by_alias=True) for enzyme in added)
    added_ids = tuple(enzyme.enzyme_id for enzyme in added)
    provisioning["catalog"]["enzymes"] = (
        *provisioning["catalog"]["enzymes"],
        *added_mappings,
    )
    provisioning["allowed_enzyme_ids"] = (
        *provisioning["allowed_enzyme_ids"],
        *added_ids,
    )
    provisioning["role_restrictions"][0]["allowed_enzyme_ids"] = (
        *provisioning["role_restrictions"][0]["allowed_enzyme_ids"],
        *added_ids,
    )
    mapping["constraints"]["max_enzymes_per_program"] = 10
    expanded = SourcePartitionDiscoveryRequest.model_validate(mapping)

    result = discover_source_partitions(expanded)

    assert result.candidate_space_size == expanded.candidate_space_size == 616_665
    assert result.examined_nodes == 1
    assert result.status is SearchCompletionStatus.TRUNCATED


def _structurally_distinct_request(
    *, include_terminal_nickase: bool = False
) -> SourcePartitionDiscoveryRequest:
    sequence = "TTTGACCTAGGGGGGGGGGGGATCGTACGATCGTACCCCCTTAGCGAAAAAAA"
    left = _nickase(
        enzyme_id="example:enzyme/left-partition@1",
        motif="GACCTA",
        cut_offset=5,
    )
    right = _nickase(
        enzyme_id="example:enzyme/right-partition@1",
        motif="TTAGCG",
        cut_offset=3,
    )
    terminal = _nickase(
        enzyme_id="example:enzyme/a-terminal@1",
        motif="TTTGAC",
        cut_offset=0,
    )
    enzymes = (terminal, left, right) if include_terminal_nickase else (left, right)
    enzyme_ids = tuple(enzyme.enzyme_id for enzyme in enzymes)
    payload = FinalPayloadReference(
        schema="hop.final-payload/v1",
        display_name="distinct exact payload",
        payload=ExactPayload(sequence=sequence[15:35]),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=20),
        pair_state_exceptions=(),
    )
    return SourcePartitionDiscoveryRequest(
        schema="hop.source-partition-request/v2",
        payload=payload,
        source=SourceDuplexMaterial(
            material_id="distinct-source-duplex",
            top_sequence_5prime=sequence,
            top_five_prime_end=EndChemistry.HYDROXYL,
            top_three_prime_end=EndChemistry.HYDROXYL,
            bottom_five_prime_end=EndChemistry.HYDROXYL,
            bottom_three_prime_end=EndChemistry.HYDROXYL,
        ),
        payload_source_map=PayloadSourceMap(
            segments=(
                PayloadSourceSegment(
                    payload_span=_span(0, 20),
                    source_material_id="distinct-source-duplex",
                    source_span=_span(15, 35),
                    orientation=SourceOrientation.FORWARD,
                ),
            )
        ),
        enzyme_provisioning=EnzymeProvisioningPolicy(
            catalog=CharacterizedEnzymeCatalog(
                schema="hop/characterized-enzyme-catalog/v1",
                catalog_id="example:enzyme-catalog/distinct-source-partition@1",
                enzymes=enzymes,
            ),
            allowed_enzyme_ids=enzyme_ids,
            forbidden_enzyme_ids=(),
            reserved_enzyme_ids=(),
            max_operations=3,
            role_restrictions=(
                EnzymeRoleRestriction(
                    role=EnzymeRole.STRAND_EXPOSURE,
                    allowed_enzyme_ids=enzyme_ids,
                ),
            ),
        ),
        constraints=SourcePartitionConstraints(
            fragment_policy=SacrificialFragmentPolicy(
                preferred_maximum_nt=11,
                absolute_maximum_nt=15,
            ),
            required_survivors=(
                SourcePartitionSurvivor(
                    survivor_id="retained-top",
                    precursor_strand=Strand.TOP,
                    source_span=_span(8, 43),
                ),
                SourcePartitionSurvivor(
                    survivor_id="retained-bottom",
                    precursor_strand=Strand.BOTTOM,
                    source_span=_span(0, 53),
                ),
            ),
            max_enzymes_per_program=2,
        ),
        enumeration=SourcePartitionEnumerationPolicy(
            max_search_nodes=6 if include_terminal_nickase else 3,
            max_realizations=2,
        ),
    )


def test_discovers_a_structurally_distinct_partition() -> None:
    result = discover_source_partitions(_structurally_distinct_request())

    assert result.status is SearchCompletionStatus.COMPLETE
    assert len(result.realizations) == 1
    realization = result.realizations[0]
    assert tuple(site.nick.boundary.offset for site in realization.nicked_duplex.sites) == (8, 43)
    assert realization.selected.retained_fragment_ids == ("top-8-43", "bottom-0-53")


def test_terminal_nick_is_closed_rejection_and_later_candidates_continue() -> None:
    result = discover_source_partitions(
        _structurally_distinct_request(include_terminal_nickase=True)
    )

    terminal = result.dispositions[0]
    assert terminal.enzyme_ids == ("example:enzyme/a-terminal@1",)
    assert terminal.failure_codes == (SourcePartitionFailure.NONPARTITIONING_TERMINAL_CUT,)
    assert len(result.realizations) == 1
