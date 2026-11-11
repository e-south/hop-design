"""Explicit identity and byte bindings for read-only recorded-discovery capture."""

from typing import Literal

from pydantic import Field, field_validator

from hop_design.models.base import HopModel

from .manifest import Digest, EditionArtifact, artifact_path


class RecordedDesignSource(HopModel):
    schema_id: Literal["hop.recorded-design-source/v1"] = Field(
        default="hop.recorded-design-source/v1", alias="schema"
    )
    producer: dict[str, str]
    snapshot_digest: Digest
    files: dict[str, EditionArtifact]

    @field_validator("producer")
    @classmethod
    def complete_producer(cls, value: dict[str, str]) -> dict[str, str]:
        required = {
            "package_version",
            "package_content",
            "python",
            "implementation",
            "pydantic",
            "pydantic-core",
            "PyYAML",
            "typer",
        }
        if set(value) not in (required, required | {"package_code"}) or any(
            not item for item in value.values()
        ):
            raise ValueError("Bind the complete recorded producer identity.")
        for key in ("package_content", "package_code"):
            if key not in value:
                continue
            content = value[key]
            if (
                not content.startswith("sha256:")
                or len(content) != 71
                or any(character not in "0123456789abcdef" for character in content[7:])
            ):
                raise ValueError("Recorded producer content must be a SHA-256 digest.")
        return value

    @field_validator("files")
    @classmethod
    def source_files(cls, value: dict[str, EditionArtifact]) -> dict[str, EditionArtifact]:
        if not {"survey.sqlite", "effort.json", "intent/manifest.json"} <= value.keys():
            raise ValueError("Bind the checkpoint, execution effort and complete resolved intent.")
        for name in value:
            artifact_path(name)
            if name not in {"survey.sqlite", "effort.json"} and not name.startswith(
                ("intent/", "revision/")
            ):
                raise ValueError("Recorded source bindings contain an unexpected input path.")
        return value
