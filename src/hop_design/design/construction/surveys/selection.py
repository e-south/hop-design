"""Exact selection and deterministic sampling, shared by every survey surface."""

import json
from pathlib import Path
from typing import Any

from hop_design.design.source_documents import load_source_mapping
from hop_design.models.construction.surveys.query import InterfaceSurveyQuery
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.models.construction.surveys.selection import InterfaceSurveySelection
from hop_design.models.construction.surveys.targets import FOUR_BASE_WORDS, InterfaceTargetDomain
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .index import SurveyIndex


def load_query(value: str | Path | dict[str, Any] | None) -> InterfaceSurveyQuery:
    source = (
        load_source_mapping(value)
        if isinstance(value, str | Path)
        else {}
        if value is None
        else value
    )
    return InterfaceSurveyQuery.model_validate_json(canonical_json_bytes(source))


def matches(path: dict[str, Any], query: InterfaceSurveyQuery) -> bool:
    return query.includes_preparation(path["materialized_realization_id"]) and all(
        p.accepts(path["values"].get(p.key)) for p in query.parameters
    )


def select_path(
    request: InterfaceSurveyRequest,
    snapshot_digest: str,
    path: dict[str, Any],
    query: InterfaceSurveyQuery,
) -> dict[str, Any]:
    if not matches(path, query):
        raise ValueError(
            "Selected preparation does not satisfy the query; no requirement was relaxed."
        )
    selection = InterfaceSurveySelection.model_validate_json(
        canonical_json_bytes(
            {
                "request_digest": sha256_digest(canonical_json_bytes(request)),
                "snapshot_digest": snapshot_digest,
                "query_digest": sha256_digest(canonical_json_bytes(query)),
                "record_digest": path["record_digest"],
                "query": query.model_dump(mode="json", by_alias=True),
                "address": path["address"],
                "materialized_realization_id": path["materialized_realization_id"],
            }
        )
    )
    return selection.model_dump(mode="json", by_alias=True)


def sample_path(
    paths: list[dict[str, Any]], query: InterfaceSurveyQuery, seed: int
) -> dict[str, Any]:
    """Hash-rank distinct exact preparations, not axes or unresolved possibilities."""
    if type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("Sampling seed must be an integer in [0, 2**64).")
    eligible = [p for p in paths if matches(p, query)]
    if not eligible:
        raise ValueError(
            "No complete preparation matches in this snapshot; no search or relaxation occurred."
        )
    return min(
        eligible,
        key=lambda p: (
            sha256_digest(canonical_json_bytes([seed, p["materialized_realization_id"]])),
            _location_key(p),
        ),
    )


def _location_key(path: dict[str, Any]) -> tuple[int, int, int] | tuple[int, str]:
    """Resolve repeated records after ranking exact preparation identity."""
    if "address" in path:
        return (0, path["address"]["target"], path["address"]["step"])
    return (1, path["option_label"])


def admit_selection(
    value: str | Path | dict[str, Any],
    request: InterfaceSurveyRequest,
    index: SurveyIndex,
) -> InterfaceSurveySelection:
    source = load_source_mapping(value) if isinstance(value, str | Path) else value
    selected = InterfaceSurveySelection.model_validate_json(canonical_json_bytes(source))
    if selected.request_digest != sha256_digest(canonical_json_bytes(request)):
        raise ValueError("Selected survey request digest disagrees with the request.")
    if selected.query_digest != sha256_digest(canonical_json_bytes(selected.query)):
        raise ValueError("Selected query digest disagrees with its predicates.")
    if (
        selected.query.membership is not None
        and selected.query.membership.snapshot_digest != selected.snapshot_digest
    ):
        raise ValueError("Selected preparation membership disagrees with its snapshot.")
    content = index.record(selected.address.target, step=selected.address.step)
    if selected.record_digest != sha256_digest(content):
        raise ValueError("Selected survey record digest disagrees with the recorded evaluation.")
    record = json.loads(content)
    if record["witnesses"] != [selected.materialized_realization_id]:
        raise ValueError("Selected survey identity disagrees with the recorded witness.")
    if len(record["projections"]) != 1 or not matches(record["projections"][0], selected.query):
        raise ValueError("Selected preparation does not satisfy the query.")
    # snapshot_digest describes the pool at selection time, not current coverage.
    # Append is allowed: the exact request, record, identity, and predicates remain checked.
    return selected


def interfaces_excluded(
    domain: InterfaceTargetDomain,
    excluded: tuple[tuple[str, str], ...],
    query: InterfaceSurveyQuery,
) -> bool:
    """A joint query is excluded only when every permitted target has a recorded proof."""
    if query.membership is not None:
        return False
    sides = _interface_sides(domain, query)
    total = len(sides[0]) * len(sides[1])
    return (
        total > 0
        and sum(left in sides[0] and right in sides[1] for left, right in excluded) == total
    )


def interfaces_pending(
    domain: InterfaceTargetDomain,
    ended: tuple[tuple[str, str], ...],
    query: InterfaceSurveyQuery,
) -> bool:
    """Use actual continuation availability, separate from support or exclusion."""
    if query.membership is not None:
        return False
    sides = _interface_sides(domain, query)
    total = len(sides[0]) * len(sides[1])
    return sum(left in sides[0] and right in sides[1] for left, right in ended) < total


def _interface_sides(domain: InterfaceTargetDomain, query: InterfaceSurveyQuery) -> list[set[str]]:
    sides = []
    for side in ("left", "right"):
        words = getattr(domain, f"{side}_words") or FOUR_BASE_WORDS
        predicates = [p for p in query.parameters if p.key == f"{side}_end_word"]
        sides.append({word for word in words if all(p.accepts(word) for p in predicates)})
    return sides
