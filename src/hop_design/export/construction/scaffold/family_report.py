"""Paginated comparison packet assembled only from admitted molecular facts."""

from hop_design.models.construction.projections.family_report import (
    ConstructionFamilyReportProjection,
)

from .comparison_plate import comparison_plates
from .family_report_changes import comparison_pages
from .family_report_text import describe_member, render_report_text
from .recovery_plate import recovery_plate
from .report_primitives import page, text
from .request_change_plate import request_change_plate


def render_family_report(
    report: ConstructionFamilyReportProjection, files: dict[str, bytes]
) -> tuple[str, tuple[bytes, ...]]:
    edited_sources = {e.source_member for e in report.authored_edits}
    pending = [m for m in report.members if not m.choices and m.name not in edited_sources]
    pages = comparison_plates(report, files)
    if report.recovery:
        recovered = recovery_plate(report, files)
        pages = (
            [recovered] if sum(len(m.choices) for m in report.members) == 1 else [*pages, recovered]
        )
    for start in range(0, len(pending), 4):
        lines = [text(25, 70, "Every request retains its outcome and exact diagnostics.")]
        for slot, member in enumerate(pending[start : start + 4]):
            y = 117 + slot * 175
            lines += [
                text(25, y, member.name + " · Requested " + describe_member(member), 18),
                text(25, y + 33, "Obtained: no complete molecule for this recorded outcome."),
                text(25, y + 58, f"{member.status}; {member.scope.replace('_', ' ')}"),
            ]
            for i, diagnostic in enumerate(member.preparation_constraints[:2]):
                if isinstance(diagnostic, dict):
                    lines.append(
                        text(
                            25,
                            y + 84 + 22 * i,
                            f"This selected preparation needs {diagnostic.get('requested')} nt; "
                            f"supplies {diagnostic.get('available')} nt.",
                        )
                    )
            if not member.preparation_constraints:
                lines.append(text(25, y + 84, "Coverage and rejection details: report.md."))
        lines.append(
            text(
                25,
                145 + min(4, len(pending) - start) * 175,
                "A failed selected preparation does not prove global absence.",
                14,
            )
        )
        pages.append(
            page(
                "Requests without a completed molecule",
                lines,
                height=180 + min(4, len(pending) - start) * 175,
            )
        )
    if report.authored_edits:
        for edit in report.authored_edits:
            source = next(m for m in report.members if m.name == edit.source_member)
            target = next(m for m in report.members if m.name == edit.target_member)
            pages.append(request_change_plate(source, target, files))
    for i, detail in enumerate(comparison_pages(report, files), start=1):
        files[f"details/comparison-{i}.svg"] = detail
    return render_report_text(report, len(pages)), tuple(pages)
