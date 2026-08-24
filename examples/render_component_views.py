#!/usr/bin/env python3
"""Render route-neutral foldback and basal component views."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import hop_design as hop
import hop_design.views as views


def _foldback_evaluation() -> hop.FoldbackEvaluation:
    return hop.evaluate_foldback(
        hop.FoldbackEvaluationRequest(
            precursor_sequence="CCTCAGCA",
            retained_tract_span=hop.Span(
                start=hop.Boundary(offset=2),
                end=hop.Boundary(offset=6),
            ),
            source_turn_span=hop.Span(
                start=hop.Boundary(offset=6),
                end=hop.Boundary(offset=8),
            ),
            protected_region=hop.Span(
                start=hop.Boundary(offset=0),
                end=hop.Boundary(offset=2),
            ),
            turn_extension="T",
            foldback_arm="CTGA",
            constraints=hop.FoldbackConstraints(
                max_non_watson_crick_pairs=0,
                terminal_watson_crick_bp_min=4,
                terminal_watson_crick_bp_max=4,
                max_uninterrupted_watson_crick_bp=4,
                max_added_nt=5,
                required_turn_nt=3,
                allow_protected_region_non_watson_crick_pairs=False,
            ),
        )
    )


def _basal_evaluation() -> hop.BasalEvaluation:
    return hop.evaluate_basal_pairing(
        hop.BasalPairingRequest(left_arm="AGTG", right_arm="CATG"),
        constraints=hop.BasalConstraintProfile(
            require_terminal_watson_crick=False,
            allow_active_gt_wobble=True,
            max_active_hard_mismatches=4,
            max_active_non_watson_crick_pairs=4,
            forbid_active_middle_double_hard=False,
            minimum_active_pair_support_index=0.0,
            maximum_active_pair_disruption_index=4.0,
            require_outer_hard_for_active_double=False,
            reject_compact_profiles=(),
            reserve_compact_profiles=(),
        ),
    )


def _digest(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def render_component_views(output: Path) -> dict[str, object]:
    """Write two typed view documents and their deterministic SVG renderings."""
    target = output.expanduser().resolve()
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Component-view output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    foldback = views.build_foldback_junction_view(_foldback_evaluation())
    basal = views.build_basal_pairing_view(_basal_evaluation())
    artifacts = {
        "foldback-junction.json": foldback.model_dump_json(
            by_alias=True,
            indent=2,
        ).encode()
        + b"\n",
        "foldback-junction.svg": views.render_workflow_svg(foldback),
        "basal-junction.json": basal.model_dump_json(by_alias=True, indent=2).encode() + b"\n",
        "basal-junction.svg": views.render_workflow_svg(basal),
    }

    temporary_root = Path(tempfile.mkdtemp(prefix=f".{target.name}.staging-", dir=target.parent))
    staging = temporary_root / target.name
    staging.mkdir()
    try:
        for relative, content in artifacts.items():
            (staging / relative).write_bytes(content)
        staging.rename(target)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)

    return {
        "artifacts": {
            relative: _digest(content) for relative, content in sorted(artifacts.items())
        },
        "basal_pair_kinds": [pair.kind for pair in basal.panels[0].pairings],
        "schema": "hop.component-view-demo/v1",
        "view_kinds": [foldback.kind, basal.kind],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(render_component_views(args.out), sort_keys=True))


if __name__ == "__main__":
    main()
