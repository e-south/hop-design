"""Inspection projections; mutation and authorization stay in the session."""

import copy
from pathlib import Path
from typing import Any

from hop_design import construction
from hop_design.api import _InspectionProjection

from .inspection_cache import PreviewCache, state_key
from .inspection_commands import command_context
from .inspection_hover import HoverCache
from .inspection_plots import InspectionPlots


def inspected_selection(state: dict[str, Any]) -> dict[str, Any] | None:
    """Filtering can exclude a pin while retaining its inspected drawing."""
    return state["selection"] or (state["view_receipt"] or {}).get("selection")


def state_response(
    state: dict[str, Any],
    designs: construction.DesignChoices | construction.AtlasEdition,
    root: Path,
    plots: InspectionPlots,
    *,
    transport_cohort: str | None,
    can_back: bool,
    compact: bool = False,
) -> dict[str, Any]:
    answer = state["choices"]
    compact = compact and state["presentation"]["landscape"] == "similarity"
    cohort = state_key(
        [
            answer["snapshot_digest"],
            answer["query_digest"],
            state["family_stage"],
            compact,
            _InspectionProjection.profile,
        ]
    )
    unchanged = transport_cohort == cohort
    result = copy.deepcopy(
        {
            k: _InspectionProjection.display(answer) if k == "choices" else v
            for k, v in state.items()
            if not ((unchanged or compact) and k == "choices")
        }
    )
    result.update(
        copy.deepcopy(
            {
                k: v
                for k, v in plots.get(designs, state, compact=compact).items()
                if not (unchanged and k in {"families", "compact", "map_index", "cohort_summary"})
            }
        )
    )
    result.update(cohort=cohort, cohort_unchanged=unchanged)
    if not unchanged:
        result["feature_parameters"] = _InspectionProjection.parameters(designs, answer)
    display_axes = state["presentation"].get("display_axes")
    projection = plots.projection(answer, None if display_axes is None else tuple(display_axes))
    result["trace_projection"] = {"projection": projection.projection, "frame": projection.frame}
    selected = inspected_selection(result)
    result["inspection_explanation"] = (
        _InspectionProjection.explain(
            answer,
            selected["materialized_realization_id"],
            reference=(result["view_receipt"] or {}).get("reference_identity"),
        )
        if selected
        else None
    )
    result["selected_trace"] = (
        projection.trace(selected["materialized_realization_id"]) if selected else None
    )
    result["figure_layout"] = (
        _InspectionProjection.layout(
            result["preview"]["teaching_geometry"], projection.figure_geometry
        )
        if result["preview"]
        else None
    )
    result.update(command_context({**result, "choices": answer}, designs._directory, root))
    result["can_back"] = can_back
    return result


def preview_response(
    state: dict[str, Any],
    designs: construction.DesignChoices | construction.AtlasEdition,
    plots: InspectionPlots,
    hover: HoverCache,
    identity: str,
    *,
    phases: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    display_axes = state["presentation"].get("display_axes")
    projection = plots.projection(
        state["choices"], None if display_axes is None else tuple(display_axes)
    )
    trace = projection.trace(identity)
    preview = hover.get(
        designs,
        identity,
        state["choices"]["query"],
        answer=state["choices"],
        render_policy=state["render_policy"],
        **(
            {"phases": phases, "presentation": state["presentation"]["route"]}
            if phases is not None
            else {}
        ),
    )
    if "route_scenes" in preview:
        preview["route_scenes"]["token"] = state["token"]
    return {
        **preview,
        "figure_layout": _InspectionProjection.layout(
            preview["teaching_geometry"], projection.figure_geometry
        ),
        "trace": trace,
        "inspection_explanation": _InspectionProjection.explain(
            state["choices"],
            identity,
            reference=(inspected_selection(state) or {}).get("materialized_realization_id"),
        ),
        "token": state["token"],
    }


def prepare_selection(
    state: dict[str, Any],
    designs: construction.DesignChoices | construction.AtlasEdition,
    cache: PreviewCache,
    selected: dict[str, Any],
    history: list[str],
    *,
    reference: dict[str, Any] | None,
    receipt: dict[str, Any] | None,
    restore: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    """Prepare a view and history; the session commits them atomically."""
    if (
        reference
        and reference["materialized_realization_id"] == selected["materialized_realization_id"]
    ):
        reference = None
    policy = restore["render_policy"] if restore else state["render_policy"]
    preview, stage = cache.inspect(designs, selected, reference, restore or state, state["preview"])
    identity = selected["materialized_realization_id"]
    if restore is not None:
        history = list(restore["exploration"]["history"])
    else:
        history = [i for i in history if i != identity] + [identity]
    current = state["view_receipt"] or {}
    view = restore or designs.view(
        selected,
        stage=stage,
        reference_identity=(reference or {}).get("materialized_realization_id"),
        camera=current.get("camera"),
        presentation=state["presentation"],
        exploration={**state["exploration"], "history": history},
        render_policy=policy,
    )
    updates = {
        "selection": selected,
        "preview": preview,
        "preview_status": "compatible",
        "handoff": None,
        "sample_receipt": receipt,
        "stage": view["stage"],
        "view_receipt": view,
        "presentation": view["presentation"],
        "exploration": view["exploration"],
        "render_policy": view["render_policy"],
        "family_stage": view["presentation"]["family_stage"],
    }

    return updates, history
