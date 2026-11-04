"""Delegate resumable hairpin snapshots to the verified scaffold discovery owner."""

import json
import tempfile
from pathlib import Path
from typing import Any, Literal

from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.intents.execution import HairpinExecution
from hop_design.models.construction.intents.progress import DiscoveryProgress
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..discovery.explore import _discover_with_receipts
from ..execution.feedback import DiscoveryCancelled, DiscoveryFeedback
from ..variants.admission import captured_generated_variants, captured_variant_source
from ..variants.public import ScaffoldExploration, _admitted_exploration
from .hairpin_choices import HairpinDesignChoices
from .hairpin_history import HairpinSnapshot, snapshot_paths, snapshot_source, validate_execution


def evaluate_hairpins(
    root: Path,
    max_evaluations: int,
    *,
    resolution: bytes,
    first_choices: int | None = None,
    feedback: DiscoveryFeedback | None = None,
) -> HairpinDesignChoices:
    """Commit a contiguous batch; observers count only published molecular snapshots."""
    if max_evaluations > 64:
        raise ValueError("Hairpin discovery permits at most 64 complete continuations per call.")
    previous = None
    previous_count = 0
    previous_digest = None
    cancelled = False

    def emit(
        phase: Literal["searching", "checkpointed", "stopped"],
        evaluated: int,
        reason: str | None = None,
    ) -> None:
        if feedback is not None:
            feedback.emit(
                DiscoveryProgress(
                    product=json.loads(resolution)["intent"]["product"],
                    phase=phase,
                    evaluations=evaluated,
                    new_evaluations=evaluated - previous_count,
                    evaluation_budget=max_evaluations,
                    termination_reason=reason,
                )
            )

    def stop_requested() -> bool:
        nonlocal cancelled
        cancelled = feedback is not None and feedback.stop_requested()
        return cancelled

    def stopped_without_work() -> HairpinDesignChoices:
        emit("stopped", previous_count, "cancelled")
        if previous is not None:
            return load_hairpin_choices(root, resolution)
        raise DiscoveryCancelled(
            "Discovery cancelled before a new molecular snapshot. "
            "Saved intent remains available to continue."
        )

    ordinal = len(snapshot_paths(root))
    if ordinal or (root / "scaffolds").exists():
        previous, previous_execution = snapshot_source(root)
        summary = json.loads((previous / "summary.json").read_bytes())
        previous_count = (
            previous_execution.evaluated_pairs
            if previous_execution
            else summary["coverage"]["evaluated_pairs"]
        )
        recorded = json.loads((previous / "branches/0000/summary.json").read_bytes())["coverage"][
            "recorded_pairs"
        ]
        if previous_count == recorded:
            emit("stopped", previous_count, "recorded_pairs_examined")
            return load_hairpin_choices(root, resolution)
        previous_digest = sha256_digest((previous / "manifest.json").read_bytes())
    emit("searching", previous_count)
    if stop_requested():
        return stopped_without_work()
    effort = json.loads((root / "effort.json").read_bytes())
    product = _apply_effort(json.loads(resolution)["effective_request"], effort)
    request = ScaffoldDiscoveryRequest.model_validate_json(
        canonical_json_bytes(
            {
                "schema": "hop.scaffold-discovery/v7"
                if effort.get("objective")
                else "hop.scaffold-discovery/v6",
                **({"objective": effort["objective"]} if effort.get("objective") else {}),
                "product": product,
                "comparison_stage": "hairpin",
                "max_branches": 1,
                "max_continuations_per_branch": max_evaluations,
            }
        )
    )
    with tempfile.TemporaryDirectory(prefix="hop-hairpin-execution-") as temporary:
        path = Path(temporary) / "request.json"
        path.write_bytes(canonical_json_bytes(request))
        try:
            packet, receipts = _discover_with_receipts(
                path,
                first_choices=first_choices,
                start_pair=previous_count,
                local_source=None if previous is None else previous / "branches/0000",
                feedback=DiscoveryFeedback(should_stop=stop_requested) if feedback else None,
            )
        except DiscoveryCancelled:
            if not cancelled:
                raise
            return stopped_without_work()
    summary = json.loads(packet.json_bytes)
    branch = summary["branches"][0]["coverage"]
    evaluated = previous_count + branch["evaluated_pairs"]
    stopped: Literal[
        "recorded_pairs_examined", "evaluation_limit", "first_choices", "cancelled"
    ] = (
        "cancelled"
        if cancelled
        else "recorded_pairs_examined"
        if evaluated == branch["recorded_pairs"]
        else "evaluation_limit"
    )
    if (
        not cancelled
        and first_choices is not None
        and evaluated < previous_count + max_evaluations
        and evaluated < branch["recorded_pairs"]
    ):
        stopped = "first_choices"
    execution = HairpinExecution(
        schema="hop.hairpin-design-execution/v2"
        if previous_count
        else "hop.hairpin-design-execution/v1",
        max_evaluations=max_evaluations,
        first_choices=first_choices,
        previous_evaluated_pairs=previous_count,
        evaluated_pairs=evaluated,
        previous_snapshot_digest=previous_digest,
        snapshot_digest=sha256_digest(dict(packet._files)["manifest.json"]),
        stopping_reason=stopped,
    )
    validate_execution(execution, json.loads(dict(packet._files)["branches/0000/summary.json"]))
    files = {f"scaffolds/{name}": data for name, data in packet._files}
    files["execution.json"] = canonical_json_bytes(execution)
    snapshot = HairpinSnapshot._create(
        files,
        execution.model_dump(mode="json", by_alias=True),
        "# Hairpin discovery snapshot\n\nVerified preparations and all examined failures. "
        "Execution effort and stopping policy are separate from molecular permissions.\n",
    )
    roots: tuple[ProtectedRoot, ...] = (ProtectedRoot.capture(root / "intent"),)
    if previous is not None:
        roots = (*roots, ProtectedRoot.capture(previous))
    object.__setattr__(snapshot, "_roots", roots)
    target = snapshot.write(root / "hairpin-snapshots" / f"{ordinal:04d}")
    if previous_count:
        from .hairpin_pages import captured_hairpin_pages

        with captured_hairpin_pages(target, generated=(packet, receipts)) as admitted:
            pool = _admitted_exploration(admitted, source_path=target)
    else:
        with captured_generated_variants(packet, receipts, target / "scaffolds") as admitted:
            pool = _admitted_exploration(admitted)
    result = _choices(root, resolution, pool, execution)
    emit("checkpointed", evaluated)
    emit("stopped", evaluated, stopped)
    return result


def _apply_effort(product: dict[str, Any], effort: dict[str, Any]) -> dict[str, Any]:
    for key in ("foldback", "basal"):
        if job := product.get(key):
            job["search"]["max_search_nodes"] = effort["local_nodes"]
            job["search"]["max_realizations"] = effort["local_realizations"]
            job["search"]["result_quota"] = effort["local_realizations"]
    return product


def load_hairpin_choices(
    root: Path, resolution: bytes, *, snapshot_digest: str | None = None
) -> HairpinDesignChoices:
    source, execution = snapshot_source(root, snapshot_digest)
    if execution is not None and execution.schema_id.endswith("/v2"):
        source = source.parent
    with captured_variant_source(source) as admitted:
        native = json.loads((admitted[0][0] / "intent/request.json").read_bytes())
        effort = json.loads((root / "effort.json").read_bytes())
        product = _apply_effort(
            json.loads(resolution)["effective_request"],
            effort,
        )
        if native["product"] != product:
            raise ValueError("Hairpin preparations disagree with the resolved molecular intent.")
        if native.get("objective") != effort.get("objective"):
            raise ValueError("Hairpin preparations disagree with the bound search objective.")
        if execution is not None and not execution.schema_id.endswith("/v2"):
            validate_execution(
                execution, json.loads((admitted[0][0] / "branches/0000/summary.json").read_bytes())
            )
        pool = _admitted_exploration(admitted, source_path=source)
    return _choices(root, resolution, pool, execution)


def _choices(
    root: Path, resolution: bytes, pool: ScaffoldExploration, execution: HairpinExecution | None
) -> HairpinDesignChoices:
    result = object.__new__(HairpinDesignChoices)
    object.__setattr__(result, "_directory", root)
    object.__setattr__(result, "_resolution", resolution)
    object.__setattr__(result, "_pool", pool)
    object.__setattr__(
        result,
        "_objective",
        SurveyEvaluationLimits.model_validate_json((root / "effort.json").read_bytes()).objective,
    )
    object.__setattr__(
        result, "_execution", canonical_json_bytes(execution) if execution else b"null"
    )
    return result
