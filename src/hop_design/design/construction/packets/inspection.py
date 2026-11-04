"""Private pinned-molecule packet; full route artwork has a separate lifetime."""

from dataclasses import asdict
from pathlib import Path
from typing import ClassVar, Self

from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview
from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE

from .atlas import MolecularAtlasPacket
from .publication import SourceBoundConstructionPacket


class MolecularInspectionPacket(MolecularAtlasPacket):
    _packet_schema: ClassVar[str] = "hop.molecular-inspection-packet/v1"

    @classmethod
    def _create(cls, files: dict[str, bytes], summary: dict[str, object], report: str) -> Self:
        # Keep all exact facts, but draw only the selected molecule. In particular,
        # comparison facts belong here without generating a second comparison plate.
        overview = files.get("overview.svg")
        if overview is None:
            overview = render_teaching_overview(summary, profile=INSPECTOR_FIGURE)
            summary = {**summary, "inspection_profile": asdict(INSPECTOR_FIGURE)}
        return super(MolecularAtlasPacket, cls)._create(
            {"overview.svg": overview},
            summary,
            "# Selected molecule\n\nExact molecular record and comparison. "
            "Open the route to draw all processing states.\n",
        )

    def write(self, destination: str | Path, *, print_pages: bool = False) -> Path:
        if print_pages is not False:
            raise ValueError("Use the complete atlas for printable route export.")
        return SourceBoundConstructionPacket.write(self, destination)
