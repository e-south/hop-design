"""Measured local teaching annotations, separate from molecule and page composition."""

from .features import local_dimensions, projected_end_spans
from .layout import (
    OverviewLabels,
    compact_recognition_overlays,
    label_backplates,
    teaching_brackets,
)

__all__ = [
    "OverviewLabels",
    "compact_recognition_overlays",
    "label_backplates",
    "local_dimensions",
    "projected_end_spans",
    "teaching_brackets",
]
