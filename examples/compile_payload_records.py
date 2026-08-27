#!/usr/bin/env python3
"""
--------------------------------------------------------------------------------
HOP Design
examples/compile_payload_records.py

Compiles bounded payload records against one explicit hairpin anatomy.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

import hop_design as hop


def _foldback() -> hop.FoldbackOption:
    return hop.FoldbackOption(
        option_id="selected-foldback",
        request=hop.FoldbackEvaluationRequest(
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
                terminal_watson_crick_bp_min=0,
                terminal_watson_crick_bp_max=4,
                max_uninterrupted_watson_crick_bp=4,
                max_added_nt=5,
                required_turn_nt=3,
                allow_protected_region_non_watson_crick_pairs=False,
            ),
        ),
    )


def _basal() -> hop.BasalOption:
    return hop.BasalOption(
        option_id="selected-basal",
        request=hop.BasalDesignRequest(
            pairing=hop.BasalPairingRequest(
                left_arm="AAAA",
                right_arm="TTTT",
            ),
            constraints=hop.BasalConstraintProfile(
                require_terminal_watson_crick=True,
                allow_active_gt_wobble=True,
                max_active_hard_mismatches=0,
                max_active_non_watson_crick_pairs=0,
                forbid_active_middle_double_hard=True,
                minimum_active_pair_support_index=4.0,
                maximum_active_pair_disruption_index=0.0,
                require_outer_hard_for_active_double=True,
                reject_compact_profiles=(),
                reserve_compact_profiles=(),
            ),
            acceptance="active_only",
            terminal_nick=None,
        ),
    )


def _design_space() -> hop.ResolvedDesignSpace:
    payloads = hop.collect_payloads(
        (
            hop.PayloadRecord(
                record_id="decoy-a",
                payload=hop.ExactPayload(sequence="AGTG"),
            ),
            hop.PayloadRecord(
                record_id="decoy-b",
                payload=hop.ExactPayload(sequence="CATT"),
            ),
            hop.PayloadRecord(
                record_id="decoy-c",
                payload=hop.ExactPayload(sequence="GCTA"),
            ),
        ),
        duplicate_policy=hop.DuplicateSequencePolicy.FAIL,
    )
    return hop.ResolvedDesignSpace(
        space_id="payload-records",
        payloads=payloads,
        foldbacks=(_foldback(),),
        basals=(_basal(),),
        releases=(hop.ReleaseOption(option_id="no-release-claim", request=None),),
        defaults_ref="example:defaults/payload-first@1",
        catalog_ref="example:catalog/payload-first-anatomy@1",
        constraint_profile_ref="example:constraint-profile/payload-first@1",
        design_derivation_ref="example:design-derivation/payload-first@1",
        per_design_constraints=hop.DesignLimits(max_candidates=1),
        limits=hop.DesignSpaceLimits(max_designs=3),
        duplicate_final_sequence_policy=hop.DuplicateDesignSequencePolicy.FAIL,
    )


def compile_payload_records(output: Path) -> dict[str, object]:
    """Write and replay one bundle per payload under a create-only root."""
    target = output.expanduser().resolve()
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"Payload-record output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    space = _design_space()
    plan = hop.plan_design_space(space)
    if plan.infeasible_count:
        raise ValueError("The example payload records contain an infeasible design.")

    temporary_root = Path(tempfile.mkdtemp(prefix=f".{target.name}.staging-", dir=target.parent))
    staging = temporary_root / target.name
    staging.mkdir()
    rows: list[dict[str, str]] = []
    try:
        for row in plan.rows:
            compilation = hop.compile(row.spec)
            bundle_path = compilation.write(staging / row.payload_record_id)
            verified = hop.load_verified_bundle(bundle_path)
            rows.append(
                {
                    "bundle_id": verified.bundle.bundle_id,
                    "design_id": verified.plan.design_id,
                    "encoding_digest": (verified.plan.hairpin_encoding_insert.sequence_digest),
                    "paired_payload_sequence": verified.plan.paired_payload_sequence,
                    "payload_id": row.payload_record_id,
                    "payload_sequence": verified.plan.payload_sequence,
                }
            )
        staging.rename(target)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)

    return {
        "bundle_verified_count": len(rows),
        "design_count": plan.cardinality,
        "designs": rows,
        "feasible_count": plan.feasible_count,
        "method_resolution_status": "not_evaluated",
        "payload_count": len(space.payloads.records),
        "schema": "hop.payload-record-compilation/v1",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(compile_payload_records(args.out), sort_keys=True))


if __name__ == "__main__":
    main()
