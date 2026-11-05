"""Permit only regenerated producer-bound proofs to differ during an upgrade."""

import json
from typing import Any

from hop_design.models.construction.surveys.proofs import EmptyBasalPlane
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..completion.batching import preceding_steps
from ..index import SurveyIndex


class ProducerTransition:
    """Compare full records and authorities, rebinding only known proof references."""

    def __init__(
        self,
        saved: SurveyIndex,
        replay: SurveyIndex,
        source_producer: dict[str, str],
        producer: dict[str, str],
    ):
        self.saved, self.replay = saved, replay
        self.source_digest = sha256_digest(canonical_json_bytes(source_producer))
        self.producer_digest = sha256_digest(canonical_json_bytes(producer))
        self.rebound_proof_references = 0

    def _proof(self, old: str, new: str) -> str:
        before = EmptyBasalPlane.model_validate_json(self.saved.get_object(old))
        after_raw = self.replay.get_object(new)
        after = EmptyBasalPlane.model_validate_json(after_raw)
        rebound = before.model_dump(mode="json", by_alias=True)
        rebound["producer_digest"] = self.producer_digest
        if (
            before.producer_digest != self.source_digest
            or after.producer_digest != self.producer_digest
            or canonical_json_bytes(rebound) != after_raw
        ):
            raise ValueError("Survey exclusion proof changed during producer replay.")
        self.rebound_proof_references += int(old != new)
        return old

    def _proof_list(self, old: dict[str, Any], new: dict[str, Any]) -> None:
        before, after = old.get("empty_basal_planes", []), new.get("empty_basal_planes", [])
        if len(before) != len(after):
            raise ValueError("Survey exclusion scope changed during producer replay.")
        if "empty_basal_planes" in new:
            new["empty_basal_planes"] = [
                self._proof(a, b) for a, b in zip(before, after, strict=True)
            ]

    def compare(self, raw: bytes, expected: dict[str, Any], *, prelude: bool = False) -> None:
        """Keep every scientific field, continuation, ordering and non-proof byte exact."""
        before, after = json.loads(raw), json.loads(canonical_json_bytes(expected))
        self._proof_list(before, after)
        skipped_before, skipped_after = (
            before.get("skipped_empty", []),
            after.get("skipped_empty", []),
        )
        if len(skipped_before) != len(skipped_after):
            raise ValueError("Survey skipped work changed during producer replay.")
        for old, new in zip(skipped_before, skipped_after, strict=True):
            self._proof_list(old, new)
        old_steps = before.get("preceding_completion_steps", [])
        new_steps = after.get("preceding_completion_steps", [])
        if len(old_steps) != len(new_steps) or (prelude and (old_steps or new_steps)):
            raise ValueError("Survey completion batch changed during producer replay.")
        # Existing batching contract forbids nested preludes or hidden compilations.
        for old, _old_record, new_record in zip(
            old_steps,
            preceding_steps(self.saved, before),
            preceding_steps(self.replay, expected),
            strict=True,
        ):
            self.compare(self.saved.get_object(old), new_record, prelude=True)
        if "preceding_completion_steps" in after:
            after["preceding_completion_steps"] = old_steps
        if canonical_json_bytes(after) != raw:
            raise ValueError("Survey result or continuation changed during producer replay.")
        for digest in (before["product_request"], *(before["bundle"] or {}).values()):
            if digest is not None and self.saved.get_object(digest) != self.replay.get_object(
                digest
            ):
                raise ValueError("Survey molecular authority changed during producer replay.")
