"""Diagram-ready coordinates over admitted whole preparations; no new search or joins."""

from typing import Any

from hop_design.models.construction.variants.parameters import (
    ParameterSelection,
    parameter_definition,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .parameters.filter import conditional_availability, domain_marks

_REGIONS = {
    "closing": "Loop side",
    "assembly": "Open side",
    "stem": "Supplied stem",
    "interfaces": "Interfaces",
}
_DIMENSIONS = {
    "loop_nt": ("Loop size", "nt"),
    "loop_side_paired_bp": ("Loop-side extension", "bp"),
    "open_side_paired_positions": ("Open-side pairing", "positions"),
    "five_prime_unpaired_nt": ("5-prime terminal tail", "nt"),
    "three_prime_unpaired_nt": ("3-prime terminal tail", "nt"),
}


def _background(option: dict[str, Any], stage: str) -> dict[str, Any] | None:
    regions = {name: option["variants"][stage][name] for name in _REGIONS}
    if any(value is None for value in regions.values()):
        return None
    return regions


def choice_space(
    options: list[dict[str, Any]],
    eligible: list[str],
    stage: str,
    metadata: dict[str, Any] | None = None,
    selections: tuple[ParameterSelection, ...] = (),
) -> dict[str, Any]:
    """Project only active-query witnesses, preserving exact product/preparation multiplicity."""
    admitted = set(eligible)
    candidates = [o for o in options if o["label"] in admitted]
    backgrounds: dict[str, dict[str, Any]] = {}
    methods: dict[str, list[dict[str, str]]] = {}
    paths: list[dict[str, Any]] = []
    products: dict[str, list[str]] = {}
    metadata = metadata or {}
    for option in candidates:
        background = _background(option, stage)
        background_id = None
        if background is not None:
            background_id = sha256_digest(canonical_json_bytes(background))
            backgrounds[background_id] = background
        method_id = sha256_digest(canonical_json_bytes(option["methods"]))
        methods[method_id] = option["methods"]
        interface = option["interface"]
        values = {
            "loop_word": option.get("loop_sequence"),
            "background": background_id,
            "methods": method_id,
            **{key: option.get("geometry", {}).get(key) for key in _DIMENSIONS},
            **{
                f"{side}_gap": interface["achieved_distances_bp"][side] if interface else None
                for side in ("left", "right")
            },
            **option.get("parameter_values", {}),
        }
        identity = option["molecular_identity"][stage]
        paths.append({"option_label": option["label"], "molecule_id": identity, "values": values})
        products.setdefault(identity, []).append(option["label"])

    varying_regions = [
        name
        for name in _REGIONS
        if len({canonical_json_bytes(b[name]) for b in backgrounds.values()}) > 1
    ]
    background_labels = {}
    for identity, regions in backgrounds.items():
        labels = []
        for name in varying_regions:
            words = list(dict.fromkeys(s["sequence"] for s in regions[name]["sequences"]))
            labels.append(f"{_REGIONS[name]}: {' / '.join(words) or 'no sequence'}")
        background_labels[identity] = "; ".join(labels) or "Shared assessed surroundings"

    axes = []

    def axis(key: str, label: str, kind: str, at: str, unit: str = "") -> None:
        definition = parameter_definition(key)
        domain = metadata.get("parameter_domains", {}).get(key, {})
        observed = sorted({p["values"][key] for p in paths if p["values"].get(key) is not None})
        declared_values = domain.get("values")
        fixed = (
            len(declared_values) == 1
            if declared_values is not None
            else domain.get("minimum") is not None
            and domain.get("minimum") == domain.get("maximum")
        )
        values = {p["values"].get(key) for p in paths} | domain_marks(domain)
        values.update(
            p["values"][key]
            for p in metadata.get("local_parameter_support", [])
            if key in p["values"]
        )
        for selection in selections:
            if selection.key == key:
                values.update(selection.values or (selection.minimum, selection.maximum))
        ordered = sorted(v for v in values if v is not None)
        entries = []
        for value in [*ordered, *([None] if None in values else [])]:
            text = "Unassessed / not applicable" if value is None else str(value)
            detail: Any = None
            if value is not None and key == "background":
                text = background_labels.get(str(value), "Unobserved scaffold selection")
                detail = backgrounds.get(str(value))
            elif value is not None and key == "methods":
                detail = methods.get(str(value))
                text = (
                    " / ".join(m["name"] for m in detail)
                    if detail is not None
                    else "Unobserved method selection"
                )
            elif value is not None and key.endswith("_method"):
                text = metadata.get("parameter_names", {}).get(value, str(value))
            entries.append({"value": value, "label": text, "detail": detail})
        axes.append(
            {
                **definition.model_dump(mode="json"),
                "key": key,
                "label": label,
                "kind": kind,
                "stage": at,
                "unit": unit,
                "varying": len(values) > 1,
                "observed_values": observed,
                "observed_variation": len(observed) > 1,
                "fixed_by_request": fixed,
                "domain_status": "declared" if domain else "observed_only",
                "values": entries,
                "declared": domain,
            }
        )

    axis("loop_word", "Loop word", "categorical", "hairpin")
    axis("background", "Outside-loop scaffold", "categorical", stage)
    for key, (label, unit) in _DIMENSIONS.items():
        axis(key, label, "numeric", "hairpin", unit)
    for side in ("left", "right"):
        axis(f"{side}_gap", f"{side.title()} end-to-stem gap", "numeric", "released_insert", "bp")
    axis("methods", "Enzyme methods", "categorical", "preparation")
    existing = {a["key"] for a in axes}
    extra = (
        {selection.key for selection in selections}
        | set(metadata.get("parameter_domains", {}))
        | {key for path in paths for key in path["values"]}
    )
    for key in sorted(extra - existing):
        definition = parameter_definition(key)
        axis(key, definition.label, definition.kind, definition.stage, definition.unit)
    for path in paths:
        for item in axes:
            path["values"].setdefault(item["key"], None)
    return {
        "schema": "hop.scaffold-choice-space/v1",
        "scope": "active_query_complete_options_only",
        "stage": stage,
        "axes": axes,
        "paths": paths,
        "selections": [s.model_dump(mode="json", exclude_none=True) for s in selections],
        "availability": conditional_availability(paths, axes, selections),
        "local_support": metadata.get("local_parameter_support", []),
        "branch_coverage": metadata.get("parameter_branch_coverage", []),
        "primer_boundaries": metadata.get("primer_boundaries", []),
        "joint_permissions": metadata.get("joint_permissions", {}),
        "products": [
            {"molecule_id": identity, "option_labels": labels}
            for identity, labels in products.items()
        ],
    }
