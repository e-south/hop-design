from __future__ import annotations

import json
from pathlib import Path

import pytest

import hop_design as hop
from hop_design.export.bundle import BundleIntegrityError, verify_bundle_contents
from hop_design.models.bundle import HopBundle, bundle_id, manifest_digest_for_bundle
from hop_design.serialization import canonical_json_bytes, sha256_digest

EXPECTED_FILES = {
    "hairpin-encoding.fasta",
    "hop-bundle.json",
    "hop-plan.json",
    "hop-spec.json",
    "provenance.json",
}

verify_bundle = hop.verify_bundle


def _reseal_bundle_manifest(output: Path, data: dict[str, object]) -> None:
    manifest_path = output / "hop-bundle.json"
    provisional = HopBundle.model_validate_json(json.dumps(data))
    manifest_digest = manifest_digest_for_bundle(provisional)
    data["manifest_digest"] = manifest_digest
    data["bundle_id"] = bundle_id(design_id=data["design_id"], manifest_digest=manifest_digest)
    manifest_path.write_bytes(canonical_json_bytes(data))


def _replace_artifact_and_reseal_bundle(output: Path, artifact_path: str, content: bytes) -> None:
    (output / artifact_path).write_bytes(content)
    manifest_path = output / "hop-bundle.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in data["artifacts"]:
        if artifact["path"] == artifact_path:
            artifact["digest"] = sha256_digest(content)
            artifact["size_bytes"] = len(content)
            break
    else:
        raise AssertionError(f"Missing artifact entry: {artifact_path}")
    if artifact_path == "hop-plan.json":
        data["plan_digest"] = sha256_digest(content)
    if artifact_path == "hop-spec.json":
        data["spec_digest"] = sha256_digest(content)
    _reseal_bundle_manifest(output, data)


def _add_artifact_and_reseal_bundle(output: Path, artifact_path: str, content: bytes) -> None:
    (output / artifact_path).write_bytes(content)
    manifest_path = output / "hop-bundle.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["artifacts"].append(
        {
            "path": artifact_path,
            "media_type": "text/x-fasta",
            "digest": sha256_digest(content),
            "size_bytes": len(content),
        }
    )
    data["artifacts"].sort(key=lambda artifact: artifact["path"])
    _reseal_bundle_manifest(output, data)


def test_bundle_is_deterministic_and_content_addressed() -> None:
    first = hop.compile(sequence="NRY", design_id="demo")
    second = hop.compile(sequence="NRY", design_id="demo")

    assert first.bundle == second.bundle
    assert first.artifacts == second.artifacts
    assert first.bundle.bundle_id.startswith("hop:bundle/demo/")
    assert len(first.bundle.manifest_digest.removeprefix("sha256:")) == 64


def test_existing_member_bundle_identity_is_frozen_for_space_compilation() -> None:
    compilation = hop.compile(sequence="ACGT", design_id="identity-tracer")

    assert compilation.bundle.bundle_id == "hop:bundle/identity-tracer/71c1d27113eab374"
    assert compilation.bundle.manifest_digest == (
        "sha256:71c1d27113eab374449f9f3ae3b38f64dbc44c2171a055286aa797744382d892"
    )
    assert compilation.bundle.spec_digest == (
        "sha256:a38d3d8b8b63c1bf087c5e3d8935b526502099a486ef0d83193986afdaf1461a"
    )
    assert compilation.bundle.plan_digest == (
        "sha256:0b5022ad7bc256202dbd873d40d4cf39253a968b7fc7cb1a2f0f1769c7c4713b"
    )


def test_bundle_write_and_verification_round_trip(tmp_path: Path) -> None:
    compilation = hop.compile(sequence="ACGT", design_id="demo")
    output = compilation.write(tmp_path / "demo")

    assert {path.name for path in output.iterdir()} == EXPECTED_FILES
    verified = verify_bundle(output)
    assert verified == compilation.bundle
    bundle_data = json.loads((output / "hop-bundle.json").read_text())
    assert bundle_data["schema"] == "hop.bundle/v2"


def test_load_verified_bundle_returns_typed_semantic_contents(tmp_path: Path) -> None:
    compilation = hop.compile(sequence="ACGT", design_id="demo")
    output = compilation.write(tmp_path / "demo")

    loaded = hop.load_verified_bundle(output)

    assert isinstance(compilation.bundle, HopBundle)
    assert not hasattr(compilation.bundle, "spec")
    assert not hasattr(compilation.bundle, "plan")
    assert isinstance(loaded, hop.VerifiedHopBundle)
    assert loaded.bundle == compilation.bundle
    assert loaded.plan == compilation.plan
    assert loaded.spec == compilation.spec
    assert loaded.plan.hairpin_encoding_insert.sequence == (
        compilation.plan.hairpin_encoding_insert.sequence
    )
    assert set(loaded.artifacts) == EXPECTED_FILES - {"hop-bundle.json"}
    assert "final-insert.fasta" not in loaded.artifacts


def test_verified_bundle_rejects_direct_construction_without_semantic_replay(
    tmp_path: Path,
) -> None:
    loaded = hop.load_verified_bundle(
        hop.compile(sequence="ACGT", design_id="demo").write(tmp_path / "demo")
    )
    other_plan = hop.compile(sequence="TGCA", design_id="other").plan

    with pytest.raises(BundleIntegrityError, match="deterministic replay"):
        hop.VerifiedHopBundle(
            bundle=loaded.bundle,
            spec=loaded.spec,
            plan=other_plan,
            provenance=loaded.provenance,
            artifacts=loaded.artifacts,
        )


def test_integrity_parser_does_not_claim_semantic_verification(tmp_path: Path) -> None:
    output = hop.compile(sequence="ACGT", design_id="demo").write(tmp_path / "demo")

    contents = verify_bundle_contents(output)

    assert not isinstance(contents, hop.VerifiedHopBundle)


def test_bundle_verification_detects_mutation(tmp_path: Path) -> None:
    output = hop.compile(sequence="ACGT", design_id="demo").write(tmp_path / "demo")
    (output / "hairpin-encoding.fasta").write_text(">modified\nAAAA\n")

    with pytest.raises(BundleIntegrityError, match="digest mismatch"):
        verify_bundle(output)


def test_bundle_verification_rejects_noncanonical_manifest_bytes(tmp_path: Path) -> None:
    output = hop.compile(sequence="ACGT", design_id="demo").write(tmp_path / "manifest")
    manifest_path = output / "hop-bundle.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_path.write_text(f"{json.dumps(manifest, indent=2)}\n", encoding="utf-8")

    with pytest.raises(BundleIntegrityError, match="canonical JSON"):
        verify_bundle(output)


def test_bundle_verification_rejects_resealed_but_invalid_plan(tmp_path: Path) -> None:
    output = hop.compile(sequence="ACGT", design_id="demo").write(tmp_path / "invalid-plan")
    plan_path = output / "hop-plan.json"
    data = json.loads(plan_path.read_text(encoding="utf-8"))
    data["lock"]["catalog_ref"] = "hop:catalog/other@1"
    _replace_artifact_and_reseal_bundle(output, "hop-plan.json", canonical_json_bytes(data))

    with pytest.raises(BundleIntegrityError, match=r"hop-plan\.json is invalid"):
        verify_bundle(output)


@pytest.mark.parametrize(
    ("artifact_path", "message"),
    [
        ("hop-spec.json", r"hop-spec\.json is invalid"),
        ("provenance.json", r"provenance\.json is invalid"),
    ],
)
def test_bundle_verification_rejects_resealed_invalid_semantic_artifacts(
    tmp_path: Path,
    artifact_path: str,
    message: str,
) -> None:
    output = hop.compile(sequence="ACGT", design_id="demo").write(
        tmp_path / artifact_path.removesuffix(".json")
    )
    _replace_artifact_and_reseal_bundle(output, artifact_path, b"{}\n")

    with pytest.raises(BundleIntegrityError, match=message):
        verify_bundle(output)


def test_bundle_verification_rejects_resealed_cross_artifact_drift(tmp_path: Path) -> None:
    output = hop.compile(sequence="ACGT", design_id="demo").write(tmp_path / "cross-artifact")
    provenance_path = output / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["plan_id"] = "hop:plan/unrelated/0000000000000000"
    _replace_artifact_and_reseal_bundle(
        output,
        "provenance.json",
        canonical_json_bytes(provenance),
    )

    with pytest.raises(BundleIntegrityError, match="provenance does not match"):
        verify_bundle(output)


def test_bundle_verification_rejects_resealed_fasta_drift(tmp_path: Path) -> None:
    output = hop.compile(sequence="ACGT", design_id="demo").write(tmp_path / "fasta-drift")
    _replace_artifact_and_reseal_bundle(output, "hairpin-encoding.fasta", b">other\nAAAA\n")

    with pytest.raises(BundleIntegrityError, match=r"hairpin-encoding\.fasta does not match"):
        verify_bundle(output)


def test_bundle_verification_rejects_resealed_plan_identity_drift(tmp_path: Path) -> None:
    output = hop.compile(sequence="ACGT", design_id="demo").write(tmp_path / "plan-identity")
    plan_path = output / "hop-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["design_id"] = "other"
    _replace_artifact_and_reseal_bundle(output, "hop-plan.json", canonical_json_bytes(plan))

    with pytest.raises(BundleIntegrityError, match=r"plan identity|design identity"):
        verify_bundle(output)


def test_bundle_verification_rejects_resealed_plan_spec_digest_drift(tmp_path: Path) -> None:
    output = hop.compile(sequence="ACGT", design_id="demo").write(tmp_path / "spec-digest")
    plan_path = output / "hop-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["spec_digest"] = f"sha256:{'0' * 64}"
    _replace_artifact_and_reseal_bundle(output, "hop-plan.json", canonical_json_bytes(plan))

    with pytest.raises(BundleIntegrityError, match=r"plan identity|exact spec digest"):
        verify_bundle(output)


def test_bundle_verification_rejects_resealed_spec_lock_drift(tmp_path: Path) -> None:
    output = hop.compile(sequence="ACGT", design_id="demo").write(tmp_path / "spec-lock")
    spec_path = output / "hop-spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["defaults_ref"] = "hop:defaults/other@1"
    spec_content = canonical_json_bytes(spec)
    _replace_artifact_and_reseal_bundle(output, "hop-spec.json", spec_content)

    plan_path = output / "hop-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["spec_digest"] = sha256_digest(spec_content)
    _replace_artifact_and_reseal_bundle(output, "hop-plan.json", canonical_json_bytes(plan))

    with pytest.raises(BundleIntegrityError, match=r"plan identity|lock does not match"):
        verify_bundle(output)


def test_bundle_verification_rejects_resealed_spec_plan_payload_drift(
    tmp_path: Path,
) -> None:
    output = hop.compile(sequence="ACGT", design_id="demo").write(tmp_path / "spec-plan-payload")
    spec_path = output / "hop-spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["payload"] = {"kind": "exact", "sequence": "AAAA"}
    spec_content = canonical_json_bytes(spec)
    _replace_artifact_and_reseal_bundle(output, "hop-spec.json", spec_content)

    plan_path = output / "hop-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["spec_digest"] = sha256_digest(spec_content)
    _replace_artifact_and_reseal_bundle(output, "hop-plan.json", canonical_json_bytes(plan))

    provenance_path = output / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["spec_digest"] = sha256_digest(spec_content)
    _replace_artifact_and_reseal_bundle(
        output,
        "provenance.json",
        canonical_json_bytes(provenance),
    )

    with pytest.raises(BundleIntegrityError, match=r"plan identity|spec and plan disagree"):
        verify_bundle(output)


def test_bundle_verification_rejects_redundant_source_fasta(tmp_path: Path) -> None:
    output = hop.compile(sequence="ACGT", design_id="demo").write(tmp_path / "source-fasta")
    plan = json.loads((output / "hop-plan.json").read_text(encoding="utf-8"))
    source = plan["source_oligo"]
    content = f">{source['record_id']} symbolic=false\n{source['sequence']}\n".encode()
    _add_artifact_and_reseal_bundle(output, "source-oligo.fasta", content)

    with pytest.raises(BundleIntegrityError, match="redundant source-oligo"):
        verify_bundle(output)


def test_bundle_write_refuses_to_replace_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "demo"
    output.mkdir()

    with pytest.raises(FileExistsError):
        hop.compile(sequence="ACGT", design_id="demo").write(output)


def test_bundle_verification_requires_a_valid_manifest(tmp_path: Path) -> None:
    with pytest.raises(BundleIntegrityError, match="manifest is missing"):
        verify_bundle(tmp_path / "missing")

    invalid = tmp_path / "invalid"
    invalid.mkdir()
    (invalid / "hop-bundle.json").write_text("{")
    with pytest.raises(BundleIntegrityError, match="manifest is invalid"):
        verify_bundle(invalid)


def test_bundle_verification_rejects_missing_and_unmanifested_files(tmp_path: Path) -> None:
    missing = hop.compile(sequence="ACGT", design_id="missing").write(tmp_path / "missing")
    (missing / "hop-spec.json").unlink()
    with pytest.raises(BundleIntegrityError, match="missing or unsafe"):
        verify_bundle(missing)

    extra = hop.compile(sequence="ACGT", design_id="extra").write(tmp_path / "extra")
    (extra / "surprise.txt").write_text("not declared\n")
    with pytest.raises(BundleIntegrityError, match="unmanifested files"):
        verify_bundle(extra)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("spec_digest", f"sha256:{'0' * 64}", "hop-spec.json digest"),
        ("manifest_digest", f"sha256:{'0' * 64}", "manifest digest mismatch"),
        ("bundle_id", "hop:bundle/demo/0000000000000000", "identifier"),
    ],
)
def test_bundle_verification_rejects_corrupt_manifest_roots(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    output = hop.compile(sequence="ACGT", design_id="demo").write(tmp_path / field)
    manifest_path = output / "hop-bundle.json"
    data = json.loads(manifest_path.read_text())
    data[field] = value
    manifest_path.write_bytes(canonical_json_bytes(data))

    with pytest.raises(BundleIntegrityError, match=message):
        verify_bundle(output)
