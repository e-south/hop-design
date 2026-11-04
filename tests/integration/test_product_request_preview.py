"""User-authored end-relative permissions expand without implicit molecular repair."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app

ROOT = Path(__file__).resolve().parents[2]


def _request():
    request = json.loads((ROOT / "examples/complete-construction/product-request.json").read_text())
    request["ends"]["left"]["cohesive_end_sequence"] = "CATT"
    request["basal"]["geometry"]["pairing_constraints"] = []
    request["basal"]["geometry"]["max_noncanonical_pairs"] = 4
    request["basal"]["end_footprint_pairing"] = {
        "reference": "left_end_source_contacts",
        "proximal": "match",
        "within": "any",
    }
    return request


def _write(tmp_path, request, name="request.json"):
    path = tmp_path / name
    path.write_text(json.dumps(request))
    return path


@pytest.mark.parametrize(
    "gap,expected", [(6, {6: "T", 7: "T", 8: "A", 9: "C"}), (8, {8: "T", 9: "T", 10: "A", 11: "C"})]
)
def test_semantic_end_footprint_uses_existing_source_orientation(tmp_path, gap, expected):
    request = _request()
    request["ends"]["left"]["payload_end_offset_bp"] = gap
    # An explicit constraint outside the window stays exactly authored.
    request["basal"]["geometry"]["pairing_constraints"] = [
        {"position_from_ligation": 0, "allowed_class": "match", "allowed_source_bases": ["A"]}
    ]
    prepared = construction.prepare_construction_request(_write(tmp_path, request))
    contacts = json.loads(prepared.source_json_bytes)["basal"]["geometry_domain"][
        "pairing_constraints"
    ]
    assert [c["position_from_ligation"] for c in contacts] == list(range(gap + 4))
    assert contacts[0]["allowed_source_bases"] == ["A"]
    assert all(c["allowed_class"] == "match" for c in contacts[:gap])
    assert {
        c["position_from_ligation"]: c["allowed_source_bases"][0] for c in contacts[gap:]
    } == expected
    assert all(c["allowed_class"] == "any" for c in contacts[gap:])
    assert json.loads(prepared.request_json_bytes) == request
    preview = json.loads(prepared.preview_json_bytes)
    assert preview["basal"]["source_end_footprint"] == [
        {"position_from_ligation": position, "source_base": base}
        for position, base in expected.items()
    ]
    assert preview["basal"]["minimum_adapter_annealing_nt"] == 17
    assert preview["evaluated"] is False


def test_preview_compares_coupled_fields_and_roundtrips_cli(tmp_path):
    before = _request()
    after = deepcopy(before)
    for end in after["ends"].values():
        end["payload_end_offset_bp"] = 8
    after["basal"]["geometry"]["minimum_adapter_annealing_nt"] = 19
    old = _write(tmp_path, before, "before.json")
    path = _write(tmp_path, after)
    prepared = construction.prepare_construction_request(path, compare_to=old)
    report = json.loads(prepared.preview_json_bytes)
    changed = {c["field"]: c for c in report["changes"]}
    assert changed["ends.left.payload_end_offset_bp"]["before"] == 6
    assert changed["ends.left.payload_end_offset_bp"]["after"] == 8
    assert changed["basal.geometry.minimum_adapter_annealing_nt"]["after"] == 19
    assert report["reference"]["basal"]["source_end_footprint"][0]["position_from_ligation"] == 6
    assert report["basal"]["source_end_footprint"][0]["position_from_ligation"] == 8
    outcome = CliRunner().invoke(
        app,
        [
            "construction",
            "prepare",
            str(path),
            "--compare-to",
            str(old),
            "--out",
            str(tmp_path / "cli"),
        ],
    )
    assert outcome.exit_code == 0, outcome.output
    assert (tmp_path / "cli/preview.json").read_bytes() == prepared.preview_json_bytes
    assert "17 -> 19" in outcome.output
    assert "not a verified construction" in outcome.output
    assert json.loads((tmp_path / "cli/request.json").read_bytes()) == after


@pytest.mark.parametrize(
    "kind", ["conflict", "source-base", "ambiguous-frame", "wrong-end", "empty-without-rule"]
)
def test_semantic_pairing_fails_closed_before_output(tmp_path, kind):
    request = _request()
    if kind == "conflict":
        request["basal"]["end_footprint_pairing"]["within"] = "wobble"
        request["basal"]["geometry"]["pairing_constraints"] = [
            {"position_from_ligation": 6, "allowed_class": "match"}
        ]
    elif kind == "source-base":
        request["basal"]["geometry"]["pairing_constraints"] = [
            {"position_from_ligation": 6, "allowed_class": "any", "allowed_source_bases": ["A"]}
        ]
    elif kind == "ambiguous-frame":
        request["basal"]["geometry"]["nick_offsets_nt"] = [0, 2]
    elif kind == "wrong-end":
        request["basal"]["end_footprint_pairing"]["reference"] = "right_end_source_contacts"
    else:
        del request["basal"]["end_footprint_pairing"]
    path = _write(tmp_path, request)
    with pytest.raises(ValueError):
        construction.prepare_construction_request(path)
    result = CliRunner().invoke(
        app, ["construction", "prepare", str(path), "--out", str(tmp_path / "out")]
    )
    assert result.exit_code == 2
    assert not (tmp_path / "out").exists()


def test_semantic_and_literal_permissions_produce_identical_inputs(tmp_path):
    semantic = _request()
    semantic["basal"]["geometry"]["pairing_constraints"] = [
        {"position_from_ligation": 10, "allowed_class": "match", "allowed_adapter_bases": ["G"]}
    ]
    literal = deepcopy(semantic)
    del literal["basal"]["end_footprint_pairing"]
    literal["basal"]["geometry"]["pairing_constraints"] = [
        {"position_from_ligation": i, "allowed_class": "match" if i < 6 else "any"}
        for i in range(10)
    ] + semantic["basal"]["geometry"]["pairing_constraints"]
    first = construction.prepare_construction_request(_write(tmp_path, semantic, "semantic.json"))
    second = construction.prepare_construction_request(_write(tmp_path, literal, "literal.json"))
    assert first.source_json_bytes == second.source_json_bytes
    assert first.request_json_bytes != second.request_json_bytes


def test_semantic_expansion_is_bounded(tmp_path):
    request = _request()
    request["ends"]["left"]["payload_end_offset_bp"] = 100000
    with pytest.raises(ValueError, match="at most 100000"):
        construction.prepare_construction_request(_write(tmp_path, request))
