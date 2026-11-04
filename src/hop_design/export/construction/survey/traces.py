"""Shared complete-path geometry for publication and small inspection overlays."""

from dataclasses import asdict
from typing import Any

from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..presentation.figure_profile import PUBLICATION_FIGURE, FigureProfile
from ..presentation.parameter_labels import LABEL_CATALOG_DIGEST
from .figure_layout import AXIS_LANDING_Y
from .layout import node_geometry, node_label, plot_layout
from .presentation import present_choices


def trace_commands(axes: list[dict[str, Any]], path: dict[str, Any]) -> str:
    commands = []
    for i, axis in enumerate(axes):
        value = path["values"][axis["definition"]["key"]]
        move = i == 0 or axis["band"] != axes[i - 1]["band"]
        commands.append(f"{'M' if move else 'L'}{axis['x']:.4f} {axis['y'][value]:.4f}")
    return " ".join(commands)


class TraceProjection:
    """An inspection-owned index over a whole admitted cohort, never a one-row fit."""

    def __init__(
        self,
        choices: dict[str, Any],
        *,
        profile: FigureProfile = PUBLICATION_FIGURE,
        display_axes: tuple[str, ...] | None = None,
    ) -> None:
        self._profile = profile
        presentation = present_choices(choices, display_axes=display_axes)
        layout = plot_layout(presentation, profile=profile)
        self.axes = layout.axes
        self._paths = {p["materialized_realization_id"]: p for p in choices["paths"]}
        self._nodes = {
            axis["definition"]["key"]: {n["value"]: n for n in axis["definition"]["nodes"]}
            for axis in self.axes
        }
        self.frame = f"0 0 {profile.width} {layout.height:g}"
        self.figure_geometry = {
            "frame": self.frame,
            "anchors": {
                a["definition"]["key"]: [a["x"], AXIS_LANDING_Y]
                for a in self.axes
                if a["band"] == 0
            },
        }
        self.projection = sha256_digest(
            canonical_json_bytes(
                {
                    "profile": asdict(profile),
                    **(
                        {"display_projection": presentation["display_projection"]}
                        if "display_projection" in presentation
                        else {}
                    ),
                    "parameter_labels": LABEL_CATALOG_DIGEST,
                    "axes": [
                        {
                            "key": a["definition"]["key"],
                            "label": a["definition"]["label"],
                            "unit": a["definition"]["unit"],
                            "x": a["x"],
                            "band": a["band"],
                            "positions": list(a["y"].items()),
                            "node_labels": [
                                (n["value"], node_geometry(a["definition"], n, profile=profile))
                                for n in a["definition"]["nodes"]
                            ],
                        }
                        for a in self.axes
                    ],
                }
            )
        )

    def trace(self, identity: str) -> dict[str, Any]:
        if identity not in self._paths:
            raise ValueError("Preview must name a preparation in the recorded pool.")
        path = self._paths[identity]
        values = []
        for axis in self.axes:
            definition = axis["definition"]
            key = definition["key"]
            value = path["values"][key]
            values.append(
                {
                    "key": key,
                    "label": definition["label"],
                    "value": value,
                    "display": node_label(definition, self._nodes[key][value]),
                    "node_label": node_geometry(
                        definition, self._nodes[key][value], profile=self._profile
                    ),
                    "unit": definition["unit"],
                    "x": axis["x"],
                    "y": axis["y"][value],
                }
            )
        return {
            "materialized_realization_id": identity,
            "eligible": path["matches"],
            "projection": self.projection,
            "path": trace_commands(self.axes, path),
            "frame": self.frame,
            "values": values,
        }
