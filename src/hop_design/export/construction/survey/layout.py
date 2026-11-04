"""Stable axis coordinates and label allocation, independent of SVG interactions."""

from dataclasses import dataclass
from itertools import groupby
from textwrap import wrap
from typing import Any

from ..molecular.primitives.typography import text_width
from ..presentation.figure_profile import PUBLICATION_FIGURE, FigureProfile
from ..presentation.regions import REGIONS, teaching_region
from .axis_frame import AxisFrame, measured_frame

WIDTH = 1200
FONT = PUBLICATION_FIGURE.axis_font
STATES = {
    "supported": ("#377f75", "#e4f0ec", "none"),
    "supported_elsewhere": ("#7d9297", "#ffffff", "none"),
    "unresolved": ("#a1aeb2", "#ffffff", "2 3"),
    "excluded_in_scope": ("#a46060", "#eee5e5", "6 2"),
}


def band_count(axes: list[dict[str, Any]]) -> int:
    """An all-fixed view retains a positive frame for its explanatory label."""
    return max((axis["band"] + 1 for axis in axes), default=1)


def node_label(axis: dict[str, Any], node: dict[str, Any]) -> str:
    value = node["label"]
    if axis["representation"] == "orientation":
        value = {"five_prime": "5\u2032", "three_prime": "3\u2032"}.get(value, value)
    return str(value)


def node_lines(axis: dict[str, Any], node: dict[str, Any]) -> list[str]:
    value = node_label(axis, node)
    if axis["representation"] == "sequence" and len(value) > 16:
        # Long sequences remain exact in the node title and portable domain key.
        return [f"{len(value)} nt"]
    return wrap(value, width=8, break_long_words=axis["representation"] != "recognition") or [""]


def node_geometry(
    axis: dict[str, Any], node: dict[str, Any], *, profile: FigureProfile = PUBLICATION_FIGURE
) -> dict[str, Any]:
    """One label contour for the static figure and its exact inspection overlay."""
    lines = node_lines(axis, node)
    return {
        "lines": lines,
        "width": max(18, max(text_width(line, profile.axis_font) for line in lines) + 4),
        "height": len(lines) * profile.axis_font + 4,
    }


def heading_lines(
    axis: dict[str, Any], *, profile: FigureProfile = PUBLICATION_FIGURE
) -> list[str]:
    return wrap(
        axis.get("label", axis["symbol"]),
        width=profile.heading_columns,
        break_long_words=False,
    )


def _region_widths(
    items: list[tuple[dict[str, Any], float]], profile: FigureProfile
) -> list[float]:
    """Reserve a shared heading once per contiguous molecular region in a row."""
    widths = [width for _, width in items]
    if profile.width >= PUBLICATION_FIGURE.width:
        return widths
    for region, group in groupby(
        enumerate(items), key=lambda item: teaching_region(item[1][0].get("neighborhood", "whole"))
    ):
        columns = list(group)
        label = REGIONS[region][0]
        minimum = max(text_width(word, profile.axis_font) for word in label.split()) + 8
        available = sum(width for _, (_, width) in columns) + 6 * (len(columns) - 1)
        extra = max(0.0, minimum - available) / len(columns)
        for index, _ in columns:
            widths[index] += extra
    return widths


def _axis_bands(
    items: list[tuple[dict[str, Any], float]], profile: FigureProfile
) -> list[list[tuple[dict[str, Any], float]]]:
    """Minimize row count, then balance measured space without reordering axes."""
    budget = profile.width - 52
    best: dict[int, tuple[int, float, tuple[int, ...]]] = {len(items): (0, 0.0, ())}
    for start in reversed(range(len(items))):
        candidates = []
        for stop in range(start + 1, len(items) + 1):
            needed = sum(_region_widths(items[start:stop], profile)) + 6 * (stop - start - 1)
            if needed > budget:
                break
            rows, slack, ends = best[stop]
            candidates.append((rows + 1, slack + (budget - needed) ** 2, (stop, *ends)))
        if not candidates:
            raise ValueError("Axis label exceeds the publication-width layout.")
        best[start] = min(candidates)
    bands, start = [], 0
    for stop in best[0][2]:
        bands.append(items[start:stop])
        start = stop
    return bands


def categorical_positions(
    axis: dict[str, Any], *, frame: AxisFrame, profile: FigureProfile = PUBLICATION_FIGURE
) -> dict[Any, float]:
    """Give witnessed categories room; retain every unresolved permission as a tick.

    Categorical spacing encodes no numerical distance. Global witness counts keep
    positions stable when the same pool is filtered.
    """
    nodes = axis["nodes"]
    top, span = frame.top, frame.bottom - frame.top
    observed = [n for n in nodes if n["supported_preparations"] > 0]
    pending = [n for n in nodes if n["supported_preparations"] == 0]
    if len(nodes) <= 10 or not observed or not pending:
        return {
            n["value"]: top + (i + 0.5) / max(1, len(nodes)) * span for i, n in enumerate(nodes)
        }
    share = min(0.8, len(observed) * (profile.axis_font + 12) / span)
    groups = (
        (observed, top, span * share),
        (pending, top + span * share, span * (1 - share)),
    )
    return {
        n["value"]: start + (i + 0.5) / len(group) * span
        for group, start, span in groups
        for i, n in enumerate(group)
    }


@dataclass(frozen=True)
class SurveyLayout:
    axes: list[dict[str, Any]]
    frame: AxisFrame

    @property
    def height(self) -> float:
        return band_count(self.axes) * self.frame.height


def plot_layout(
    choices: dict[str, Any], *, profile: FigureProfile = PUBLICATION_FIGURE
) -> SurveyLayout:
    axes = choices["axes"]
    widths = []
    heading_rows, node_rows = 0, 1
    for axis in axes:
        unit = {"positions": "pos", "contacts": "ct"}.get(axis["unit"], axis["unit"])
        headings = heading_lines(axis, profile=profile)
        heading_rows = max(heading_rows, len(headings))
        labels = [*headings, unit]
        for node in axis["nodes"]:
            lines = node_lines(axis, node)
            node_rows = max(node_rows, len(lines))
            labels.extend(lines)
        width = max(18, max(text_width(label, profile.axis_font) for label in labels) + 4)
        widths.append(width)
    bands = _axis_bands(list(zip(axes, widths, strict=True)), profile)
    frame = measured_frame(
        font=profile.axis_font,
        heading_rows=heading_rows,
        node_rows=node_rows,
        region_rows=2 if profile.width < WIDTH else 1,
    )
    result = []
    for band, items in enumerate(bands):
        items = [
            (axis, width)
            for (axis, _), width in zip(items, _region_widths(items, profile), strict=True)
        ]
        gap = (profile.width - 52 - sum(w for _, w in items)) / max(1, len(items) - 1)
        left = 26.0
        for axis, width in items:
            values = [n["value"] for n in axis["nodes"]]
            if len(set(values)) != len(values):
                raise ValueError("Survey axis values must be unique.")
            numeric = axis["kind"] == "numeric" and values and max(values) > min(values)
            positions = (
                {
                    value: frame.bottom
                    - (value - min(values))
                    / (max(values) - min(values))
                    * (frame.bottom - frame.top)
                    for value in values
                }
                if numeric
                else categorical_positions(axis, frame=frame, profile=profile)
            )
            positions = {value: y + band * frame.height for value, y in positions.items()}
            x = profile.width / 2 if len(items) == 1 else left + width / 2
            result.append(
                {"definition": axis, "x": x, "y": positions, "band": band, "width": width}
            )
            left += width + gap
    return SurveyLayout(result, frame)


def plot_axes(
    choices: dict[str, Any], *, profile: FigureProfile = PUBLICATION_FIGURE
) -> list[dict[str, Any]]:
    return plot_layout(choices, profile=profile).axes


def visible_labels(
    axis: dict[str, Any],
    positions: dict[Any, float],
    choices: dict[str, Any],
    selected: set[Any],
    *,
    profile: FigureProfile = PUBLICATION_FIGURE,
) -> set[Any]:
    predicate: dict[str, Any] = next(
        (p for p in choices["query"]["parameters"] if p["key"] == axis["key"]), {}
    )
    pinned = set(predicate.get("values") or ()) | {
        predicate.get("minimum"),
        predicate.get("maximum"),
    }
    values = [n["value"] for n in axis["nodes"]]
    bounds = {min(values), max(values), 0} if axis["kind"] == "numeric" and values else set()

    def priority(node: dict[str, Any]) -> tuple[int, float]:
        v = node["value"]
        rank = (
            0
            if v in selected
            else 1
            if v in pinned
            else 2
            if v in bounds
            else 3
            if node["state"] == "supported"
            else 4
        )
        return rank, positions[v]

    chosen: set[Any] = set()
    occupied: list[tuple[float, float]] = []
    for node in sorted(axis["nodes"], key=priority):
        value = node["value"]
        half = node_geometry(axis, node, profile=profile)["height"] / 2
        y = positions[value]
        if all(y + half + 2 <= lo or y - half - 2 >= hi for lo, hi in occupied):
            chosen.add(value)
            occupied.append((y - half, y + half))
    return chosen
