"""A known preparation resolves inside a broader ordinary molecular request."""

import json
from pathlib import Path

import pytest

from hop_design import construction
from hop_design.design.construction.local_public import _discover_request
from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.partitions import PartitionPlans
from hop_design.design.construction.surveys.preference_addressing import (
    PreferenceOutOfScope,
    addresses_for_preparation,
)
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document


@pytest.fixture(scope="module")
def reference():
    packet = construction.execute_construction_request(
        Path("examples/complete-construction/product-request.json"),
        design_id="preference-addressing-example",
        continuation="sole-witness",
    )
    return packet._compilation._verified_source().result


def broad(document=None):
    document = survey_document() if document is None else document
    document["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "N" * 14
    )
    return SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))


def test_reference_maps_to_exact_local_members_under_broader_permissions(reference):
    branches = broad()
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=100)
    plans = PartitionPlans(request=branches.request, limits=limits.sequence_space_limits)
    route = reference.realizations[0]
    addresses = addresses_for_preparation(
        result=reference, preparation=route, branches=branches, limits=limits, partitions=plans
    )
    assert addresses
    assert len(addresses) == 1  # Other annealing minima resolve different adapter orders.
    for address in addresses:
        assert branches.request.targets.pair_at(address.target) == ("AGTC", "AGTC")
        assert address.source_context == "ACGTACAGTCGTAC"
        product = branches.product(
            address.target,
            branch=address.context_rank * branches.geometry_count + address.geometry_rank,
            limits=limits,
        )
        selected = plans.get(product).product(product, address.page).construction_source()
        foldback = json.loads(_discover_request(selected.foldback).json_bytes)["realizations"]
        basal = json.loads(_discover_request(selected.basal).json_bytes)["realizations"]
        assert route.foldback_authority.source_reference_sequence in {
            f["source_reference_sequence"] for f in foldback
        }
        assert route.basal_authority.source_precursor_sequence in {
            b["source_precursor_sequence"] for b in basal
        }
        assert len(address.materials) == 6
    assert addresses == addresses_for_preparation(
        result=reference, preparation=route, branches=branches, limits=limits, partitions=plans
    )


@pytest.mark.parametrize(
    "change", ["payload", "ends", "gap", "context", "orientation", "adapter", "primer", "catalog"]
)
def test_out_of_scope_reference_is_not_coerced_into_request(reference, change):
    document = survey_document()
    if change == "payload":
        document["stem_arm"] = "A" * len(document["stem_arm"])
    elif change == "ends":
        document["targets"] = {"left_words": ["AAAA"], "right_words": ["AAAA"]}
    elif change == "gap":
        document["placements"] = [{"left_bp": 0, "right_bp": 0}]
    elif change == "orientation":
        document["interfaces"]["left"]["orientation"] = "reverse"
    elif change == "adapter":
        document["materialization"]["endpoint_auxiliaries"]["adapter"][
            "three_prime_handle_sequence"
        ] = "ACACACACACACAC"
    elif change == "primer":
        document["materialization"]["endpoint_auxiliaries"]["forward_primer"].update(
            min_annealing_length_nt=13, max_annealing_length_nt=13
        )
    elif change == "catalog":
        missing = "example:enzyme/nt.bpu10i@1"
        document["enzyme_catalog"]["enzymes"] = [
            enzyme
            for enzyme in document["enzyme_catalog"]["enzymes"]
            if enzyme["enzyme_id"] != missing
        ]
        document["foldback"]["enzymes"].update(allowed_enzyme_ids=[], role_restrictions=[])
    branches = broad(document)
    if change == "context":
        data = branches.request.model_dump(mode="json", by_alias=True)
        data["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
            "C" * 14
        )
        branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(data)))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=100)
    with pytest.raises(PreferenceOutOfScope):
        addresses_for_preparation(
            result=reference,
            preparation=reference.realizations[0],
            branches=branches,
            limits=limits,
            partitions=PartitionPlans(
                request=branches.request, limits=limits.sequence_space_limits
            ),
        )
