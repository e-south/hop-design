"""
--------------------------------------------------------------------------------
HOP Design
tests/repo/test_local_envelope_example.py

Checks the public local-envelope example against real discovery and replay.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
import runpy
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_local_envelope_preserves_public_payload_and_unresolved_association(tmp_path):
    example = runpy.run_path(str(ROOT / "examples/local-envelope/search.py"))
    output = tmp_path / "example"
    rows = example["search_example"](
        ROOT / "examples/basal-junction/request.yaml",
        output,
        basal_budget=4,
        foldback_budget=10,
    )
    assert len(rows) == 10
    assert all(row["completion"] == "complete" for row in rows)
    assert {row["family"] for row in rows} == {"basal", "foldback"}
    assert any(row["observed_witness_count"] for row in rows)
    for row in rows:
        result = json.loads((output / row["result"]).read_text())
        container = result["discovery" if row["family"] == "basal" else "neighborhood"]
        request = container["request"]
        assert request["payload"]["payload"]["sequence"] == "ATAACTTCGTATAGCATACATTATACGAAGTTAT"
        assert container["disposition"]["completion"] == row["completion"]
        if row["family"] == "basal":
            assert request["geometry_domain"]["minimum_adapter_annealing_nt"] is None
            assert len(request["geometry_domain"]["pairing_constraints"]) == 4 - row["n"]
        else:
            assert 2 * row["A"] + row["C"] <= 10
            assert request["geometry_domain"]["junction_offsets_nt"] == [0, 1, 2, 3]
    with pytest.raises(FileExistsError):
        example["search_example"](
            ROOT / "examples/basal-junction/request.yaml",
            output,
            basal_budget=4,
            foldback_budget=10,
        )


@pytest.mark.parametrize("change", ["partition", "left_end"])
def test_local_envelope_refuses_inputs_outside_its_coordinate_scope(tmp_path, change):
    example = runpy.run_path(str(ROOT / "examples/local-envelope/search.py"))
    request = yaml.safe_load((ROOT / "examples/basal-junction/request.yaml").read_text())
    if change == "partition":
        request["search"]["sequence_partition"] = {"part_count": 2, "part_index": 0}
    else:
        request["geometry_domain"]["future_release"]["product_end"] = "left"
    source = tmp_path / "input.json"
    source.write_text(json.dumps(request))
    with pytest.raises(ValueError, match="unpartitioned source-duplex right 5-prime"):
        example["search_example"](source, tmp_path / "out", basal_budget=4, foldback_budget=10)
    assert not (tmp_path / "out").exists()
