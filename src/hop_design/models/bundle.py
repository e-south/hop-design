"""Portable bundle manifest contracts."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.method import MethodKind
from hop_design.models.references import ExternalRef, ReferenceId


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
    """A verified, portable inventory for one HOP compilation."""

    schema_id: Literal["hop.bundle/v1"] = Field(default="hop.bundle/v1", alias="schema")
    bundle_id: ReferenceId
    design_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,63}$")
    spec_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    plan_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    manifest_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    artifacts: tuple[ArtifactManifestEntry, ...]
    external_refs: tuple[ExternalRef, ...] = ()


class ProvenanceRecord(HopModel):
    """Deterministic compilation provenance without host-specific state."""

    schema_id: Literal["hop.provenance/v1"] = Field(default="hop.provenance/v1", alias="schema")
    compiler_distribution: Literal["hop-design"] = "hop-design"
    compiler_version: str = Field(min_length=1)
    plan_id: ReferenceId
    spec_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    defaults_ref: ReferenceId
    catalog_ref: ReferenceId
    constraint_profile_ref: ReferenceId
    processing_route_ref: ReferenceId


class MethodBundle(HopModel):
    """Content-addressed output for one complete method request."""

    schema_id: Literal["hop.method-bundle/v1"] = Field(
        default="hop.method-bundle/v1", alias="schema"
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
