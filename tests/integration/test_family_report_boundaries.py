# ruff: noqa: F811
"""A readable report never erases negative scope, chemistry or authority boundaries."""

import csv
import json
import shutil

import pytest

from hop_design import construction
from tests.integration.test_construction_family import family_path
from tests.integration.test_construction_family_report import (  # noqa: F401
    family_capture,
    reseal,
)
from tests.integration.test_request_execution import hairpin_request


@pytest.mark.parametrize(
    "fault", ["missing", "extra", "symlink", "manifest-path", "interpretation", "malformed"]
)
def test_invalid_saved_report_inputs_fail_before_publication(family_capture, tmp_path, fault):
    root = tmp_path / "bad"
    shutil.copytree(family_capture / "executed", root)
    if fault == "missing":
        (root / "family.json").unlink()
    elif fault == "extra":
        (root / "unlisted").write_text("not inventoried")
    elif fault == "symlink":
        (root / "linked").symlink_to(root / "family.json")
    elif fault == "manifest-path":
        from hop_design.serialization import canonical_json_bytes

        manifest = json.loads((root / "manifest.json").read_text())
        manifest["artifacts"]["../outside"] = next(iter(manifest["artifacts"].values()))
        (root / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    else:
        data = json.loads((root / "summary.json").read_text())
        if fault == "interpretation":
            data["interpretation"] = "All routes globally feasible and validated."
        else:
            data["members"] = None
        (root / "summary.json").write_text(json.dumps(data))
        reseal(root)
    with pytest.raises((ValueError, OSError)):
        construction.project_construction_family_report(root).write(tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("stop", ["exhausted", "bounded", "multiple", "failed", "shared"])
def test_report_keeps_all_scoped_outcomes(tmp_path, stop):
    path = family_path(tmp_path)
    data = json.loads(path.read_text())
    if stop == "exhausted":
        data["members"] = data["members"][:1]
        data["base_request"]["ends"]["left"]["cohesive_end_sequence"] = "GATC"
    elif stop == "bounded":
        data["members"] = [{"name": "bounded", "loop_nt": 3}]
        data["base_request"]["stem_arm"] = "CCTGAGC"
        data["base_request"]["foldback"]["search"]["max_search_nodes"] = 1
    elif stop == "multiple":
        data["members"] = [{"name": "multiple", "loop_side_paired_bp": 7}]
        data["base_request"]["foldback"]["search"].update(max_realizations=2, result_quota=2)
    elif stop == "failed":
        data["members"] = data["members"][-1:]
    else:
        data["members"] = [
            {"name": "reference", "loop_nt": 3, "loop_side_paired_bp": 7},
            {"name": "other", "loop_nt": 4},
        ]
        data["shared_properties"].append("loop_side_paired_bp")
    path.write_text(json.dumps(data))
    construction.execute_construction_family(path, continuation="sole-witness").write(
        tmp_path / "saved"
    )
    report = construction.project_construction_family_report(tmp_path / "saved")
    result = json.loads(report.json_bytes)
    if stop != "shared":
        m = result["members"][0]
        assert m["choices"] == []
        assert (
            m["status"]
            == {
                "exhausted": "infeasible",
                "bounded": "unresolved",
                "multiple": "selection-required",
                "failed": "infeasible",
            }[stop]
        )
        assert m["scope"] == ("selected_combination" if stop == "failed" else "local_domain")
    else:
        assert len(result["members"]) == 2
        assert result["members"][1]["choices"][0]["shared_property_differences"]
    assert result["selected_members"] == []
    report.write(tmp_path / "readable")


def test_direct_hairpin_report_retains_endpoint_and_source_chemistry(tmp_path):
    base = json.loads(hairpin_request(tmp_path).read_text())
    base["materialization"]["source_preparation"]["source_ssdna"]["five_prime_end"] = "phosphate"
    data = {
        "schema": "hop.construction-family/v1",
        "base_request": base,
        "members": [{"name": "hairpin", "loop_nt": 4}],
        "shared_properties": ["stem_sequence", "endpoint"],
        "bounds": {"max_members": 1, "max_total_search_nodes": 20000, "max_total_continuations": 1},
    }
    path = tmp_path / "family.json"
    path.write_text(json.dumps(data))
    construction.execute_construction_family(path, continuation="sole-witness").write(
        tmp_path / "saved"
    )
    report = construction.project_construction_family_report(tmp_path / "saved")
    c = json.loads(report.json_bytes)["members"][0]["choices"][0]
    assert c["stage_role"] == "endpoint"
    assert c["product_stages"]["product"].get("cohesive_ends", []) == []
    assert c["product_stages"]["bases"] == []
    output = report.write(tmp_path / "report")
    assert b"No later released ends" in (output / c["stage_drawing"]).read_bytes()
    with (output / c["preparation"]).with_name("oligos.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert next(r for r in rows if r["name"] == "source_ssdna")["five_prime_end"] == "phosphate"


def test_report_rejects_input_overwrite_and_foreign_selection(family_capture, tmp_path):
    packet = construction.project_construction_family_report(family_capture / "executed")
    with pytest.raises((ValueError, OSError)):
        packet.write(family_capture / "executed/embedded-report")
    subset = tmp_path / "subset"
    shutil.copytree(family_capture / "executed", subset)
    # A valid different family cannot smuggle an unrelated selected set through name equality.
    path = family_path(tmp_path)
    data = json.loads(path.read_text())
    data["members"] = data["members"][-1:]
    path.write_text(json.dumps(data))
    construction.execute_construction_family(path, continuation="sole-witness").write(
        tmp_path / "failed-only"
    )
    with pytest.raises(ValueError, match="belong"):
        construction.project_construction_family_report(
            tmp_path / "failed-only", selection=family_capture / "set.json"
        )
