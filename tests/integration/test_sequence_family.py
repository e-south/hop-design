"""A bounded symbolic stem expands to required exact preparations, never a pooled claim."""

import json
import shutil
from pathlib import Path

import pytest

from hop_design import construction
from hop_design.models.sequence import reverse_complement_iupac


def request(tmp_path, domain=None, limit=4):
    base = json.loads(Path("examples/molecular-editing/request.json").read_bytes())
    base["max_branches"] = 1
    stem = base["product"]["stem_arm"]
    value = {
        "schema": "hop.sequence-family/v1",
        "base_request": base,
        "stem_domain": domain or stem[:12] + "N" + stem[13:],
        "max_members": limit,
        "max_total_branches": 4,
        "shared_properties": ["non_stem_sequences", "terminal_chemistry"],
        "shared_material_roles": [
            "ligation_adapter",
            "source_materialization_forward_primer",
            "source_materialization_reverse_primer",
            "endpoint_forward_primer",
            "endpoint_reverse_primer",
        ],
    }
    path = tmp_path / "family.json"
    path.write_text(json.dumps(value))
    return path


def test_family_bounds_fail_before_search(tmp_path):
    with pytest.raises(ValueError, match=r"expan|members"):
        construction.prepare_sequence_family(request(tmp_path, limit=3))


def test_family_retains_required_members_without_complete_preparations(tmp_path):
    path = request(tmp_path)
    value = json.loads(path.read_bytes())
    value["base_request"]["product"]["foldback"]["geometry"].update(
        loop_lengths_nt=[3], loop_sequences=["TTC"], annealing_arm_lengths_bp=[6]
    )
    path.write_text(json.dumps(value))
    packet = construction.execute_sequence_family(path)
    summary = json.loads(packet.json_bytes)
    assert len(summary["missing_members"]) == 4
    assert len(summary["members"]) == 4
    assert summary["options"] == []
    assert all(m["coverage"] is not None for m in summary["members"])
    assert summary["global_feasibility"] == "not_assessed"


def test_one_n_family_requires_all_exact_members_and_verified_shared_flanks(tmp_path):
    path = request(tmp_path)
    preview = construction.prepare_sequence_family(path)
    assert json.loads(preview.json_bytes)["required_members"] == 4
    packet = construction.execute_sequence_family(path)
    root = packet.write(tmp_path / "family")
    summary = json.loads(packet.json_bytes)
    assert summary["missing_members"] == []
    assert len(summary["members"]) == 4
    selected = {}
    for member in summary["members"]:
        assert len(member["option_labels"]) == 1
        label = member["option_labels"][0]
        selected[member["name"]] = label
        view = json.loads((root / f"views/{label}.json").read_bytes())
        regions = {r["region"]: r["observed_sequence"] for r in view["regions"]}
        assert regions["stem_primary"] == member["stem_arm"]
        assert regions["stem_return"] == reverse_complement_iupac(member["stem_arm"])
    moved = tmp_path / "relocated"
    shutil.move(root, moved)
    with pytest.raises(ValueError, match="required member"):
        construction.select_sequence_family(
            moved, members=dict(list(selected.items())[:3]), baseline=next(iter(selected))
        )
    result = construction.select_sequence_family(
        moved, members=selected, baseline=next(iter(selected))
    )
    output = result.write(tmp_path / "selected")
    assert (output / "oligos.csv").is_file()
    assert len(json.loads(result.json_bytes)["members"]) == 4
    replay = construction.select_construction_set(output / "set.json")
    assert json.loads(replay.json_bytes)["set_id"] == json.loads(result.json_bytes)["set_id"]
