"""An authored request remains authoritative during explicit local continuation."""

import json

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from tests.integration.test_request_execution import hairpin_request, request_path


@pytest.fixture(params=["hairpin", "insert"])
def prepared_case(tmp_path, request):
    path = hairpin_request(tmp_path) if request.param == "hairpin" else request_path(tmp_path)
    authored = json.loads(path.read_text())
    authored["foldback"]["search"].update(
        max_realizations=2, result_quota=2, max_retained_overhead_nt=18
    )
    authored["foldback"]["geometry"]["loop_lengths_nt"] = [4, 6]
    path.write_text(json.dumps(authored))
    prepared = construction.prepare_construction_request(path)
    prepared.write(tmp_path / "inputs")
    selections = {}
    receipts = {}
    for family in ("foldback", "basal"):
        local_path = tmp_path / f"inputs/{family}.json"
        if not local_path.exists():
            continue
        local = construction.discover_local_neighborhood(local_path)
        local.write(tmp_path / family)
        choices = construction.list_local_realizations(local)
        assert choices
        receipts[family] = local
        selections[f"{family}_path"] = tmp_path / f"{family}/result.json"
        selections[f"{family}_realization_id"] = choices[-1].realization_id
    assert receipts["foldback"].realization_count == 2
    return path, authored, prepared, receipts, selections


def test_explicit_continuation_preserves_authored_request_and_selected_ids(tmp_path, prepared_case):
    path, authored, prepared, receipts, selections = prepared_case
    receipt = construction.continue_construction_request(path, design_id="continued", **selections)
    receipt.write(tmp_path / "continued")
    summary = json.loads(receipt.json_bytes)
    assert summary["continuation"] == "explicit-selection"
    assert summary["local_coverage"]["foldback"]["realization_count"] == 2
    assert (tmp_path / "continued/inputs/request.json").read_bytes() == prepared.request_json_bytes
    assert (
        tmp_path / "continued/inputs/construction.json"
    ).read_bytes() == prepared.source_json_bytes
    selected_args = dict(receipts)
    selected_args.update({key: value for key, value in selections.items() if key.endswith("_id")})
    component = authored.get("hairpin_basal_component")
    expected_design = construction.compile_design_from_local_realizations(
        design_id="continued",
        payload_sequence=authored["stem_arm"],
        endpoint=authored["endpoint"],
        hairpin_basal_arms=None
        if component is None
        else (component["left_arm"], component["right_arm"]),
        **selected_args,
    )
    assert (tmp_path / "continued/design/hop-plan.json").read_bytes() == expected_design.artifacts[
        "hop-plan.json"
    ]
    expected = construction.compile_construction_from_local_realizations(
        tmp_path / "inputs/construction.json",
        design_bundle_path=tmp_path / "continued/design",
        **selected_args,
    )
    assert summary["result_id"] == expected.result_id
    assert summary["status"] == expected.status
    assert summary["selected_local_realizations"] == {
        key.removesuffix("_realization_id"): value
        for key, value in selections.items()
        if key.endswith("_id")
    }
    arguments = [
        "construction",
        "continue",
        str(path),
        "--design-id",
        "continued",
        "--out",
        str(tmp_path / "cli"),
    ]
    for key, value in selections.items():
        arguments += ["--" + key.removesuffix("_path").replace("_", "-"), str(value)]
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code == 0, result.output
    assert (tmp_path / "cli/summary.json").read_bytes() == receipt.json_bytes
    with pytest.raises(FileExistsError):
        receipt.write(tmp_path / "continued")


@pytest.mark.parametrize("edit", ["end", "permission", "selection"])
def test_continuation_rejects_stale_local_evidence_or_unknown_selection(
    tmp_path, prepared_case, edit, monkeypatch
):
    path, authored, _, _, selections = prepared_case
    from hop_design.design.construction import request_execution

    def unexpected_compilation(*args, **kwargs):
        raise AssertionError("Mismatched local evidence must reject before design compilation")

    monkeypatch.setattr(
        request_execution, "compile_design_from_local_realizations", unexpected_compilation
    )
    if edit == "selection":
        selections["foldback_realization_id"] = "not-selected"
    elif edit == "permission":
        authored["foldback"]["search"]["max_search_nodes"] += 1
    elif authored["ends"] is None:
        authored["foldback"]["geometry"]["minimum_loop_length_nt"] += 1
    else:
        authored["ends"]["right"]["cohesive_end_sequence"] = "GATC"
    path.write_text(json.dumps(authored))
    with pytest.raises(ValueError, match=r"not found exactly once|does not derive"):
        construction.continue_construction_request(path, design_id="stale", **selections)
    assert not (tmp_path / "out").exists()


def test_continuation_invalid_design_id_rejects_before_local_loading(tmp_path, monkeypatch):
    def unexpected_load(*args, **kwargs):
        raise AssertionError("Bad design identity must reject before evidence loading")

    from hop_design.design.construction import request_continuation

    monkeypatch.setattr(request_continuation, "load_verified_local_neighborhood", unexpected_load)
    with pytest.raises(ValueError, match="design_id"):
        construction.continue_construction_request(
            tmp_path / "absent-request.json",
            design_id="UPPERCASE",
            foldback_path=tmp_path / "absent-local.json",
            foldback_realization_id="explicit",
        )


def test_continuation_preserves_fixed_source_material_and_reports_conflict(tmp_path, prepared_case):
    path, authored, _, _, selections = prepared_case
    first = construction.continue_construction_request(
        path, design_id="material-reference", **selections
    )
    first.write(tmp_path / "reference")
    reference = json.loads((tmp_path / "reference/handoff/projection.json").read_text())
    material = reference["realization"]["source_preparation"]["source_ssdna"]
    authored["materialization"]["source_preparation"]["source_ssdna"] = {
        "mode": "fixed",
        "material": material,
    }
    path.write_text(json.dumps(authored))
    locked = construction.continue_construction_request(
        path, design_id="material-locked", **selections
    )
    locked.write(tmp_path / "locked")
    assert json.loads(locked.json_bytes)["status"] == "complete"
    locked_view = json.loads((tmp_path / "locked/handoff/projection.json").read_text())
    assert locked_view["realization"]["source_preparation"]["source_ssdna"] == material
    # Fixed material remains authored even when it no longer fits the selected route.
    material.pop("material_id")
    material["sequence_5prime"] = "A"
    path.write_text(json.dumps(authored))
    rejected = construction.continue_construction_request(
        path, design_id="material-conflict", **selections
    )
    rejected.write(tmp_path / "conflict")
    assert json.loads(rejected.json_bytes)["status"] == "infeasible"
    assert not (tmp_path / "conflict/handoff").exists()
    saved = json.loads((tmp_path / "conflict/inputs/request.json").read_text())
    assert (
        saved["materialization"]["source_preparation"]["source_ssdna"]["material"][
            "sequence_5prime"
        ]
        == "A"
    )


@pytest.mark.parametrize("partial", ["path", "id"])
def test_continuation_rejects_endpoint_incompatible_or_partial_basal_selection(
    tmp_path, prepared_case, partial
):
    path, authored, _, _, selections = prepared_case
    if authored["endpoint"] == "ssdna_hairpin":
        selections["basal_path" if partial == "path" else "basal_realization_id"] = "unused"
        message = "omit basal"
    else:
        selections.pop("basal_path" if partial == "path" else "basal_realization_id")
        message = "requires both"
    with pytest.raises(ValueError, match=message):
        construction.continue_construction_request(path, design_id="partial", **selections)
