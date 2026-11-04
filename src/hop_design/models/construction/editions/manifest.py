"""Portable edition contracts; captured evidence is not a new molecular authority."""

from pathlib import PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.intents.refinement import DesignRefinementQuery
from hop_design.models.construction.surveys.query import InterfaceSurveyQuery

Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


def artifact_path(value: str) -> str:
    path = PurePosixPath(value)
    if (
        not value
        or value == "."
        or path.is_absolute()
        or path.as_posix() != value
        or ".." in path.parts
        or "\\" in value
        or "\x00" in value
    ):
        raise ValueError("Edition artifacts require normalized relative paths.")
    return value


class EditionArtifact(HopModel):
    sha256: Digest
    bytes: int = Field(ge=0)


class EditionMember(HopModel):
    materialized_realization_id: str = Field(min_length=1)
    directory: Annotated[str, Field(pattern=r"^members/[0-9a-f]{64}$")]


class AtlasEditionManifest(HopModel):
    schema_id: Literal["hop.atlas-edition/v1", "hop.atlas-edition/v2"] = Field(
        default="hop.atlas-edition/v1", alias="schema"
    )
    producer: dict[str, str]
    snapshot_digest: Digest
    members: tuple[EditionMember, ...] = Field(min_length=1)
    artifacts: dict[str, EditionArtifact]

    @field_validator("artifacts")
    @classmethod
    def safe_paths(cls, value: dict[str, EditionArtifact]) -> dict[str, EditionArtifact]:
        for name in value:
            artifact_path(name)
        if "edition.json" in value:
            raise ValueError("Edition manifest cannot inventory itself.")
        return value

    @model_validator(mode="after")
    def complete_members(self) -> Self:
        identities = [m.materialized_realization_id for m in self.members]
        directories = [m.directory for m in self.members]
        if len(set(identities)) != len(identities) or len(set(directories)) != len(directories):
            raise ValueError("Edition members must be unique preparations.")
        required = {"choices.json", "resolution.json"}
        if self.schema_id == "hop.atlas-edition/v2":
            required.add("descriptors.json")
        for member in self.members:
            if self.schema_id == "hop.atlas-edition/v2":
                required.update(
                    f"{member.directory}/{name}" for name in ("selection.json", "evidence.zip")
                )
                continue
            required.update(
                f"{member.directory}/{name}"
                for name in (
                    "selection.json",
                    "atlas/summary.json",
                    "atlas/projection.svg",
                    "atlas/manifest.json",
                    "atlas/report.md",
                )
            )
            if not any(
                name.startswith(f"{member.directory}/materials/") for name in self.artifacts
            ):
                raise ValueError("Edition member has no captured materials.")
        if not required <= self.artifacts.keys():
            raise ValueError("Edition is missing required molecular artifacts.")
        return self


class EditionSelection(HopModel):
    schema_id: Literal["hop.atlas-edition-selection/v1"] = Field(
        default="hop.atlas-edition-selection/v1", alias="schema"
    )
    edition_digest: Digest
    materialized_realization_id: str = Field(min_length=1)
    query: InterfaceSurveyQuery | DesignRefinementQuery = Field(
        default_factory=InterfaceSurveyQuery
    )
