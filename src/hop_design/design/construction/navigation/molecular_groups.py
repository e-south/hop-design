"""Reversible structural groups over exact stage-qualified molecular identities."""

from collections import defaultdict
from typing import Any

from hop_design.models.construction.variants.parameters import parameter_definition
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .distributions import geometry_distributions

HAIRPIN_FEATURES = (
    "loop_nt",
    "foldback_arm_bp",
    "open_side_paired_positions",
    "five_prime_unpaired_nt",
    "three_prime_unpaired_nt",
)
INSERT_FEATURES = ("left_gap", "right_gap", "left_end_polarity", "right_end_polarity")


def _words(rows: list[dict[str, Any]], key: str) -> str:
    return " / ".join(
        sorted({str(r["values"][key]) for r in rows if r["values"].get(key) is not None})
    )


def _family_labels(families: list[dict[str, Any]], keys: list[str]) -> None:
    """Name extra features only where the leading measurements are ambiguous."""
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for family in families:
        groups[tuple(tuple(family["features"].get(k, ())) for k in keys[:2])].append(family)
    for group in groups.values():
        named = keys[:2]
        for key in keys[2:]:
            signatures = {tuple(tuple(f["features"].get(k, ())) for k in named) for f in group}
            if len(signatures) == len(group):
                break
            if len({tuple(f["features"].get(key, ())) for f in group}) > 1:
                named = [*named, key]
        for family in group:
            labels = []
            for key in named:
                definition = parameter_definition(key)
                values = family["features"].get(key)
                value = "/".join(map(str, values)) if values else "not recorded"
                unit = definition.unit if values else ""
                labels.append(f"{definition.label} {value} {unit}".strip())
            family["label"] = " · ".join(labels) or "Geometry not recorded"


def molecular_families(
    choices: dict[str, Any],
    *,
    stage: str = "endpoint",
    endpoint: str = "released_insert",
) -> dict[str, Any]:
    if stage not in {"hairpin", "endpoint"}:
        raise ValueError("Molecular families require the hairpin or endpoint identity stage.")
    hairpin = stage == "hairpin" or endpoint in {"hairpin", "adapter_ligated_hairpin"}
    keys = HAIRPIN_FEATURES if hairpin else INSERT_FEATURES
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    preparations: dict[str, dict[str, Any]] = {}
    for source in choices["paths"]:
        path = {**source, "values": dict(source["values"])}
        identity = path["materialized_realization_id"]
        if identity in preparations:
            previous = preparations[identity]
            if any(previous[k] != path[k] for k in ("molecular_identity", "values", "matches")):
                raise ValueError("Repeated preparation has inconsistent molecular coordinates.")
            continue
        preparations[identity] = path
        product = path["molecular_identity"].get(stage)
        if product is None:
            raise ValueError("Requested molecular identity stage is absent from the choices.")
        grouped[product].append(path)
    for path in preparations.values():
        values = dict(path["values"])
        for key, value in path["values"].items():
            canonical = parameter_definition(key).canonical_key
            if canonical in values and values[canonical] != value:
                raise ValueError("Equivalent molecular coordinates disagree.")
            values[canonical] = value
        path["values"] = values
    products: list[dict[str, Any]] = []
    families: dict[str, dict[str, Any]] = {}
    for identity, rows in sorted(grouped.items()):
        features = {
            key: sorted({r["values"][key] for r in rows if r["values"].get(key) is not None})
            for key in keys
        }
        features = {key: values for key, values in features.items() if values}
        family_id = sha256_digest(canonical_json_bytes([stage, endpoint, features]))
        eligible = sorted(r["materialized_realization_id"] for r in rows if r["matches"])
        words = (
            _words(rows, "loop_word")
            if hairpin
            else " · ".join(
                filter(
                    None,
                    (
                        _words(rows, "left_end_word"),
                        _words(rows, "right_end_word"),
                    ),
                )
            )
        )
        products.append(
            {
                "identity": identity,
                "family_id": family_id,
                "features": features,
                "label": (f"Loop {words}" if hairpin and words else words) or "Recorded molecule",
                "preparations": sorted(r["materialized_realization_id"] for r in rows),
                "eligible_preparations": eligible,
                "state": "supported" if eligible else "supported_elsewhere",
            }
        )
        family = families.setdefault(
            family_id,
            {
                "identity": family_id,
                "features": features,
                "products": [],
                "eligible_products": [],
                "preparations": [],
            },
        )
        family["products"].append(identity)
        family["preparations"].extend(r["materialized_realization_id"] for r in rows)
        if eligible:
            family["eligible_products"].append(identity)
    if not hairpin:
        same_labels: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for product in products:
            same_labels[product["label"]].append(product)
        for peers in same_labels.values():
            loops = {p["identity"]: _words(grouped[p["identity"]], "loop_word") for p in peers}
            if len(set(loops.values())) > 1:
                for product in peers:
                    word = loops[product["identity"]]
                    if word:
                        product["label"] += f" · loop {word}"
    varied = [key for key in keys if len({tuple(p["features"].get(key, [])) for p in products}) > 1]
    dimensions = [
        key
        for key in varied
        if all(
            len(p["features"].get(key, [])) == 1 and type(p["features"][key][0]) is int
            for p in products
        )
    ]
    for family in families.values():
        family["preparations"].sort()
        current_query = choices["query"]
        members = set(family["preparations"])
        if current_query.get("membership") is not None:
            members.intersection_update(current_query["membership"]["preparations"])
        family["query"] = {
            **current_query,
            "membership": {
                "snapshot_digest": choices["snapshot_digest"],
                "preparations": sorted(members),
            },
        }
    _family_labels(list(families.values()), varied or list(keys))
    return {
        "schema": "hop.molecular-families/v1",
        "stage": stage,
        "product": "hairpin" if stage == "hairpin" else endpoint,
        "basis": "exact_products_grouped_by_recorded_structure",
        "products": products,
        "families": sorted(families.values(), key=lambda family: family["identity"]),
        "features": [parameter_definition(k).model_dump(mode="json") for k in keys],
        "distributions": geometry_distributions(
            list(preparations.values()),
            ("loop_nt", "foldback_arm_bp") if hairpin else ("left_gap", "right_gap"),
        ),
        "layout": {"kind": "feature_map", "x": dimensions[0], "y": dimensions[1]}
        if len(dimensions) >= 2
        else {"kind": "mosaic"},
    }
