"""Replay every committed continuation before treating indexed coverage as evidence."""

import json
import tempfile
from pathlib import Path
from typing import Any

from hop_design.design.runtime import producer_identity
from hop_design.serialization import canonical_json_bytes

from .admission import open_survey
from .admission.preference import store_preference_files
from .branches import SurveyBranches
from .completion.batching import preceding_steps
from .evaluate import LocalReceipts, evaluate_step
from .execute import load_request
from .index import SurveyIndex
from .navigation.history import proof_references


def verify_interface_survey(request_path: str | Path, index_path: str | Path) -> dict[str, Any]:
    """Recompute recorded positives, negatives, cursors and coverage; never extend the input."""
    request, producer = load_request(request_path), producer_identity()
    saved, limits = open_survey(Path(index_path), request=request, producer=producer)
    with (
        saved,
        tempfile.TemporaryDirectory(prefix="hop-survey-replay-") as directory,
        SurveyIndex.create(
            Path(directory) / "replay.sqlite",
            request=request,
            producer=producer,
            limits=limits.model_dump(mode="json"),
        ) as replay,
    ):
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
            expected = evaluate_step(
                replay, locals_, branches, limits, target=target, address=address
            )
            if (
                canonical_json_bytes(expected) != raw
                or witnesses != len(expected["witnesses"])
                or exhausted != (expected["next"] is None and expected["exhaustion_proven"])
            ):
                raise ValueError(f"Survey evaluation {target}/{step} failed molecular replay.")
            # Check *all* referenced authorities, not just a copied manifest digest.
            record = json.loads(raw)
            authorities = (
                record["product_request"],
                *(record["bundle"] or {}).values(),
                *proof_references(record),
                *record.get("preceding_completion_steps", ()),
                *(step["product_request"] for step in preceding_steps(saved, record)),
            )
            for digest in (d for d in authorities if d is not None):
                if saved.get_object(digest) != replay.get_object(digest):
                    raise ValueError("Survey molecular authority failed replay.")
            replay.append(
                target, step=step, record=raw, witness_count=witnesses, exhausted=exhausted
            )
            previous, address, count = target, expected["next"], count + 1
        if producer_identity() != producer:
            raise ValueError("Survey producer changed during replay.")
        return {
            "schema": "hop.interface-survey-verification/v1",
            "replayed_evaluations": count,
            "coverage": replay.coverage(),
            **locals_.proofs.coverage(),
        }
