"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/space_package.py

Inventories design-set authority files and writes regenerable projections.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping
from pathlib import Path

from hop_design.export.spaces import render_review_html
from hop_design.models.bundle import ArtifactManifestEntry
from hop_design.models.design_space import HairpinDesignSet, SubstrateSpaceSpec
from hop_design.serialization import sha256_digest


def render_designs_csv(
    design_set: HairpinDesignSet,
    member_encodings: Mapping[str, tuple[str, str]],
) -> bytes:
    """Render a readable exact-sequence index."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=(
            "ordinal",
            "variable_assignment",
            "exact_payload",
            "derived_paired_payload",
            "hairpin_encoding",
            "hairpin_length",
            "disposition",
            "member_bundle_id",
        ),
        lineterminator="\n",
    )
    writer.writeheader()
    for record in design_set.members:
        _, sequence = member_encodings[record.member_bundle_id]
        writer.writerow(
            {
                "ordinal": record.canonical_ordinal,
                "variable_assignment": ";".join(
                    f"{assignment.position}={assignment.base}"
                    for assignment in record.variable_assignment
                ),
                "exact_payload": record.exact_payload,
                "derived_paired_payload": record.derived_paired_payload,
                "hairpin_encoding": sequence,
                "hairpin_length": record.exact_hairpin_length,
                "disposition": record.disposition,
                "member_bundle_id": record.member_bundle_id,
            }
        )
    return output.getvalue().encode("utf-8")


def render_sequences_fasta(
    design_set: HairpinDesignSet,
    member_encodings: Mapping[str, tuple[str, str]],
) -> bytes:
    """Render exact hairpin encodings for downstream sequence handoff."""
    lines: list[str] = []
    for record in design_set.members:
        design_id, sequence = member_encodings[record.member_bundle_id]
        lines.extend((f">{design_id}", sequence))
    return ("\n".join(lines) + "\n").encode("utf-8")


def design_set_artifacts(bundle_root: Path) -> tuple[ArtifactManifestEntry, ...]:
    """Inventory every canonical design-set artifact except its root manifest."""
    media_types = {
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".fasta": "text/x-fasta",
        ".fa": "text/x-fasta",
    }
    return tuple(
        ArtifactManifestEntry(
            path=path.relative_to(bundle_root).as_posix(),
            media_type=media_types.get(path.suffix, "application/octet-stream"),
            digest=sha256_digest(path.read_bytes()),
            size_bytes=path.stat().st_size,
        )
        for path in sorted(bundle_root.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    )


def write_space_projections(
    root: Path,
    *,
    spec: SubstrateSpaceSpec,
    design_set: HairpinDesignSet,
    member_encodings: Mapping[str, tuple[str, str]],
    verified_member_count: int,
    defaults_display_name: str,
    defaults_anatomy_summary: str,
    foldback_ref: str,
    basal_ref: str,
) -> None:
    """Write regenerable human and sequence projections outside the authority."""
    (root / "designs.csv").write_bytes(render_designs_csv(design_set, member_encodings))
    (root / "sequences.fasta").write_bytes(render_sequences_fasta(design_set, member_encodings))
    (root / "review.html").write_bytes(
        render_review_html(
            spec,
            design_set,
            verified_member_count=verified_member_count,
            defaults_display_name=defaults_display_name,
            defaults_anatomy_summary=defaults_anatomy_summary,
            foldback_ref=foldback_ref,
            basal_ref=basal_ref,
        )
    )


__all__ = [
    "design_set_artifacts",
    "render_designs_csv",
    "render_sequences_fasta",
    "write_space_projections",
]
