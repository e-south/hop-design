"""Content bindings for a supplied preparation used only to order discovery."""

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.bundle import ArtifactManifestEntry
from hop_design.models.references import ReferenceId


class SurveyPreparationReference(HopModel):
    """The reference is replayed; its witness is never imported as a new result."""

    result_id: ReferenceId
    materialized_realization_id: ReferenceId
    files: tuple[ArtifactManifestEntry, ...] = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def bounded_authority(self) -> "SurveyPreparationReference":
        paths = tuple(entry.path for entry in self.files)
        if len(set(paths)) != len(paths):
            raise ValueError("Preferred preparation files must be distinct.")
        if "construction-bundle.json" not in paths:
            raise ValueError("Preferred preparation requires its construction manifest.")
        if sum(entry.size_bytes for entry in self.files) > 64 * 1024 * 1024:
            raise ValueError("Preferred preparation exceeds the 64-MiB input bound.")
        if any("\\" in path for path in paths):
            raise ValueError("Preferred preparation files require portable relative paths.")
        return self
