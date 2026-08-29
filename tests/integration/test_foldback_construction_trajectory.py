"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_foldback_construction_trajectory.py

Tests exact foldback cleavage programs and state-aware molecular trajectories.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.models.construction.foldback import (
    FoldbackCleavageProgramKind,
    FoldbackLocalRealization,
)
from hop_design.models.enzymes import EnzymeClass
from hop_design.models.molecular_state import EndChemistry, StrandEnd
from hop_design.models.physical import Strand
from hop_design.models.sequence import reverse_complement_iupac
from tests.contract.test_foldback_construction_discovery import (
    _nickase,
    _request,
    _terminus_enzyme,
)


def test_single_cleavage_uses_the_complement_source_terminus_and_reference_nick() -> None:
    result = discover_foldback_neighborhood(_request(_nickase()))
    realization = result.realizations[0]

    assert realization.program_kind is FoldbackCleavageProgramKind.SINGLE_CLEAVAGE
    assert realization.foldback_nick.strand is Strand.TOP
    assert realization.terminus.strand is Strand.BOTTOM
    assert realization.terminus.kind == "source_terminus"
    assert len(realization.source_reference_sequence) == realization.terminus.boundary.offset
    assert realization.source_bottom_strand.five_prime_end is EndChemistry.PHOSPHATE
    assert realization.material_requirements == ("source_bottom_5prime_phosphate",)
    assert len(realization.reaction_program.stages) == 1
    assert all(not item.report.has_errors for item in realization.stage_assessments)
    assert realization.reaction_program.states[-1].state_id == "released-foldback-strands"
    assert realization.ligation_bond.upstream_end is StrandEnd.THREE_PRIME
    assert realization.ligation_bond.downstream_end is StrandEnd.FIVE_PRIME
    assert realization.ligated_strand.sequence == realization.retained_sequence


def test_sequential_program_defines_the_terminus_before_the_foldback_nick() -> None:
    result = discover_foldback_neighborhood(_request(_nickase(), _terminus_enzyme()))
    realization = next(
        item
        for item in result.realizations
        if item.program_kind is FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK
    )

    assert [stage.operations[0].role for stage in realization.reaction_program.stages] == [
        "terminus_definition",
        "foldback_nick",
    ]
    assert realization.terminus.enzyme_class is EnzymeClass.DUPLEX_RESTRICTION
    assert realization.terminus.strand is Strand.BOTTOM
    assert realization.foldback_nick.strand is Strand.TOP
    assert realization.material_requirements == ()
    assert all(not item.report.has_errors for item in realization.stage_assessments)
    assert realization.released_fragment_ids
    assert tuple(item.resolved_against_state_id for item in realization.stage_assessments) == (
        "source-duplex",
        "terminus-defined-duplexes",
    )


def test_sequential_program_never_uses_one_strand_for_both_controlled_boundaries() -> None:
    result = discover_foldback_neighborhood(_request(_nickase(), _terminus_enzyme()))

    sequential = tuple(
        item
        for item in result.realizations
        if item.program_kind is FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK
    )
    assert sequential
    assert all(item.terminus.strand is not item.foldback_nick.strand for item in sequential)


def test_unintended_actionable_site_rejects_the_exact_program() -> None:
    duplicate_site_nickase = _nickase(motif="ACA")
    assert duplicate_site_nickase.enzyme_class is EnzymeClass.NICKASE

    result = discover_foldback_neighborhood(
        _request(
            duplicate_site_nickase,
            max_search_nodes=200,
            max_realizations=200,
        )
    )

    assert result.neighborhood.status == "infeasible"
    assert {reason.code for reason in result.neighborhood.failure_reasons} == {
        "unintended-actionable-site"
    }


def test_route_authority_rejects_an_invented_sequential_post_state() -> None:
    result = discover_foldback_neighborhood(_request(_nickase(), _terminus_enzyme()))
    realization = next(
        item
        for item in result.realizations
        if item.program_kind is FoldbackCleavageProgramKind.SEQUENTIAL_TERMINUS_PLUS_NICK
    )
    data = realization.model_dump(mode="python")
    intermediate = data["reaction_program"]["states"][1]["molecules"][0]
    replacement = "A" * len(intermediate["reference_sequence_5prime"])
    intermediate["reference_sequence_5prime"] = replacement
    intermediate["complement_sequence_5prime"] = reverse_complement_iupac(replacement)

    with pytest.raises(ValidationError, match=r"identity|replay"):
        FoldbackLocalRealization.model_validate(data)


@pytest.mark.parametrize("control", ("foldback_nick", "terminus"))
def test_resealed_foldback_realization_rejects_tampered_boundary_controls(
    control: str,
) -> None:
    result = discover_foldback_neighborhood(_request(_nickase(), _terminus_enzyme()))
    realization = result.realizations[0]
    content = realization.model_dump(mode="python", exclude={"foldback_realization_id"})
    content[control]["boundary"]["offset"] += 1

    with pytest.raises(ValidationError, match=r"control|replay|boundary"):
        FoldbackLocalRealization.create(**content)


def test_resealed_foldback_realization_rejects_emptied_stage_intended_bindings() -> None:
    result = discover_foldback_neighborhood(_request(_nickase(), _terminus_enzyme()))
    realization = result.realizations[0]
    content = realization.model_dump(mode="python", exclude={"foldback_realization_id"})
    content["stage_assessments"][0]["intended_bindings"] = ()

    with pytest.raises(ValidationError, match=r"assessment|binding|replay"):
        FoldbackLocalRealization.create(**content)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (("payload_sequence", "GACT"), ("loop_sequence", "CCC")),
)
def test_foldback_realization_identity_rejects_mutated_molecular_content(
    field: str,
    replacement: str,
) -> None:
    result = discover_foldback_neighborhood(_request(_nickase(), _terminus_enzyme()))
    realization = result.realizations[0]
    data = realization.model_dump(mode="python")
    data[field] = replacement

    with pytest.raises(ValidationError, match=r"identity|replay|derive"):
        FoldbackLocalRealization.model_validate(data)

    content = {key: value for key, value in data.items() if key != "foldback_realization_id"}
    with pytest.raises(ValidationError, match=r"mapping|replay|derive"):
        FoldbackLocalRealization.create(**content)
