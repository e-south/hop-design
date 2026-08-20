"""Atomic bundle writing and integrity verification."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

from pydantic import TypeAdapter

from hop_design.export.fasta import render_fasta
from hop_design.kernel.bundle_identity import bundle_id, manifest_digest_for_bundle
from hop_design.models.bundle import HopBundle, ProvenanceRecord
from hop_design.models.plan import HopPlan
from hop_design.models.spec import DesignSpec, HopSpec, ResolvedHopSpec
from hop_design.serialization import canonical_json_bytes, sha256_digest

_SPEC_ADAPTER: TypeAdapter[DesignSpec] = TypeAdapter(DesignSpec)


class WritableCompilation(Protocol):
    """Minimum compile-result surface needed by the bundle writer."""

    @property
    def bundle(self) -> HopBundle:
        """Return the root manifest."""
        ...

    @property
    def artifacts(self) -> Mapping[str, bytes]:
        """Return generated content artifacts by relative path."""
        ...


class BundleVerifier(Protocol):
    """Callable semantic verifier supplied by the design layer."""

    def __call__(self, bundle_path: str | Path) -> HopBundle:
        """Verify one staged bundle and return its root manifest."""
        ...


@dataclass(frozen=True)
class VerifiedBundleContents:
    """Integrity-checked bundle content for higher-layer semantic replay."""

    bundle: HopBundle
    spec: DesignSpec
    plan: HopPlan
    provenance: ProvenanceRecord
    artifacts: Mapping[str, bytes]


class BundleIntegrityError(ValueError):
    """Raised when a bundle inventory or artifact fails verification."""


def write_bundle_files(
    compilation: WritableCompilation,
    output: Path,
    *,
    verifier: BundleVerifier,
) -> Path:
    """Write a bundle atomically and refuse to replace an existing path."""
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to replace existing bundle path: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        for relative_path, content in compilation.artifacts.items():
            destination = temporary / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        (temporary / "hop-bundle.json").write_bytes(canonical_json_bytes(compilation.bundle))
        verifier(temporary)
        os.replace(temporary, output)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return output


def verify_bundle_contents(bundle_path: str | Path) -> VerifiedBundleContents:
    """Verify content identity and parse artifacts for design-layer replay."""
    root = Path(bundle_path)
    manifest_path = root / "hop-bundle.json"
    if not root.is_dir() or not manifest_path.is_file():
        raise BundleIntegrityError(f"Bundle manifest is missing: {manifest_path}")
    manifest_content = manifest_path.read_bytes()
    try:
        bundle = HopBundle.model_validate_json(manifest_content)
    except Exception as exc:
        raise BundleIntegrityError(f"Bundle manifest is invalid: {exc}") from exc
    if manifest_content != canonical_json_bytes(bundle):
        raise BundleIntegrityError("Bundle manifest must use canonical JSON bytes.")

    expected_files = {"hop-bundle.json"}
    artifact_contents: dict[str, bytes] = {}
    for artifact in bundle.artifacts:
        artifact_path = root / artifact.path
        expected_files.add(artifact.path)
        if not artifact_path.is_file() or artifact_path.is_symlink():
            raise BundleIntegrityError(f"Bundle artifact is missing or unsafe: {artifact.path}")
        content = artifact_path.read_bytes()
        artifact_contents[artifact.path] = content
        actual_digest = sha256_digest(content)
        if actual_digest != artifact.digest:
            raise BundleIntegrityError(f"Bundle artifact digest mismatch: {artifact.path}")
        if len(content) != artifact.size_bytes:
            raise BundleIntegrityError(f"Bundle artifact size mismatch: {artifact.path}")

    actual_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    unexpected = sorted(actual_files - expected_files)
    if unexpected:
        raise BundleIntegrityError(f"Bundle contains unmanifested files: {', '.join(unexpected)}")

    entries = {artifact.path: artifact for artifact in bundle.artifacts}
    for manifest_artifact_path, expected_digest in (
        ("hop-spec.json", bundle.spec_digest),
        ("hop-plan.json", bundle.plan_digest),
    ):
        if (
            manifest_artifact_path not in entries
            or entries[manifest_artifact_path].digest != expected_digest
        ):
            raise BundleIntegrityError(
                f"Bundle {manifest_artifact_path} digest does not match manifest root."
            )

    computed_manifest_digest = manifest_digest_for_bundle(bundle)
    if computed_manifest_digest != bundle.manifest_digest:
        raise BundleIntegrityError("Bundle manifest digest mismatch.")
    expected_bundle_id = bundle_id(
        design_id=bundle.design_id,
        manifest_digest=computed_manifest_digest,
    )
    if bundle.bundle_id != expected_bundle_id:
        raise BundleIntegrityError("Bundle identifier does not match its content digest.")

    required_artifacts = {
        "final-insert.fasta",
        "hop-plan.json",
        "hop-spec.json",
        "provenance.json",
    }
    missing_required = sorted(required_artifacts - artifact_contents.keys())
    if missing_required:
        raise BundleIntegrityError(
            f"Bundle omits required artifacts: {', '.join(missing_required)}"
        )
    try:
        spec = _SPEC_ADAPTER.validate_json(artifact_contents["hop-spec.json"])
    except Exception as exc:
        raise BundleIntegrityError(f"Bundle hop-spec.json is invalid: {exc}") from exc
    try:
        plan = HopPlan.model_validate_json(artifact_contents["hop-plan.json"])
    except Exception as exc:
        raise BundleIntegrityError(f"Bundle hop-plan.json is invalid: {exc}") from exc
    try:
        provenance = ProvenanceRecord.model_validate_json(artifact_contents["provenance.json"])
    except Exception as exc:
        raise BundleIntegrityError(f"Bundle provenance.json is invalid: {exc}") from exc

    if spec.design_id != bundle.design_id or plan.design_id != bundle.design_id:
        raise BundleIntegrityError("Bundle design identity does not match its spec and plan.")
    if spec.payload.sequence != plan.payload_sequence:
        raise BundleIntegrityError("Bundle spec and plan disagree on the authored payload.")
    if plan.spec_digest != bundle.spec_digest:
        raise BundleIntegrityError("Bundle plan does not reference its exact spec digest.")
    if bundle.external_refs != spec.external_refs:
        raise BundleIntegrityError("Bundle external references do not match its spec.")
    if (
        plan.lock.defaults_ref != spec.defaults_ref
        or plan.lock.constraint_profile_ref != spec.constraint_profile_ref
        or plan.lock.processing_route_ref != spec.processing_route_ref
    ):
        raise BundleIntegrityError("Bundle plan lock does not match its authored spec references.")
    if isinstance(spec, HopSpec) and (
        plan.lock.foldback_junction_ref != spec.junction.foldback.ref
        or plan.lock.basal_junction_ref != spec.junction.basal.ref
    ):
        raise BundleIntegrityError("Bundle plan junction lock does not match its authored spec.")
    if isinstance(spec, ResolvedHopSpec) and plan.lock.catalog_ref != spec.catalog_ref:
        raise BundleIntegrityError("Bundle plan catalog lock does not match its authored spec.")

    provenance_lock = (
        provenance.compiler_version,
        provenance.defaults_ref,
        provenance.catalog_ref,
        provenance.constraint_profile_ref,
        provenance.processing_route_ref,
    )
    plan_lock = (
        plan.lock.compiler_version,
        plan.lock.defaults_ref,
        plan.lock.catalog_ref,
        plan.lock.constraint_profile_ref,
        plan.lock.processing_route_ref,
    )
    if (
        provenance.plan_id != plan.plan_id
        or provenance.spec_digest != bundle.spec_digest
        or provenance_lock != plan_lock
    ):
        raise BundleIntegrityError("Bundle provenance does not match its plan and spec.")
    if artifact_contents["final-insert.fasta"] != render_fasta(plan.final_insert):
        raise BundleIntegrityError("Bundle final-insert.fasta does not match its plan.")
    source_fasta = artifact_contents.get("source-oligo.fasta")
    if plan.source_oligo.sequence == plan.final_insert.sequence:
        if source_fasta is not None:
            raise BundleIntegrityError("Bundle contains a redundant source-oligo.fasta artifact.")
    elif source_fasta != render_fasta(plan.source_oligo):
        raise BundleIntegrityError("Bundle source-oligo.fasta does not match its plan.")
    return VerifiedBundleContents(
        bundle=bundle,
        spec=spec,
        plan=plan,
        provenance=provenance,
        artifacts=MappingProxyType(artifact_contents),
    )
