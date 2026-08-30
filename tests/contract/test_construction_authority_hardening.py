"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_construction_authority_hardening.py

Tests fail-closed construction authorities against coherent contract drift.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.models.construction import (
    FailureReasonCount,
    FinalPayloadReference,
    MethodResolutionStatus,
    PairState,
    PairStateException,
    PayloadCompatibilityAccounting,
    PayloadCompatibilityStatus,
    PayloadSourceMap,
    PayloadSourceSegment,
    ProjectionInventoryItem,
    ProjectionInventoryStatus,
    RealizationGroup,
    RealizationGrouping,
    RelaxationCoordinate,
    RelaxationMode,
    RelaxationPolicy,
    RelaxationShellSummary,
    SourceOrientation,
    geometry_id,
    validate_linear_source_map,
)
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.payload import ExactPayload
from tests.contract.test_foldback_construction_discovery import _nickase as foldback_nickase
from tests.contract.test_foldback_construction_discovery import _request as foldback_request
from tests.contract.test_foldback_construction_discovery import (
    _terminus_enzyme as foldback_terminus_enzyme,
)


def _payload() -> FinalPayloadReference:
    return FinalPayloadReference(
        payload=ExactPayload(sequence="ACTG"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"basal_boundary": Boundary(offset=1)}, "basal boundary"),
        ({"foldback_boundary": Boundary(offset=3)}, "foldback boundary"),
        (
            {
                "pair_state_exceptions": (
                    PairStateException(
                        payload_position=1,
                        allowed_states=(PairState(reference_base="C", paired_base="A"),),
                    ),
                    PairStateException(
                        payload_position=1,
                        allowed_states=(PairState(reference_base="C", paired_base="G"),),
                    ),
                )
            },
            "positions must be unique",
        ),
        (
            {
                "pair_state_exceptions": (
                    PairStateException(
                        payload_position=4,
                        allowed_states=(PairState(reference_base="A", paired_base="T"),),
                    ),
                )
            },
            "within the final payload",
        ),
    ],
)
def test_payload_authority_rejects_coordinate_and_pairing_drift(
    updates: dict[str, object],
    message: str,
) -> None:
    content = _payload().model_dump(mode="python")
    content.update(updates)

    with pytest.raises(ValidationError, match=message):
        FinalPayloadReference.model_validate(content)


def test_pair_state_authority_rejects_duplicate_and_non_nucleotide_states() -> None:
    state = PairState(reference_base="C", paired_base="A")
    with pytest.raises(ValidationError, match="must not repeat"):
        PairStateException(payload_position=1, allowed_states=(state, state))

    for value in (1, "AC"):
        with pytest.raises(ValidationError, match=r"DNA strings|exactly one nucleotide"):
            PairState(reference_base=value, paired_base="T")


def test_source_mapping_rejects_length_overlap_coverage_and_orientation_drift() -> None:
    with pytest.raises(ValidationError, match="equal lengths"):
        PayloadSourceSegment(
            payload_span=Span(start=Boundary(offset=0), end=Boundary(offset=2)),
            source_material_id="source",
            source_span=Span(start=Boundary(offset=0), end=Boundary(offset=3)),
            orientation=SourceOrientation.FORWARD,
        )
    with pytest.raises(ValidationError, match="must not be empty"):
        PayloadSourceSegment(
            payload_span=Span(start=Boundary(offset=0), end=Boundary(offset=0)),
            source_material_id="source",
            source_span=Span(start=Boundary(offset=0), end=Boundary(offset=0)),
            orientation=SourceOrientation.FORWARD,
        )
    with pytest.raises(ValidationError, match="must not overlap"):
        PayloadSourceMap(
            segments=(
                PayloadSourceSegment(
                    payload_span=Span(start=Boundary(offset=0), end=Boundary(offset=3)),
                    source_material_id="source-a",
                    source_span=Span(start=Boundary(offset=0), end=Boundary(offset=3)),
                    orientation=SourceOrientation.FORWARD,
                ),
                PayloadSourceSegment(
                    payload_span=Span(start=Boundary(offset=2), end=Boundary(offset=4)),
                    source_material_id="source-b",
                    source_span=Span(start=Boundary(offset=0), end=Boundary(offset=2)),
                    orientation=SourceOrientation.FORWARD,
                ),
            )
        )

    for payload_span, orientation, message in (
        (
            Span(start=Boundary(offset=0), end=Boundary(offset=3)),
            SourceOrientation.FORWARD,
            "complete final payload",
        ),
        (
            Span(start=Boundary(offset=0), end=Boundary(offset=4)),
            SourceOrientation.REVERSE_COMPLEMENT,
            "forward payload",
        ),
    ):
        source_map = PayloadSourceMap(
            segments=(
                PayloadSourceSegment(
                    payload_span=payload_span,
                    source_material_id="source",
                    source_span=Span(
                        start=Boundary(offset=4),
                        end=Boundary(offset=4 + payload_span.length.value),
                    ),
                    orientation=orientation,
                ),
            )
        )
        with pytest.raises(ValueError, match=message):
            validate_linear_source_map(_payload(), source_map)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (
            {
                "radius": 0,
                "examined": False,
                "complete": True,
                "candidate_count": 0,
                "realization_ids": (),
                "rejected_count": 0,
                "failure_reasons": (),
            },
            "Unexamined shells",
        ),
        (
            {
                "radius": 0,
                "examined": True,
                "complete": False,
                "candidate_count": 0,
                "realization_ids": (),
                "rejected_count": 0,
                "failure_reasons": (),
            },
            "at least one candidate",
        ),
        (
            {
                "radius": 0,
                "examined": True,
                "complete": True,
                "candidate_count": 2,
                "realization_ids": (),
                "rejected_count": 2,
                "failure_reasons": (
                    FailureReasonCount(code="conflict", count=1),
                    FailureReasonCount(code="conflict", count=1),
                ),
            },
            "codes must be unique",
        ),
    ],
)
def test_relaxation_shell_accounting_rejects_non_evidence(
    content: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        RelaxationShellSummary.model_validate(content)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (
            {
                "status": PayloadCompatibilityStatus.COMPLETE,
                "total_assignments": 2,
                "compatible_assignments": 1,
                "excluded_assignments": 1,
                "conflict_counts": (),
                "exhaustive": False,
            },
            "must be exhaustive",
        ),
        (
            {
                "status": PayloadCompatibilityStatus.COMPLETE,
                "total_assignments": 2,
                "compatible_assignments": 2,
                "excluded_assignments": 1,
                "conflict_counts": (),
                "exhaustive": True,
            },
            "must equal total assignments",
        ),
        (
            {
                "status": PayloadCompatibilityStatus.COMPLETE,
                "total_assignments": 2,
                "compatible_assignments": 1,
                "excluded_assignments": 1,
                "conflict_counts": (FailureReasonCount(code="conflict", count=2),),
                "exhaustive": True,
            },
            "cannot exceed excluded assignments",
        ),
        (
            {
                "status": PayloadCompatibilityStatus.NOT_COMPUTED,
                "total_assignments": 2,
                "compatible_assignments": None,
                "excluded_assignments": None,
                "conflict_counts": (),
                "exhaustive": False,
                "warning": None,
            },
            "requires a conservative warning",
        ),
    ],
)
def test_payload_accounting_rejects_overstated_or_incoherent_evidence(
    content: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        PayloadCompatibilityAccounting.model_validate(content)


def test_projection_inventory_and_groups_fail_closed_on_resealed_metadata() -> None:
    for status, projection_id in (
        (ProjectionInventoryStatus.AVAILABLE, None),
        (ProjectionInventoryStatus.NOT_GENERATED, f"hop:projection/{'a' * 64}@1"),
    ):
        with pytest.raises(ValidationError, match="Available projections require an id"):
            ProjectionInventoryItem(
                projection_schema="hop.example/v1",
                renderer_version="example/1",
                status=status,
                projection_id=projection_id,
            )

    with pytest.raises(ValidationError, match="must match the declared grouping dimension"):
        RealizationGroup(
            grouping=RealizationGrouping.ACHIEVED_GEOMETRY,
            group_key=f"hop:final-product/{'a' * 64}@1",
            realization_ids=(f"hop:local-realization/{'b' * 64}@1",),
            multiplicity=1,
        )
    with pytest.raises(ValidationError, match="must not repeat a member"):
        RealizationGroup(
            grouping=RealizationGrouping.ACHIEVED_GEOMETRY,
            group_key=f"hop:geometry/{'a' * 64}@1",
            realization_ids=(
                f"hop:local-realization/{'b' * 64}@1",
                f"hop:local-realization/{'b' * 64}@1",
            ),
            multiplicity=2,
        )


def test_relaxation_policy_rejects_ambiguous_bounds_and_execution_semantics() -> None:
    with pytest.raises(ValidationError, match="maximum must not precede"):
        RelaxationCoordinate(name="loop_length_nt", minimum=4, maximum=3)
    duplicate = RelaxationCoordinate(name="loop_length_nt", minimum=2, maximum=4)
    with pytest.raises(ValidationError, match="names must be unique"):
        RelaxationPolicy(
            mode=RelaxationMode.THROUGH_RADIUS,
            max_radius=1,
            coordinates=(duplicate, duplicate),
        )
    with pytest.raises(ValidationError, match="exact_only relaxation requires"):
        RelaxationPolicy(mode=RelaxationMode.EXACT_ONLY, max_radius=1)
    with pytest.raises(ValidationError, match="requires enabled coordinates"):
        RelaxationPolicy(mode=RelaxationMode.THROUGH_RADIUS, max_radius=1)


def test_neighborhood_result_rejects_resealed_claim_group_and_inventory_drift() -> None:
    result = discover_foldback_neighborhood(
        foldback_request(foldback_nickase(), foldback_terminus_enzyme())
    ).neighborhood

    resolved_claim = result.claim_boundary.model_copy(
        update={"method": MethodResolutionStatus.RESOLVED}
    )
    content = result.model_dump(mode="python")
    content["claim_boundary"] = resolved_claim
    with pytest.raises(ValidationError, match="cannot claim a material-bound method"):
        type(result).model_validate(content)

    wrong_geometry = result.achieved_geometry_groups[0].model_copy(
        update={
            "group_key": geometry_id(
                result.realizations[0].achieved_geometry.model_copy(update={"loop_length_nt": 4})
            )
        }
    )
    content = result.model_dump(mode="python")
    content["achieved_geometry_groups"] = (wrong_geometry,)
    with pytest.raises(ValidationError, match="group key must match"):
        type(result).model_validate(content)

    duplicate_inventory = (*result.projection_inventory, result.projection_inventory[0])
    content = result.model_dump(mode="python")
    content["projection_inventory"] = duplicate_inventory
    with pytest.raises(ValidationError, match="unique by schema and renderer"):
        type(result).model_validate(content)
