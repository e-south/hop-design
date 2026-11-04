"""Compact family reading surface; exact member views remain individually available."""

from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.projections.family_report import (
    ConstructionFamilyReportProjection,
)

from ..labels import endpoint_label, material_role_label
from .control_text import PROPERTY_LABELS
from .report_primitives import drawing_fragment, embed, page, text


def comparison_plates(
    report: ConstructionFamilyReportProjection, files: dict[str, bytes]
) -> list[bytes]:
    rows = [(m, c) for m in report.members for c in m.choices]
    if report.baseline:
        rows.sort(key=lambda row: row[0].name != report.baseline)
    comparisons = {
        (c.molecular.right.source_result_id, c.molecular.right.materialized_realization_id): c
        for c in report.comparisons
    }
    pages = []
    for start in range(0, len(rows), 3):
        group = rows[start : start + 3]
        unused = (3 - len(group)) * 157
        shared = []
        for field, label in (
            ("stem_bp", "bp supplied stem"),
            ("open_side_paired_positions", "open-side paired positions"),
            ("loop_side_paired_bp", "bp loop-side extension"),
        ):
            values = {c.geometry[field] for _, c in group}
            if len(values) == 1:
                shared.append(f"{next(iter(values))} {label}")
        purpose = "Requested family → Obtained molecules → selected preparations"
        if len(report.compared_properties) == 1:
            purpose = "Intended comparison: " + PROPERTY_LABELS[report.compared_properties[0]]
        elif report.compared_properties:
            purpose = f"Compare {len(report.compared_properties)} declared properties (report.md)"
        lines = [
            text(25, 67, purpose, 17),
            text(25, 95, "Shared in this panel: " + "; ".join(shared), 14),
            text(25, 123, "What changes in my molecule", 19),
            text(550, 123, "Count the closing nucleotides", 17),
        ]
        material_rows = []
        for slot, (member, choice) in enumerate(group):
            y = 154 + slot * 157
            selected = "selected preparation" if choice.selected else "not selected"
            label = f"{member.name} · {choice.geometry['loop_nt']}-nt loop · {selected}"
            if slot == 0:
                label = "Reference scaffold · " + label
            lines.append(text(25, y, label, 16))
            if choice.shared_property_differences:
                lines.append(
                    text(25, y + 22, "Shared requirement disagreement; inspect member report.", 13)
                )
            lines.append(
                embed(
                    drawing_fragment(files[choice.portrait], hairpin=True, annotate=slot == 0),
                    5,
                    y - 30,
                    550,
                    shape_only=True,
                )
            )
            lines.append(embed(drawing_fragment(files[choice.closing_drawing]), 550, y + 9, 340))
            comp = comparisons.get((choice.source_result_id, choice.materialized_realization_id))
            if comp:
                conserved = comp.molecular.assessment.non_loop_sequences_conserved
                sentence = {
                    True: "Non-loop sequences unchanged",
                    False: "Other sequence regions also change",
                    None: "Non-loop sequence agreement not assessed",
                }[conserved]
                if conserved is not True:
                    lines.append(
                        text(25, y + 114, sentence + f" versus {comp.baseline_member}.", 13)
                    )
                roles = (
                    ", ".join(material_role_label(r) for r in comp.molecular.changed_material_roles)
                    or "none"
                )
                material_rows.append(f"{member.name} versus {comp.baseline_member}: {roles}")
            else:
                lines.append(
                    text(
                        25,
                        y + 114,
                        f"Hairpin {choice.stage_role}; exact dimensions in member view.",
                        13,
                    )
                )
        controls = {c.property: c for c in (report.selected_controls or report.family_controls)}
        molecular = [
            controls.get(k) for k in ("non_loop_sequences", "regional_contacts", "regional_joins")
        ]
        if all(
            c and c.status in ("required_and_verified", "observed_agreement") for c in molecular
        ):
            required = all(c and c.required for c in molecular)
            lines.append(
                text(
                    25,
                    606 - unused,
                    ("Selected set — " if report.selected_controls else "Requested family — ")
                    + ("required and verified" if required else "observed agreement")
                    + ": surrounding sequences, contacts and joins.",
                    14,
                )
            )
        lines.append(text(25, 641 - unused, "What changes in making it", 19))
        for i, row in enumerate(
            material_rows or ["No between-member preparation comparison supplied."]
        ):
            lines.append(text(25, 669 - unused + i * 22, row, 14))
        representative, choice = group[0]
        lines.append(
            text(
                25,
                751 - unused,
                f"Product stages · {representative.name} · "
                + endpoint_label(ConstructionEndpoint(choice.endpoint)),
                17,
            )
        )
        if choice.product_stages.hairpin_role == "endpoint":
            strand = choice.product_stages.product.strands[0]
            lines += [
                text(25, 799 - unused, "The pictured hairpin is the requested endpoint.", 17),
                text(
                    25, 838 - unused, "○ Recorded covalent join     │ Canonical pairing contact", 17
                ),
                text(
                    25,
                    877 - unused,
                    f"Terminal state: 5\u2032 {strand.five_prime_end.value} · "
                    f"3\u2032 {strand.three_prime_end.value}",
                    17,
                ),
                text(25, 916 - unused, "No downstream release interface requested.", 16),
            ]
        else:
            lines.append(
                embed(
                    drawing_fragment(files[choice.stage_drawing], height=190), 0, 767 - unused, 900
                )
            )
        lines += [
            text(
                25,
                981 - unused,
                "Retrieve each exact preparation and every outcome through report.md.",
                15,
            ),
            text(
                25,
                1007 - unused,
                "Destination compatibility and preparation performance remain unevaluated.",
                14,
            ),
            text(
                25,
                1033 - unused,
                "Pairing architecture; drawings use separate scales. "
                "Biological effects remain untested.",
                13,
            ),
        ]
        pages.append(page("Compare the scaffold you can make", lines, height=1060 - unused))
    return pages
