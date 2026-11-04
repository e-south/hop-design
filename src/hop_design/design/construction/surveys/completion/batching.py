"""Batch navigation and proved empty work before one complete molecular attempt."""

import json
from collections.abc import Iterator
from typing import Any

from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.serialization import canonical_json_bytes

from ..branches import SurveyBranches
from ..evaluate import LocalReceipts
from ..index import SurveyIndex
from .execute import evaluate_completion_step


def preceding_steps(index: SurveyIndex, record: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Recover independently hashed steps without duplicating large saved frontiers."""
    for digest in record.get("preceding_completion_steps", ()):
        step = json.loads(index.get_object(digest))
        if step.get("preceding_completion_steps") or step["bundle"] is not None:
            raise ValueError("A completion prelude cannot nest batches or hide a compilation.")
        yield step


def evaluate_completion_batch(
    index: SurveyIndex,
    locals_: LocalReceipts,
    branches: SurveyBranches,
    limits: SurveyEvaluationLimits,
    *,
    target: int,
    address: dict[str, Any],
) -> dict[str, Any]:
    """Honor the work cap, preserve every step and stop at the first compilation.

    A navigation seek that spends its own node allowance ends this batch too.
    Unresolved zero-result local searches cannot be skipped as proved empties.
    Resource exceptions leave the entire evaluation uncommitted, as in the
    ordinary survey batch. Object-cache writes cannot establish coverage.
    """
    prior: list[str] = []
    proofs: list[str] = []
    continuations = navigation = 0
    for offset in range(limits.continuation_batch_size):
        result = evaluate_completion_step(
            index, locals_, branches, limits, target=target, address=address
        )
        continuations += result["continuations_examined"]
        navigation += result["navigation_nodes"]
        proofs.extend(result["empty_basal_planes"])
        following = result["next"]
        ready = (
            following is not None
            and result["bundle"] is None
            and (
                ("completion_seek" in address and "completion" in following)
                or (
                    "completion" in address
                    and result["recorded_pairs"] == 0
                    and result["exhaustion_proven"]
                )
            )
        )
        if not ready or offset + 1 == limits.continuation_batch_size:
            if prior:
                result["preceding_completion_steps"] = prior
                result["continuations_examined"] = continuations
                result["navigation_nodes"] = navigation
                result["empty_basal_planes"] = proofs
            return result
        prior.append(index.put_object(canonical_json_bytes(result)))
        address = following
    raise AssertionError("A positive batch limit always returns a terminal step.")
