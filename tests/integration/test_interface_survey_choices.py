"""Conditional plotting reads recorded complete paths without inventing joins or searches."""

import json
import sqlite3
from xml.etree import ElementTree as ET

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.design.construction.surveys.index import SurveyIndex
from tests.support.interface_surveys import indexed_survey, survey_selection


@pytest.fixture
def indexed_choices(tmp_path):
    return indexed_survey(tmp_path)


def test_choices_preserve_declared_unexamined_values_and_exact_witness_address(indexed_choices):
    path, index = indexed_choices
    before = index.read_bytes()
    query = construction.query_interface_survey(path, index)
    assert index.read_bytes() == before
    assert query["coverage"]["target_pairs"] == 2
    assert query["coverage"]["supported_pairs"] == 1
    axes = {a["key"]: a for a in query["axes"]}
    assert {n["value"]: n["state"] for n in axes["left_end_word"]["nodes"]} == {
        "AGTC": "supported",
        "TGCA": "unresolved",
    }
    assert len(query["paths"]) == 1
    trace = query["paths"][0]
    assert trace["address"] == {"target": 0, "step": 0}
    assert trace["values"]["left_gap"] == trace["values"]["right_gap"] == 6
    assert trace["values"]["foldback_arm_bp"] == 6
    assert trace["values"]["join_offset_nt"] == 2
    assert trace["values"]["self_paired_arm_bp"] == 4
    assert trace["values"]["loop_nt"] == 4
    assert len(trace["values"]["loop_word"]) == 4
    assert trace["overhead"]["ordered_unique_oligo_nt"] > trace["overhead"]["hairpin_non_stem_nt"]
    assert {"hairpin", "endpoint"} == set(trace["molecular_identity"])
    assert not list(index.parent.rglob("*.svg"))
    receipt = construction.retrieve_interface_survey_witness(
        path,
        index,
        selection=survey_selection(path, index, **trace["address"]),
        destination=index.parent / "selected",
    )
    assert trace["materialized_realization_id"] in receipt.materialized_realization_ids


def test_filtering_keeps_supported_context_and_does_not_reclassify_missing_witnesses(
    indexed_choices,
):
    path, index = indexed_choices
    query = construction.query_interface_survey(
        path,
        index,
        {
            "schema": "hop.interface-survey-query/v1",
            "parameters": [{"key": "right_end_word", "values": ["TGCA"]}],
        },
    )
    assert query["matching_preparations"] == 0
    assert len(query["paths"]) == 1 and not query["paths"][0]["matches"]
    left = next(a for a in query["axes"] if a["key"] == "left_end_word")
    assert {n["value"]: n["state"] for n in left["nodes"]} == {
        "AGTC": "supported_elsewhere",
        "TGCA": "unresolved",
    }
    assert query["coverage"]["supported_pairs"] == 1


def test_unknown_axes_and_duplicate_selections_fail_in_the_shared_parameter_contract(
    indexed_choices,
):
    path, index = indexed_choices
    with pytest.raises(ValueError, match="Unknown molecular parameter"):
        construction.query_interface_survey(
            path,
            index,
            {
                "schema": "hop.interface-survey-query/v1",
                "parameters": [{"key": "free_bases", "values": [1]}],
            },
        )


def test_query_cli_matches_api_without_creating_a_new_evaluation(indexed_choices):
    path, index = indexed_choices
    before = index.read_bytes()
    result = CliRunner().invoke(
        app, ["construction", "survey", "query", str(path), "--index", str(index)]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == construction.query_interface_survey(path, index)
    assert index.read_bytes() == before


def test_complete_survey_path_projects_exact_atlas_without_new_search(indexed_choices):
    path, index = indexed_choices
    trace = construction.query_interface_survey(path, index)["paths"][0]
    before = index.read_bytes()
    packet = construction.inspect_interface_survey_atlas(
        path,
        index,
        selection=survey_selection(path, index, **trace["address"]),
    )
    result = json.loads(packet.json_bytes)
    assert index.read_bytes() == before
    assert not list(index.parent.rglob("*.svg"))
    assert result["address"] == trace["address"]
    atlas = result["atlas"]
    assert atlas["materialized_realization_id"] == trace["materialized_realization_id"]
    assert len(atlas["states"]) == 11
    assert len(atlas["transitions"]) == 10
    assert len(atlas["inputs"]) == 5  # Four primers and the adapter.
    assert result["projection"]["molecular_identity"] == trace["molecular_identity"]
    assert all(result["projection"]["values"][k] == v for k, v in trace["values"].items())
    svg = ET.fromstring(packet.svg_bytes)
    bases = [e for e in svg.iter() if "data-base-index" in e.attrib]
    assert len(bases) == sum(len(s["bases"]) for s in atlas["states"])
    parameters = {p["key"]: p for p in result["teaching"]["parameters"]}
    assert parameters["left_end_word"]["value"] == parameters["right_end_word"]["value"] == "AGTC"
    assert parameters["foldback_arm_bp"]["value"] == 6
    assert parameters["self_paired_arm_bp"]["value"] == 4
    assert result["teaching"]["context"]["joint_placements"] == [{"left_bp": 6, "right_bp": 6}]
    packet.write(index.parent / "atlas")
    assert (index.parent / "atlas" / "teaching.svg").is_file()


def test_survey_atlas_rejects_mismatched_selected_identity(indexed_choices):
    path, index = indexed_choices
    selected = survey_selection(path, index, 0, 0)
    selected["materialized_realization_id"] = "not-the-selected-route"
    with pytest.raises(ValueError, match="identity"):
        construction.inspect_interface_survey_atlas(path, index, selection=selected)


def test_survey_atlas_cli_matches_api(indexed_choices):
    path, index = indexed_choices
    trace = construction.query_interface_survey(path, index)["paths"][0]
    output = index.parent / "cli-atlas"
    selection_path = index.parent / "selection.json"
    selection_path.write_text(json.dumps(survey_selection(path, index, **trace["address"])))
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "survey",
            "atlas",
            str(path),
            "--index",
            str(index),
            "--selection",
            str(selection_path),
            "--out",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    packet = construction.inspect_interface_survey_atlas(
        path,
        index,
        selection=survey_selection(path, index, **trace["address"]),
    )
    assert (output / "summary.json").read_bytes() == packet.json_bytes
    assert (output / "projection.svg").read_bytes() == packet.svg_bytes


def test_admitted_choices_preserve_snapshot_and_do_not_reopen_index(indexed_choices):
    request, index = indexed_choices
    pool = construction.load_interface_survey_choices(request, index)
    original = pool.query()
    assert original == construction.query_interface_survey(request, index)
    assert original["snapshot_digest"].startswith("sha256:")
    index.rename(index.with_suffix(".moved"))
    request.unlink()
    choices = pool.query({"parameters": [{"key": "right_end_word", "values": ["TGCA"]}]})
    assert choices["matching_preparations"] == 0
    assert choices["snapshot_digest"] == original["snapshot_digest"]
    assert choices["coverage"] == original["coverage"]
    choices["paths"].clear()
    choices["context"]["joint_placements"].clear()
    assert pool.query() == original


@pytest.mark.parametrize("invalid", [False, 0, []])
def test_admitted_choices_reject_falsey_nonobject_queries(indexed_choices, invalid):
    request, index = indexed_choices
    pool = construction.load_interface_survey_choices(request, index)
    with pytest.raises(ValueError):
        pool.query(invalid)


def test_admission_cannot_mix_a_concurrent_append_with_earlier_coordinates(
    indexed_choices,
    monkeypatch,
):
    request, path = indexed_choices
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
    before = construction.query_interface_survey(request, path)
    iterate = SurveyIndex.evaluations
    appended = False

    def concurrent(index, **kwargs):
        nonlocal appended
        for row in iterate(index, **kwargs):
            yield row
            if not appended:
                appended = True
                construction.evaluate_interface_survey(
                    request,
                    path,
                    max_evaluations=1,
                    local_nodes=100,
                    local_realizations=16,
                    release_site_pairs=100,
                    resume=True,
                )

    monkeypatch.setattr(SurveyIndex, "evaluations", concurrent)
    snapshot = construction.load_interface_survey_choices(request, path).query()
    assert appended
    assert snapshot == before
    after = construction.query_interface_survey(request, path)
    assert after["snapshot_digest"] != before["snapshot_digest"]
