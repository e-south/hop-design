"""Presentation continuity over recorded states, independent of session transport."""

import copy
from typing import Any

from hop_design import construction
from hop_design.api import _InspectionProjection


def history_frame(state: dict[str, Any], history: list[str]) -> dict[str, Any]:
    """Undo stores small receipts and identities, never drawings or molecular scenes."""
    return {
        key: copy.deepcopy(state[key])
        for key in (
            "view_receipt",
            "sample_receipt",
            "family_stage",
            "presentation",
            "exploration",
            "render_policy",
        )
    } | {
        "query": state["choices"]["query"],
        "history": tuple(history),
        "eligible": state["selection"] is not None,
    }


def requires_redraw(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    return bool(
        previous["render_policy"] != current["render_policy"]
        or previous["presentation"]["molecule"] != current["presentation"]["molecule"]
        or previous["presentation"]["route"] != current["presentation"]["route"]
        or (
            current["presentation"]["route"] == "assembly" and previous["stage"] != current["stage"]
        )
    )


def unselected_presentation(
    choices: construction.DesignChoices | construction.AtlasEdition,
    payload: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    if "render_policy" in payload:
        raise ValueError("Select a preparation before changing its render policy.")
    if payload["stage"] != "all" or payload["camera"] is not None:
        raise ValueError("Select a preparation before inspecting its processing state.")
    presentation = choices.inspection_settings(presentation=payload.get("presentation", current))[
        "presentation"
    ]
    if presentation["landscape"] == "similarity" and not choices.has_landscape:
        raise ValueError("Capture molecular coordinates before opening the similarity view.")
    return {
        "presentation": presentation,
        "family_stage": presentation["family_stage"],
    }


def processing_stage(preview: dict[str, Any], previous: dict[str, Any] | None, wanted: str) -> str:
    states = preview["summary"]["atlas"]["states"]
    if wanted == "all" or any(s["state"]["state_id"] == wanted for s in states):
        return wanted
    old = previous["summary"]["atlas"]["states"] if previous else []
    phase = next((s["state"]["phase"] for s in old if s["state"]["state_id"] == wanted), None)
    matches = [s["state"]["state_id"] for s in states if s["state"]["phase"] == phase]
    return matches[0] if len(matches) == 1 else "all"


def initial_state(
    choices: construction.DesignChoices | construction.AtlasEdition,
) -> dict[str, Any]:
    answer = choices.query()
    presentation: dict[str, Any] = {
        "landscape": "similarity" if choices.has_landscape else "families"
    }
    axes = _InspectionProjection.display_axes(answer)
    if axes:
        presentation["display_axes"] = axes
    return {
        "mode": "design",
        "discovery": choices.resolution,
        "choices": answer,
        "selection": None,
        "preview": None,
        "preview_status": None,
        "sample_receipt": None,
        "handoff": None,
        "stage": "all",
        "render_policy": "captured",
        "family_stage": "endpoint",
        "view_receipt": None,
        **choices.inspection_settings(presentation=presentation),
    }
