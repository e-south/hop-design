"""Select a readable molecular projection without changing eligibility or identity."""

import json
from typing import Any

from ..presentation.parameter_labels import parameter_labels
from .display_projection import select_display_axes


def fixed_domain(axis: dict[str, Any]) -> bool:
    domain = axis.get("domain", {})
    if domain.get("basis") not in ("declared", "declared_permissions"):
        return False
    if "values" in domain:
        return len(set(domain["values"])) == 1
    return domain.get("minimum") is not None and domain.get("minimum") == domain.get("maximum")


def present_choices(
    choices: dict[str, Any], *, display_axes: tuple[str, ...] | None = None
) -> dict[str, Any]:
    """Keep product features, varying methods and active detailed constraints.

    Observed constants have separate context; they never become fixed permissions.
    Equivalent measurements have one axis, but every exact path remains available.
    """
    active = {p["key"] for p in choices.get("query", {}).get("parameters", [])}
    axes, fixed, detail, observed_constants = [], [], [], []
    seen = set()
    definitions, label_projection = parameter_labels(choices["axes"])
    for axis in definitions:
        key = axis.get("canonical_key", axis["key"])
        if key in seen:
            continue
        seen.add(key)
        if fixed_domain(axis):
            fixed.append(axis)
        elif (
            axis.get("domain", {}).get("basis") == "observed_only"
            and len(axis["nodes"]) == 1
            and not active.intersection({axis["key"], *axis.get("equivalent_measurements", [])})
        ):
            observed_constants.append(axis)
        elif axis.get("symbol") and (
            axis.get("design_role") == "product"
            or axis.get("representation") == "recognition"
            or active.intersection({axis["key"], *axis.get("equivalent_measurements", [])})
        ):
            axes.append(axis)
        else:
            detail.append(axis)
    # Basal/released-end coordinates share the left-hand neighborhood of the
    # folded hairpin. Keep foldback and loop axes under its right-hand cap.
    order = {region: i for i, region in enumerate(("assembly", "interfaces", "closing", "loop"))}
    axes.sort(key=lambda a: order.get(a.get("neighborhood", ""), 4))
    projection = None
    if display_axes is not None:
        axes, projection = select_display_axes(definitions, display_axes)
        projection["fixed"] = [a["key"] for a in fixed]
        projection["observed_constants"] = [a["key"] for a in observed_constants]
    allowed = {a["key"]: {n["value"] for n in a["nodes"]} for a in axes}
    groups: dict[str, dict[str, dict[str, Any]]] = {}
    for path in choices["paths"]:
        coordinates = [path["values"].get(a["key"]) for a in axes]
        if any(v not in allowed[a["key"]] for a, v in zip(axes, coordinates, strict=True)):
            raise ValueError("A complete plotted path is missing a declared coordinate.")
        key = json.dumps(coordinates)
        groups.setdefault(key, {})[path["materialized_realization_id"]] = path
    return {
        **({"display_projection": projection} if projection is not None else {}),
        "label_projection": label_projection,
        "axes": axes,
        "fixed": fixed,
        "observed_constants": observed_constants,
        "detail": detail,
        "traces": [list(group.values()) for group in groups.values()],
        "preparations": len({p["materialized_realization_id"] for p in choices["paths"]}),
    }
