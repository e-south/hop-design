"""Verified output boundary for the linear-source method plan."""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import replace
from pathlib import Path

import pytest
from Bio import SeqIO
from pydantic import ValidationError

import hop_design as hop
import hop_design.methods as methods
from hop_design.kernel.bundle_identity import (
    manifest_digest_for_method_bundle,
    method_bundle_id,
)
from hop_design.kernel.strand_state import complement_iupac
from hop_design.models.bundle import MethodBundle
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.support.linear_source_method import HAIRPIN_ENCODING, linear_source_method_request

EXPECTED_METHOD_FILES = {
    "hairpin-encoding.fasta",
    "hairpin-pcr-duplex.fasta",
    "hairpin-pcr-duplex.gb",
    "method-bundle.json",
    "method-plan.json",
    "method-request.json",
    "method-trajectory.json",
    "method-trajectory.svg",
    "restriction-product.fasta",
}


def _reseal_manifest(output: Path, data: dict[str, object]) -> None:
    manifest_path = output / "method-bundle.json"
    provisional = MethodBundle.model_validate_json(canonical_json_bytes(data))
    manifest_digest = manifest_digest_for_method_bundle(provisional)
    data["manifest_digest"] = manifest_digest
    data["bundle_id"] = method_bundle_id(
        request_id=data["request_id"],
        manifest_digest=manifest_digest,
    )
    manifest_path.write_bytes(canonical_json_bytes(data))


def _replace_artifact_and_reseal(output: Path, artifact_path: str, content: bytes) -> None:
    (output / artifact_path).write_bytes(content)
    manifest_path = output / "method-bundle.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in data["artifacts"]:
        if artifact["path"] == artifact_path:
            artifact["digest"] = sha256_digest(content)
            artifact["size_bytes"] = len(content)
            break
    else:
        raise AssertionError(f"Missing artifact entry: {artifact_path}")
    if artifact_path == "method-request.json":
        data["request_digest"] = sha256_digest(content)
    if artifact_path == "method-plan.json":
        data["plan_digest"] = sha256_digest(content)
    _reseal_manifest(output, data)


def test_method_bundle_round_trips_one_complete_replayable_plan(tmp_path: Path) -> None:
    request = linear_source_method_request()

    compilation = methods.compile_linear_source_method_bundle(request)
    output = compilation.write(tmp_path / "method-bundle")
    loaded = methods.load_verified_method_bundle(output)

    assert compilation.result.plan is not None
    assert loaded.request == request
    assert loaded.plan == compilation.result.plan
    assert loaded.bundle == compilation.bundle
    assert loaded.bundle.schema_id == "hop.method-bundle/v2"
    assert loaded.bundle.hairpin_encoding_digest == (
        "sha256:" + hashlib.sha256(HAIRPIN_ENCODING.encode()).hexdigest()
    )
    assert {
        path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()
    } == (EXPECTED_METHOD_FILES)

    trajectory = json.loads(loaded.artifacts["method-trajectory.json"])
    assert trajectory["schema"] == "hop.workflow-view/v1"
    assert trajectory["kind"] == "method_trajectory"
    assert [panel["panel_id"] for panel in trajectory["panels"]] == [
        "source_pcr_duplex",
        "multi_site_nicked_duplex",
        "denatured_fragment_set",
        "length_selected_fragment_set",
        "adapter_annealed_complex",
        "ligated_hairpin",
        "hairpin_pcr_duplex",
        "restriction_digest_product",
    ]
    source_bottom = trajectory["panels"][0]["tracks"][1]
    assert source_bottom["direction"] == "3to5"
    assert source_bottom["sequence"] == complement_iupac(
        loaded.plan.source_pcr_duplex.top_strand.sequence
    )
    denatured_bottom = trajectory["panels"][2]["tracks"][2]
    assert denatured_bottom["direction"] == "5to3"
    assert denatured_bottom["sequence"] == (
        loaded.plan.denatured_fragment_set.fragments[2].sequence
    )
    genbank = loaded.artifacts["hairpin-pcr-duplex.gb"].decode()
    assert "129 bp    ds-DNA     linear" in genbank
    assert '                     /state="hairpin-pcr-duplex"' in genbank
    assert '                     /projection="hairpin-encoding"' in genbank

    parsed = SeqIO.read(io.StringIO(genbank), "genbank")
    assert len(parsed.seq) == 129
    assert parsed.annotations["molecule_type"] == "DNA"
    assert parsed.annotations["topology"] == "linear"
    assert str(parsed.seq).upper() == loaded.plan.hairpin_pcr_duplex.top_strand.sequence


def test_method_bundle_outer_schema_rejects_the_retired_plan_v1_container() -> None:
    bundle = methods.compile_linear_source_method_bundle(linear_source_method_request()).bundle
    data = bundle.model_dump(mode="json", by_alias=True)
    data["schema"] = "hop.method-bundle/v1"

    with pytest.raises(ValidationError):
        MethodBundle.model_validate(data)


def test_method_bundle_rejects_resealed_generated_artifact_drift(tmp_path: Path) -> None:
    output = methods.compile_linear_source_method_bundle(linear_source_method_request()).write(
        tmp_path / "resealed"
    )
    _replace_artifact_and_reseal(
        output,
        "method-trajectory.svg",
        b'<svg xmlns="http://www.w3.org/2000/svg"/>\n',
    )

    with pytest.raises(hop.BundleIntegrityError, match="artifacts disagree"):
        methods.verify_method_bundle(output)


def test_method_bundle_rejects_unmanifested_and_symlinked_content(tmp_path: Path) -> None:
    extra = methods.compile_linear_source_method_bundle(linear_source_method_request()).write(
        tmp_path / "extra"
    )
    (extra / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
    with pytest.raises(hop.BundleIntegrityError, match="unmanifested files"):
        methods.verify_method_bundle(extra)

    linked = methods.compile_linear_source_method_bundle(linear_source_method_request()).write(
        tmp_path / "linked"
    )
    target = linked / "outside.json"
    target.write_text("{}\n", encoding="utf-8")
    artifact = linked / "method-plan.json"
    artifact.unlink()
    artifact.symlink_to(target)
    with pytest.raises(hop.BundleIntegrityError, match="unsafe symlinks"):
        methods.verify_method_bundle(linked)

    nested = methods.compile_linear_source_method_bundle(linear_source_method_request()).write(
        tmp_path / "nested"
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "stolen.json").write_text("{}\n", encoding="utf-8")
    (nested / "escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(hop.BundleIntegrityError, match=r"unsafe symlinks: escape"):
        methods.verify_method_bundle(nested)


def test_method_bundle_write_rejects_unsafe_artifact_path_before_writing(
    tmp_path: Path,
) -> None:
    compilation = methods.compile_linear_source_method_bundle(linear_source_method_request())
    unsafe = replace(compilation, artifacts={"../escaped.txt": b"escape\n"})

    with pytest.raises(hop.BundleIntegrityError, match="path is unsafe"):
        unsafe.write(tmp_path / "unsafe")
    assert not (tmp_path / "escaped.txt").exists()

    dot = replace(compilation, artifacts={".": b"escape\n"})
    with pytest.raises(hop.BundleIntegrityError, match="path is unsafe"):
        dot.write(tmp_path / "dot")


def test_method_bundle_requires_complete_resolution(tmp_path: Path) -> None:
    request = linear_source_method_request(min_length_nt=60)

    with pytest.raises(methods.MethodResolutionError, match="HOP-METHOD-001"):
        methods.compile_linear_source_method_bundle(request)
    assert not (tmp_path / "infeasible").exists()


def test_public_method_example_is_the_canonical_sanitized_fixture() -> None:
    example = Path(__file__).parents[2] / "examples" / "linear-source-method.json"

    assert example.read_bytes() == canonical_json_bytes(linear_source_method_request())


def test_public_matched_design_fixture_compiles_to_the_method_encoding() -> None:
    example_root = Path(__file__).parents[2] / "examples"
    design_spec = hop.load_spec(example_root / "linear-source-matched-design.yaml")
    method_request = methods.LinearSourceMultinickHairpinPcrRequest.model_validate_json(
        (example_root / "linear-source-method.json").read_text(encoding="utf-8")
    )

    design = hop.compile(design_spec)

    assert method_request.expected_hairpin_encoding is not None
    assert (
        design.plan.hairpin_encoding_insert.sequence
        == method_request.expected_hairpin_encoding
        == HAIRPIN_ENCODING
    )


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("request_digest", "request digest"),
        ("hairpin_encoding_digest", "hairpin-encoding digest"),
    ],
)
def test_method_bundle_rejects_resealed_root_identity_drift(
    tmp_path: Path,
    field: str,
    message: str,
) -> None:
    output = methods.compile_linear_source_method_bundle(linear_source_method_request()).write(
        tmp_path / field
    )
    manifest_path = output / "method-bundle.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data[field] = f"sha256:{'0' * 64}"
    _reseal_manifest(output, data)

    with pytest.raises(hop.BundleIntegrityError, match=message):
        methods.verify_method_bundle(output)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("request_id", "example:method-request/other@1", "request identity"),
        ("request_digest", f"sha256:{'0' * 64}", "exact request"),
    ],
)
def test_method_bundle_rejects_resealed_plan_root_drift(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    output = methods.compile_linear_source_method_bundle(linear_source_method_request()).write(
        tmp_path / f"plan-{field}"
    )
    plan_path = output / "method-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan[field] = value
    _replace_artifact_and_reseal(output, "method-plan.json", canonical_json_bytes(plan))

    with pytest.raises(hop.BundleIntegrityError, match=message):
        methods.verify_method_bundle(output)


def test_method_bundle_rejects_resealed_invalid_request(tmp_path: Path) -> None:
    output = methods.compile_linear_source_method_bundle(linear_source_method_request()).write(
        tmp_path / "invalid-request"
    )
    _replace_artifact_and_reseal(output, "method-request.json", b"{}\n")

    with pytest.raises(hop.BundleIntegrityError, match="request or plan is invalid"):
        methods.verify_method_bundle(output)
