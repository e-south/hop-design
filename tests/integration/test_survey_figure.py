"""Portable figures share exact query semantics and the browser drawing."""

import csv
import io
import json
from xml.etree import ElementTree as ET

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.commands.construction.editor.surveys import SurveySession
from hop_design.export.construction.survey.plot import render_survey_plot
from tests.support.interface_surveys import indexed_survey


def test_figure_contains_every_domain_and_does_not_require_selection(tmp_path):
    request, index = indexed_survey(tmp_path)
    pool = construction.load_interface_survey_choices(request, index)
    original = index.read_bytes()
    assert pool.plot_svg_bytes() == render_survey_plot(pool.query())
    packet = pool.figure()
    folder = packet.write(tmp_path / "figure")
    assert (folder / "plot.svg").read_bytes() == render_survey_plot(pool.query())
    assert (folder / "parameter-key.svg").read_bytes() == pool.parameter_key_svg_bytes
    assert (folder / "figure.pdf").read_bytes().startswith(b"%PDF")
    assert json.loads((folder / "choices.json").read_bytes()) == pool.query()
    rows = list(csv.DictReader(io.StringIO((folder / "domains.csv").read_text())))
    assert len(rows) == sum(len(a["nodes"]) for a in pool.query()["axes"])
    assert {r["value"] for r in rows if r["key"] == "left_end_word"} == {"AGTC", "TGCA"}
    methods = [r for r in rows if r["key"] == "release_method"]
    assert methods and methods[0]["label"] == "BsaI-HFv2"
    assert methods[0]["display"] == "BsaI-HFv2"
    assert not (folder / "selection.json").exists()
    assert index.read_bytes() == original
    with pytest.raises(FileExistsError):
        packet.write(folder)


def test_selected_figure_and_cli_keep_the_exact_query_bound_identity(tmp_path):
    request, index = indexed_survey(tmp_path)
    pool = construction.load_interface_survey_choices(request, index)
    query = {"parameters": [{"key": "left_end_word", "values": ["AGTC"]}]}
    selected = pool.sample(seed=1, query=query)
    selection_file = tmp_path / "selection.json"
    selection_file.write_text(json.dumps(selected))
    expected = pool.figure(selection=selected).write(tmp_path / "api")
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "survey",
            "query",
            str(request),
            "--index",
            str(index),
            "--selection",
            str(selection_file),
            "--out",
            str(tmp_path / "cli"),
        ],
    )
    assert result.exit_code == 0, result.output

    def files(root):
        return {
            path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()
        }

    assert files(tmp_path / "cli") == files(expected)
    assert json.loads((expected / "selection.json").read_text()) == selected
    with pytest.raises(ValueError, match=r"selection|Selection"):
        pool.figure(query={}, selection=selected)
    corrupted = {**selected, "snapshot_digest": "sha256:" + "0" * 64}
    with pytest.raises(ValueError, match=r"selection|Selection"):
        pool.figure(selection=corrupted)


def test_browser_uses_the_static_plot_for_initial_selected_and_excluded_views(tmp_path):
    request, index = indexed_survey(tmp_path)
    session = SurveySession(request, index, tmp_path / "browser")
    state = session.state()
    assert state["plot_svg"].encode() == render_survey_plot(state["choices"])
    state = session.sample({"token": state["token"], "seed": 1})
    identity = state["selection"]["materialized_realization_id"]
    assert state["plot_svg"].encode() == render_survey_plot(
        state["choices"],
        selected_identity=identity,
    )
    state = session.query(
        {
            "token": state["token"],
            "query": {
                "parameters": [{"key": "left_end_word", "values": ["TGCA"]}],
            },
        }
    )
    assert state["selection"] is None
    assert state["plot_svg"].encode() == render_survey_plot(
        state["choices"],
        selected_identity=identity,
    )
    drawing = ET.fromstring(state["plot_svg"])
    assert not any(e.get("data-brush-axis") == "left_gap" for e in drawing.iter())


def test_path_query_is_admitted_once_before_selection_and_drawing(tmp_path, monkeypatch):
    from hop_design.design.construction.surveys import selection as selection_module

    request, index = indexed_survey(tmp_path)
    pool = construction.load_interface_survey_choices(request, index)
    first = {"parameters": [{"key": "left_end_word", "values": ["AGTC"]}]}
    second = {"parameters": [{"key": "left_end_word", "values": ["TGCA"]}]}
    selected = pool.sample(seed=1, query=first)
    calls = []

    def changing_query(path):
        calls.append(path)
        return first if len(calls) == 1 else second

    monkeypatch.setattr(selection_module, "load_source_mapping", changing_query)
    packet = pool.figure(tmp_path / "query.json", selection=selected)
    folder = packet.write(tmp_path / "figure")
    assert len(calls) == 1
    assert json.loads((folder / "query.json").read_text()) == selected["query"]
    assert json.loads((folder / "choices.json").read_text())["matching_preparations"] == 1
