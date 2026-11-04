"""Explain local alternatives; only the existing preservation query certifies a control."""

from collections.abc import Iterator
from heapq import nsmallest
from pathlib import Path

from .landscape_source import molecular_landscape
from .local_contrast import (
    NoLoopAlternative,
    coordinate_changes,
    describe_changes,
    loop_alternatives,
)
from .neighbor_work import NeighborWork
from .numerical.comparison import PreparedComparison
from .similarity import dissimilarity
from .types import ChoiceSource, Record


def neighboring_preparations(
    choices: ChoiceSource,
    identity: str,
    *,
    query: Record | str | Path | None = None,
    limit: int = 5,
    verify_controls: bool = True,
    work: NeighborWork | None = None,
    answer: Record | None = None,
) -> Record:
    if type(limit) is not int or not 1 <= limit <= 32:
        raise ValueError("Choose between 1 and 32 neighboring preparations.")
    if type(verify_controls) is not bool:
        raise ValueError("Control verification must be true or false.")
    work = work or NeighborWork()
    with work.activate():
        return _neighbors(choices, identity, query, limit, verify_controls, work, answer)


def _neighbors(
    choices: ChoiceSource,
    identity: str,
    query: Record | str | Path | None,
    limit: int,
    verify_controls: bool,
    work: NeighborWork,
    answer: Record | None,
) -> Record:
    work.check()
    if answer is not None and answer["query"] != query:
        raise ValueError("Admitted neighbor context disagrees with its query.")
    # The local inspector already owns a query-bound answer. Reuse it only inside
    # that operation; captured landscape bytes and membership are still checked.
    landscape = (
        choices.landscape() if answer is None else molecular_landscape(choices, answer=answer)
    )
    work.check()
    descriptors = {p.identity: p for p in landscape.preparations}
    if identity not in descriptors:
        raise ValueError("Reference must be a preparation in this recorded landscape.")
    answer = choices.query(query) if answer is None else answer
    work.check()
    paths = {p["materialized_realization_id"]: p for p in answer["paths"]}
    old = paths[identity]
    rows = tuple(descriptors.values())
    index = {row.identity: i for i, row in enumerate(rows)}
    with PreparedComparison(rows, landscape.basis) as comparison:

        def distances() -> Iterator[tuple[float, str]]:
            for key, path in paths.items():
                work.check()
                if key != identity and path["matches"]:
                    yield comparison.distance(index[identity], index[key]), key

        ranked_ids = nsmallest(
            limit,
            distances(),
        )
    # Construct explanatory records only for returned neighbors; the numerical
    # kernel shares the reference's arithmetic and exact edit-distance semantics.
    ranked = [
        (dissimilarity(descriptors[identity], descriptors[key], landscape.basis), key)
        for _, key in ranked_ids
    ]
    verified: set[str] = set()
    notice = None
    if verify_controls and any(
        paths[key]["values"].get("loop_word") != old["values"].get("loop_word") for _, key in ranked
    ):
        try:
            controlled = loop_alternatives(
                choices, answer, (identity,), candidates=tuple(key for _, key in ranked)
            )
            verified = {
                p["materialized_realization_id"] for p in controlled["paths"] if p["matches"]
            }
        except NoLoopAlternative as error:
            notice = str(error)
    work.check()
    neighbors = []
    for difference, key in ranked:
        changes = coordinate_changes(old["values"], paths[key]["values"])
        description = (
            f"Loop {old['values']['loop_word']} → {paths[key]['values']['loop_word']}; "
            "surroundings preserved"
            if key in verified
            else describe_changes(changes)
        )
        neighbors.append(
            {
                "materialized_realization_id": key,
                "description": description,
                "dissimilarity": difference.model_dump(mode="json"),
                "coordinate_changes": changes,
                "preservation": "non_loop_hairpin_verified"
                if key in verified
                else "not_established",
            }
        )
    return {
        "reference_identity": identity,
        "landscape_digest": landscape.digest,
        "neighbors": neighbors,
        "preservation_notice": notice,
        "preservation_requested": verify_controls,
    }
