"""An explicit request edit beside its scoped outcome, never an invented failed product."""

from hop_design.models.construction.complete.preparation_diagnostics import (
    PreparationConstraintDiagnostic,
)
from hop_design.models.construction.projections.family_report import FamilyReportMember

from .family_report_text import describe_member
from .primer_span import primer_span_drawing
from .report_primitives import embed, page, text


def request_change_plate(
    source: FamilyReportMember, target: FamilyReportMember, files: dict[str, bytes]
) -> bytes:
    lines = [
        text(25, 75, source.name + " → " + target.name, 21),
        text(
            25, 107, "Explicit request edit; one alternative, not a uniquely necessary repair.", 16
        ),
        text(25, 145, "Requested: " + describe_member(source), 17),
        text(25, 174, "Edited to: " + describe_member(target), 17),
        text(25, 209, "Before: " + source.status + " · " + source.scope.replace("_", " "), 15),
        text(25, 234, "After: " + target.status + " · " + target.scope.replace("_", " "), 15),
    ]
    for i, d in enumerate(source.preparation_constraints[:2]):
        if isinstance(d, dict):
            lines.append(
                text(
                    25,
                    265 + i * 23,
                    f"Selected preparation: {d.get('available')} nt available; "
                    f"{d.get('requested')} nt required.",
                    16,
                )
            )
    span = next(
        (
            d
            for d in source.preparation_constraints
            if isinstance(d, dict) and d.get("code") == "primer-annealing-span-exceeded"
        ),
        None,
    )
    if span:
        lines.append(primer_span_drawing(PreparationConstraintDiagnostic.model_validate(span), 296))
    offset = 90 if span else 0
    if target.choices:
        lines += [
            text(25, 445 if span else 322, "Obtained alternative", 17),
            embed(files[target.choices[0].portrait], 10, 295 + offset, 800, shape_only=True),
        ]
    else:
        lines.append(
            text(25, 352, "No completed target molecule; inspect its recorded outcome.", 17)
        )
    if not source.choices:
        lines += [
            text(
                25,
                498 + offset,
                "No completed before-molecule: its molecular differences are not assessed.",
                15,
            ),
            text(
                25, 523 + offset, "The failed preparation does not prove global impossibility.", 15
            ),
        ]
    lines += [
        text(
            25,
            554 + offset,
            "Exact preparations and both requests: report.md. The edit does not select its target.",
            14,
        )
    ]
    return page("Adapt a request after inspecting its outcome", lines, height=650 if span else 585)
