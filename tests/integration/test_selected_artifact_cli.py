"""Selected local authorities compose through explicit file arguments."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.api import verify_bundle
from hop_design.cli import app
from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.sequence import reverse_complement_iupac
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.contract.test_route_realization_design import _compile_selected, _pcr_authorities
from tests.integration.test_complete_construction_discovery import _material
from tests.integration.test_construction_cli import _write_bundle
from tests.integration.test_construction_source_compiler import (
    _materialization,
    _source,
    _write_source,
)


@pytest.mark.parametrize(
    "kind", ["construction-summary", "construction-navigation", "construction-trajectory"]
)
@pytest.mark.parametrize("linked", [False, True])
def test_projection_cannot_write_into_verified_input_bundle(
    tmp_path: Path, kind: str, linked: bool
) -> None:
    bundle, _ = _write_bundle(tmp_path / "case")
    receipt = construction.load_verified_construction_bundle(bundle)
    destination = bundle
    if linked:
        destination = tmp_path / "bundle-link"
        destination.symlink_to(bundle, target_is_directory=True)
    output = destination / "projection"
    before = {
        path.relative_to(bundle): path.read_bytes() for path in bundle.rglob("*") if path.is_file()
    }
    arguments = ["construction", "project", str(bundle), "--kind", kind, "--out", str(output)]
    if kind == "construction-trajectory":
        arguments += ["--realization-id", receipt.materialized_realization_ids[0]]
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code != 0, result.output
    assert "outside the verified" in " ".join(result.output.split())
    assert not output.exists()
    assert {
        path.relative_to(bundle): path.read_bytes() for path in bundle.rglob("*") if path.is_file()
    } == before
    assert construction.load_verified_construction_bundle(bundle).bundle_id == receipt.bundle_id


@pytest.mark.parametrize(
    "kind,operation",
    [
        ("construction-summary", "project_complete_construction_summary"),
        ("construction-navigation", "project_construction_navigation"),
        ("construction-trajectory", "project_construction_trajectory"),
    ],
)
def test_projection_rejects_parent_redirected_into_bundle_after_cli_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str, operation: str
) -> None:
    bundle, _ = _write_bundle(tmp_path / "case")
    receipt = construction.load_verified_construction_bundle(bundle)
    parent = tmp_path / "exports"
    parent.mkdir()
    original = getattr(construction, operation)

    def redirect_parent(*args, **kwargs):
        projection = original(*args, **kwargs)
        parent.rename(tmp_path / "original-exports")
        parent.symlink_to(bundle, target_is_directory=True)
        return projection

    monkeypatch.setattr(construction, operation, redirect_parent)
    arguments = [
        "construction",
        "project",
        str(bundle),
        "--kind",
        kind,
        "--out",
        str(parent / "view"),
    ]
    if kind == "construction-trajectory":
        arguments += ["--realization-id", receipt.materialized_realization_ids[0]]
    result = CliRunner().invoke(app, arguments)
    assert result.exit_code != 0
    assert result.stdout == ""
    assert not (bundle / "view").exists()
    assert construction.load_verified_construction_bundle(bundle).bundle_id == receipt.bundle_id


@pytest.mark.parametrize(
    "replaced_artifact", [None, "construction-bundle.json", "construction-result.json"]
)
def test_selected_design_cli_matches_public_compilation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replaced_artifact: str | None
) -> None:
    payload, foldback, basal = _pcr_authorities()
    foldback_path, basal_path = tmp_path / "foldback.json", tmp_path / "basal.json"
    foldback_path.write_bytes(canonical_json_bytes(foldback))
    basal_path.write_bytes(canonical_json_bytes(basal))
    output = tmp_path / "design"
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "compile-local-design",
            "--design-id",
            "route-design",
            "--payload",
            payload.payload.sequence,
            "--endpoint",
            "hairpin_pcr_duplex",
            "--foldback",
            str(foldback_path),
            "--foldback-realization-id",
            foldback.realizations[0].foldback_realization_id,
            "--basal",
            str(basal_path),
            "--basal-realization-id",
            basal.realizations[0].basal_realization_id,
            "--out",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    expected = _compile_selected()
    assert report["plan"] == expected.plan.model_dump(mode="json", by_alias=True)
    assert report["bundle"] == expected.bundle.model_dump(mode="json", by_alias=True)
    assert (output / "hop-plan.json").read_bytes() == expected.artifacts["hop-plan.json"]

    encoding = expected.plan.hairpin_encoding_insert.sequence
    source = _source(
        foldback=foldback.neighborhood.request,
        basal=basal.discovery.request,
        endpoint=ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        materialization=_materialization(
            adapter=_material("adapter", basal.realizations[0].proximal_adapter_sequence),
            forward_primer=_material("forward", encoding[:4]),
            reverse_primer=_material("reverse", reverse_complement_iupac(encoding[-4:])),
        ),
    )
    source_path = _write_source(tmp_path / "construction.yaml", source)
    bundle_path = tmp_path / "construction"
    runner = CliRunner()
    compile_arguments = [
        "construction",
        "compile-selected",
        str(source_path),
        "--design-bundle",
        str(output),
        "--foldback",
        str(foldback_path),
        "--foldback-realization-id",
        foldback.realizations[0].foldback_realization_id,
        "--basal",
        str(basal_path),
        "--basal-realization-id",
        basal.realizations[0].basal_realization_id,
        "--out",
        str(bundle_path),
    ]
    original_bundle_id = verify_bundle(output).bundle_id
    nested_arguments = [*compile_arguments[:-1], str(output / "nested-construction")]
    rejected = runner.invoke(app, nested_arguments)
    assert rejected.exit_code != 0, rejected.output
    assert "outside the verified" in " ".join(rejected.output.split())
    assert not (output / "nested-construction").exists()
    assert verify_bundle(output).bundle_id == original_bundle_id
    admitted_files: dict[str, bytes] = {}
    if replaced_artifact is not None:
        original_write = construction.ConstructionCompilation.write

        def replace_after_write(self: construction.ConstructionCompilation, target: Path) -> Path:
            written = original_write(self, target)
            for name in ("construction-bundle.json", "construction-result.json"):
                admitted_files[name] = (written / name).read_bytes()
            (written / replaced_artifact).write_bytes(b"{}")
            return written

        monkeypatch.setattr(construction.ConstructionCompilation, "write", replace_after_write)
    compiled = runner.invoke(app, compile_arguments)
    assert compiled.exit_code == 0, compiled.output
    report = json.loads(compiled.output)
    if replaced_artifact is not None:
        assert (bundle_path / replaced_artifact).read_bytes() == b"{}"
        assert report["bundle"] == json.loads(admitted_files["construction-bundle.json"])
        assert report["result"] == json.loads(admitted_files["construction-result.json"])
        assert report["bundle_file_sha256"] == sha256_digest(
            admitted_files["construction-bundle.json"]
        )
        assert report["result_sha256"] == sha256_digest(admitted_files["construction-result.json"])
        (bundle_path / replaced_artifact).write_bytes(admitted_files[replaced_artifact])
    assert report["nominal_combinations"] == report["examined_combinations"] == 1
    assert report["status"] == "complete"
    verified = runner.invoke(app, ["construction", "verify-complete", str(bundle_path)])
    assert verified.exit_code == 0, verified.output
    assert json.loads(verified.output) == report
    receipt = construction.load_verified_construction_bundle(bundle_path)
    for kind in ("construction-summary", "construction-navigation", "construction-trajectory"):
        target = tmp_path / kind
        arguments = [
            "construction",
            "project",
            str(bundle_path),
            "--kind",
            kind,
            "--out",
            str(target),
        ]
        if kind == "construction-trajectory":
            arguments += [
                "--realization-id",
                receipt.materialized_realization_ids[0],
                "--selection-reason",
                "Exact caller selection.",
            ]
        projection = runner.invoke(app, arguments)
        assert projection.exit_code == 0, projection.output
        assert (
            json.loads((target / "projection.json").read_bytes())["source_result_id"]
            == receipt.result_id
        )
    assert "Exact caller selection." in (tmp_path / "construction-trajectory/report.md").read_text()
    assert (tmp_path / "construction-trajectory/oligos.csv").is_file()
    assert (tmp_path / "construction-trajectory/oligos.fasta").is_file()
    (bundle_path / "construction-result.json").write_bytes(b"{}")
    assert runner.invoke(app, ["construction", "verify-complete", str(bundle_path)]).exit_code != 0


@pytest.mark.parametrize(
    "replaced_artifact", ["construction-bundle.json", "construction-result.json"]
)
def test_complete_verification_report_retains_the_admitted_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replaced_artifact: str
) -> None:
    bundle, _ = _write_bundle(tmp_path)
    runner = CliRunner()
    arguments = ["construction", "verify-complete", str(bundle)]
    expected = runner.invoke(app, arguments)
    assert expected.exit_code == 0, expected.output
    original_load = construction.load_verified_construction_bundle

    def replace_after_load(path: Path) -> construction.VerifiedConstructionBundle:
        admitted = original_load(path)
        (path / replaced_artifact).write_bytes(b"{}")
        return admitted

    monkeypatch.setattr(construction, "load_verified_construction_bundle", replace_after_load)
    observed = runner.invoke(app, arguments)
    assert observed.exit_code == 0, observed.output
    assert (bundle / replaced_artifact).read_bytes() == b"{}"
    assert json.loads(observed.output) == json.loads(expected.output)
