"""Renderer-independent workflow view contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from hop_design.models.base import HopModel
from hop_design.models.coordinates import Span
from hop_design.models.junction import Strand
from hop_design.models.references import ReferenceId
from hop_design.models.sequence import SequenceValidationError, normalize_dna_sequence


class TrackDirection(StrEnum):
    FORWARD = "5to3"
    REVERSE = "3to5"


class ViewTrack(HopModel):
    track_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    label: str = Field(min_length=1)
    sequence: str
    strand: Strand
    direction: TrackDirection

    @field_validator("sequence", mode="before")
    @classmethod
    def normalize_sequence(cls, value: object) -> str:
        if not isinstance(value, str):
            raise SequenceValidationError("DNA sequence must be a string.")
        return normalize_dna_sequence(value, allow_degenerate=True)


class ViewFeature(HopModel):
    feature_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    track_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    role: str = Field(min_length=1)
    label: str = Field(min_length=1)
    span: Span


class ViewPairing(HopModel):
    left_track_id: str
    left_index: int = Field(ge=0)
    right_track_id: str
    right_index: int = Field(ge=0)
    kind: Literal["watson_crick", "gt_wobble", "hard_mismatch"]


class ViewPanel(HopModel):
    panel_id: str = Field(pattern=r"^[a-z][a-z0-9_-]*$")
    title: str = Field(min_length=1)
    tracks: tuple[ViewTrack, ...] = Field(min_length=1)
    features: tuple[ViewFeature, ...] = ()
    pairings: tuple[ViewPairing, ...] = ()

    @model_validator(mode="after")
    def validate_references(self) -> ViewPanel:
        tracks = {track.track_id: track for track in self.tracks}
        if len(tracks) != len(self.tracks):
            raise ValueError("View panel track ids must be unique.")
        feature_ids = tuple(feature.feature_id for feature in self.features)
        if len(feature_ids) != len(set(feature_ids)):
            raise ValueError("View panel feature ids must be unique.")
        for feature in self.features:
            track = tracks.get(feature.track_id)
            if track is None:
                raise ValueError("View feature must reference a panel track.")
            if feature.span.end.offset > len(track.sequence):
                raise ValueError("View feature span must stay inside its referenced track.")
        for pairing in self.pairings:
            left = tracks.get(pairing.left_track_id)
            right = tracks.get(pairing.right_track_id)
            if left is None or right is None:
                raise ValueError("View pairing must reference panel tracks.")
            if pairing.left_index >= len(left.sequence) or pairing.right_index >= len(
                right.sequence
            ):
                raise ValueError("View pairing indexes must stay inside their tracks.")
        return self


class WorkflowView(HopModel):
    schema_id: Literal["hop.workflow-view/v1"] = Field(
        default="hop.workflow-view/v1", alias="schema"
    )
    view_id: ReferenceId
    kind: Literal["foldback_qa", "released_workflow", "basal_terminal_nick"]
    panels: tuple[ViewPanel, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_panels(self) -> WorkflowView:
        panel_ids = tuple(panel.panel_id for panel in self.panels)
        if len(panel_ids) != len(set(panel_ids)):
            raise ValueError("Workflow view panel ids must be unique.")
        return self


__all__ = [
    "TrackDirection",
    "ViewFeature",
    "ViewPairing",
    "ViewPanel",
    "ViewTrack",
    "WorkflowView",
]
