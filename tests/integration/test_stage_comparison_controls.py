"""Stage-qualified controls survive explicit selection and portable retrieval."""

import json
import shutil
from pathlib import Path

import pytest

from hop_design import construction


@pytest.fixture(scope="module")
def loop_method_panel(tmp_path_factory):
    root = tmp_path_factory.mktemp("stage-controls")
    value = json.loads(Path("examples/scaffold-comparison/grouped.json").read_bytes())
    words = ("AAA", "ATA", "GAA", "TTC")
    value["discovery"]["product"]["foldback"]["geometry"].update(
        loop_lengths_nt=[3], loop_sequences=list(words)
    )
    value["schema"] = "hop.comparison-brief/v3"
    value["required_members"] = [
        {
            "name": f"{word.lower()}-{method}",
            "loop_sequence": word,
            "release_enzyme_id": f"example:enzyme/{enzyme}@1",
        }
        for word in words
        for method, enzyme in (("bsai", "bsai-hfv2"), ("bsmbi", "bsmbi-v2"))
    ]
    value["groups"] = [
        {
            "name": word.lower(),
            "members": [f"{word.lower()}-bsai", f"{word.lower()}-bsmbi"],
            "product_relationship": "identical",
        }
        for word in words
    ]
    value["stage_controls"] = [
        {"property": prop, "stage": "endpoint", "scope": "set"}
        for prop in ("non_loop_sequences", "non_loop_pairing", "terminal_chemistry")
    ]
    path = root / "discovery.json"
    path.write_text(json.dumps(value["discovery"]))
    pool = construction.discover_scaffolds(path).write(root / "pool")
    return value, pool


def test_retained_controls_allow_loop_by_method_panel_and_relocate(loop_method_panel, tmp_path):
    value, pool = loop_method_panel
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(value))
    packet = construction.assess_scaffold_comparison(path, pool)
    result = json.loads(packet.json_bytes)
    assert result["status"] == "comparison_available"
    assert result["distinct_molecules"] == {"hairpin": 8, "endpoint": 4}
    assert {c["status"] for c in result["sets"][0]["stage_controls"]} == {"shared"}
    output = packet.write(tmp_path / "comparison")
    selected = construction.select_scaffold_comparison(
        output, set_label="set-0001", baseline="aaa-bsai"
    ).write(tmp_path / "selected")
    request = json.loads((selected / "set.json").read_bytes())
    opening = (selected / "pages/comparison-1.svg").read_text()
    assert "sequences outside the loop-derived region" in opening
    assert "Exact preparations: report.md and members/" in opening
    assert request["schema"] == "hop.construction-set/v2"
    assert len(request["stage_controls"]) == 3
    moved = tmp_path / "moved"
    shutil.move(selected, moved)
    replay = construction.select_construction_set(moved / "set.json")
    assert json.loads(replay.json_bytes)["stage_controls"] == result["sets"][0]["stage_controls"]
    assert "Required at requested endpoint, whole set" in replay.report_text


def test_hairpin_control_rejects_discarded_preparation_differences(loop_method_panel, tmp_path):
    value, pool = loop_method_panel
    value = json.loads(json.dumps(value))
    value["stage_controls"][0]["stage"] = "hairpin"
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(value))
    result = json.loads(construction.assess_scaffold_comparison(path, pool).json_bytes)
    assert not result["sets"]
    assert result["group_coverage"]["rejections"] == {"stage_control_mismatch": 1}
    assert result["stage_controls"][0]["stage"] == "hairpin"


def test_controls_require_explicit_valid_scope_and_version(loop_method_panel, tmp_path):
    value, _ = loop_method_panel
    path = tmp_path / "invalid.json"
    for control in (
        {"property": "non_loop_sequences", "stage": "endpoint", "scope": "group"},
        {
            "property": "non_loop_sequences",
            "stage": "endpoint",
            "scope": "group",
            "group": "missing",
        },
        {"property": "non_loop_sequences", "stage": "endpoint", "scope": "set", "group": "aaa"},
    ):
        path.write_text(json.dumps({**value, "stage_controls": [control]}))
        with pytest.raises(ValueError):
            construction.prepare_scaffold_comparison(path)
    path.write_text(json.dumps({**value, "schema": "hop.comparison-brief/v2"}))
    with pytest.raises(ValueError):
        construction.prepare_scaffold_comparison(path)
