"""User-facing shared properties read from the same verified hairpin projection."""

import json
from collections.abc import Sequence
from typing import Any

from hop_design.models.construction.projections.hairpin import HairpinPortraitProjection

from ..comparison_regions import architecture_facts

MOLECULAR_CONTROLS = ("non_loop_sequences", "regional_contacts", "regional_joins")


def shared_values(portrait: dict[str, Any], include: Sequence[str] = ()) -> dict[str, Any]:
    architecture = HairpinPortraitProjection.model_validate_json(json.dumps(portrait))
    strand = portrait["state"]["molecules"][0]
    span = portrait["stem_primary_span"]
    release = portrait["later_release"]
    interfaces = (
        []
        if release is None
        else [
            {key: end[key] for key in ("product_end", "sequence", "overhang_end")}
            for end in sorted(release["cohesive_ends"], key=lambda e: e["product_end"])
        ]
    )
    values = {
        "stem_sequence": strand["sequence"][span["start"]["offset"] : span["end"]["offset"]],
        "endpoint": portrait["endpoint"],
        "release_interfaces": interfaces,
        "terminal_chemistry": {key: strand[key] for key in ("five_prime_end", "three_prime_end")},
        **architecture.scaffold_dimensions,
    }
    if "non_stem_sequences" in include:
        facts = architecture_facts(architecture)
        values["non_stem_sequences"] = {
            "stage": portrait["state"]["phase"],
            "regions": {
                key.split(".")[2]: value
                for key, value in facts.items()
                if key.startswith("hairpin.region.")
                and key.endswith(".sequence")
                and key.split(".")[2] not in ("stem_primary", "stem_return")
            },
        }
    if any(key in include for key in MOLECULAR_CONTROLS):
        facts = architecture_facts(architecture)
        for name, suffix in zip(
            MOLECULAR_CONTROLS, (".sequence", ".contacts", ".joins"), strict=True
        ):
            if name in include:
                values[name] = {
                    "stage": portrait["state"]["phase"],
                    "regions": {
                        key.split(".")[2]: value
                        for key, value in facts.items()
                        if key.startswith("hairpin.region.")
                        and key.endswith(suffix)
                        and (name != "non_loop_sequences" or key != "hairpin.region.loop.sequence")
                    },
                }
    return values
