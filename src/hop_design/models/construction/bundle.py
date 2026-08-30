"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/bundle.py

Defines the portable authority manifest for one complete-construction result.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.bundle import ArtifactManifestEntry
from hop_design.models.references import ReferenceId


class ConstructionBundle(HopModel):
    """Content-addressed authority for one verified complete-construction result."""

    schema_id: Literal["hop.construction-bundle/v3"] = Field(
        default="hop.construction-bundle/v3", alias="schema"
    )
    bundle_id: ReferenceId
    result_id: ReferenceId
    design_bundle_id: ReferenceId
    result_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    manifest_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    artifacts: tuple[ArtifactManifestEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_artifact_paths(self) -> ConstructionBundle:
        paths = tuple(artifact.path for artifact in self.artifacts)
        if len(paths) != len(set(paths)):
            raise ValueError("Construction-bundle artifact paths must be unique.")
        return self


__all__ = ["ConstructionBundle"]
