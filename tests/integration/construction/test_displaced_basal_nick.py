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


def _cleanup_case(tmp_path, *, retain_cleanup_fragment=False):
    source, design, selection, payload = _case(tmp_path, "C", False)
    upstream = "A" * 15 + "CGTC"
    prefix = upstream + "A" * 15 + "C"
    source["composition"]["materialization"]["source_preparation"]["source_ssdna"][
        "upstream_sequence_spec"
    ] = upstream
    source_sequence = prefix + payload + "TCAGATGCTGA"
    assert len(source_sequence) == 80
    enzymes = [
        source[family]["enzyme_provisioning"]["catalog"]["enzymes"][0]
        for family in ("foldback", "basal")
    ]

    def span(start, end):
        return {"start": {"offset": start}, "end": {"offset": end}}

    partition_request = {
        "schema": "hop.source-partition-request/v2",
        "payload": source["foldback"]["payload"],
        "source": {
            "material_id": "source",
            "top_sequence_5prime": source_sequence,
            "top_five_prime_end": "hydroxyl",
            "top_three_prime_end": "hydroxyl",
            "bottom_five_prime_end": "phosphate",
            "bottom_three_prime_end": "hydroxyl",
        },
        "payload_source_map": {
            "segments": [
                {
                    "payload_span": span(0, 34),
                    "source_material_id": "source",
                    "source_span": span(35, 69),
                    "orientation": "forward",
                }
            ],
        },
        "enzyme_provisioning": {
            "catalog": {"catalog_id": "example:enzyme-catalog/cleanup@1", "enzymes": enzymes},
            "allowed_enzyme_ids": [enzyme["enzyme_id"] for enzyme in enzymes],
            "forbidden_enzyme_ids": [],
            "reserved_enzyme_ids": [],
            "role_restrictions": [],
            "max_operations": 3,
        },
        "constraints": {
            "fragment_policy": {"preferred_maximum_nt": 19, "absolute_maximum_nt": 19},
            "required_survivors": [
                {"survivor_id": "top", "precursor_strand": "top", "source_span": span(0, 69)},
                {
                    "survivor_id": "bottom",
                    "precursor_strand": "bottom",
                    "source_span": span(34, 80),
                },
            ],
            "max_enzymes_per_program": 2,
        },
        "enumeration": {"max_search_nodes": 3, "max_realizations": 3},
    }
    if retain_cleanup_fragment:
        partition_request["constraints"]["fragment_policy"] = {
            "preferred_maximum_nt": 18,
            "absolute_maximum_nt": 18,
        }
        partition_request["constraints"]["required_survivors"].append(
            {
                "survivor_id": "cleanup",
                "precursor_strand": "bottom",
                "source_span": span(15, 34),
            }
        )
    partition = construction.discover_source_partition(
        _write(tmp_path / "partition.json", partition_request)
    )
    partition_record = json.loads(partition.json_bytes)["realizations"][0]
    design.write(tmp_path / "design")
    selection.update(
        source_partition=partition,
        source_partition_realization_id=partition_record["realization_id"],
    )
    return source, selection, prefix, payload


def test_selected_partition_supplies_additional_cleanup_cuts_to_complete_route(tmp_path):
    source, selection, prefix, payload = _cleanup_case(tmp_path)
    result = construction.compile_construction_from_local_realizations(
        _write(tmp_path / "construction.json", source),
        design_bundle_path=tmp_path / "design",
        **selection,
    )
    assert result.status == "complete"
    assert result.valid_realizations == 1
    bundle = result.write(tmp_path / "construction")
    assert construction.load_verified_construction_bundle(bundle).bundle_id == result.bundle_id
    record = json.loads((bundle / "construction-result.json").read_bytes())["realizations"][0]
    states = {state["phase"]: state for state in record["construction_program"]["states"]}
    assert sorted(len(m["sequence"]) for m in states["denatured_fragments"]["molecules"]) == [
        11,
        15,
        19,
        46,
        69,
    ]
    assert [len(m["sequence"]) for m in states["selected_fragments"]["molecules"]] == [69, 46]
    closed = states["foldback_closed_hairpin"]["molecules"][0]
    assert (
        closed["sequence"]
        == prefix + payload + "TCAGCATCTGA" + reverse_complement_iupac(payload) + "G"
    )
    assert len(states["adapter_ligated"]["formed_bonds"]) == 2


@pytest.mark.parametrize("incompatibility", ("source", "survivors"))
def test_cleanup_must_preserve_prepared_source_and_exact_local_survivors(tmp_path, incompatibility):
    source, selection, _, _ = _cleanup_case(
        tmp_path,
        retain_cleanup_fragment=incompatibility == "survivors",
    )
    if incompatibility == "source":
        policy = source["composition"]["materialization"]["source_preparation"]["source_ssdna"]
        policy["upstream_sequence_spec"] = "C" + policy["upstream_sequence_spec"][1:]
    result = construction.compile_construction_from_local_realizations(
        _write(tmp_path / "construction.json", source),
        design_bundle_path=tmp_path / "design",
        **selection,
    )
    assert result.status == "infeasible"
    bundle = result.write(tmp_path / "construction")
    assert construction.load_verified_construction_bundle(bundle).bundle_id == result.bundle_id
    data = json.loads((bundle / "construction-result.json").read_bytes())
    expected = (
        "source-partition-source-incompatible"
        if incompatibility == "source"
        else "source-partition-selection-incompatible"
    )
    assert data["combination_dispositions"][0]["rejection_reason"] == expected
    assert not data.get("source_partition_rejection_candidates")


@pytest.mark.parametrize("forgery", ("missing-plan", "fragment-chemistry", "survivor", "nick"))
def test_individual_cleanup_route_rejects_resealed_molecular_forgery(tmp_path, forgery):
    from hop_design.models.construction.complete import MaterializedConstructionRealization
    from hop_design.models.construction.payload import _content_id

    source, selection, _, _ = _cleanup_case(tmp_path)
    result = construction.compile_construction_from_local_realizations(
        _write(tmp_path / "construction.json", source),
        design_bundle_path=tmp_path / "design",
        **selection,
    )
    bundle = result.write(tmp_path / "construction")
    record = json.loads((bundle / "construction-result.json").read_bytes())["realizations"][0]
    if forgery == "missing-plan":
        del record["source_partition_plan"]
    else:
        plan = record["source_partition_plan"]["realization"]
        if forgery == "fragment-chemistry":
            plan["denatured"]["fragments"][2]["five_prime_end"] = "hydroxyl"
        elif forgery == "survivor":
            plan["selected"]["retained_fragment_ids"].pop()
        else:
            plan["nicked_duplex"]["sites"].pop()
    record.pop("materialized_realization_id")
    record["materialized_realization_id"] = _content_id("materialized-construction", 1, record)
    with pytest.raises(ValueError):
        MaterializedConstructionRealization.model_validate_json(json.dumps(record))
