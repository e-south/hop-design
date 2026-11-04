"""Show literal material changes without interpreting ambiguous sequence alignments."""

from html import escape
from typing import Any

from hop_design.models.construction.complete.material import MaterialUseRole

from ..labels import material_role_label
from ..scaffold.report_primitives import text


def material_rows(
    options: list[dict[str, Any]],
    names: list[str],
    y: int,
    *,
    baseline: tuple[str, dict[str, Any]],
) -> tuple[list[str], int]:
    reference_name, reference_option = baseline
    reference = reference_option["materials"]
    rows = [text(25, y, f"Preparation changes relative to {reference_name}", 18)]
    for name, option in zip(names, options, strict=True):
        if name == reference_name:
            continue
        changed = False
        for role in dict.fromkeys([*reference, *option["materials"]]):
            before, after = reference.get(role), option["materials"].get(role)
            if before == after:
                continue
            changed = True
            label = material_role_label(MaterialUseRole(role))
            y += 25
            rows.append(f'<g data-material-role="{escape(role)}">')
            if before is None or after is None:
                rows.append(
                    text(25, y, f"{name} · {label}: {'added' if before is None else 'removed'}", 14)
                )
            else:
                a, b = before["sequence_5prime"], after["sequence_5prime"]
                rows.append(text(25, y, f"{name} · {label}: {len(a)} → {len(b)} nt", 14))
                if a == b:
                    y += 19
                    rows.append(text(45, y, "Sequence unchanged; terminal chemistry differs.", 13))
                elif len(a) == len(b):
                    differences = [
                        i for i, pair in enumerate(zip(a, b, strict=True)) if pair[0] != pair[1]
                    ]
                    # A literal 5-prime coordinate comparison is unambiguous for equal lengths.
                    # All changed intervals remain available in exact material records.
                    start = max(0, differences[0] - 2)
                    end = min(len(a), start + 46, differences[-1] + 3)
                    for sequence in (a, b):
                        y += 19
                        rows.append(text(45, y, f"{start + 1}-{end}", 11))
                        for j, base in enumerate(sequence[start:end], start):
                            color = "#8B4A89" if j in differences else "#52616A"
                            rows.append(
                                f'<text x="{115 + (j - start) * 12}" y="{y}" '
                                f'font-size="14" fill="{color}">{base}</text>'
                            )
                    y += 18
                    rows.append(
                        text(
                            45,
                            y,
                            f"{len(differences)} differing "
                            f"{'position' if len(differences) == 1 else 'positions'} (purple); "
                            "first region shown (5\u2032 → 3\u2032; positions start at 1).",
                            12,
                        )
                    )
                else:
                    y += 19
                    rows.append(
                        text(
                            45,
                            y,
                            "Length and sequence change; exact oligos accompany each preparation.",
                            13,
                        )
                    )
            rows.append("</g>")
        if not changed:
            y += 25
            rows.append(text(25, y, f"{name}: external oligo specifications unchanged.", 14))
    if len(options) == 1:
        y += 25
        rows.append(text(25, y, "Exact external oligos accompany this preparation.", 14))
    return rows, y
