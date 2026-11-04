"""Reject material preservation obligations that the requested endpoint cannot supply."""

import json
from pathlib import Path

from hop_design import construction


def test_hairpin_preview_explains_absent_endpoint_primer(tmp_path):
    request = json.loads(Path("examples/scaffold-comparison/hairpin.json").read_bytes())
    request["preserve_material_roles"] = ["endpoint_forward_primer"]
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(request))
    preview = json.loads(construction.prepare_scaffold_comparison(path).json_bytes)
    assert preview["status"] == "conflicting_requirements"
    conflict = next(
        c for c in preview["conflicts"] if c["requested_field"] == "preserve_material_roles"
    )
    assert conflict["inherited_value"] == "adapter_ligated_hairpin"
    assert conflict["requested_value"] == "endpoint_forward_primer"
    assert "endpoint" in conflict["explicit_edit"]
    outcome = construction.execute_scaffold_comparison(path)
    assert json.loads(outcome.json_bytes)["execution"] == "not_started"
