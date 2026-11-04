"""A declared cleanup admits additional nick sites only with an exact survivor proof."""

import json
import shutil

import pytest

from hop_design import construction
from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document


def cleanup_intent(*, maximum=None):
    context = survey_document()
    stem = context.pop("stem_arm")
    context.pop("targets")
    context.pop("name", None)
    context.update(
        schema="hop.construction-context/v1",
        context_id="source-cleanup-example",
        description="Two repeated basal nick sites in disposable source context.",
        product="released_insert",
        source_context_objective="all_words",
    )
    context["placements"] = [{"left_bp": 6, "right_bp": 6}]
    context["basal"]["annealing_lengths_nt"] = [17]
    context["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "GCAATGGCAATGAC"
    )
    if maximum is not None:
        context["source_cleanup"] = {
            "preferred_maximum_nt": maximum,
            "absolute_maximum_nt": maximum,
        }
    return {
        "stem_arm": stem,
        "product": "released_insert",
        "ends": {"left": "AGTC", "right": "AGTC"},
        "context": context,
    }


def test_discovery_reuses_source_partition_verification_for_permitted_cleanup(tmp_path):
    effort = {"local_nodes": 100, "local_realizations": 16, "release_site_pairs": 100}
    missing = construction.discover_designs(
        cleanup_intent(),
        tmp_path / "missing",
        max_evaluations=1,
        effort=effort,
    )
    allowed = construction.discover_designs(
        cleanup_intent(maximum=24),
        tmp_path / "allowed",
        max_evaluations=1,
        effort=effort,
    )
    assert not missing.query()["paths"]
    assert allowed.query()["paths"]
    selected = allowed.sample(seed=1)
    verified = allowed.retrieve(selected, tmp_path / "preparation")
    result = verified._verified_source().result
    partition = result.source_partition_authority
    assert partition is not None
    program = next(
        item
        for item in partition.realizations
        if item.realization_id == result.provenance.source_partition_realization_id
    )
    route = next(
        r
        for r in result.realizations
        if r.materialized_realization_id == selected["materialized_realization_id"]
    )
    foldback = next(
        r
        for r in result.foldback_authority.realizations
        if r.foldback_realization_id == route.foldback_realization_id
    )
    basal = next(
        r
        for r in result.basal_authority.realizations
        if r.basal_realization_id == route.basal_realization_id
    )
    expected = {binding.enzyme_id for binding in foldback.enzyme_bindings}
    expected.add(basal.basal_nick.enzyme_id)
    assert set(program.enzyme_ids) == expected
    assert all(item.source_partition_binding is not None for item in result.realizations)
    atlas = json.loads(allowed.atlas(selected).json_bytes)
    parameters = {p["key"]: p for p in atlas["teaching"]["parameters"]}
    assert parameters["basal_method"]["coverage"] == "located"
    assert parameters["foldback_method"]["coverage"] == "located"
    source_operations = [
        op
        for state in atlas["atlas"]["states"]
        for op in state["operations"]
        if op["timing"] == "planned" and op["role"] != "end_generation"
    ]
    assert [op["role"] for op in source_operations].count("basal_nick") == 1
    assert [op["role"] for op in source_operations].count("foldback_nick") == 1
    assert [op["role"] for op in source_operations].count("strand_exposure") == 2
    relocated = tmp_path / "relocated"
    shutil.copytree(tmp_path / "allowed", relocated)
    loaded = construction.load_design_choices(relocated)
    assert loaded.sample(seed=1) == selected
    after = loaded.find_more(max_evaluations=1)
    assert after.resolution == allowed.resolution
    assert selected["materialized_realization_id"] in {
        p["materialized_realization_id"] for p in after.query()["paths"]
    }


@pytest.mark.parametrize("maximum", [1, 5])
def test_cleanup_cannot_discard_fragments_larger_than_the_permission(maximum, tmp_path):
    choices = construction.discover_designs(
        cleanup_intent(maximum=maximum),
        tmp_path / "designs",
        max_evaluations=1,
        effort={"local_nodes": 100, "local_realizations": 16, "release_site_pairs": 100},
    )
    assert not choices.query()["paths"]


def test_reversed_source_cleanup_returns_replayable_outcomes_instead_of_aborting(tmp_path):
    intent = cleanup_intent(maximum=24)
    intent["context"]["foldback"]["geometry"]["nick_strand"] = "bottom"
    root = tmp_path / "reversed"
    choices = construction.discover_designs(
        intent,
        root,
        max_evaluations=4,
        effort={"local_nodes": 100, "local_realizations": 16, "release_site_pairs": 100},
    )
    verified = construction.verify_interface_survey(
        root / "intent/request.json", root / "survey.sqlite"
    )
    assert verified["replayed_evaluations"] > 0
    assert verified["coverage"] == choices.query()["coverage"]


@pytest.mark.parametrize("obstruction", ["payload_cut", "primer_footprint"])
def test_cleanup_does_not_waive_other_molecular_requirements(obstruction, tmp_path):
    intent = cleanup_intent(maximum=24)
    if obstruction == "payload_cut":
        intent["stem_arm"] = "GCAATG" + intent["stem_arm"][6:]
    else:
        intent["context"]["materialization"]["source_preparation"]["forward_primer"][
            "annealing_length_nt"
        ] = 500
    choices = construction.discover_designs(
        intent,
        tmp_path / "designs",
        max_evaluations=1,
        effort={"local_nodes": 100, "local_realizations": 16, "release_site_pairs": 100},
    )
    assert not choices.query()["paths"]


def _product(intent):
    resolved = json.loads(construction.resolve_design_request(intent).json_bytes)
    survey = InterfaceSurveyRequest.model_validate_json(json.dumps(resolved["effective_request"]))
    return SurveyBranches(survey).product(
        0,
        branch=0,
        limits=SurveyEvaluationLimits(
            local_nodes=100, local_realizations=16, release_site_pairs=100
        ),
    )


def test_request_execution_uses_same_cleanup_owner_and_rejects_multiple_contexts(tmp_path):
    product = _product(cleanup_intent(maximum=24))
    request = tmp_path / "request.json"
    request.write_text(product.model_dump_json(by_alias=True))
    prepared = construction.prepare_construction_request(request)
    inputs = prepared.write(tmp_path / "inputs")
    selected = {}
    for family in ("foldback", "basal"):
        receipt = construction.discover_local_neighborhood(inputs / f"{family}.json")
        path = receipt.write(tmp_path / family) / "result.json"
        selected[f"{family}_path"] = path
        selected[f"{family}_realization_id"] = construction.list_local_realizations(receipt)[
            0
        ].realization_id
    execution = construction.continue_construction_request(
        request,
        design_id="cleanup-request",
        **selected,
    )
    assert execution._compilation.materialized_realization_ids
    assert execution._compilation._verified_source().result.source_partition_authority is not None
    document = product.model_dump(mode="json", by_alias=True)
    document["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] += (
        "N"
    )
    # A one-combination execution quota must not conceal the broader molecular domain.
    document["enumeration"]["max_combinations"] = 1
    request.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="exact source context"):
        construction.continue_construction_request(request, design_id="cleanup-broad", **selected)
