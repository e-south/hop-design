"""Bind the shared achieved hairpin architecture to one exact selected result."""

from hop_design.models.construction.hairpin_geometry import describe_hairpin
from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection
from hop_design.models.construction.projections.trajectory import (
    CompleteConstructionTrajectoryProjection,
)


def project_hairpin_portrait(
    trajectory: CompleteConstructionTrajectoryProjection,
) -> HairpinPortraitProjection:
    architecture = describe_hairpin(trajectory.realization)
    return HairpinPortraitProjection.create(
        source_result_id=trajectory.source_result_id,
        materialized_realization_id=trajectory.realization.materialized_realization_id,
        **dict(architecture),
    )


__all__ = ["project_hairpin_portrait"]
