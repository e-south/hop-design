"""One derivation for recorded family choices and their shared-property interpretation."""

from collections.abc import Sequence
from typing import Any

from .properties import shared_values


def describe_choice(
    name: str,
    ordinal: int,
    portrait: dict[str, Any],
    shared: Sequence[str],
    reference: dict[str, Any],
) -> dict[str, Any]:
    values = shared_values(portrait, shared)
    differences = [
        {"property": key, "reference": reference[key], "observed": values[key]}
        for key in shared
        if values[key] != reference[key]
    ]
    prefix = f"members/{name}/choices/{ordinal}"
    return {
        "source_result_id": portrait["source_result_id"],
        "materialized_realization_id": portrait["materialized_realization_id"],
        "portrait": f"{prefix}/projection.json",
        "selection": f"{prefix}/selection.json",
        "geometry": {
            key: portrait[key]
            for key in ("loop_nt", "loop_side_paired_bp", "open_side_paired_positions", "stem_bp")
        },
        "shared_property_differences": differences,
        "eligible_for_shared_family": not differences,
    }


FAMILY_INTERPRETATION = (
    "Each member continues one recorded local pair. Failure does not "
    "prove global absence; display order is not a selection or optimum."
)
