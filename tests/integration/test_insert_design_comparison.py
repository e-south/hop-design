"""Insert choices preserve the requested stage and retrieve explicit comparative membership."""

import csv
import json
import shutil

import pytest

from hop_design import construction
from tests.integration.test_design_discovery import intent_document
from tests.integration.test_design_diversity import diverse_intent


@pytest.fixture(scope="module")
def insert_choices(tmp_path_factory):
    return construction.discover_designs(
        diverse_intent(),
        tmp_path_factory.mktemp("insert-comparison") / "choices",
        max_evaluations=16,
        objective={"kind": "diversity", "parameters": ["loop_nt"]},
    )


def test_preserved_insert_query_drives_plot_selection_and_retrieval(insert_choices, tmp_path):
    choices = insert_choices
    reference = choices.sample(seed=0, query={"parameters": [{"key": "loop_nt", "values": [4]}]})
    query = choices.preserve(reference, stage="endpoint", except_neighborhood="loop")
    answer = choices.query(query)
    assert answer["matching_preparations"] >= 2
    assert answer["query"]["surroundings"]["stage"] == "endpoint"
    assert sum(p["matches"] for p in answer["paths"]) == answer["matching_records"]
    selected = choices.sample(seed=1, query=query)
    assert selected["query"] == answer["query"]
    assert (
        json.loads(choices.figure(query=query, selection=selected).json_bytes)["paths"]
        == answer["paths"]
    )
    files = dict(choices.figure(query=query, selection=selected)._files)
    assert {"parameter-key.svg", "parameter-key.json", "plot.svg", "query.json"} <= files.keys()
    atlas = json.loads(choices.atlas(selected).json_bytes)
    assert (
        json.loads(files["teaching.json"])["materialized_realization_id"]
        == selected["materialized_realization_id"]
    )
    assert b'data-teaching-resolution="every-base"' in files["figure.svg"]
    locations = {location["key"]: location for location in atlas["parameter_locations"]}
    arm = locations["foldback_arm_bp"]
    assert arm["definition"]["canonical_key"] == "foldback_arm_bp"
    assert arm["reference_addresses"] == locations["loop_side_paired_bp"]["reference_addresses"]
    for key in ("loop_nt", "foldback_arm_bp", "left_gap", "right_gap"):
        assert locations[key]["boundary_anchors"]
        assert locations[key]["definition"]["design_role"] == "product"
    receipt = choices.retrieve(selected, tmp_path / "selected")
    assert selected["materialized_realization_id"] in receipt.materialized_realization_ids
    assert json.loads((tmp_path / "selected/design-selection.json").read_bytes()) == selected
    wrong = {**query, "reference": {**query["reference"], "snapshot_digest": "sha256:" + "0" * 64}}
    with pytest.raises(ValueError, match="snapshot"):
        choices.query(wrong)


def test_required_insert_comparison_is_not_an_allowed_alternative(insert_choices, tmp_path):
    request = {
        "stage": "endpoint",
        "required_members": [
            {"name": "loop4", "dimensions": {"loop_nt": 4}},
            {"name": "loop5", "dimensions": {"loop_nt": 5}},
        ],
        "stage_controls": [{"property": "non_loop_sequences", "stage": "endpoint", "scope": "set"}],
        "max_group_evaluations": 64,
    }
    comparison = insert_choices.compare(request)
    assert comparison["sets"]
    chosen = insert_choices.select_set(
        comparison, set_label=comparison["sets"][0]["label"], baseline="loop4"
    )
    receipt = insert_choices.retrieve(chosen, tmp_path / "set")
    assert len(receipt.materialized_realization_ids) == 2
    assert set(chosen["members"]) == {"loop4", "loop5"}
    assert (tmp_path / "set/design-selection.json").is_file()
    report = (tmp_path / "set/report.md").read_text()
    assert "released insert" in report
    assert "sequences outside the loop-derived region" in report
    assert "oligos.csv" in report and "oligo-uses.csv" in report
    orders = list(csv.DictReader((tmp_path / "set/oligos.csv").open()))
    uses = list(csv.DictReader((tmp_path / "set/oligo-uses.csv").open()))
    assert {u["member"] for u in uses} == {"loop4", "loop5"}
    assert len(uses) == 12
    assert {u["material_id"] for u in uses} == {o["material_id"] for o in orders}
    assert len(
        {(o["sequence_5prime"], o["five_prime_end"], o["three_prime_end"]) for o in orders}
    ) == len(orders)
    for name in chosen["members"]:
        assert (tmp_path / f"set/members/{name}/views/teaching.svg").is_file()
        assert (tmp_path / f"set/members/{name}/views/projection.svg").is_file()
    missing = insert_choices.compare(
        {**request, "required_members": [{"name": "loop9", "dimensions": {"loop_nt": 9}}]}
    )
    assert missing["sets"] == []
    assert missing["missing_members"][0]["reason"] == "not_observed_in_evaluated_pool"
    edited = json.loads(json.dumps(chosen))
    edited["members"]["loop4"] = edited["members"]["loop5"]
    with pytest.raises(ValueError, match=r"membership|selection|disagree"):
        insert_choices.retrieve(edited, tmp_path / "tampered")
    assert not (tmp_path / "tampered").exists()
    shutil.copytree(insert_choices._directory, tmp_path / "relocated")
    continued = construction.load_design_choices(tmp_path / "relocated").find_more(
        max_evaluations=1
    )
    restored = continued.retrieve(chosen, tmp_path / "after-continuation")
    assert restored.materialized_realization_ids == receipt.materialized_realization_ids


def test_endpoint_preservation_keeps_discarded_hairpin_differences_out_of_the_control(tmp_path):
    request = intent_document()
    request["context"]["basal"]["annealing_lengths_nt"] = [17, 24]
    request["context"]["source_context_objective"] = "paired_scaffold_completions"
    choices = construction.discover_designs(
        request,
        tmp_path / "choices",
        max_evaluations=8,
        objective={"kind": "diversity", "parameters": ["adapter_annealing_min_nt"]},
    )
    reference = choices.sample(seed=0)
    hairpin = choices.query(
        choices.preserve(reference, stage="hairpin", except_neighborhood="loop")
    )
    endpoint = choices.query(
        choices.preserve(reference, stage="endpoint", except_neighborhood="loop")
    )
    assert hairpin["matching_preparations"] == 1
    assert endpoint["matching_preparations"] == 4
    assert endpoint["matching_products"] == {"hairpin": 4, "endpoint": 2}
    assert endpoint["search_objective"]["matching_classes"] == 2


def test_browser_uses_public_preservation_for_plot_preview_and_handoff(insert_choices, tmp_path):
    from hop_design.commands.design.browser import create_design_server

    choices = insert_choices
    query = choices.preserve(choices.sample(seed=0), stage="endpoint", except_neighborhood="loop")
    server = create_design_server(choices._directory, tmp_path / "browser")
    try:
        session = server.session
        state = session.state()
        state = session.query({"token": state["token"], "query": query})
        assert state["choices"]["paths"] == choices.query(query)["paths"]
        expected = choices.sample(
            seed=1,
            query=query,
            strategy=state["exploration"]["strategy"],
            stage=state["family_stage"],
            history=state["exploration"]["history"],
        )
        state = session.sample({"token": state["token"], "seed": 1})
        assert state["sample_receipt"] == expected
        assert state["selection"] == expected["selection"]
        assert state["preview"]["summary"]["selection"] == state["selection"]
        assert state["preview"]["summary"]["atlas"]["construction_cost"]["distinct_orders"] > 0
        state = session.retrieve({"token": state["token"], "selection": state["selection"]})
        selected_path = (
            tmp_path / "browser" / state["handoff"]["directory"] / "design-selection.json"
        )
        assert json.loads(selected_path.read_bytes()) == state["selection"]
    finally:
        server.server_close()
        server.session.close()


def test_duplicate_required_names_are_rejected_before_assessment(insert_choices):
    with pytest.raises(ValueError, match="names must be unique"):
        insert_choices.compare(
            {
                "stage": "endpoint",
                "required_members": [
                    {"name": "same", "dimensions": {"loop_nt": 4}},
                    {"name": "same", "dimensions": {"loop_nt": 5}},
                ],
                "max_group_evaluations": 8,
            }
        )
