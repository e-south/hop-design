"""One exact atlas packet, with readable print pages rendered only for export."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

from hop_design.export.construction.molecular.atlas_comparison import render_atlas_comparison
from hop_design.export.construction.molecular.printing.atlas import (
    native_route_plate,
    paginate_atlas,
)
from hop_design.export.construction.molecular.printing.teaching import teaching_print_files
from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview
from hop_design.export.construction.scaffold.report_pdf import render_report_pdf
from hop_design.models.construction.projections.atlas import AtlasComparison
from hop_design.models.construction.projections.overhead.complete import ConstructionCost
from hop_design.serialization import canonical_json_bytes

from .publication import SourceBoundConstructionPacket


@dataclass(frozen=True, init=False, repr=False)
class MolecularAtlasPacket(SourceBoundConstructionPacket):
    def inspection_summary(self, selection: dict[str, Any]) -> dict[str, Any]:
        """Compact navigation facts; complete molecular records remain in this packet."""
        from ..navigation.inspection_summary import inspection_summary

        summary = json.loads(self.json_bytes)
        if (
            selection.get("materialized_realization_id")
            != summary["atlas"]["materialized_realization_id"]
        ):
            raise ValueError("Inspection selection disagrees with the molecular packet.")
        return inspection_summary(summary, selection)

    @classmethod
    def _create(cls, files: dict[str, bytes], summary: dict[str, object], report: str) -> Self:
        if summary.get("teaching") is not None and "overview.svg" not in files:
            files = {**files, "overview.svg": render_teaching_overview(summary)}
        atlas = summary.get("atlas")
        if isinstance(atlas, dict) and atlas.get("construction_cost") is not None:
            cost = ConstructionCost.model_validate_json(
                canonical_json_bytes(atlas["construction_cost"])
            )
            files = {**files, "construction-cost.json": canonical_json_bytes(cost)}
            if "[Construction cost](construction-cost.json)" not in report:
                report += (
                    "\n[Construction cost](construction-cost.json)\n\n"
                    + "\n\n".join(cost.summary_lines)
                    + "\n"
                )
        if summary.get("comparison") is not None:
            comparison = AtlasComparison.model_validate_json(
                canonical_json_bytes(summary["comparison"])
            )
            files = {**files, "comparison.svg": render_atlas_comparison(comparison)}
            if "[Exact comparison](comparison.svg)" not in report:
                report += (
                    "\n[Exact comparison](comparison.svg) lists sequence "
                    "and material differences.\n"
                )
        return super()._create(files, summary, report)

    @property
    def svg_bytes(self) -> bytes:
        return dict(self._files)["projection.svg"]

    @property
    def pdf_bytes(self) -> bytes:
        pages, _ = paginate_atlas(self.svg_bytes)
        return render_report_pdf(pages, title="HOP complete molecular preparation")

    def write(self, destination: str | Path, *, print_pages: bool = True) -> Path:
        """Browser previews omit print work; saved exports include the readable route."""
        if type(print_pages) is not bool:
            raise ValueError("print_pages must be a Boolean.")
        if not print_pages:
            return super().write(destination)
        pages, layout = paginate_atlas(self.svg_bytes)
        plate, plate_layout = native_route_plate(self.svg_bytes)
        files = dict(self._files) | {
            "projection.pdf": render_report_pdf(pages, title="HOP complete molecular preparation"),
            "print-layout.json": canonical_json_bytes(layout),
            "route-plate.svg": plate,
            "route-plate.pdf": render_report_pdf(
                (plate,), title="HOP complete molecular route plate"
            ),
            "route-plate-layout.json": canonical_json_bytes(plate_layout),
            **{f"pages/{i:02}.svg": page for i, page in enumerate(pages, 1)},
        }
        if "teaching.svg" in files:
            files.update(teaching_print_files(files["teaching.svg"]))
        if "page_width_pt" in layout:
            page_guidance = (
                f"{layout['page_width_pt'] / 72:g}-inch pages use explicit coordinate "
                "continuations for longer scenes. "
                "These view splits do not represent molecular cuts. "
            )
        else:
            page_guidance = (
                "Page widths preserve the recorded strand layout; pages break between states. "
            )
        report = self._report + (
            "\n[Readable complete route](projection.pdf): print at native size for nucleotide "
            f"text of at least {layout['minimum_sequence_font_pt']:g} pt. "
            + page_guidance
            + "Rescaling to a smaller sheet reduces legibility. "
            "[Print layout](print-layout.json) records physical dimensions and state membership.\n"
            "\n[Full route plate](route-plate.pdf) retains the complete source composition "
            f"at {plate_layout['width_pt'] / 72:.2f} by "
            f"{plate_layout['height_pt'] / 72:.2f} inches. "
            "Its [editable SVG](route-plate.svg) keeps the original viewBox and molecular layout. "
            f"Shrinking this plate to {plate_layout['reference_width_pt'] / 72:g} inches "
            "would make its smallest sequence text "
            f"{plate_layout['reference_sequence_font_pt']:.2f} pt. "
            "[Plate dimensions](route-plate-layout.json) report that scale separately from "
            "the readable continuation pages.\n"
        )
        packet = type(self)._create(files, json.loads(self._summary), report)
        object.__setattr__(packet, "_roots", self._roots)
        return SourceBoundConstructionPacket.write(packet, destination)
