"""Portable bundle manifest contracts."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.method import MethodKind
from hop_design.models.references import ExternalRef, ReferenceId
from hop_design.serialization import canonical_json_bytes, sha256_digest


class ArtifactManifestEntry(HopModel):
    """A content-addressed file in a HOP bundle."""

    path: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)

    @field_validator("path")
    @classmethod
    def require_safe_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not path.parts or path.is_absolute() or ".." in path.parts or value != path.as_posix():
            raise ValueError("Bundle artifact path must be a normalized safe relative path.")
        return value


class HopBundle(HopModel):
    """A content-addressed root manifest for one HOP compilation."""

    schema_id: Literal["hop.bundle/v2"] = Field(default="hop.bundle/v2", alias="schema")
    bundle_id: ReferenceId
    design_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    spec_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    manifest_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    artifacts: tuple[ArtifactManifestEntry, ...]
    external_refs: tuple[ExternalRef, ...] = ()


def bundle_manifest_seed(
    *,
    design_id: str,
    spec_digest: str,
    plan_digest: str,
    artifacts: Sequence[ArtifactManifestEntry],
    external_refs: Sequence[ExternalRef],
) -> dict[str, object]:
    """Return the canonical content sealed by a design-bundle manifest."""
    return {
        "artifacts": [item.model_dump(mode="json") for item in artifacts],
        "design_id": design_id,
        "external_refs": [item.model_dump(mode="json") for item in external_refs],
        "plan_digest": plan_digest,
        "spec_digest": spec_digest,
    }


def manifest_digest_for_bundle(bundle: HopBundle) -> str:
    """Recompute the manifest digest of an embedded design bundle."""
    return sha256_digest(
        canonical_json_bytes(
            bundle_manifest_seed(
                design_id=bundle.design_id,
                spec_digest=bundle.spec_digest,
                plan_digest=bundle.plan_digest,
                artifacts=bundle.artifacts,
                external_refs=bundle.external_refs,
            )
        )
    )


def bundle_id(*, design_id: str, manifest_digest: str) -> str:
    """Derive the stable design-bundle identifier from its manifest digest."""
    suffix = manifest_digest.removeprefix("sha256:")[:16]
    return f"hop:bundle/{design_id}/{suffix}"


def validate_bundle_manifest(bundle: HopBundle) -> None:
    """Require an embedded bundle to replay its exact manifest and root identity."""
    manifest_digest = manifest_digest_for_bundle(bundle)
    if bundle.manifest_digest != manifest_digest or bundle.bundle_id != bundle_id(
        design_id=bundle.design_id,
        manifest_digest=manifest_digest,
    ):
        raise ValueError("Design bundle manifest and root identity must replay exactly.")


class ProvenanceRecord(HopModel):
    """Deterministic compilation provenance without host-specific state."""

    schema_id: Literal["hop.provenance/v2"] = Field(default="hop.provenance/v2", alias="schema")
    compiler_distribution: Literal["hop-design"] = "hop-design"
    compiler_version: str = Field(min_length=1)
    plan_id: ReferenceId
    spec_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    defaults_ref: ReferenceId
    catalog_ref: ReferenceId
    constraint_profile_ref: ReferenceId
    design_derivation_ref: ReferenceId


class MethodBundle(HopModel):
    """Content-addressed output for one complete method request."""

    schema_id: Literal["hop.method-bundle/v2"] = Field(
        default="hop.method-bundle/v2", alias="schema"
    )
    bundle_id: ReferenceId
    request_id: ReferenceId
    method_kind: MethodKind
    compiler_version: str = Field(min_length=1)
    request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    hairpin_encoding_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    manifest_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    artifacts: tuple[ArtifactManifestEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_artifact_paths(self) -> MethodBundle:
        paths = tuple(artifact.path for artifact in self.artifacts)
        if len(paths) != len(set(paths)):
            raise ValueError("Method-bundle artifact paths must be unique.")
        return self
