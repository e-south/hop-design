"""Declared molecular meanings exist before a complete preparation is selected."""

import json
from xml.etree import ElementTree as ET

from hop_design import construction
from tests.support.interface_surveys import indexed_survey


def test_request_key_is_selection_free_and_matches_query_vocabulary(tmp_path):
    request, index = indexed_survey(tmp_path)
    pool = construction.load_interface_survey_choices(request, index)
    before = index.read_bytes()
    choices = pool.query()
    key = pool.parameter_key()
    assert key["schema"] == "hop.parameter-definition-key/v1"
    assert key["request_digest"] == choices["request_digest"]
    assert {p["definition"]["key"] for p in key["parameters"]} == {
        a["key"] for a in choices["axes"]
    }
    parameters = {p["definition"]["key"]: p for p in key["parameters"]}
    assert parameters["left_end_word"]["domain"]["values"] == ["AGTC", "TGCA"]
    assert parameters["left_gap"]["definition"]["stage"] == "released_insert"
    assert parameters["self_paired_arm_bp"]["definition"]["relationship"] == "R = A - D"
    assert all(set(p) == {"definition", "domain"} for p in key["parameters"])
    assert "coverage" not in key and "materialized_realization_id" not in key
    pool.query({"parameters": [{"key": "left_end_word", "values": ["TGCA"]}]})
    assert pool.parameter_key() == key
    key["parameters"].clear()
    assert pool.parameter_key()["parameters"]
    assert index.read_bytes() == before


def test_definition_glyph_has_every_coarse_key_without_invented_measurements(tmp_path):
    request, index = indexed_survey(tmp_path)
    pool = construction.load_interface_survey_choices(request, index)
    key = pool.parameter_key()
    drawing = pool.parameter_key_svg_bytes
    svg = ET.fromstring(drawing)
    assert svg.attrib["data-schema"] == key["schema"]
    assert "selected" not in svg.attrib["aria-label"].lower()
    linked = {
        key
        for item in svg.iter()
        for key in json.loads(item.attrib.get("data-teaching-keys", "[]"))
    }
    assert {
        "foldback_arm_bp",
        "loop_nt",
        "left_gap",
        "right_gap",
        "open_side_paired_positions",
    } <= linked
    assert linked <= {p["definition"]["key"] for p in key["parameters"]}
    metadata = next(e for e in svg if e.tag.endswith("}metadata"))
    assert json.loads(metadata.text) == key
    text = " ".join(svg.itertext())
    assert "Schematic" in text and "not to scale" in text
    assert "sticky" in text.lower() and "5\u2032" in text
    assert not any("data-address" in e.attrib for e in svg.iter())
    assert drawing == pool.parameter_key_svg_bytes
    _, _, width, height = map(float, svg.attrib["viewBox"].split())
    assert width / height >= 3
    assert float(svg.attrib["font-size"]) * 504 / width >= 9


def test_browser_parameter_key_precedes_selection_and_is_shared_with_export(tmp_path):
    from hop_design.commands.construction.editor.surveys import SurveySession

    request, index = indexed_survey(tmp_path)
    session = SurveySession(request, index, tmp_path / "view")
    initial = session.state()
    assert initial["preview"] is None
    key = session.root / initial["parameter_key"].removeprefix("/files/")
    assert key.read_bytes() == session.pool.parameter_key_svg_bytes
    selected = session.sample({"token": initial["token"], "seed": 17})
    assert selected["parameter_key"] == initial["parameter_key"]
    preview = session.root / selected["preview"]["drawing"].removeprefix("/files/")
    assert not (preview.parent / "projection.pdf").exists()
    packet = construction.inspect_interface_survey_atlas(
        request, index, selection=selected["selection"]
    )
    published = packet.write(tmp_path / "atlas")
    assert (published / "projection.pdf").read_bytes() == packet.pdf_bytes
    assert (published / "parameter-key.svg").read_bytes() == key.read_bytes()
    assert "Parameter definitions" in (published / "report.md").read_text()
