"""Explicit member-to-member request edits; never inferred remedies."""

from hop_design.models.construction.projections.family_report import (
    FamilyReportEdit,
    FamilyReportMember,
)


def describe_edits(
    members: tuple[FamilyReportMember, ...], edits: tuple[tuple[str, str], ...]
) -> tuple[FamilyReportEdit, ...]:
    lookup = {m.name: m for m in members}
    if len(set(edits)) != len(edits):
        raise ValueError("Duplicate authored member edit.")
    output = []
    for source, target in edits:
        if source == target or source not in lookup or target not in lookup:
            raise ValueError("An authored edit must name two distinct family members.")
        a, b = lookup[source], lookup[target]
        changes = {
            key: (a.requested_variation[key], b.requested_variation[key])
            for key in a.requested_variation
            if a.requested_variation[key] != b.requested_variation[key]
        }
        effective = {
            key: (a.effective_geometry[key], b.effective_geometry[key])
            for key in a.effective_geometry
            if a.effective_geometry[key] != b.effective_geometry[key]
        }
        if not changes:
            raise ValueError("Authored member edit must change a requested dimension.")
        output.append(
            FamilyReportEdit(
                source_member=source,
                target_member=target,
                requested_changes=changes,
                effective_changes=effective,
            )
        )
    return tuple(output)
