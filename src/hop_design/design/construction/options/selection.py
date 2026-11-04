"""Translate explicit visible option labels to the existing exact set contract."""

import json
from pathlib import Path

from hop_design.export.construction.scaffold.options_report import selected_plate
from hop_design.models.construction.family.selection import ConstructionSetRequest
from hop_design.serialization import canonical_json_bytes

from ..families.selection import ConstructionSet, _select_admitted_construction_set
from .admission import captured_options
from .drawings import complementary_drawings
from .intent import bind_comparison, read_comparison


def select_construction_options(
    path: str | Path,
    *,
    option_labels: tuple[str, ...],
    baseline: str,
    shared_properties: tuple[str, ...] = (),
    compared_properties: tuple[str, ...] = (),
    comparison: str | Path | None = None,
) -> ConstructionSet:
    """Retrieve one molecule or a declared comparison without constructing authority paths."""
    intent = None
    roots = []
    if comparison is not None:
        if shared_properties or compared_properties:
            raise ValueError("Use comparison intent or separate properties, not both.")
        intent, comparison_root = read_comparison(comparison)
        roots.append(comparison_root)
        shared_properties = intent.shared_properties
        compared_properties = tuple(
            k
            for k in intent.members[0].dimensions
            if len({m.dimensions[k] for m in intent.members}) > 1
        )
    with captured_options(path) as (root, pool, receipts, protected):
        roots.append(protected)
        options = {o["label"]: o for o in pool["options"]}
        missing = set(option_labels) - options.keys()
        if missing:
            raise ValueError(f"Unknown option labels: {sorted(missing)}.")
        binding = (
            None if intent is None else bind_comparison(intent, [options[o] for o in option_labels])
        )
        request = {
            "schema": "hop.construction-set/v1",
            "members": [{"name": label, **options[label]["selection"]} for label in option_labels],
            "baseline": baseline,
            "shared_properties": list(shared_properties),
            "compared_properties": list(compared_properties),
        }
        request_path = root / "select-options.json"
        request_path.write_bytes(canonical_json_bytes(request))
        selected = _select_admitted_construction_set(
            request_path,
            ConstructionSetRequest.model_validate_json(json.dumps(request)),
            {label: receipts[label] for label in option_labels},
            tuple(roots),
        )
        files = dict(selected._files)
        for label in option_labels:
            prefix = f"members/{label}/portrait"
            for leaf, content in complementary_drawings(
                receipts[label],
                options[label]["materialized_realization_id"],
                files[f"{prefix}/projection.json"],
                files[f"{prefix}/projection.svg"],
            ).items():
                files[f"{prefix}/{leaf}"] = content
        summary = json.loads(selected.json_bytes)
        if binding is not None:
            files["selected-intent.json"] = canonical_json_bytes(binding)
        context = json.loads((root / "inputs/request.json").read_bytes())
        files["product-request.json"] = canonical_json_bytes(context)
        files.update(selected_plate(summary, files, context=context))
        selected = ConstructionSet._create(files, summary, selected.report_text)
        object.__setattr__(selected, "_roots", tuple(roots))
    return selected
