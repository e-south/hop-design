"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_basal_release_coordinates.py

Checks independent basal end placement and its payload-relative source cuts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from itertools import product

import pytest
from pydantic import ValidationError

from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.kernel.construction.basal import (
    BasalPlacementFailure,
    iter_basal_program_solutions,
    iter_basal_programs,
)
from hop_design.models.construction import (
    BasalFutureReleaseAction,
    BasalFutureReleaseRequirement,
    BasalGeometryDomain,
    BasalPairAllowance,
    BasalPairConstraint,
    BasalTarget,
    ConstructionEndpoint,
)
from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.complete import ReleaseSideRequirement
from hop_design.models.construction.complete.auxiliary.pairing import (
    resolve_adapter_pairing_sequence,
)
from hop_design.models.construction.complete.pcr.pairing import complete_adapter_pairing
from hop_design.models.enzymes import EnzymeClass
from hop_design.models.molecular_state import StrandEnd
from hop_design.models.physical import SiteOrientation, Strand
from tests.contract.test_basal_construction_discovery import _enzyme, _nickase, _provisioning
from tests.contract.test_basal_construction_discovery import _request as basal_request
from tests.contract.test_basal_ligation_coordinates import _request as displaced_request


def _requirement(*, offset: int, side: str = "right", polarity=StrandEnd.FIVE_PRIME, sequence="AC"):
    return {
        "product_end": side,
        "orientation": SiteOrientation.REVERSE if side == "right" else SiteOrientation.FORWARD,
        "cohesive_end_sequence": sequence,
        "overhang_end": polarity,
        "recognition_material": "source_duplex",
        "payload_end_offset_bp": offset,
    }


def test_future_release_requires_an_explicit_payload_end_offset() -> None:
    content = _requirement(offset=0)
    content.pop("payload_end_offset_bp")
    with pytest.raises(ValidationError, match="payload_end_offset_bp"):
        BasalFutureReleaseRequirement.model_validate(content)


def test_complete_release_requires_the_same_explicit_coordinate_contract() -> None:
    content = {
        "orientation": SiteOrientation.REVERSE,
        "cohesive_end_sequence": "AC",
        "overhang_end": StrandEnd.FIVE_PRIME,
    }
    with pytest.raises(ValidationError, match="payload_end_offset_bp"):
        ReleaseSideRequirement.model_validate(content)
    assert (
        ReleaseSideRequirement.model_validate(
            {**content, "payload_end_offset_bp": 2}
        ).payload_end_offset_bp
        == 2
    )


@pytest.mark.parametrize("offset", (-1, 1.5))
def test_payload_end_offset_is_a_nonnegative_integral_pair_count(offset) -> None:
    with pytest.raises(ValidationError, match="payload_end_offset_bp"):
        BasalFutureReleaseRequirement.model_validate(_requirement(offset=offset))


def test_exact_end_expansion_preserves_the_independent_coordinate() -> None:
    future = BasalFutureReleaseRequirement.model_validate(_requirement(offset=2, sequence="AR"))
    domain = BasalGeometryDomain(
        nick_offsets_nt=(0, 1, 3),
        pairing_constraints=(
            BasalPairConstraint(position_from_ligation=0, allowed_class=BasalPairAllowance.MATCH),
        ),
        future_release=future,
    )
    targets = tuple(domain.exact_targets())
    assert {
        (
            target.nick_offset_nt,
            target.future_release.payload_end_offset_bp,
            target.future_release.cohesive_end_sequence,
        )
        for target in targets
    } == set(product((0, 1, 3), (2,), ("AA", "AG")))
    exact = next(future.exact_requirements())
    assert future.permits(exact)
    assert not future.permits(exact.model_copy(update={"payload_end_offset_bp": 1}))


@pytest.mark.parametrize("side", ("left", "right"))
@pytest.mark.parametrize("polarity", (StrandEnd.FIVE_PRIME, StrandEnd.THREE_PRIME))
@pytest.mark.parametrize("end_offset", (0, 1, 2))
def test_future_source_cuts_follow_end_offset_independently_of_nick(side, polarity, end_offset):
    forward_cuts = (3, 5) if polarity is StrandEnd.FIVE_PRIME else (5, 3)
    cutter = _enzyme(
        "example:enzyme/basal-end-coordinate@1",
        enzyme_class=EnzymeClass.DUPLEX_RESTRICTION,
        pattern="TTC",
        reference_cut=forward_cuts[0],
        complement_cut=forward_cuts[1],
    )
    policy = _provisioning(_nickase(), cutter)
    payload_boundary = 20
    observations = []
    for nick_offset in (0, 2, 5):
        target = BasalTarget(
            nick_strand=Strand.TOP,
            nick_offset_nt=nick_offset,
            future_release=BasalFutureReleaseRequirement.model_validate(
                _requirement(offset=end_offset, side=side, polarity=polarity)
            ),
        )
        programs = iter_basal_programs(
            policy, target=target, endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX
        )
        assert len(programs) == 1
        action = programs[0].future_release_action
        start, motif = action.source_recognition_placement(payload_boundary=payload_boundary)
        assert motif == "TTC"
        source_cuts = (start + forward_cuts[0], start + forward_cuts[1])
        assert sorted(source_cuts) == [
            payload_boundary - end_offset - 2,
            payload_boundary - end_offset,
        ]
        assert action.requirement.orientation is (
            SiteOrientation.REVERSE if side == "right" else SiteOrientation.FORWARD
        )
        action.assert_source_recognition_replay(
            sequence="A" * start + motif + "A" * (payload_boundary - start - len(motif)),
            payload_boundary=payload_boundary,
        )
        observations.append((start, source_cuts))
    assert len(set(observations)) == 1


def _literal_end_solutions(
    nick_offset: int, end_offset: int, side: str, polarity: StrandEnd
) -> set[tuple[str, str]]:
    """Enumerate a two-position source/adapter control in signed payload coordinates."""
    fixed = {}
    placements = [(-nick_offset - 2, "AG"), (-end_offset - 5, "TTC")]
    if side == "left":
        placements.append((-end_offset - 2, "AC" if polarity is StrandEnd.FIVE_PRIME else "GT"))
    for start, motif in placements:
        for index, base in enumerate(motif, start):
            if index in fixed and fixed[index] != base:
                return set()
            fixed[index] = base
    first = min(fixed)
    free = [index for index in range(first, 0) if index not in fixed]
    expected = set()
    complement = str.maketrans("ACGT", "TGCA")
    for assignment in product("ACGT", repeat=len(free)):
        bases = {**fixed, **dict(zip(free, assignment, strict=True))}
        source = "".join(bases[index] for index in range(first, 0))
        retained = source[-nick_offset:].translate(complement)[::-1] if nick_offset else ""
        for adapter_bases in product("ACGT", repeat=2):
            adapter = "".join(adapter_bases)
            return_arm = retained + adapter
            end_sequence = "GT" if polarity is StrandEnd.FIVE_PRIME else "AC"
            if side == "left" or all(
                return_arm[index] == end_sequence[index - end_offset]
                for index in range(end_offset, min(end_offset + 2, len(return_arm)))
            ):
                expected.add((source, adapter))
    return expected


@pytest.mark.parametrize(("nick_offset", "end_offset"), tuple(product(range(3), repeat=2)))
@pytest.mark.parametrize("side", ("left", "right"))
@pytest.mark.parametrize("polarity", (StrandEnd.FIVE_PRIME, StrandEnd.THREE_PRIME))
def test_basal_sequence_search_matches_literal_independent_end_oracle(
    nick_offset, end_offset, side, polarity
):
    target = BasalTarget(
        nick_strand=Strand.TOP,
        nick_offset_nt=nick_offset,
        pairing_constraints=tuple(
            BasalPairConstraint(position_from_ligation=index, allowed_class=BasalPairAllowance.ANY)
            for index in range(2)
        ),
        future_release=BasalFutureReleaseRequirement.model_validate(
            _requirement(offset=end_offset, side=side, polarity=polarity)
        ),
    )
    nickase = _enzyme(
        "example:enzyme/end-oracle-nick@1",
        enzyme_class=EnzymeClass.NICKASE,
        pattern="AG",
        reference_cut=2,
        complement_cut=None,
    )
    cutter = _enzyme(
        "example:enzyme/end-oracle-release@1",
        enzyme_class=EnzymeClass.DUPLEX_RESTRICTION,
        pattern="TTC",
        reference_cut=3 if polarity is StrandEnd.FIVE_PRIME else 5,
        complement_cut=5 if polarity is StrandEnd.FIVE_PRIME else 3,
    )
    (program,) = iter_basal_programs(
        _provisioning(nickase, cutter),
        target=target,
        endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
    )
    solutions = tuple(
        item
        for item in iter_basal_program_solutions(
            payload_sequence="CCCC",
            target=target,
            endpoint=ConstructionEndpoint.CLONE_READY_DUPLEX,
            program=program,
        )
        if not isinstance(item, BasalPlacementFailure)
    )
    observed = {
        (item.source_precursor_sequence[: item.payload_span.start.offset], item.adapter_sequence)
        for item in solutions
    }
    assert observed == _literal_end_solutions(nick_offset, end_offset, side, polarity)
    for item in solutions:
        assert item.source_precursor_sequence[item.payload_span.start.offset :] == "CCCC"
        assert [
            pair.position_from_ligation
            for pair in item.pairing_state.pairs
            if pair.participates_in_end_projection
        ] == [
            position
            for position in range(2)
            if end_offset <= nick_offset + position < end_offset + 2
        ]


@pytest.mark.parametrize("change", ("adapter_end", "source_end", "pair_membership"))
def test_basal_replay_rejects_resealed_future_end_drift(change):
    request = (
        displaced_request("bottom", 6, future_release=True)
        if change == "source_end"
        else basal_request(ConstructionEndpoint.CLONE_READY_DUPLEX)
    )
    record = discover_basal_neighborhood(request).realizations[0]
    content = {
        name: getattr(record, name)
        for name in type(record).model_fields
        if name != "basal_realization_id"
    }
    if change == "pair_membership":
        pairing = record.projection.pairing_state
        altered_pairs = (
            pairing.pairs[0].model_copy(update={"participates_in_end_projection": False}),
            *pairing.pairs[1:],
        )
        assert pairing.pairs[0].participates_in_end_projection
        content["projection"] = record.projection.model_copy(
            update={"pairing_state": pairing.model_copy(update={"pairs": altered_pairs})}
        )
    else:
        action = record.future_release_action
        requirement = action.requirement.model_copy(update={"cohesive_end_sequence": "GGGG"})
        assert action.requirement.cohesive_end_sequence != requirement.cohesive_end_sequence
        action_content = {
            name: getattr(action, name) for name in type(action).model_fields if name != "action_id"
        }
        action_content["requirement"] = requirement
        changed_action = BasalFutureReleaseAction.create(**action_content)
        local = record.local_realization
        local_content = {
            name: getattr(local, name)
            for name in type(local).model_fields
            if name != "local_realization_id"
        }
        local_content.update(
            boundary_condition_ids=(changed_action.action_id,),
            achieved_geometry=local.achieved_geometry.model_copy(
                update={"future_release": requirement}
            ),
        )
        content.update(
            future_release_action=changed_action,
            local_realization=type(local).create(**local_content),
        )
    with pytest.raises(ValidationError, match="future end"):
        BasalRealizationRecord.create(**content)


def _distal_end_context():
    request = basal_request(ConstructionEndpoint.CLONE_READY_DUPLEX)
    domain = request.geometry_domain
    request = request.model_copy(
        update={
            "geometry_domain": domain.model_copy(
                update={
                    "minimum_adapter_annealing_nt": 6,
                    "future_release": domain.future_release.model_copy(
                        update={
                            "payload_end_offset_bp": 2,
                            "recognition_material": "endpoint_material",
                        }
                    ),
                }
            )
        }
    )
    result = discover_basal_neighborhood(request)
    record = result.realizations[0]
    source_prefix = (
        "CG"
        + record.source_precursor_sequence[
            : record.payload_source_map.segments[0].source_span.start.offset
        ]
    )
    return result, source_prefix


def test_future_end_resolves_only_explicitly_permitted_distal_bases():
    result, source_prefix = _distal_end_context()
    record = result.realizations[0]
    constraints = tuple(
        BasalPairConstraint(position_from_ligation=position, allowed_class=BasalPairAllowance.ANY)
        for position in (4, 5)
    )
    adapter = resolve_adapter_pairing_sequence(
        record, source_prefix=source_prefix, constraints=constraints, fixed_sequence=None
    )
    assert adapter[2:6] == "TTAT"
    assert adapter[:4] == record.proximal_adapter_sequence
    pairing = complete_adapter_pairing(
        record, source_prefix=source_prefix, adapter_sequence=adapter
    )
    assert [
        pair.position_from_ligation for pair in pairing.pairs if pair.participates_in_end_projection
    ] == [2, 3, 4, 5]


def test_future_end_does_not_relax_canonical_distal_pairing_implicitly():
    result, source_prefix = _distal_end_context()
    record = result.realizations[0]
    with pytest.raises(ValueError, match="future end"):
        resolve_adapter_pairing_sequence(
            record, source_prefix=source_prefix, constraints=(), fixed_sequence=None
        )


def test_basal_projection_separates_future_release_gap_from_local_retained_accounting():
    from hop_design.design.construction.projections.basal import project_basal_feasibility

    result, _ = _distal_end_context()
    projection = project_basal_feasibility(result)
    for row in projection.realizations:
        assert row.nick_offset_nt == 0
        assert row.payload_end_offset_bp == 2
        assert row.retained_overhead_nt == 4
        assert (
            row.future_reference_cut_from_payload,
            row.future_complementary_cut_from_payload,
        ) == (-6, -2)
        assert row.future_product_end == "right"
        assert row.future_cohesive_end_sequence == "ATAA"
        assert row.future_overhang_end is StrandEnd.FIVE_PRIME
        assert row.pending_adapter_end_bases == ((4, "A"), (5, "T"))
