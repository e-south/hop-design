"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_complete_construction_bundle.py

Tests portable complete-construction authority writing and semantic replay.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from hop_design.design.construction.complete import discover_constructions
from hop_design.design.construction.complete.bundle import (
    compile_construction_bundle,
    load_verified_construction_bundle,
    verify_construction_bundle,
)
from hop_design.design.construction.complete.discovery import VerifiedConstructionSpaceResult
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.construction.verification import (
    verify_basal_neighborhood_result,
    verify_foldback_neighborhood_result,
)
from hop_design.kernel.bundle_identity import (
    construction_bundle_id,
    manifest_digest_for_construction_bundle,
)
from hop_design.models.bundle import (
    ArtifactManifestEntry,
    HopBundle,
    bundle_id,
    manifest_digest_for_bundle,
)
from hop_design.models.construction import (
    ConstructionBundle,
    ConstructionEndpoint,
    FinalPayloadReference,
    FoldbackTarget,
)
from hop_design.models.coordinates import Boundary
from hop_design.models.enzymes import RecognitionOrientationSemantics
from hop_design.models.payload import ExactPayload
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.contract.test_foldback_construction_discovery import (
    _nickase,
    _request,
    _terminus_enzyme,
)
from tests.integration.test_complete_construction_discovery import (
    _basal_result,
    _construction_request,
    _verified_design,
)


def _verified_construction(tmp_path: Path, *, include_basal: bool = False):
    payload = FinalPayloadReference(
        payload=ExactPayload(sequence="GACA"),
        basal_boundary=Boundary(offset=0),
        foldback_boundary=Boundary(offset=4),
    )
    foldback = discover_foldback_neighborhood(
        _request(
            _nickase(
                motif="TCAGATGCTGA",
                cut_offset=0,
                orientation_semantics=RecognitionOrientationSemantics.DECLARED_ONLY,
            ),
            _terminus_enzyme(),
            target=FoldbackTarget(
                junction_offset_nt=0,
                loop_length_nt=3,
                annealing_arm_length_bp=4,
            ),
        )
    )
    design = _verified_design(tmp_path)
    basal = _basal_result(payload) if include_basal else None
    request = _construction_request(
        payload=payload,
        foldback=foldback,
        basal=basal,
        design=design,
        endpoint=ConstructionEndpoint.SSDNA_HAIRPIN,
    )
    return discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=None if basal is None else verify_basal_neighborhood_result(basal),
        design=design,
    )


def _reseal_manifest(output: Path, data: dict[str, object]) -> None:
    manifest_path = output / "construction-bundle.json"
    data["artifacts"] = tuple(data["artifacts"])
    provisional = ConstructionBundle.model_validate(data)
    manifest_digest = manifest_digest_for_construction_bundle(provisional)
    data["manifest_digest"] = manifest_digest
    data["bundle_id"] = construction_bundle_id(
        result_id=str(data["result_id"]),
        manifest_digest=manifest_digest,
    )
    manifest_path.write_bytes(canonical_json_bytes(data))


def _replace_artifact_and_reseal(output: Path, artifact_path: str, content: bytes) -> None:
    (output / artifact_path).write_bytes(content)
    manifest_path = output / "construction-bundle.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    for artifact in data["artifacts"]:
        if artifact["path"] == artifact_path:
            artifact["digest"] = sha256_digest(content)
            artifact["size_bytes"] = len(content)
            break
    else:
        raise AssertionError(f"Missing artifact entry: {artifact_path}")
    if artifact_path == "construction-result.json":
        data["result_digest"] = sha256_digest(content)
    _reseal_manifest(output, data)


def test_construction_bundle_round_trips_verified_authorities_deterministically(
    tmp_path: Path,
) -> None:
    verified = _verified_construction(tmp_path)

    first = compile_construction_bundle(verified)
    second = compile_construction_bundle(verified)
    output = first.write(tmp_path / "construction-bundle")
    loaded = load_verified_construction_bundle(output)

    assert first.bundle == second.bundle == loaded.bundle
    assert dict(first.artifacts) == dict(second.artifacts) == dict(loaded.artifacts)
    assert first.bundle.bundle_id == "hop:construction-bundle/abdc5c8cb477/db4bf0435353bdc4"
    assert first.bundle.manifest_digest == (
        "sha256:db4bf0435353bdc46a1c80d4ef65f1b2584f7f17bb9b6d58dcc4f5661a5f6171"
    )
    assert first.bundle.result_digest == (
        "sha256:2a02390fa8ac86a3114f2155f7662f2dbf3459d104c857caa8e49821abc1e395"
    )
    assert sha256_digest(canonical_json_bytes(first.bundle)) == (
        "sha256:1d1140815e9fce6480f974f5fb063fcb5886688f323b38f1aaa400fb3573e968"
    )
    assert loaded.construction.result == verified.result
    assert loaded.construction.design == verified.design
    assert {
        path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()
    } == {
        "construction-bundle.json",
        "construction-result.json",
        "authorities/design/hop-bundle.json",
        *{f"authorities/design/{path}" for path in verified.design.artifacts},
    }


def test_construction_bundle_rejects_unverified_input(tmp_path: Path) -> None:
    verified = _verified_construction(tmp_path)

    with pytest.raises(TypeError, match="requires a verified result"):
        compile_construction_bundle(verified.result)  # type: ignore[arg-type]


def test_construction_bundle_manifest_rejects_duplicate_artifact_paths(tmp_path: Path) -> None:
    bundle = compile_construction_bundle(_verified_construction(tmp_path)).bundle
    data = bundle.model_dump(mode="python", by_alias=True)
    data["artifacts"] = (bundle.artifacts[0], bundle.artifacts[0])

    with pytest.raises(ValueError, match="artifact paths must be unique"):
        ConstructionBundle.model_validate(data)


def test_construction_bundle_replays_a_forged_verified_container(tmp_path: Path) -> None:
    verified = _verified_construction(tmp_path)
    forged = object.__new__(VerifiedConstructionSpaceResult)
    object.__setattr__(
        forged,
        "result",
        verified.result.model_copy(update={"projection_inventory": ()}),
    )
    object.__setattr__(forged, "foldback", verified.foldback)
    object.__setattr__(forged, "basal", verified.basal)
    object.__setattr__(forged, "design", verified.design)

    with pytest.raises(ValueError, match="deterministic composition replay"):
        compile_construction_bundle(forged)


def test_construction_bundle_rejects_tampered_content(tmp_path: Path) -> None:
    output = compile_construction_bundle(_verified_construction(tmp_path)).write(
        tmp_path / "tampered"
    )
    result_path = output / "construction-result.json"
    result_path.write_bytes(result_path.read_bytes() + b"\n")

    with pytest.raises(ValueError, match="artifact digest mismatch"):
        verify_construction_bundle(output)


def test_construction_bundle_rejects_resealed_local_authority_drift(tmp_path: Path) -> None:
    output = compile_construction_bundle(_verified_construction(tmp_path)).write(
        tmp_path / "resealed-local"
    )
    result_path = output / "construction-result.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))
    data["foldback_authority"]["neighborhood"]["projection_inventory"] = []
    _replace_artifact_and_reseal(output, "construction-result.json", canonical_json_bytes(data))

    with pytest.raises(ValueError, match="Construction result cannot be replayed"):
        verify_construction_bundle(output)


def test_construction_bundle_rejects_resealed_basal_authority_drift(tmp_path: Path) -> None:
    output = compile_construction_bundle(
        _verified_construction(tmp_path, include_basal=True)
    ).write(tmp_path / "resealed-basal")
    result_path = output / "construction-result.json"
    data = json.loads(result_path.read_text(encoding="utf-8"))
    data["basal_authority"]["discovery"]["projection_inventory"] = [
        {
            "projection_schema": "hop.synthetic-projection/v1",
            "renderer_version": "synthetic@1",
            "status": "not_generated",
            "projection_id": None,
        }
    ]
    _replace_artifact_and_reseal(output, "construction-result.json", canonical_json_bytes(data))

    with pytest.raises(ValueError, match="Construction result cannot be replayed"):
        verify_construction_bundle(output)


def test_construction_bundle_rejects_resealed_design_artifact_drift(tmp_path: Path) -> None:
    output = compile_construction_bundle(_verified_construction(tmp_path)).write(
        tmp_path / "resealed-design"
    )
    plan_path = "authorities/design/hop-plan.json"
    plan_data = json.loads((output / plan_path).read_text(encoding="utf-8"))
    plan_data["payload_sequence"] = "GACT"
    plan_content = canonical_json_bytes(plan_data)
    (output / plan_path).write_bytes(plan_content)

    design_manifest_path = output / "authorities/design/hop-bundle.json"
    design_data = json.loads(design_manifest_path.read_text(encoding="utf-8"))
    for artifact in design_data["artifacts"]:
        if artifact["path"] == "hop-plan.json":
            artifact["digest"] = sha256_digest(plan_content)
            artifact["size_bytes"] = len(plan_content)
            break
    design_data["artifacts"] = tuple(design_data["artifacts"])
    design_data["external_refs"] = tuple(design_data["external_refs"])
    design_data["plan_digest"] = sha256_digest(plan_content)
    provisional = HopBundle.model_validate(design_data)
    design_digest = manifest_digest_for_bundle(provisional)
    design_data["manifest_digest"] = design_digest
    design_data["bundle_id"] = bundle_id(
        design_id=str(design_data["design_id"]),
        manifest_digest=design_digest,
    )
    design_content = canonical_json_bytes(design_data)
    design_manifest_path.write_bytes(design_content)

    manifest_path = output / "construction-bundle.json"
    root_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    root_data["design_bundle_id"] = design_data["bundle_id"]
    changed = {
        plan_path: plan_content,
        "authorities/design/hop-bundle.json": design_content,
    }
    for artifact in root_data["artifacts"]:
        content = changed.get(artifact["path"])
        if content is not None:
            artifact["digest"] = sha256_digest(content)
            artifact["size_bytes"] = len(content)
    _reseal_manifest(output, root_data)

    with pytest.raises(ValueError, match=r"hop-plan\.json is invalid"):
        verify_construction_bundle(output)


def test_construction_bundle_rejects_missing_extra_and_symlinked_content(
    tmp_path: Path,
) -> None:
    missing = compile_construction_bundle(_verified_construction(tmp_path / "m")).write(
        tmp_path / "missing"
    )
    (missing / "construction-result.json").unlink()
    with pytest.raises(ValueError, match="artifact is missing or unsafe"):
        verify_construction_bundle(missing)

    extra = compile_construction_bundle(_verified_construction(tmp_path / "e")).write(
        tmp_path / "extra"
    )
    (extra / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unmanifested files"):
        verify_construction_bundle(extra)

    linked = compile_construction_bundle(_verified_construction(tmp_path / "s")).write(
        tmp_path / "linked"
    )
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    artifact = linked / "construction-result.json"
    artifact.unlink()
    artifact.symlink_to(outside)
    with pytest.raises(ValueError, match="unsafe symlinks"):
        verify_construction_bundle(linked)


def test_construction_bundle_rejects_resealed_inventoried_extra_content(
    tmp_path: Path,
) -> None:
    output = compile_construction_bundle(_verified_construction(tmp_path)).write(
        tmp_path / "inventoried-extra"
    )
    content = b"unexpected\n"
    path = "unexpected.txt"
    (output / path).write_bytes(content)
    manifest_path = output / "construction-bundle.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["artifacts"].append(
        ArtifactManifestEntry(
            path=path,
            media_type="text/plain",
            digest=sha256_digest(content),
            size_bytes=len(content),
        ).model_dump(mode="json")
    )
    _reseal_manifest(output, data)

    with pytest.raises(ValueError, match="artifact set differs from its schema"):
        verify_construction_bundle(output)


def test_construction_bundle_write_rejects_unsafe_paths_and_existing_destinations(
    tmp_path: Path,
) -> None:
    compilation = compile_construction_bundle(_verified_construction(tmp_path))
    unsafe = replace(compilation, artifacts={"../escaped.txt": b"escape\n"})

    with pytest.raises(ValueError, match="path is unsafe"):
        unsafe.write(tmp_path / "unsafe")
    assert not (tmp_path / "escaped.txt").exists()

    destination = tmp_path / "existing"
    destination.mkdir()
    with pytest.raises(FileExistsError, match="Refusing to replace existing bundle path"):
        compilation.write(destination)


def test_construction_bundle_failed_verification_commits_no_destination(
    tmp_path: Path,
) -> None:
    compilation = compile_construction_bundle(_verified_construction(tmp_path))
    artifacts = dict(compilation.artifacts)
    artifacts["construction-result.json"] = b"{}\n"
    invalid = replace(compilation, artifacts=artifacts)
    destination = tmp_path / "invalid"

    with pytest.raises(ValueError, match="artifact digest mismatch"):
        invalid.write(destination)
    assert not destination.exists()
    assert not tuple(tmp_path.glob(".invalid.*"))
