"""Carry an inspection's display and comparison choices through publication packets."""

import json
from dataclasses import dataclass
from pathlib import Path

from hop_design.design.source_documents import load_source_mapping
from hop_design.serialization import canonical_json_bytes

from ..intents.base import Source
from ..packets.atlas import MolecularAtlasPacket
from ..packets.publication import SourceBoundConstructionPacket
from .types import ChoiceSource, Record


@dataclass(frozen=True)
class FigureContext:
    selection: Source | None
    view: str
    stage: str
    layout: str
    receipt: Record | None
    display_axes: tuple[str, ...] | None = None

    @property
    def color(self) -> Record | None:
        return self.receipt["presentation"].get("color") if self.receipt else None

    def atlas(self, choices: ChoiceSource) -> MolecularAtlasPacket | None:
        return None if self.receipt is None else choices.atlas(self.receipt)

    def attach(
        self, packet: SourceBoundConstructionPacket, atlas: MolecularAtlasPacket | None
    ) -> SourceBoundConstructionPacket:
        if self.receipt is None:
            return packet
        if atlas is None:
            raise ValueError("The inspected figure requires its selected molecular packet.")
        files = {**dict(packet._files), "view.json": canonical_json_bytes(self.receipt)}
        result = type(packet)._create(
            files,
            {
                **json.loads(packet.json_bytes),
                "selection": self.receipt["selection"],
                "view_receipt": self.receipt,
                "rendering": json.loads(atlas.json_bytes)["rendering"],
            },
            packet.report_text,
        )
        object.__setattr__(result, "_roots", packet._roots)
        return result


def figure_context(
    choices: ChoiceSource,
    selection: Source | None,
    view: str | None,
    stage: str | None,
    layout: str | None,
    render_policy: str | None,
    reference: Source | None,
    display_axes: tuple[str, ...] | None = None,
) -> FigureContext:
    raw = load_source_mapping(selection) if isinstance(selection, str | Path) else selection
    receipt = (
        choices.restore_view(raw)
        if raw and raw.get("schema", "").startswith("hop.atlas-view/")
        else None
    )
    if receipt is None and (render_policy is not None or reference is not None):
        if selection is None:
            raise ValueError("A rendering policy or comparison requires an exact selection.")
        receipt = choices.view(selection)
    presentation = dict(receipt["presentation"]) if receipt else {}
    if display_axes is None and "display_axes" in presentation:
        display_axes = tuple(presentation["display_axes"])
    elif display_axes is not None and "display_axes" in presentation:
        presentation["display_axes"] = list(display_axes)
    for key, value in (("landscape", view), ("family_stage", stage), ("layout", layout)):
        if value is not None:
            presentation[key] = value
    if receipt is not None:
        from .guided_sampling import selection_source

        receipt = choices.view(
            receipt["selection"],
            stage=receipt["stage"],
            camera=receipt["camera"],
            presentation=presentation,
            exploration=receipt["exploration"],
            render_policy=render_policy or receipt["render_policy"],
            reference_identity=(
                selection_source(choices, reference)["materialized_realization_id"]
                if reference is not None
                else receipt["reference_identity"]
            ),
        )
        selection = receipt["selection"]
    mode = presentation.get("landscape", "parameters")
    if display_axes is not None and mode != "parameters" and selection is None:
        raise ValueError("Display axes require a parameter figure or a selected landscape trace.")
    return FigureContext(
        selection,
        mode,
        stage
        or (presentation.get("family_stage", "endpoint") if mode == "families" else "endpoint"),
        layout or (presentation.get("layout", "auto") if mode == "families" else "auto"),
        receipt,
        display_axes,
    )
