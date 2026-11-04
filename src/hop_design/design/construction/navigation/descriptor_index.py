"""Compact comparison facts from an integrity-bound, immutable survey snapshot.

These facts are recorded at complete compilation. Reading them does not replay
the cohort; selected molecular retrieval retains its separate authority checks.
"""

import json
from typing import TYPE_CHECKING

from hop_design.models.construction.variants.similarity import MolecularDescriptor
from hop_design.serialization import canonical_json_bytes

if TYPE_CHECKING:
    from ..surveys.choices import InterfaceSurveyChoices


def indexed_descriptors(pool: "InterfaceSurveyChoices") -> tuple[MolecularDescriptor, ...] | None:
    rows = json.loads(pool._snapshot)["paths"]
    if not all("molecular_descriptor" in row for row in rows):
        return None  # Older snapshots require the existing full admission path.
    found: dict[str, MolecularDescriptor] = {}
    for row in rows:
        schema = row.get("molecular_descriptor_schema")
        if schema not in {"hop.molecular-descriptor/v1", "hop.molecular-descriptor/v2"}:
            raise ValueError("Unsupported recorded molecular descriptor schema.")
        descriptor = MolecularDescriptor.model_validate_json(
            canonical_json_bytes(row["molecular_descriptor"])
        )
        if (schema == "hop.molecular-descriptor/v2") != (
            descriptor.retained_terminal_bases is not None
        ):
            raise ValueError(
                "Recorded molecular descriptor disagrees with its terminal comparison schema."
            )
        if (
            descriptor.identity != row["materialized_realization_id"]
            or descriptor.stem != pool._request.stem_arm
            or descriptor.endpoint != "clone_ready_duplex"
        ):
            raise ValueError("Recorded molecular descriptor disagrees with its witness scope.")
        previous = found.get(descriptor.identity)
        if previous is not None and previous != descriptor:
            raise ValueError("One preparation has conflicting recorded molecular descriptors.")
        found[descriptor.identity] = descriptor
    return tuple(found[key] for key in sorted(found))
