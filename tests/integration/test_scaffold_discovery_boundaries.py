"""Discovery keeps restrictive intent and explains distinct negative outcomes."""

import json
from pathlib import Path

import pytest

from hop_design import construction
from tests.integration.test_scaffold_discovery import discovery_request, method_request


def edit(path, update):
    request = json.loads(path.read_bytes())
    update(request)
    path.write_text(json.dumps(request))
    return request


def test_preview_reads_as_product_request_and_discloses_material_policies(tmp_path):
    path = discovery_request(tmp_path)
    packet = construction.prepare_scaffold_discovery(path)
    assert "Open-side pairing: 18 positions" in packet.report_text
    assert "Adapter: constrain" in packet.report_text
    assert "Released duplex insert" in packet.report_text
    summary = json.loads(packet.json_bytes)
    assert summary["requested_scaffold"] == summary["scaffold"]
    assert summary["material_policies"]["adapter"] == "constrain"
    assert "source_forward_primer" in summary["material_policies"]
    assert "endpoint_forward_primer" in summary["material_policies"]
    assert "forward_primer" not in summary["material_policies"]


@pytest.mark.parametrize("kind", ["dimension", "release", "site"])
def test_negative_overview_explains_recorded_boundary(tmp_path, kind):
    path = method_request(tmp_path) if kind == "release" else discovery_request(tmp_path)

    def change(request):
        request["max_continuations_per_branch"] = 1
        if kind == "dimension":
            request["preparation_changes"]["adapter_redesign"] = "preserve"
        elif kind == "release":
            request["preparation_changes"]["release_enzyme_ids"] = ["example:enzyme/bbsi-hf@1"]
        else:
            product = request["product"]
            product["stem_arm"] = "GGTCTC" + product["stem_arm"][6:]

    edit(path, change)
    result = construction.discover_scaffolds(path)
    target = result.write(tmp_path / "negative")
    summary = json.loads(result.json_bytes)
    assert not summary["options"]
    opening = (target / "pages/discovery-1.svg").read_text()
    explanation = {
        "dimension": "Open-side pairing: requested 18 positions; observed 17",
        "release": "Release continuation did not produce the required insert interfaces",
        "site": "An unintended actionable site was detected in the complete route",
    }[kind]
    assert explanation in opening
    assert "unexamined" in opening
    assert "global impossibility" in opening
    if kind == "release":
        assert "BbsI-HF" in opening


@pytest.mark.parametrize(
    "field,value",
    [("max_branches", True), ("max_branches", 65), ("max_continuations_per_branch", 0)],
)
def test_outer_bounds_are_strict(tmp_path, field, value):
    path = discovery_request(tmp_path)
    edit(path, lambda r: r.update({field: value}))
    with pytest.raises(ValueError):
        construction.prepare_scaffold_discovery(path)


@pytest.mark.parametrize("kind", ["unknown", "forbidden", "reserved"])
def test_method_permissions_fail_visibly_before_search(tmp_path, kind):
    path = method_request(tmp_path)

    def change(request):
        if kind == "unknown":
            request["preparation_changes"]["release_enzyme_ids"] = ["example:unknown@1"]
        else:
            request["product"]["release"]["enzymes"][f"{kind}_enzyme_ids"] = [
                "example:enzyme/bbsi-hf@1"
            ]

    edit(path, change)
    preview = json.loads(construction.prepare_scaffold_discovery(path).json_bytes)
    assert preview["status"] == "conflicting_requirements"
    assert preview["branches"] == []
    with pytest.raises(ValueError, match=r"(?i)conflict"):
        construction.discover_scaffolds(path)


def test_direct_hairpin_keeps_endpoint_and_rejects_adapter_redesign(tmp_path):
    path = discovery_request(tmp_path, adapter_redesign="preserve")
    source = Path("examples/scaffold-options/hairpin.json")

    def change(request):
        request["product"] = json.loads(source.read_bytes())
        request["scaffold"] = {"loop_nt": {"minimum": 3, "maximum": 3}}
        request["max_continuations_per_branch"] = 2

    edit(path, change)
    packet = construction.discover_scaffolds(path)
    summary = json.loads(packet.json_bytes)
    assert summary["options"]
    for option in summary["options"]:
        assert option["molecular_identity"]["hairpin"] == option["molecular_identity"]["endpoint"]
    edit(path, lambda r: r["preparation_changes"].update(adapter_redesign="allow"))
    assert json.loads(construction.prepare_scaffold_discovery(path).json_bytes)["conflicts"]


def test_candidate_annealing_floor_is_not_achieved_pairing(tmp_path):
    path = discovery_request(tmp_path)
    edit(
        path,
        lambda r: r.update(
            scaffold={"open_side_paired_positions": {"minimum": 1, "maximum": 1}},
            max_continuations_per_branch=1,
        ),
    )
    packet = construction.discover_scaffolds(path)
    summary = json.loads(packet.json_bytes)
    assert not summary["options"]
    preview = json.loads(construction.prepare_scaffold_discovery(path).json_bytes)
    candidate = preview["branches"][0]["request"]["basal"]["geometry"]
    assert candidate["minimum_adapter_annealing_nt"] == 1
    assert summary["coverage"]["global_route_feasibility"] == "not_assessed"


def test_fixed_adapter_is_retained_when_desired_dimension_changes(tmp_path):
    import csv

    path = discovery_request(tmp_path, adapter_redesign="preserve")
    edit(
        path,
        lambda r: r.update(
            scaffold={"open_side_paired_positions": {"minimum": 17, "maximum": 17}},
            max_continuations_per_branch=1,
        ),
    )
    baseline = construction.discover_scaffolds(path)
    root = baseline.write(tmp_path / "baseline")
    option = json.loads(baseline.json_bytes)["options"][0]
    with (root / option["preparation"]).with_name("oligos.csv").open() as handle:
        adapter = next(row for row in csv.DictReader(handle) if "adapter" in row["roles"])
    material = {k: adapter[k] for k in ("sequence_5prime", "five_prime_end", "three_prime_end")}

    def change(request):
        request["scaffold"]["open_side_paired_positions"] = {"minimum": 18, "maximum": 18}
        request["product"]["materialization"]["endpoint_auxiliaries"]["adapter"] = {
            "mode": "fixed",
            "material": material,
        }

    edit(path, change)
    preview = json.loads(construction.prepare_scaffold_discovery(path).json_bytes)
    assert preview["material_policies"]["adapter"] == "fixed"
    inner = preview["branches"][0]["request"]
    fixed = inner["materialization"]["endpoint_auxiliaries"]["adapter"]["material"]
    assert {k: fixed[k] for k in material} == material
    result = json.loads(construction.discover_scaffolds(path).json_bytes)
    assert result["options"] == []
    assert result["branches"][0]["failures"][0]["scaffold_mismatches"][0]["observed"] == 17
