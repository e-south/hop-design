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
from hop_design.export.construction.handoff.materials import render_oligos_csv, render_oligos_fasta
from hop_design.export.construction.handoff.report import render_construction_report
from hop_design.export.publication import (
    publish_directory_create_only,
    publish_directory_files_create_only,
)
from hop_design.models.construction.projections import (
    CompleteConstructionTrajectoryProjection,
    ConstructionScientificProjection,
)


@dataclass(frozen=True, init=False, repr=False)
class ConstructionProjection:
    """Portable deterministic bytes for one non-authoritative scientific projection."""

    _projection: ConstructionScientificProjection

    @classmethod
    def _create(cls, projection: ConstructionScientificProjection) -> Self:
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

    def write(
        self,
        destination: str | Path,
        *,
        selection_reason: str | None = None,
        protected_root: str | Path | None = None,
    ) -> Path:
        """Atomically write the projection packet into a new directory."""
        if selection_reason is not None:
            if not isinstance(self._projection, CompleteConstructionTrajectoryProjection):
                raise ValueError("A selection reason only applies to a selected trajectory.")
            if not selection_reason.strip():
                raise ValueError("Selection reason must contain text.")
        output = Path(destination)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing projection path: {output}")
        files = self._artifact_files(selection_reason)
        if protected_root is not None:
            publish_directory_files_create_only(files, output, protected_root=Path(protected_root))
            return output
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            for name, content in files.items():
                (staging / name).write_bytes(content)
            publish_directory_create_only(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return output

    def _artifact_files(self, selection_reason: str | None) -> dict[str, bytes]:
        files = {"projection.json": self.json_bytes, "projection.svg": self.svg_bytes}
        csv_bytes = self.csv_bytes
        if csv_bytes is not None:
            files["projection.csv"] = csv_bytes
        if isinstance(self._projection, CompleteConstructionTrajectoryProjection):
            files["report.md"] = render_construction_report(
                self._projection, selection_reason=selection_reason
            )
            files["oligos.csv"] = render_oligos_csv(self._projection.realization)
            files["oligos.fasta"] = render_oligos_fasta(self._projection.realization)
        return files

    def __repr__(self) -> str:
        return (
            f"ConstructionProjection(schema_id={self.schema_id!r}, "
            f"projection_id={self.projection_id!r}, "
            f"source_result_id={self.source_result_id!r})"
        )


__all__ = ["ConstructionProjection"]
