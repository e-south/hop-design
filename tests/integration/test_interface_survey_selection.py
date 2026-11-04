"""One exact query-bound selection drives CLI, atlas, and preparation retrieval."""

import json

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from tests.support.interface_surveys import indexed_survey


@pytest.fixture
def indexed_choices(tmp_path):
    return indexed_survey(tmp_path)


def test_selected_trace_roundtrips_through_atlas_and_handoff(indexed_choices, tmp_path):
    request, index = indexed_choices
    pool = construction.load_interface_survey_choices(request, index)
    query = {"parameters": [{"key": "left_end_word", "values": ["AGTC"]}]}
    path = pool.query(query)["paths"][0]
    selected = pool.select(
        **path["address"],
        materialized_realization_id=path["materialized_realization_id"],
        query=query,
    )
    assert selected["query"] == pool.query(query)["query"]
    assert selected["query_digest"] == pool.query(query)["query_digest"]
    assert selected["snapshot_digest"] == pool.query(query)["snapshot_digest"]
    assert selected["materialized_realization_id"] == path["materialized_realization_id"]
    packet = construction.inspect_interface_survey_atlas(request, index, selection=selected)
    assert isinstance(packet, construction.InterfaceSurveyAtlas)
    assert b'data-atlas="true"' in packet.svg_bytes
    assert json.loads(packet.json_bytes)["selection"] == selected
    output = tmp_path / "handoff"
    receipt = construction.retrieve_interface_survey_witness(
        request, index, selection=selected, destination=output
    )
    assert receipt.materialized_realization_ids == (selected["materialized_realization_id"],)
    assert json.loads((output / "selection.json").read_text()) == selected


def test_sampling_chooses_eligible_complete_records_without_evaluation(indexed_choices):
    request, index = indexed_choices
    pool = construction.load_interface_survey_choices(request, index)
    before = index.read_bytes()
    selected = pool.sample(seed=23)
    assert selected == pool.sample(seed=23)
    assert (
        selected["materialized_realization_id"]
        == pool.query()["paths"][0]["materialized_realization_id"]
    )
    assert index.read_bytes() == before
    missing = {"parameters": [{"key": "left_end_word", "values": ["TGCA"]}]}
    with pytest.raises(ValueError, match="No complete preparation matches"):
        pool.sample(seed=23, query=missing)
    with pytest.raises(ValueError, match="does not satisfy"):
        pool.select(
            **selected["address"],
            materialized_realization_id=selected["materialized_realization_id"],
            query=missing,
        )
    with pytest.raises(ValueError):
        pool.sample(seed=True)


@pytest.mark.parametrize(
    "field", ["materialized_realization_id", "request_digest", "query_digest", "record_digest"]
)
def test_changed_selection_fails_before_handoff_publication(indexed_choices, tmp_path, field):
    request, index = indexed_choices
    selected = construction.load_interface_survey_choices(request, index).sample(seed=0)
    selected[field] = (
        "sha256:" + "0" * 64 if field != "materialized_realization_id" else "wrong-identity"
    )
    output = tmp_path / "absent" / "handoff"
    with pytest.raises(ValueError):
        construction.retrieve_interface_survey_witness(
            request, index, selection=selected, destination=output
        )
    assert not output.exists()


def test_selection_survives_append_but_does_not_claim_the_new_snapshot(indexed_choices, tmp_path):
    request, index = indexed_choices
    pool = construction.load_interface_survey_choices(request, index)
    selected = pool.sample(seed=0)
    construction.evaluate_interface_survey(
        request,
        index,
        max_evaluations=1,
        local_nodes=100,
        local_realizations=16,
        release_site_pairs=100,
        resume=True,
    )
    assert (
        construction.load_interface_survey_choices(request, index).query()["snapshot_digest"]
        != selected["snapshot_digest"]
    )
    receipt = construction.retrieve_interface_survey_witness(
        request, index, selection=selected, destination=tmp_path / "after"
    )
    assert selected["materialized_realization_id"] in receipt.materialized_realization_ids


def test_cli_sample_and_select_use_the_same_selection_document(indexed_choices, tmp_path):
    request, index = indexed_choices
    pool = construction.load_interface_survey_choices(request, index)
    expected = pool.sample(seed=23)
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["construction", "survey", "sample", str(request), "--index", str(index), "--seed", "23"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == expected
    explicit = runner.invoke(
        app,
        [
            "construction",
            "survey",
            "select",
            str(request),
            "--index",
            str(index),
            "--target",
            str(expected["address"]["target"]),
            "--step",
            str(expected["address"]["step"]),
            "--identity",
            expected["materialized_realization_id"],
        ],
    )
    assert explicit.exit_code == 0, explicit.output
    assert json.loads(explicit.output) == expected
    path = tmp_path / "selection.json"
    path.write_text(result.output)
    atlas = runner.invoke(
        app,
        [
            "construction",
            "survey",
            "atlas",
            str(request),
            "--index",
            str(index),
            "--selection",
            str(path),
            "--out",
            str(tmp_path / "atlas"),
        ],
    )
    assert atlas.exit_code == 0, atlas.output
    handoff = runner.invoke(
        app,
        [
            "construction",
            "survey",
            "retrieve",
            str(request),
            "--index",
            str(index),
            "--selection",
            str(path),
            "--out",
            str(tmp_path / "selected"),
        ],
    )
    assert handoff.exit_code == 0, handoff.output
    assert json.loads(handoff.output)["witnesses"] == [expected["materialized_realization_id"]]


def test_rehashed_false_coordinates_cannot_satisfy_a_selected_query(indexed_choices, tmp_path):
    from tests.integration.test_interface_survey_integrity import mutate

    request, index = indexed_choices
    mutate(request, index, lambda row: row["projections"][0]["values"].update(left_end_word="TGCA"))
    query = {"parameters": [{"key": "left_end_word", "values": ["TGCA"]}]}
    selected = construction.load_interface_survey_choices(request, index).sample(
        seed=0, query=query
    )
    with pytest.raises(ValueError, match="plotting facts"):
        construction.retrieve_interface_survey_witness(
            request, index, selection=selected, destination=tmp_path / "false"
        )
    assert not (tmp_path / "false").exists()


def test_selected_query_parameters_remain_in_the_teaching_projection(indexed_choices):
    request, index = indexed_choices
    query = {"parameters": [{"key": "loop_side_paired_bp", "values": [6]}]}
    selected = construction.load_interface_survey_choices(request, index).sample(
        seed=0, query=query
    )
    packet = construction.inspect_interface_survey_atlas(request, index, selection=selected)
    summary = json.loads(packet.json_bytes)
    parameters = {p["key"]: p for p in summary["teaching"]["parameters"]}
    assert parameters["loop_side_paired_bp"]["value"] == 6
