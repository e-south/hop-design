"""Conditional availability within a frozen edition; no search or molecular derivation."""

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from hop_design.models.construction.surveys.query import InterfaceSurveyQuery
from hop_design.serialization import canonical_json_bytes, sha256_digest


@dataclass(frozen=True)
class SelectionIndex:
    """Small immutable coordinates from metadata checked at edition admission.

    Keep all records for a repeated identity: selection is existential, even if
    several recorded addresses produce the same preparation. Molecular files
    still pass their separate integrity checks when inspected or retrieved.
    """

    snapshot: str
    coordinates: Mapping[str, tuple[bytes, ...]]

    @classmethod
    def from_choices(cls, index: dict[str, Any]) -> "SelectionIndex":
        values: dict[str, list[bytes]] = {}
        for path in index["paths"]:
            values.setdefault(path["materialized_realization_id"], []).append(
                canonical_json_bytes(path["values"])
            )
        return cls(
            index["snapshot_digest"],
            MappingProxyType({identity: tuple(rows) for identity, rows in values.items()}),
        )

    def accepts(self, identity: str, query: InterfaceSurveyQuery) -> bool:
        query.validate_membership(self.snapshot, self.coordinates)
        if not query.includes_preparation(identity):
            return False
        return any(
            all(p.accepts(values.get(p.key)) for p in query.parameters)
            for values in (json.loads(raw) for raw in self.coordinates.get(identity, ()))
        )


def project_choices(index: dict[str, Any], query: InterfaceSurveyQuery) -> dict[str, Any]:
    query.validate_membership(
        index["snapshot_digest"], (p["materialized_realization_id"] for p in index["paths"])
    )
    # Evaluate predicates once per preparation. Facet availability ignores only
    # that facet's own predicate; membership always remains in force.
    failures = [
        frozenset(s.key for s in query.parameters if not s.accepts(p["values"].get(s.key)))
        for p in index["paths"]
    ]
    included = [
        query.includes_preparation(p["materialized_realization_id"]) for p in index["paths"]
    ]
    paths = [
        {**p, "matches": member and not failed}
        for p, member, failed in zip(index["paths"], included, failures, strict=True)
    ]
    axes = []
    for axis in index["axes"]:
        supported: Counter[Any] = Counter()
        conditional: Counter[Any] = Counter()
        own_predicate = {axis["key"]}
        for path, member, failed in zip(paths, included, failures, strict=True):
            value = path["values"].get(axis["key"])
            supported[value] += 1
            if member and (not failed or failed == own_predicate):
                conditional[value] += 1
        nodes = []
        for node in axis["nodes"]:
            witnesses, available = supported[node["value"]], conditional[node["value"]]
            nodes.append(
                {
                    **node,
                    "supported_preparations": witnesses,
                    "conditional_preparations": available,
                    "state": "supported"
                    if available
                    else "supported_elsewhere"
                    if witnesses
                    else "excluded_in_scope"
                    if node["state"] == "excluded_in_scope"
                    else "unresolved",
                }
            )
        axes.append({**axis, "nodes": nodes})
    eligible = [p for p in paths if p["matches"]]
    stages = set.intersection(*(set(p["molecular_identity"]) for p in paths)) if paths else set()
    return {
        **index,
        "schema": "hop.atlas-edition-choices/v1",
        "paths": paths,
        "axes": axes,
        "query": query.model_dump(mode="json", by_alias=True),
        "query_digest": sha256_digest(canonical_json_bytes(query)),
        "matching_preparations": len(eligible),
        "matching_records": len(eligible),
        "matching_products": {
            s: len({p["molecular_identity"][s] for p in eligible}) for s in sorted(stages)
        },
        "validation": "captured_evidence_integrity; no_current_producer_replay",
        "source_coverage": index["coverage"],
        "fully_enumerated": False,
        "all_preparations_enumerated": False,
    }
