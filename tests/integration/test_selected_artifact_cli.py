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
from hop_design.serialization import canonical_json_bytes
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


def test_selected_design_cli_matches_public_compilation(tmp_path: Path) -> None:
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
    compiled = runner.invoke(app, compile_arguments)
    assert compiled.exit_code == 0, compiled.output
    report = json.loads(compiled.output)
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
