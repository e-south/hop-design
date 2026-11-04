"""Evaluate complete alternatives against an explicitly chosen family reference."""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from hop_design.design.runtime import producer_identity
from hop_design.export.construction.scaffold.matching_text import render_matching_report
from hop_design.serialization import sha256_digest

from ..public import project_hairpin_portrait
from .admission import admit_family
from .capture import capture_family, write_snapshot
from .matching_candidates import capture_portrait, evaluate_member
from .packet import SourceBoundFamilyPacket
from .properties import shared_values


@dataclass(frozen=True, init=False, repr=False)
class MatchedConstructionFamily(SourceBoundFamilyPacket):
    _packet_schema: ClassVar[str] = "hop.family-matching-packet/v1"


def match_construction_family(
    path: str | Path, *, reference_member: str, reference_choice: int, max_continuations: int
) -> MatchedConstructionFamily:
    """Evaluate finite witness pairs; preserve requirements and leave selection explicit.

    Saved local domains and quotas remain unchanged. A local search omitted by an
    earlier stop runs under its original bound. Coverage concerns the recorded
    witness pairs, never all possible families or laboratory performance.
    """
    if type(max_continuations) is not int or not 1 <= max_continuations <= 64:
        raise ValueError("max_continuations must be an explicit integer from 1 to 64.")
    if type(reference_choice) is not int or reference_choice < 0:
        raise ValueError("reference_choice must be an explicit nonnegative integer.")
    producer = producer_identity()
    source_root, captured = capture_family(path)
    files = {"family/" + name: content for name, content in captured.items()}
    with tempfile.TemporaryDirectory(prefix="hop-family-match-") as temporary:
        root = Path(temporary)
        write_snapshot(captured, root / "family")
        family, members = admit_family(root / "family")
        reference = next((m for m in members if m.name == reference_member), None)
        if reference is None or reference.receipt is None:
            raise ValueError("Reference must identify a complete family member.")
        identities = reference.receipt.materialized_realization_ids
        if reference_choice >= len(identities):
            raise ValueError("Reference choice does not belong to that complete member.")
        identity = identities[reference_choice]
        portrait = project_hairpin_portrait(reference.receipt, materialized_realization_id=identity)
        capture_portrait(portrait, root, "reference", files)
        controls = shared_values(json.loads(portrait.json_bytes), family["shared_properties"])
        rows, remaining = [], max_continuations
        for member in sorted(members, key=lambda m: m.name):
            if member.name == reference_member:
                continue
            row = evaluate_member(
                root, member, family["shared_properties"], controls, remaining, files
            )
            remaining -= row["evaluated_pairs"]
            rows.append(row)
        evaluated = sum(r["evaluated_pairs"] for r in rows)
        recorded = sum(r["recorded_pairs"] for r in rows)
        summary = {
            "schema": "hop.family-matching-result/v1",
            "source_family_id": family["family_id"],
            "source_manifest_digest": sha256_digest(captured["manifest.json"]),
            "producer": producer,
            "reference": {
                "member": reference_member,
                "choice": reference_choice,
                "source_result_id": reference.receipt.result_id,
                "materialized_realization_id": identity,
                "properties": controls,
                "selection": {
                    "bundle_path": f"family/members/{reference_member}/outcome/construction",
                    "selection_path": "reference/selection.json",
                },
            },
            "shared_properties": family["shared_properties"],
            "members": rows,
            "coverage": {
                "max_continuations": max_continuations,
                "evaluated_pairs": evaluated,
                "recorded_pairs": recorded,
                "completion": "recorded_pairs_examined"
                if evaluated == recorded
                else "stopped_by_bound",
                "global_family_feasibility": "not_assessed",
            },
        }
    if len(files) > 19_998 or sum(map(len, files.values())) > 500 * 1024 * 1024:
        raise ValueError(
            "Family matching exceeds its bounded packet inventory; narrow the request."
        )
    if producer_identity() != producer:
        raise ValueError("HOP producer changed during family matching.")
    packet = MatchedConstructionFamily._create(files, summary, render_matching_report(summary))
    object.__setattr__(packet, "_roots", (source_root,))
    return packet
