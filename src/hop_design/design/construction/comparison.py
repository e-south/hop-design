"""One typed comparison shared by scientific consumers and the human report."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Self

from hop_design.export.publication import publish_file_create_only
from hop_design.models.construction.projections.comparison import (
    ComparisonSelection,
    ConstructionComparisonProjection,
    PropertyComparison,
)
from hop_design.models.construction.projections.materials import external_material_uses
from hop_design.serialization import canonical_json_bytes

from .comparison_facts import _facts
from .comparison_regions import regional_facts
from .complete.bundle import ConstructionCompilation, VerifiedConstructionBundle
from .projections.trajectory import project_complete_construction_trajectory
from .public import _source


@dataclass(frozen=True, init=False, repr=False)
class ConstructionComparison:
    """Opaque comparison receipt; complete authorities remain with its two inputs."""

    _projection: ConstructionComparisonProjection

    @classmethod
    def _create(cls, projection: ConstructionComparisonProjection) -> Self:
        instance = object.__new__(cls)
        object.__setattr__(instance, "_projection", projection)
        return instance

    @property
    def json_bytes(self) -> bytes:
        return canonical_json_bytes(self._projection.model_dump(mode="json", by_alias=True))

    @property
    def report_text(self) -> str:
        from hop_design.export.construction.handoff.comparison import render_construction_comparison

        return render_construction_comparison(self._projection)

    def write(self, destination: str | Path) -> Path:
        """Write one create-only JSON projection, suitable for caller-owned analysis."""
        output = Path(destination)
        if output.suffix != ".json":
            raise ValueError("Comparison output must use the .json extension.")
        publish_file_create_only(self.json_bytes, output)
        return output


def project_construction_comparison(
    left: ConstructionCompilation | VerifiedConstructionBundle,
    right: ConstructionCompilation | VerifiedConstructionBundle,
    *,
    left_realization_id: str,
    right_realization_id: str,
) -> ConstructionComparison:
    """Compare complete selected products, preserving sequences, chemistry and stage."""
    sources = (_source(left), _source(right))
    trajectories = tuple(
        project_complete_construction_trajectory(source, materialized_realization_id=selected)
        for source, selected in zip(
            sources, (left_realization_id, right_realization_id), strict=True
        )
    )
    properties = []
    legacy = [_facts(t) for t in trajectories]
    for label in dict.fromkeys((*legacy[0], *legacy[1])):
        a, b = (f.get(label, "not required") for f in legacy)
        properties.append(
            PropertyComparison(
                field="preparation." + label, label=label, left=a, right=b, changed=a != b
            )
        )
    regions = [regional_facts(t) for t in trajectories]
    for field in dict.fromkeys((*regions[0], *regions[1])):
        a_value, b_value = (f.get(field) for f in regions)
        properties.append(
            PropertyComparison(
                field=field, label=field, left=a_value, right=b_value, changed=a_value != b_value
            )
        )
    roles = [
        {use.role: material.material_id for material, use in external_material_uses(t.realization)}
        for t in trajectories
    ]
    all_roles = tuple(dict.fromkeys((*roles[0], *roles[1])))
    selections = tuple(
        ComparisonSelection(
            source_result_id=t.source_result_id,
            materialized_realization_id=t.realization.materialized_realization_id,
            composition_status=s.result.status.value,
        )
        for t, s in zip(trajectories, sources, strict=True)
    )
    return ConstructionComparison._create(
        ConstructionComparisonProjection.create(
            left=selections[0],
            right=selections[1],
            properties=tuple(properties),
            changed_material_roles=tuple(
                r for r in all_roles if roles[0].get(r) != roles[1].get(r)
            ),
            unchanged_material_roles=tuple(
                r for r in all_roles if roles[0].get(r) == roles[1].get(r)
            ),
        )
    )
