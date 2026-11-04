"""Deterministic family/product sampling over existing complete preparations."""

from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from hop_design.design.source_documents import load_source_mapping
from hop_design.models.construction.variants.sampling import (
    GuidedSampleReceipt,
    GuidedSampleRequest,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..intents.base import Source
from .molecular_groups import molecular_families
from .types import ChoiceSource


def guided_sample(
    choices: ChoiceSource,
    *,
    seed: int,
    query: Source | None = None,
    stage: str = "endpoint",
    history: tuple[str, ...] = (),
    different_loop: bool = False,
) -> dict[str, Any]:
    request = GuidedSampleRequest.model_validate_json(
        canonical_json_bytes(
            {
                "seed": seed,
                "stage": stage,
                "history": history,
            }
        )
    )
    result = choices.query(query)
    input_query = result["query"]
    if different_loop:
        from .local_contrast import loop_alternatives

        result = loop_alternatives(choices, result, request.history)
    atlas = molecular_families(
        result, stage=request.stage, endpoint=choices.resolution["intent"]["product"]
    )
    by_preparation = {
        identity: product for product in atlas["products"] for identity in product["preparations"]
    }
    if any(identity not in by_preparation for identity in request.history):
        raise ValueError("Sampling history contains preparations outside this recorded pool.")
    products = [p for p in atlas["products"] if p["eligible_preparations"]]
    if not products:
        raise ValueError("No complete preparation matches; no search or relaxation occurred.")
    current = request.history[-1] if request.history else None
    previous = by_preparation.get(current)
    visited = {by_preparation[i]["identity"] for i in request.history}
    visited_families = {by_preparation[i]["family_id"] for i in request.history}
    candidates = (
        [p for p in products if p["family_id"] not in visited_families]
        or [p for p in products if p["identity"] not in visited]
        or [p for p in products if previous is None or p["identity"] != previous["identity"]]
        or products
    )

    def rank(kind: str, value: str) -> str:
        return sha256_digest(canonical_json_bytes([request.seed, kind, value]))

    family = min({p["family_id"] for p in candidates}, key=lambda value: rank("family", value))
    product = min(
        (p for p in candidates if p["family_id"] == family),
        key=lambda p: rank("product", p["identity"]),
    )
    preparations = [i for i in product["eligible_preparations"] if i != current] or product[
        "eligible_preparations"
    ]
    identity = min(preparations, key=lambda value: rank("preparation", value))
    eligible = sorted((p["identity"], p["family_id"], p["eligible_preparations"]) for p in products)
    status, explanation = "selected", "Selected a complete preparation from the recorded molecules."
    if previous is not None:
        if identity == current:
            status, explanation = (
                "only_preparation",
                "This is the only matching preparation in the recorded pool.",
            )
        elif previous["identity"] == product["identity"]:
            status, explanation = (
                "preparation_alternative",
                "The same molecule, with a different complete preparation.",
            )
        elif previous["family_id"] == family:
            status, explanation = (
                "different_product",
                "A different molecule with the same recorded structural features.",
            )
        else:
            status, explanation = (
                "different_family",
                "A different molecule with a different recorded geometry.",
            )
    rows = {p["materialized_realization_id"]: p for p in result["paths"]}
    if different_loop:
        assert current is not None
        status = "loop_alternative"
        old_word, new_word = (rows[i]["values"]["loop_word"] for i in (current, identity))
        explanation = (
            f"Loop {old_word} → {new_word}. "
            "Other hairpin regions retain their sequence, contacts and terminal chemistry."
        )
    from .local_contrast import coordinate_changes

    changes = (
        coordinate_changes(rows[current]["values"], rows[identity]["values"]) if current else []
    )
    return GuidedSampleReceipt.model_validate_json(
        canonical_json_bytes(
            {
                **request.model_dump(mode="json"),
                "pool_digest": getattr(choices, "digest", result["snapshot_digest"]),
                "eligible_digest": sha256_digest(canonical_json_bytes(eligible)),
                "strategy": "loop/v1" if different_loop else "families/v1",
                "query": input_query,
                "selection": choices.select(identity, query=result["query"]),
                "family_id": family,
                "product_identity": product["identity"],
                "eligible_products": len(products),
                "eligible_preparations": sum(len(p["eligible_preparations"]) for p in products),
                "status": status,
                "explanation": explanation,
                "coordinate_changes": changes,
            }
        )
    ).model_dump(mode="json", by_alias=True)


def sample_choices(
    choices: ChoiceSource,
    *,
    ordinary: Callable[..., dict[str, Any]],
    seed: int | None = None,
    query: Source | None = None,
    strategy: str | None = None,
    stage: str | None = None,
    history: tuple[str, ...] = (),
    after: Source | None = None,
) -> dict[str, Any]:
    if after is not None:
        if history:
            raise ValueError("A saved view already specifies its sampling history.")
        view = choices.restore_view(after)
        exploration = view["exploration"]
        seed = exploration["seed"] if seed is None else seed
        strategy = exploration["strategy"] if strategy is None else strategy
        stage = view["presentation"]["family_stage"] if stage is None else stage
        history = tuple(exploration["history"]) if strategy in {"families", "loop"} else ()
        if strategy == "loop":
            identity = view["selection"]["materialized_realization_id"]
            if not history or history[-1] != identity:
                history = (*history, identity)
        query = view["selection"].get("query") if query is None else query
    if seed is None:
        raise ValueError("Supply a sampling seed or a saved view with its next seed.")
    strategy = strategy or "preparations"
    stage = stage or "endpoint"
    if strategy in {"families", "loop"}:
        return guided_sample(
            choices,
            seed=seed,
            query=query,
            stage=stage,
            history=history,
            different_loop=strategy == "loop",
        )
    if strategy != "preparations" or history or stage != "endpoint":
        raise ValueError(
            "Use the families strategy for stage-qualified guided sampling and history."
        )
    return ordinary(seed=seed, query=query)


def selection_source(choices: ChoiceSource, source: Source) -> dict[str, Any]:
    """Replay guided receipts before admitting their ordinary selection."""
    raw = load_source_mapping(source) if isinstance(source, str | Path) else source
    if raw.get("schema", "").startswith("hop.atlas-view/"):
        return cast(dict[str, Any], choices.restore_view(raw)["selection"])
    if raw.get("schema") != "hop.guided-sample/v1":
        return raw
    receipt = GuidedSampleReceipt.model_validate_json(canonical_json_bytes(raw))
    replay = guided_sample(
        choices,
        seed=receipt.seed,
        query=receipt.query,
        stage=receipt.stage,
        history=receipt.history,
        different_loop=receipt.strategy == "loop/v1",
    )
    if replay != receipt.model_dump(mode="json", by_alias=True):
        raise ValueError(
            "Guided sample receipt disagrees with its recorded pool or sampling inputs."
        )
    return receipt.selection
