"""Whole-hairpin views retain actual geometry and an exact preparation identity."""

import json
from xml.etree import ElementTree

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from tests.integration.test_request_execution import hairpin_request, request_path


def test_public_portrait_reads_the_complete_hairpin_and_preserves_selection(tmp_path):
    request = hairpin_request(tmp_path)
    execution = construction.execute_construction_request(
        request, design_id="portrait-hairpin", continuation="sole-witness"
    )
    execution.write(tmp_path / "run")
    receipt = construction.load_verified_construction_bundle(tmp_path / "run/construction")
    selected_id = receipt.materialized_realization_ids[0]
    portrait = construction.project_hairpin_portrait(
        receipt, materialized_realization_id=selected_id
    )
    data = json.loads(portrait.json_bytes)
    assert data["schema"] == "hop.hairpin-portrait/v1"
    assert data["source_result_id"] == receipt.result_id
    assert data["materialized_realization_id"] == selected_id
    assert data["stage_role"] == "endpoint"
    assert data["state"]["phase"] == "ligated_product"
    assert data["stem_bp"] == 34
    assert data["open_side_paired_positions"] == 10
    assert data["loop_side_paired_bp"] == 6
    assert data["loop_nt"] == 4
    assert data["loop_span"] == {"start": {"offset": 50}, "end": {"offset": 54}}
    assert data["stem_primary_span"] == {"start": {"offset": 10}, "end": {"offset": 44}}
    assert data["join_boundaries"] == [46]
    assert data["later_release"] is None
    molecule = data["state"]["molecules"][0]
    assert len(molecule["sequence"]) == 104
    assert molecule["five_prime_end"] == molecule["three_prime_end"] == "hydroxyl"
    selection = construction.select_construction_realization(
        receipt, materialized_realization_id=data["materialized_realization_id"]
    )
    selection.write(tmp_path / "choice.json")
    restored = construction.load_construction_selection(tmp_path / "choice.json", receipt=receipt)
    assert restored.materialized_realization_id == selected_id
    with pytest.raises(ValueError, match="Unknown accepted"):
        construction.project_hairpin_portrait(receipt, materialized_realization_id="unknown")
    with pytest.raises(TypeError, match="verified construction receipt"):
        construction.project_hairpin_portrait(data, materialized_realization_id=selected_id)


def test_portrait_cli_svg_and_preparation_agree_without_moving_future_ends(tmp_path):
    execution = construction.execute_construction_request(
        request_path(tmp_path), design_id="portrait-insert", continuation="sole-witness"
    )
    execution.write(tmp_path / "run")
    receipt = construction.load_verified_construction_bundle(tmp_path / "run/construction")
    selected_id = receipt.materialized_realization_ids[0]
    portrait = construction.project_hairpin_portrait(
        receipt, materialized_realization_id=selected_id
    )
    data = json.loads(portrait.json_bytes)
    assert data["stage_role"] == "intermediate"
    assert data["state"]["phase"] == "adapter_ligated"
    assert data["open_side_paired_positions"] == 17  # Not 31 source bases or 6 final-flank bp.
    assert data["loop_side_paired_bp"] == 6
    assert data["loop_nt"] == 4
    assert data["stem_primary_span"]["start"]["offset"] == 31
    assert data["paired_primary_span"]["start"]["offset"] == 14
    assert data["join_boundaries"] == [67, 115]
    assert data["later_release"]["stage"] == "clone_ready_duplex"
    assert [e["sequence"] for e in data["later_release"]["cohesive_ends"]] == ["AGTC", "AGTC"]
    svg = ElementTree.fromstring(portrait.svg_bytes)
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert svg.find(".//s:g[@id='hairpin-shape']", ns) is not None
    assert len(svg.findall(".//s:line[@data-pair-left-index]", ns)) == 57
    assert len(svg.findall(".//s:circle[@data-join-boundary]", ns)) == 2
    release = svg.find(".//s:g[@data-stage='clone_ready_duplex']", ns)
    assert release is not None
    assert "After copying and release" in "".join(release.itertext())
    assert "hydroxyl" in "".join(svg.itertext())
    cli = CliRunner().invoke(
        app,
        [
            "construction",
            "portrait",
            str(tmp_path / "run/construction"),
            selected_id,
            "--out",
            str(tmp_path / "portrait"),
        ],
    )
    assert cli.exit_code == 0, cli.output
    assert (tmp_path / "portrait/projection.json").read_bytes() == portrait.json_bytes
    assert (tmp_path / "portrait/projection.svg").read_bytes() == portrait.svg_bytes
    assert (tmp_path / "portrait/preparation/oligos.csv").read_bytes() == (
        tmp_path / "run/handoff/oligos.csv"
    ).read_bytes()
    selection = construction.load_construction_selection(
        tmp_path / "portrait/selection.json", receipt=receipt
    )
    assert selection.materialized_realization_id == selected_id
