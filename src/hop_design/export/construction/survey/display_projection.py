"""An explicit drawing subset; complete molecular choices remain untouched."""

import json
from typing import Any
from xml.etree import ElementTree as ET

from hop_design.serialization import canonical_json_bytes


def append_display_metadata(root: ET.Element, presentation: dict[str, Any]) -> None:
    """Keep the naming and axis recipes inside the drawing they describe."""
    ET.SubElement(
        root, "{http://www.w3.org/2000/svg}metadata", {"data-parameter-labels": "true"}
    ).text = json.dumps(presentation["label_projection"])
    if "display_projection" in presentation:
        ET.SubElement(
            root, "{http://www.w3.org/2000/svg}metadata", {"data-display-projection": "true"}
        ).text = json.dumps(presentation["display_projection"])


def inspector_display_axes(choices: dict[str, Any]) -> tuple[str, ...]:
    """A shape/interface reading order, not another parameter definition catalog.

    Keep fixed features visible so the first inspection still teaches their
    meaning. Full construction coordinates remain in the cohort and query.
    """
    order = (
        "open_side_paired_positions",
        "left_end_word",
        "left_gap",
        "right_gap",
        "right_end_word",
        "foldback_arm_bp",
        "loop_nt",
    )
    applicable = {
        a["key"] for a in choices["axes"] if a.get("nodes") and a.get("applicable") is not False
    }
    return tuple(key for key in order if key in applicable)


def display_projection_files(plot: bytes) -> dict[str, bytes]:
    """Bind the exact renderer's projection receipt into the exported packet."""
    for element in ET.fromstring(plot):
        if element.get("data-display-projection"):
            return {"display-projection.json": canonical_json_bytes(json.loads(element.text or ""))}
    return {}


def select_display_axes(
    definitions: list[dict[str, Any]], keys: tuple[str, ...]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Honor ordered canonical keys, including deliberately requested constants."""
    if not isinstance(keys, tuple | list) or not keys or any(not isinstance(k, str) for k in keys):
        raise ValueError("Display axes must be a nonempty ordered collection of canonical keys.")
    if len(set(keys)) != len(keys):
        raise ValueError("Display axes must not repeat.")
    available = {a["key"]: a for a in definitions}
    selected = []
    for key in keys:
        if key not in available:
            raise ValueError(f"Display axis {key!r} is unavailable in these recorded choices.")
        axis = available[key]
        canonical = axis.get("canonical_key", key)
        if key != canonical:
            raise ValueError(f"Use canonical display axis {canonical!r} instead of {key!r}.")
        if not axis.get("nodes") or axis.get("applicable") is False:
            raise ValueError(f"Display axis {key!r} has no applicable recorded coordinates.")
        selected.append(axis)
    return selected, {
        "schema": "hop.figure-display-projection/v1",
        "displayed": list(keys),
        "omitted": [a["key"] for a in definitions if a["key"] not in keys],
    }
