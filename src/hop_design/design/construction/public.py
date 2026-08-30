"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/public.py

Provides opaque construction receipts and deterministic scientific projections.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

from hop_design.design.construction.projections import (
    project_basal_feasibility as _project_basal_feasibility,
)
from hop_design.design.construction.projections import (
    project_complete_construction_summary as _project_complete_construction_summary,
)
from hop_design.design.construction.projections import (
    project_complete_construction_trajectory as _project_complete_construction_trajectory,
)
from hop_design.design.construction.projections import (
    project_foldback_feasibility as _project_foldback_feasibility,
)
from hop_design.design.construction.projections import (
    project_relaxation_frontier as _project_relaxation_frontier,
)
from hop_design.export.construction import (
    render_projection_csv,
    render_projection_json,
    render_projection_svg,
)
from hop_design.export.publication import publish_directory_create_only
from hop_design.models.construction.basal import BasalNeighborhoodDiscoveryResult
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from hop_design.models.construction.projections import (
    CompleteConstructionSummaryProjection,
    CompleteConstructionTrajectoryProjection,
    LocalScientificProjection,
)

from .complete.bundle import ConstructionCompilation, VerifiedConstructionBundle
from .complete.discovery import VerifiedConstructionSpaceResult
from .local_public import (
    LocalNeighborhoodDiscovery,
    discover_local_neighborhood,
    load_verified_local_neighborhood,
)
from .source_partition import (
    SourcePartitionDiscovery,
    discover_source_partition,
    load_verified_source_partition,
)


@dataclass(frozen=True, init=False, repr=False)
class ConstructionProjection:
    """Portable deterministic bytes for one non-authoritative scientific projection."""

    _schema_id: str
    _projection_id: str
    _source_result_id: str
    _renderer_version: str
    _json_bytes: bytes
    _csv_bytes: bytes | None
    _svg_bytes: bytes

    @classmethod
    def _create(
        cls,
        *,
        schema_id: str,
        projection_id: str,
        source_result_id: str,
        renderer_version: str,
        json_bytes: bytes,
        csv_bytes: bytes | None,
        svg_bytes: bytes,
    ) -> Self:
        instance = object.__new__(cls)
        object.__setattr__(instance, "_schema_id", schema_id)
        object.__setattr__(instance, "_projection_id", projection_id)
        object.__setattr__(instance, "_source_result_id", source_result_id)
        object.__setattr__(instance, "_renderer_version", renderer_version)
        object.__setattr__(instance, "_json_bytes", json_bytes)
        object.__setattr__(instance, "_csv_bytes", csv_bytes)
        object.__setattr__(instance, "_svg_bytes", svg_bytes)
        return instance

    @property
    def schema_id(self) -> str:
        """Return the typed projection schema."""
        return self._schema_id

    @property
    def projection_id(self) -> str:
        """Return the deterministic projection identity."""
        return self._projection_id

    @property
    def source_result_id(self) -> str:
        """Return the construction result projected by these bytes."""
        return self._source_result_id

    @property
    def renderer_version(self) -> str:
        """Return the deterministic renderer contract version."""
        return self._renderer_version

    @property
    def json_bytes(self) -> bytes:
        """Return canonical JSON projection bytes."""
        return self._json_bytes

    @property
    def csv_bytes(self) -> bytes | None:
        """Return tidy CSV bytes when the projection defines a table."""
        return self._csv_bytes

    @property
    def svg_bytes(self) -> bytes:
        """Return deterministic scientific SVG bytes."""
        return self._svg_bytes

    def write(self, destination: str | Path) -> Path:
        """Atomically write the projection packet into a new directory."""
        output = Path(destination)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing projection path: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            (staging / "projection.json").write_bytes(self._json_bytes)
            if self._csv_bytes is not None:
                (staging / "projection.csv").write_bytes(self._csv_bytes)
            (staging / "projection.svg").write_bytes(self._svg_bytes)
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


def _source(
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
) -> VerifiedConstructionSpaceResult:
    if not isinstance(receipt, ConstructionCompilation | VerifiedConstructionBundle):
        raise TypeError("Construction projections require a verified construction receipt.")
    return receipt._verified_source()


def _foldback_source(
    receipt: ConstructionCompilation | VerifiedConstructionBundle | LocalNeighborhoodDiscovery,
) -> FoldbackNeighborhoodDiscoveryResult:
    if isinstance(receipt, LocalNeighborhoodDiscovery):
        result = receipt._verified_source()
        if not isinstance(result, FoldbackNeighborhoodDiscoveryResult):
            raise ValueError("Local-neighborhood receipt contains basal evidence, not foldback.")
        return result
    return _source(receipt).foldback.result


def _basal_source(
    receipt: ConstructionCompilation | VerifiedConstructionBundle | LocalNeighborhoodDiscovery,
) -> BasalNeighborhoodDiscoveryResult:
    if isinstance(receipt, LocalNeighborhoodDiscovery):
        result = receipt._verified_source()
        if not isinstance(result, BasalNeighborhoodDiscoveryResult):
            raise ValueError("Local-neighborhood receipt contains foldback evidence, not basal.")
        return result
    basal = _source(receipt).basal
    if basal is None:
        raise ValueError("This construction does not contain a basal authority.")
    return basal.result


def _packet(
    projection: (
        LocalScientificProjection
        | CompleteConstructionSummaryProjection
        | CompleteConstructionTrajectoryProjection
    ),
) -> ConstructionProjection:
    csv_bytes = (
        None
        if isinstance(projection, CompleteConstructionTrajectoryProjection)
        else render_projection_csv(projection)
    )
    return ConstructionProjection._create(
        schema_id=projection.schema_id,
        projection_id=projection.projection_id,
        source_result_id=projection.source_result_id,
        renderer_version=projection.renderer_version,
        json_bytes=render_projection_json(projection),
        csv_bytes=csv_bytes,
        svg_bytes=render_projection_svg(projection),
    )


def compile_construction(
    source_path: str | Path,
    *,
    design_bundle_path: str | Path,
) -> ConstructionCompilation:
    """Compile one strict construction source against one verified design bundle."""
    from hop_design.design.construction.source import compile_construction_source

    return compile_construction_source(
        source_path,
        design_bundle_path=design_bundle_path,
    )


def load_verified_construction_bundle(
    bundle_path: str | Path,
) -> VerifiedConstructionBundle:
    """Load one portable construction authority after exact semantic replay."""
    from hop_design.design.construction.complete.bundle import (
        load_verified_construction_bundle as _load,
    )

    return _load(bundle_path)


def project_foldback_feasibility(
    receipt: ConstructionCompilation | VerifiedConstructionBundle | LocalNeighborhoodDiscovery,
) -> ConstructionProjection:
    """Project every exact foldback realization from one verified construction."""
    return _packet(_project_foldback_feasibility(_foldback_source(receipt)))


def project_basal_feasibility(
    receipt: ConstructionCompilation | VerifiedConstructionBundle | LocalNeighborhoodDiscovery,
) -> ConstructionProjection:
    """Project every exact basal realization from one verified construction."""
    return _packet(_project_basal_feasibility(_basal_source(receipt)))


def project_complete_construction_summary(
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
) -> ConstructionProjection:
    """Project lossless complete-route accounting from one verified construction."""
    return _packet(_project_complete_construction_summary(_source(receipt)))


def project_construction_trajectory(
    receipt: ConstructionCompilation | VerifiedConstructionBundle,
    *,
    materialized_realization_id: str,
) -> ConstructionProjection:
    """Project one explicitly selected accepted construction chronology."""
    return _packet(
        _project_complete_construction_trajectory(
            _source(receipt),
            materialized_realization_id=materialized_realization_id,
        )
    )


def project_relaxation_frontier(
    receipt: ConstructionCompilation | VerifiedConstructionBundle | LocalNeighborhoodDiscovery,
    *,
    family: Literal["foldback", "basal"],
) -> ConstructionProjection:
    """Project one explicitly selected local relaxation family."""
    if family == "foldback":
        return _packet(_project_relaxation_frontier(_foldback_source(receipt)))
    if family == "basal":
        return _packet(_project_relaxation_frontier(_basal_source(receipt)))
    raise ValueError("Construction projection family must be foldback or basal.")


__all__ = [
    "ConstructionCompilation",
    "ConstructionProjection",
    "LocalNeighborhoodDiscovery",
    "SourcePartitionDiscovery",
    "VerifiedConstructionBundle",
    "compile_construction",
    "discover_local_neighborhood",
    "discover_source_partition",
    "load_verified_construction_bundle",
    "load_verified_local_neighborhood",
    "load_verified_source_partition",
    "project_basal_feasibility",
    "project_complete_construction_summary",
    "project_construction_trajectory",
    "project_foldback_feasibility",
    "project_relaxation_frontier",
]
