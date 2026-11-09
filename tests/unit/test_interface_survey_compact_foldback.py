"""Survey pages address admitted populations, retaining exact compiler authority."""

import json

from hop_design.design.construction.local_public import _discover_request
from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.completion.extent import local_extent
from hop_design.design.construction.surveys.partitions import PartitionPlans
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.models.sequence import reverse_complement_iupac
from tests.unit.test_interface_survey_request import survey_document


def _two_method_product():
    data = survey_document()
    data["placements"] = [{"left_bp": 6, "right_bp": 6}]
    data["basal"]["annealing_lengths_nt"] = [17]
    data["foldback"]["enzymes"].update(
        allowed_enzyme_ids=["example:enzyme/nt.bpu10i@1", "example:enzyme/nb.bsrdi@1"],
        role_restrictions=[],
    )
    data["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[7],
        junction_offsets_nt=[2],
        loop_lengths_nt=[4],
        nick_strand="top",
    )
    data["foldback"]["max_retained_overhead_nt"] = 18
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(data)))
    return branches.product(
        0,
        branch=0,
        limits=SurveyEvaluationLimits(
            local_nodes=100, local_realizations=100, release_site_pairs=10
        ),
    )


def test_each_supported_program_is_visited_before_repeating_one_program():
    product = _two_method_product()
    population = PartitionPlans().get(product).foldback
    selected = [population.select(product, rank) for rank in range(2)]
    assert {str(p.foldback.enzymes.allowed_enzyme_ids[0]) for p in selected} == {
        "example:enzyme/nt.bpu10i@1",
        "example:enzyme/nb.bsrdi@1",
    }
    for p in selected:
        assert json.loads(_discover_request(p.construction_source().foldback).json_bytes)[
            "realizations"
        ]


def test_basal_sequence_count_does_not_delay_foldback_alternatives():
    product = _two_method_product()
    plan = PartitionPlans().get(product)
    assert plan.basal.parts > 2
    selected = [plan.product(product, rank) for rank in range(3)]
    assert len({p.foldback.enzymes.allowed_enzyme_ids for p in selected}) == 2
    assert len({p.basal.search.sequence_partition.part_index for p in selected}) == 2


def test_single_nick_selection_from_optional_terminus_programs_replays():
    data = _two_method_product().model_dump(mode="json", by_alias=True)
    nickases = data["foldback"]["enzymes"]["allowed_enzyme_ids"]
    terminus = "example:enzyme/bsai-hfv2@1"
    data["foldback"]["enzymes"].update(
        allowed_enzyme_ids=[*nickases, terminus],
        role_restrictions=[
            {"role": "foldback_nick", "allowed_enzyme_ids": nickases},
            {"role": "terminus_definition", "allowed_enzyme_ids": [terminus]},
        ],
    )
    product = ProductRequest.model_validate_json(json.dumps(data))
    population = PartitionPlans().get(product).foldback
    selected = population.select(product, 0)
    assert terminus not in selected.foldback.enzymes.allowed_enzyme_ids
    assert all(r.allowed_enzyme_ids for r in selected.foldback.enzymes.role_restrictions)
    assert json.loads(_discover_request(selected.construction_source().foldback).json_bytes)[
        "realizations"
    ]


def test_compact_admitted_member_reaches_the_ordinary_local_compiler_without_raw_scan():
    data = survey_document()
    data["placements"] = [{"left_bp": 6, "right_bp": 6}]
    data["basal"]["annealing_lengths_nt"] = [17]
    data["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[16],
        junction_offsets_nt=[8],
        loop_lengths_nt=[12],
    )
    data["foldback"]["max_retained_overhead_nt"] = 44
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(data)))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=10)
    product = branches.product(0, branch=0, limits=limits)
    source = product.construction_source()
    plan = PartitionPlans().get(product)
    assert plan.foldback.parts < local_extent(source.foldback).parts
    assert plan.foldback.parts > 1_000_000
    # Last admitted member, not the first million placement strings.
    selected = plan.product(product, plan.count - 1)
    receipt = _discover_request(selected.construction_source().foldback)
    actual = json.loads(receipt.json_bytes)["realizations"]
    support = plan.foldback.result.cases[0].programs[0]
    expected = support.sequences.member_at(support.sequences.cardinality - 1)
    assert len(actual) == 1
    assert (
        reverse_complement_iupac(actual[0]["foldback_arm_sequence"]) + actual[0]["loop_sequence"]
        == expected
    )
