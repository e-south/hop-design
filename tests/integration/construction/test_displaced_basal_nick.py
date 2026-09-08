"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/construction/test_displaced_basal_nick.py

Checks retained source bases through public construction of a displaced basal nick.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from pathlib import Path

import pytest
import yaml

from hop_design import construction
from hop_design.models.sequence import reverse_complement_iupac


def _write(path: Path, content: dict) -> Path:
    path.write_text(json.dumps(content), encoding="utf-8")
    return path


def _case(tmp_path: Path, gap: str, reverse: bool):
    examples = Path(__file__).resolve().parents[3] / "examples"
    source = yaml.safe_load((examples / "construction-composed-pcr.yaml").read_text())
    payload = yaml.safe_load((examples / "basal-junction/request.yaml").read_text())["payload"]
    for family in ("foldback", "basal"):
        source[family]["payload"] = payload
    source["foldback"]["enzyme_provisioning"]["catalog"]["enzymes"][0][
        "recognition_orientation_semantics"
    ] = "both_orientations"
    source["basal"]["geometry_domain"]["nick_offsets_nt"] = [len(gap)]
    foldback = construction.discover_local_neighborhood(
        _write(tmp_path / "foldback.json", source["foldback"])
    )
    basal = construction.discover_local_neighborhood(
        _write(tmp_path / "basal.json", source["basal"])
    )
    foldback_record = next(
        item
        for item in json.loads(foldback.json_bytes)["realizations"]
        if item["payload_source_map"]["segments"][0]["orientation"]
        == ("reverse_complement" if reverse else "forward")
    )
    basal_record = next(
        item
        for item in json.loads(basal.json_bytes)["realizations"]
        if item["source_precursor_sequence"] == "A" * 15 + gap + payload["payload"]["sequence"]
    )
    design = construction.compile_design_from_local_realizations(
        design_id="displaced-basal-nick",
        payload_sequence=payload["payload"]["sequence"],
        endpoint="hairpin_pcr_duplex",
        foldback=foldback,
        foldback_realization_id=foldback_record["foldback_realization_id"],
        basal=basal,
        basal_realization_id=basal_record["basal_realization_id"],
    )
    materialization = source["composition"]["materialization"]
    materialization["source_preparation"]["source_ssdna"] = {
        "mode": "constrain",
        "upstream_sequence_spec": "CGTCCGTTGAC",
        "five_prime_end": "hydroxyl",
        "three_prime_end": "hydroxyl",
    }
    materialization["source_preparation"]["forward_primer"]["annealing_length_nt"] = (
        11 if reverse else 19
    )
    materialization["source_preparation"]["reverse_primer"]["annealing_length_nt"] = (
        19 if reverse else 11
    )
    materialization["endpoint_auxiliaries"] = {
        "adapter": {"mode": "constrain", "three_prime_handle_sequence": "CGTACCTAGTGCAGTTGCTC"},
        "forward_primer": {"mode": "derive", "annealing_length_nt": 19},
        "reverse_primer": {"mode": "derive", "annealing_length_nt": 20},
    }
    selection = {
        "foldback": foldback,
        "foldback_realization_id": foldback_record["foldback_realization_id"],
        "basal": basal,
        "basal_realization_id": basal_record["basal_realization_id"],
    }
    return source, design, selection, payload["payload"]["sequence"]


@pytest.mark.parametrize("reverse", (False, True))
@pytest.mark.parametrize("gap", ("C", "CG"))
def test_displaced_nick_retains_source_bases_through_adapter_join_and_copy(
    tmp_path: Path, gap: str, reverse: bool
) -> None:
    source, design, selection, payload = _case(tmp_path, gap, reverse)
    retained = payload + "TCAGCATCTGA" + reverse_complement_iupac(payload)
    encoding = "AAAA" + gap + retained + reverse_complement_iupac(gap) + "TTTT"
    assert design.plan.hairpin_encoding_insert.sequence == encoding

    design.write(tmp_path / "design")
    result = construction.compile_construction_from_local_realizations(
        _write(tmp_path / "construction.json", source),
        design_bundle_path=tmp_path / "design",
        **selection,
    )
    assert result.status == "complete"
    assert result.valid_realizations == 1
    bundle = result.write(tmp_path / "construction")
    replayed = construction.load_verified_construction_bundle(bundle)
    assert replayed.bundle_id == result.bundle_id
    record = json.loads((bundle / "construction-result.json").read_bytes())["realizations"][0]
    states = {state["phase"]: state for state in record["construction_program"]["states"]}
    closed = states["foldback_closed_hairpin"]
    strand = closed["molecules"][0]
    prefix = "CGTCCGTTGAC" + "A" * 15 + gap
    assert strand["sequence"] == prefix + retained + reverse_complement_iupac(gap)
    pair_coordinates = {
        frozenset((pair["left_index"], pair["right_index"]))
        for pair in closed["pairings"]
        if pair["kind"] == "watson_crick"
    }
    for index in range(len(gap)):
        assert (
            frozenset((len(prefix) - len(gap) + index, len(strand["sequence"]) - 1 - index))
            in pair_coordinates
        )
    return_use = record["material_uses"][0 if reverse else 1]["use_id"]
    assert {base["origin_id"] for base in strand["lineage"][-len(gap) :]} == {return_use}
    assert [base["origin_index"] for base in strand["lineage"][-len(gap) :]] == list(
        range(len(payload) + 11, len(payload) + 11 + len(gap))
    )
