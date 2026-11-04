"""Matched closing crops and literal sequence changes, with correspondence limits."""

from hop_design.models.construction.projections.family_report import (
    ConstructionFamilyReportProjection,
)

from .report_primitives import embed, page, text


def comparison_pages(
    report: ConstructionFamilyReportProjection, files: dict[str, bytes]
) -> list[bytes]:
    pages = []
    for comparison in report.comparisons:
        left = next(
            c
            for m in report.members
            for c in m.choices
            if c.materialized_realization_id
            == comparison.molecular.left.materialized_realization_id
            and c.source_result_id == comparison.molecular.left.source_result_id
        )
        right = next(
            c
            for m in report.members
            for c in m.choices
            if c.materialized_realization_id
            == comparison.molecular.right.materialized_realization_id
            and c.source_result_id == comparison.molecular.right.source_result_id
        )
        lines = [
            text(25, 72, comparison.baseline_member + " → " + comparison.member, 20),
            text(
                25,
                100,
                "Same regional orientation; sequence and preparation changes remain explicit.",
            ),
            text(25, 134, "Reference", 17),
            text(470, 134, "Compared member", 17),
            embed(files[left.closing_drawing], 0, 146, 440),
            embed(files[right.closing_drawing], 450, 146, 440),
        ]
        loop = next((r for r in comparison.regions if r.region == "loop"), None)
        if loop:
            lines += [text(25, 405, "Loop sequence, each 5\u2032 → 3\u2032", 18)]
            if loop.correspondence == "unique_minimum_edit" and len(loop.columns) <= 38:
                for i, column in enumerate(loop.columns):
                    x = 30 + i * 21
                    for y, base in ((445, column.reference_base), (475, column.observed_base)):
                        if column.kind != "unchanged":
                            color = {
                                "added": "#D3EEE3",
                                "removed": "#FFE2C9",
                                "substitution": "#DDD8F0",
                            }[column.kind]
                            lines.append(
                                f'<rect x="{x - 7}" y="{y - 17}" width="19" '
                                f'height="23" fill="{color}" data-change="{column.kind}"/>'
                            )
                        lines.append(text(x, y, base or "\u2013", 17))
                lines.append(
                    text(25, 510, "Green = added; orange = removed; purple = substitution.", 14)
                )
            else:
                # Ambiguous correspondence is shown side by side; never invent an edited position.
                lines += [
                    text(25, 445, loop.reference_sequence[:70], 17),
                    text(25, 475, loop.observed_sequence[:70], 17),
                    text(
                        25,
                        510,
                        "Correspondence: "
                        + loop.correspondence.replace("_", " ")
                        + f"; net {loop.length_delta:+d} nt.",
                        16,
                    ),
                ]
                if max(len(loop.reference_sequence), len(loop.observed_sequence)) > 70:
                    lines.append(
                        text(
                            25,
                            534,
                            "First 70 bases shown; exact sequences and spans in summary.json.",
                            14,
                        )
                    )
            lines.append(
                text(
                    25,
                    562,
                    "Counts establish length; repeated bases may prevent a unique edit location.",
                    14,
                )
            )
        roles = [r.value.replace("_", " ") for r in comparison.molecular.changed_material_roles]
        lines.append(text(25, 610, "Accompanying material changes", 18))
        for i, role in enumerate(roles[:6]):
            lines.append(text(25, 638 + 23 * i, role))
        if len(roles) > 6:
            lines.append(text(25, 789, "Additional material roles are listed in report.md."))
        lines += [
            text(
                25,
                828,
                "Molecular differences and preparation changes are distinct; "
                "biological effects untested.",
                14,
            ),
            text(
                25,
                853,
                "All regional differences, coordinate movement, contacts and "
                "chemistry: summary.json.",
                13,
            ),
        ]
        pages.append(page("What else changes with the requested scaffold?", lines))
    return pages
