"""Two exact survey selections expose molecular and preparation consequences."""

import json
from xml.etree import ElementTree as ET

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from tests.unit.test_interface_survey_request import survey_document


@pytest.fixture(scope="module")
def two_loop_survey(tmp_path_factory):
    root = tmp_path_factory.mktemp("survey-comparison")
    document = survey_document()
    document["targets"] = {"left_words": ["AGTC"], "right_words": ["AGTC"]}
    document["placements"] = [{"left_bp": 6, "right_bp": 6}]
    document["basal"]["annealing_lengths_nt"] = [17]
    document["foldback"]["geometry"].update(
        annealing_arm_lengths_bp=[9], loop_sequences=["GAAA", "TTTC"]
    )
    document["foldback"]["max_retained_overhead_nt"] = 32
    request, index = root / "request.json", root / "index.sqlite"
    request.write_text(json.dumps(document))
    construction.evaluate_interface_survey(
        request,
        index,
        max_evaluations=4,
        local_nodes=100,
        local_realizations=100,
        release_site_pairs=100,
    )
    pool = construction.load_interface_survey_choices(request, index)
    selections = {}
    for word in ("GAAA", "TTTC"):
        path = next(p for p in pool.query()["paths"] if p["values"]["loop_word"] == word)
        selections[word] = pool.select(
            **path["address"], materialized_realization_id=path["materialized_realization_id"]
        )
    return request, index, selections


def test_survey_comparison_keeps_both_selections_and_exact_changes(two_loop_survey):
    request, index, selections = two_loop_survey
    before = index.read_bytes()
    packet = construction.inspect_interface_survey_atlas(
        request, index, selection=selections["TTTC"], reference_selection=selections["GAAA"]
    )
    summary = json.loads(packet.json_bytes)
    assert summary["selection"] == selections["TTTC"]
    assert summary["reference_selection"] == selections["GAAA"]
    comparison = summary["comparison"]
    loop = next(r for r in comparison["regions"] if r["region"] == "loop")
    assert (loop["reference_sequence"], loop["observed_sequence"]) == ("GAAA", "TTTC")
    assert len(loop["columns"]) == 4
    assert all(c["kind"] == "substitution" for c in loop["columns"])
    assert all(
        r["reference_sequence"] == r["observed_sequence"]
        for r in comparison["regions"]
        if r["region"] != "loop"
    )
    assert set(comparison["material_roles"]) == {
        "source_ssdna",
        "source_materialization_reverse_primer",
    }
    assert len(comparison["endpoint_regions"]) == 2
    assert all(
        r["reference_sequence"] != r["observed_sequence"] for r in comparison["endpoint_regions"]
    )
    assert {m["role"] for m in comparison["materials"]} == set(comparison["material_roles"])
    assert all(
        m["reference"]["sequence_5prime"] != m["observed"]["sequence_5prime"]
        for m in comparison["materials"]
    )
    addresses = {
        (s["state"]["state_id"], m["strand_id"], i): base
        for s in summary["atlas"]["states"]
        for m in s["state"]["molecules"]
        for i, base in enumerate(m["sequence"])
    }
    for change in comparison["substitutions"]:
        a = change["address"]
        assert addresses[a["state_id"], a["strand_id"], a["index"]] == change["observed_base"]
        assert change["reference_base"] != change["observed_base"]
    svg = ET.fromstring(packet.svg_bytes)
    assert any(e.attrib.get("data-change") == "substitution" for e in svg.iter())
    assert b"Loop comparison:" not in packet.svg_bytes
    assert json.loads(dict(packet._files)["reference-selection.json"]) == selections["GAAA"]
    assert index.read_bytes() == before


@pytest.mark.parametrize("side", ["selection", "reference_selection"])
def test_either_corrupt_selection_rejects_before_publication(two_loop_survey, side):
    request, index, selections = two_loop_survey
    values = {
        "selection": dict(selections["TTTC"]),
        "reference_selection": dict(selections["GAAA"]),
    }
    values[side]["record_digest"] = "sha256:" + "0" * 64
    before = index.read_bytes()
    with pytest.raises(ValueError):
        construction.inspect_interface_survey_atlas(request, index, **values)
    assert index.read_bytes() == before


def test_comparison_cli_is_the_same_public_operation(two_loop_survey, tmp_path):
    request, index, selections = two_loop_survey
    paths = {}
    for word, selection in selections.items():
        paths[word] = tmp_path / (word + ".json")
        paths[word].write_text(json.dumps(selection))
    expected = construction.inspect_interface_survey_atlas(
        request, index, selection=paths["TTTC"], reference_selection=paths["GAAA"]
    )
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "survey",
            "atlas",
            str(request),
            "--index",
            str(index),
            "--selection",
            str(paths["TTTC"]),
            "--reference-selection",
            str(paths["GAAA"]),
            "--out",
            str(tmp_path / "atlas"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "atlas/summary.json").read_bytes() == expected.json_bytes
    assert (tmp_path / "atlas/projection.svg").read_bytes() == expected.svg_bytes


def _select(session, selection):
    return session.select(
        {
            "token": session.state()["token"],
            **selection["address"],
            "materialized_realization_id": selection["materialized_realization_id"],
        }
    )


def test_browser_keeps_comparison_through_filtering_and_repeated_selection(
    two_loop_survey, tmp_path
):
    from hop_design.commands.construction.editor.surveys import SurveySession

    request, index, selections = two_loop_survey
    session = SurveySession(request, index, tmp_path / "browser")
    first = _select(session, selections["GAAA"])
    assert first["preview"]["summary"]["comparison"] is None
    second = _select(session, selections["TTTC"])
    reference = first["selection"]
    assert second["preview"]["summary"]["reference_selection"] == reference
    repeated = _select(session, selections["TTTC"])
    assert repeated["preview"] == second["preview"]
    filtered = session.query(
        {
            "token": repeated["token"],
            "query": {"parameters": [{"key": "loop_word", "values": ["TTTC"]}]},
        }
    )
    summary = filtered["preview"]["summary"]
    assert summary["selection"] == filtered["selection"]
    assert summary["reference_selection"] == reference
    expected = construction.inspect_interface_survey_atlas(
        request, index, selection=filtered["selection"], reference_selection=reference
    )
    assert summary == json.loads(expected.json_bytes)
    sampled = session.sample({"token": filtered["token"], "seed": 12})
    assert sampled["preview"]["summary"]["reference_selection"] == reference
    reloaded = session.reload({"token": sampled["token"]})
    assert reloaded["preview"] == sampled["preview"]
    restored = session.query({"token": reloaded["token"], "query": {}})
    returned = _select(session, selections["GAAA"])
    assert returned["preview"]["summary"]["reference_selection"] == restored["selection"]
    assert returned["preview"] != first["preview"]
    # Returning to the same target must not reuse its earlier no-reference drawing.
    loop = next(
        r for r in returned["preview"]["summary"]["comparison"]["regions"] if r["region"] == "loop"
    )
    assert (loop["reference_sequence"], loop["observed_sequence"]) == ("TTTC", "GAAA")


def test_browser_failed_comparison_retains_visible_preparation(
    two_loop_survey, tmp_path, monkeypatch
):
    from hop_design.commands.construction.editor.surveys import SurveySession

    request, index, selections = two_loop_survey
    session = SurveySession(request, index, tmp_path / "browser")
    before = _select(session, selections["GAAA"])

    def reject(*args, **kwargs):
        assert kwargs["reference_selection"] == before["selection"]
        raise ValueError("deliberate reference replay failure")

    monkeypatch.setattr(construction, "inspect_interface_survey_atlas", reject)
    with pytest.raises(ValueError, match="reference replay"):
        _select(session, selections["TTTC"])
    assert session.state() == before
