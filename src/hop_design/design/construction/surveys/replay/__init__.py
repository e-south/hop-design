"""One molecular replay loop for verification and explicit producer transitions."""

import json
from collections.abc import Callable
from typing import Any

from hop_design.design.runtime import producer_identity
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.serialization import canonical_json_bytes

from ..admission.preference import store_preference_files
from ..branches import SurveyBranches
from ..completion.batching import preceding_steps
from ..evaluate import LocalReceipts, evaluate_step
from ..index import SurveyIndex
from ..navigation.history import proof_references
from .comparison import ProducerTransition


def replay_evaluations(
    saved: SurveyIndex,
    replay: SurveyIndex,
    limits: SurveyEvaluationLimits,
    *,
    producer: dict[str, str],
    transition: ProducerTransition | None = None,
    on_replayed: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Regenerate every committed step; no selection of convenient matching records."""
    request = saved.request
    if request.preferred_preparation is not None:
        store_preference_files(
            replay,
            {
                entry.path: saved.get_object(entry.digest)
                for entry in request.preferred_preparation.files
            },
        )
    locals_, branches = LocalReceipts(replay, limits), SurveyBranches(request)
    previous, address, count = None, None, 0
    for target, step, raw, witnesses, exhausted in saved.evaluations():
        if previous != target:
            address = locals_.first_address(branches, limits, target)
        if address is None:
            raise ValueError("Survey evaluation follows an already finished target.")
        expected = evaluate_step(replay, locals_, branches, limits, target=target, address=address)
        if witnesses != len(expected["witnesses"]) or exhausted != (
            expected["next"] is None and expected["exhaustion_proven"]
        ):
            raise ValueError(f"Survey evaluation {target}/{step} failed molecular replay.")
        if transition is not None:
            transition.compare(raw, expected)
        else:
            if canonical_json_bytes(expected) != raw:
                raise ValueError(f"Survey evaluation {target}/{step} failed molecular replay.")
            record = json.loads(raw)
            authorities = (
                record["product_request"],
                *(record["bundle"] or {}).values(),
                *proof_references(record),
                *record.get("preceding_completion_steps", ()),
                *(prior["product_request"] for prior in preceding_steps(saved, record)),
            )
            for digest in (d for d in authorities if d is not None):
                if saved.get_object(digest) != replay.get_object(digest):
                    raise ValueError("Survey molecular authority failed replay.")
        replay.append(
            target,
            step=step,
            record=canonical_json_bytes(expected),
            witness_count=witnesses,
            exhausted=exhausted,
        )
        previous, address, count = target, expected["next"], count + 1
        if on_replayed is not None:
            on_replayed(count)
    if producer_identity() != producer:
        raise ValueError("Survey producer changed during replay.")
    return {
        "replayed_evaluations": count,
        "coverage": replay.coverage(),
        **locals_.proofs.coverage(),
    }
