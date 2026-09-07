#!/usr/bin/env python3
"""
--------------------------------------------------------------------------------
HOP Design
examples/compile_construction.py

Compiles, verifies, and projects one file-oriented construction request.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import hop_design as hop
import hop_design.construction as construction


def _projection_digests(
    projection: construction.ConstructionProjection,
) -> dict[str, str]:
    digests = {
        "json": hashlib.sha256(projection.json_bytes).hexdigest(),
        "svg": hashlib.sha256(projection.svg_bytes).hexdigest(),
    }
    if projection.csv_bytes is not None:
        digests["csv"] = hashlib.sha256(projection.csv_bytes).hexdigest()
    return digests


def compile_example(
    *,
    design_path: Path,
    source_path: Path,
    output: Path,
    trajectory_realization_id: str | None,
) -> dict[str, object]:
    """Compile one design and construction source into verified public artifacts."""
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Construction example output already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()
    try:
        design = hop.compile(hop.load_spec(design_path))
        design_bundle = design.write(output / "design")
        receipt = construction.compile_construction(
            source_path,
            design_bundle_path=design_bundle,
        )
        construction_bundle = receipt.write(output / "construction")
        verified = construction.load_verified_construction_bundle(construction_bundle)
        if (
            trajectory_realization_id is not None
            and trajectory_realization_id not in verified.materialized_realization_ids
        ):
            raise ValueError(
                f"Trajectory realization {trajectory_realization_id!r} is not an accepted "
                "construction realization."
            )

        projections = {
            "foldback_feasibility": construction.project_foldback_feasibility(verified),
            "foldback_retained_overhead": construction.project_retained_overhead_frontier(
                verified,
                family="foldback",
            ),
            "navigation": construction.project_construction_navigation(verified),
            "summary": construction.project_complete_construction_summary(verified),
        }
        if verified.endpoint != "ssdna_hairpin":
            projections.update(
                {
                    "basal_feasibility": construction.project_basal_feasibility(verified),
                    "basal_retained_overhead": construction.project_retained_overhead_frontier(
                        verified,
                        family="basal",
                    ),
                }
            )
        if trajectory_realization_id is not None:
            selection = construction.select_construction_realization(
                verified,
                materialized_realization_id=trajectory_realization_id,
            )
            selection.write(output / "selected-route.json")
            projections["trajectory"] = construction.project_construction_trajectory(
                verified,
                materialized_realization_id=trajectory_realization_id,
            )
            selection_sha256 = hashlib.sha256(selection.json_bytes).hexdigest()
        else:
            selection_sha256 = None
        for name, projection in projections.items():
            projection.write(output / "projections" / name)

        frontier = json.loads(projections["foldback_retained_overhead"].json_bytes)
        foldback_overhead_levels = [
            {
                "retained_overhead_nt": level["retained_overhead_nt"],
                "realization_count": level["realization_count"],
            }
            for level in frontier["levels"]
        ]
    except BaseException:
        shutil.rmtree(output, ignore_errors=True)
        raise

    case = source_path.stem.removeprefix("construction-")
    return {
        "bundle_id": verified.bundle_id,
        "bundle_verified": True,
        "case": case,
        "design_bundle_id": verified.design_bundle_id,
        "endpoint": verified.endpoint,
        "foldback_overhead_levels": foldback_overhead_levels,
        "materialized_realization_ids": list(verified.materialized_realization_ids),
        "projection_sha256": {
            name: _projection_digests(projection)
            for name, projection in sorted(projections.items())
        },
        "result_id": verified.result_id,
        "schema": "hop.construction-dogfood/v2",
        "selection_sha256": selection_sha256,
        "selected_trajectory_realization_id": trajectory_realization_id,
        "status": verified.status,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--trajectory-realization-id")
    args = parser.parse_args()
    summary = compile_example(
        design_path=args.design,
        source_path=args.source,
        output=args.out,
        trajectory_realization_id=args.trajectory_realization_id,
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
