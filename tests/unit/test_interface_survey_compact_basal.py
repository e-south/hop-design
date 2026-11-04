"""Survey basal pages contain admitted joint choices, not raw candidate prefixes."""

import json

from hop_design.design.construction.basal import discover_basal_neighborhood
from hop_design.design.construction.local_public import _discover_request
from hop_design.design.construction.surveys.partitions import PartitionPlans
from hop_design.models.construction import BasalPairAllowance, ConstructionEndpoint
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from tests.contract.test_basal_construction_discovery import _pairing_constraints, _request
from tests.unit.test_interface_survey_compact_foldback import _two_method_product


def test_complete_compact_basal_members_agree_with_ordinary_local_discovery():
    from hop_design.design.construction.surveys.basal_population import admit_population

    local = _request(
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        pairing_constraints=_pairing_constraints(
            (
                BasalPairAllowance.MATCH,
                BasalPairAllowance.ANY,
                BasalPairAllowance.ANY,
                BasalPairAllowance.MATCH,
                BasalPairAllowance.MATCH,
            )
        ),
    )
    local = local.model_copy(
        update={
            "geometry_domain": local.geometry_domain.model_copy(
                update={"max_noncanonical_pairs": 1}
            )
        }
    )
    complete = discover_basal_neighborhood(local)
    expected = {
        (r.source_precursor_sequence, r.projection.pairing_state.adapter_sequence_5prime)
        for r in complete.realizations
    }
    population = admit_population(local, DEFAULT_SEQUENCE_LIMITS)
    assert population.parts == len(expected)
    actual = set()
    for support in population.supports:
        for rank in range(support.cardinality):
            member = support.member_at(rank)
            actual.add((member.source_precursor_sequence, member.adapter_sequence))
    assert actual == expected


def test_survey_pages_select_one_supported_basal_program_and_replay_exactly():
    product = _two_method_product()
    plan = PartitionPlans().get(product)
    assert plan.basal.parts
    assert plan.basal.facts()["scope"] == "local_molecular_admission"
    # First and last admitted joint members must remain independently replayable.
    for rank in (0, plan.basal.parts - 1):
        selected = plan.basal.select(product, rank)
        local = selected.construction_source().basal
        actual = json.loads(_discover_request(local).json_bytes)
        assert len(actual["realizations"]) == 1
        assert actual["discovery"]["disposition"]["termination_reason"] == "exhausted_domain"
