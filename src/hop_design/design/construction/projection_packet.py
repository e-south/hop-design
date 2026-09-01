"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/projection_packet.py

Provides portable bytes for one non-authoritative construction projection.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from hop_design.export.construction import (
    render_projection_csv,
    render_projection_json,
    render_projection_svg,
)
from hop_design.export.publication import publish_directory_create_only
from hop_design.models.construction.projections import (
    CompleteConstructionSummaryProjection,
    CompleteConstructionTrajectoryProjection,
    ConstructionNavigationProjection,
    LocalScientificProjection,
)

type _TypedProjection = (
    LocalScientificProjection
    | CompleteConstructionSummaryProjection
    | CompleteConstructionTrajectoryProjection
    | ConstructionNavigationProjection
)


@dataclass(frozen=True, init=False, repr=False)
class ConstructionProjection:
    """Portable deterministic bytes for one non-authoritative scientific projection."""

    _projection: _TypedProjection

    @classmethod
    def _create(cls, projection: _TypedProjection) -> Self:
        instance = object.__new__(cls)
        object.__setattr__(instance, "_projection", projection)
        return instance

    @property
    def schema_id(self) -> str:
        """Return the typed projection schema."""
        return self._projection.schema_id

    @property
    def projection_id(self) -> str:
        """Return the deterministic projection identity."""
        return self._projection.projection_id

    @property
    def source_result_id(self) -> str:
        """Return the construction result projected by these bytes."""
        return self._projection.source_result_id

    @property
    def renderer_version(self) -> str:
        """Return the deterministic renderer contract version."""
        return self._projection.renderer_version

    @property
    def json_bytes(self) -> bytes:
        """Return canonical JSON projection bytes."""
        return render_projection_json(self._projection)

    @property
    def csv_bytes(self) -> bytes | None:
        """Return tidy CSV bytes when the projection defines a table."""
        if isinstance(self._projection, CompleteConstructionTrajectoryProjection):
            return None
        return render_projection_csv(self._projection)

    @property
    def svg_bytes(self) -> bytes:
        """Return deterministic scientific SVG bytes."""
        return render_projection_svg(self._projection)

    def write(self, destination: str | Path) -> Path:
        """Atomically write the projection packet into a new directory."""
        output = Path(destination)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing projection path: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            json_bytes = self.json_bytes
            csv_bytes = self.csv_bytes
            svg_bytes = self.svg_bytes
            (staging / "projection.json").write_bytes(json_bytes)
            if csv_bytes is not None:
                (staging / "projection.csv").write_bytes(csv_bytes)
            (staging / "projection.svg").write_bytes(svg_bytes)
            publish_directory_create_only(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return output

    def __repr__(self) -> str:
        return (
            f"ConstructionProjection(schema_id={self.schema_id!r}, "
            f"projection_id={self.projection_id!r}, "
            f"source_result_id={self.source_result_id!r})"
        )


__all__ = ["ConstructionProjection"]
