"""
--------------------------------------------------------------------------------
HOP Design
tests/repo/test_basal_junction_example.py

Tests the public basal-junction example with characterized enzymes and a duplex substrate.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
import runpy
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import hop_design.construction as construction
import hop_design.spaces as spaces

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "basal-junction"


def test_example_preserves_a_public_payload_and_models_real_cleavage() -> None:
    request = yaml.safe_load((EXAMPLE / "request.yaml").read_text())
    payload = request["payload"]["payload"]["sequence"]
    assert payload == "ATAACTTCGTATAGCATACATTATACGAAGTTAT"
    assert len(payload) == 34
    enzymes = {e["canonical_name"]: e for e in request["enzyme_provisioning"]["catalog"]["enzymes"]}
    assert set(enzymes) == {"Nt.BsmAI", "BbsI"}
    assert enzymes["Nt.BsmAI"]["recognition_pattern"] == "GTCTC"
    assert enzymes["Nt.BsmAI"]["cut_offset_reference_strand"] == 6
    assert enzymes["Nt.BsmAI"]["cut_offset_complement_strand"] is None
    assert enzymes["BbsI"]["recognition_pattern"] == "GAAGAC"
    assert enzymes["BbsI"]["cut_offset_reference_strand"] == 8
    assert enzymes["BbsI"]["cut_offset_complement_strand"] == 12
    assert request["geometry_domain"]["future_release"]["cohesive_end_sequence"] == "NNNN"
    assert request["geometry_domain"]["future_release"]["recognition_material"] == "source_duplex"


def test_example_runs_public_search_and_preserves_a_replayable_result(tmp_path: Path) -> None:
    namespace = runpy.run_path(str(EXAMPLE / "search.py"))
    output = tmp_path / "basal"
    summary = namespace["search_example"](EXAMPLE / "request.yaml", output)

    assert summary["payload_nt"] == 34
    assert summary["completion"] == "complete"
    assert summary["feasibility"] == "feasible"
    assert summary["accessible_end_count"] > 0
    receipt = construction.load_verified_local_neighborhood(output / "result" / "result.json")
    assert receipt.result_id == summary["result_id"]
    assert (output / "matrix" / "projection.csv").is_file()
    svg = ET.fromstring((output / "matrix" / "projection.svg").read_bytes())
    ns = {"svg": "http://www.w3.org/2000/svg"}
    cells = svg.findall(".//svg:g[@data-cell-status]", ns)
    assert len(cells) == 256
    assert all(float(cell.find("svg:rect", ns).attrib["width"]) >= 160 for cell in cells)
    labels = ["".join(label.itertext()) for label in svg.findall(".//svg:text", ns)]
    assert any("AAAA" in label for label in labels)
    assert any("TTTT" in label for label in labels)
    assert next(label for label in labels if "right end" in label).startswith("AAAA")
    request = json.loads(receipt.json_bytes)["discovery"]["request"]
    assert request["geometry_domain"]["minimum_adapter_annealing_nt"] == 15
    before = receipt.json_bytes
    with pytest.raises(FileExistsError):
        namespace["search_example"](EXAMPLE / "request.yaml", output)
    assert (
        construction.load_verified_local_neighborhood(output / "result" / "result.json").json_bytes
        == before
    )


def test_getting_started_uses_a_realistic_sequence_space_without_a_toy_grid() -> None:
    guide = (ROOT / "docs/guides/quickstart.md").read_text()
    assert "--sequence ACGT" not in guide
    assert "fixed-site-three-base-context" not in guide
    assert "examples/loxp-spacer.yaml" in guide
    spec = spaces.SubstrateSpaceSpec.model_validate(
        yaml.safe_load((ROOT / "examples/loxp-spacer.yaml").read_text())
    )
    preview = spaces.preview_space(spec)
    assert preview.theoretical_cardinality == 65536
