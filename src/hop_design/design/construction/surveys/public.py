"""File-oriented survey execution and paginated inspection of committed evaluations."""

import json
from pathlib import Path
from typing import Any, Literal

from hop_design.design.runtime import producer_identity
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.variants.objective import DesignSearchObjective

from ..execution.feedback import ProgressObserver, StopRequest
from .admission import open_survey
from .branches import SurveyBranches
from .completion.batching import preceding_steps
from .execute import evaluate_interface_survey as _evaluate
from .execute import load_request
from .inspection import evaluated_local_pair


def evaluate_interface_survey(
    request_path: str | Path,
    index_path: str | Path,
    *,
    max_evaluations: int,
    local_nodes: int,
    local_realizations: int,
    release_site_pairs: int,
    scheduling: Literal["coverage", "discovery"] = "coverage",
    objective: dict[str, Any] | None = None,
    continuation_batch_size: int = 1,
    navigation_nodes: int = 256,
    navigation_frontier: int = 4096,
    sequence_decisions: int = 100_000,
    sequence_operations: int = 1_000_000,
    sequence_site_checks: int = 1_000_000,
    sequence_result_decisions: int = 1_000_000,
    resume: bool = False,
    max_checkpoint_bytes: int = 1_073_741_824,
    on_progress: ProgressObserver | None = None,
    should_stop: StopRequest | None = None,
) -> dict[str, Any]:
    """Advance a deterministic batch; molecular scope remains in the request file."""
    return _evaluate(
        request_path,
        index_path,
        max_evaluations=max_evaluations,
        resume=resume,
        max_checkpoint_bytes=max_checkpoint_bytes,
        on_progress=on_progress,
        should_stop=should_stop,
        limits=SurveyEvaluationLimits(
            scheduling=scheduling,
            objective=None
            if objective is None
            else DesignSearchObjective.model_validate_json(json.dumps(objective)),
            continuation_batch_size=continuation_batch_size,
            navigation_nodes=navigation_nodes,
            navigation_frontier=navigation_frontier,
            local_nodes=local_nodes,
            local_realizations=local_realizations,
            release_site_pairs=release_site_pairs,
            sequence_decisions=sequence_decisions,
            sequence_operations=sequence_operations,
            sequence_site_checks=sequence_site_checks,
            sequence_result_decisions=sequence_result_decisions,
        ),
    )


def inspect_interface_survey(
    request_path: str | Path,
    index_path: str | Path,
    *,
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """Read an integrity-checked index. Use verify_interface_survey for molecular replay."""
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Survey inspection requires offset >= 0 and 1 <= limit <= 1000.")
    request = load_request(request_path)
    branches = SurveyBranches(request)
    index, _ = open_survey(Path(index_path), request=request, producer=producer_identity())
    with index:
        rows = []
        for target, step, content, count, exhausted in index.evaluations(
            offset=offset, limit=limit
        ):
            record = json.loads(content)
            left, right = request.targets.pair_at(target)
            if count != len(record["witnesses"]) or exhausted != (
                record["next"] is None and record["exhaustion_proven"]
            ):
                raise ValueError("Survey evaluation accounting disagrees with its record.")
            rows.append(
                {
                    "target": target,
                    "step": step,
                    "left_end": left,
                    "right_end": right,
                    "kind": record["schema"],
                    "navigation_nodes": record.get("navigation_nodes", 0),
                    "navigation_nodes_complete": record.get("navigation_nodes_complete", True),
                    "navigation_stop": record.get("navigation_stop"),
                    "empty_basal_planes": record.get("empty_basal_planes", []),
                    "evaluated_local_pair": evaluated_local_pair(index, record),
                    "basal_release_projection": (
                        None
                        if record["product_request"] is None
                        else json.loads(index.get_object(record["product_request"]))["release"][
                            "basal_projection"
                        ]
                    ),
                    **{
                        key: record.get(key)
                        for key in (
                            "branch",
                            "page",
                            "pair",
                            "witnesses",
                            "local_coverage",
                            "rejection",
                            "outcome",
                        )
                    },
                    "skipped_empty": [
                        {
                            **attempt,
                            "basal_release_projection": branches.release_projection(
                                attempt["branch"]
                            ).model_dump(mode="json"),
                        }
                        for attempt in record.get("skipped_empty", [])
                    ],
                    "preceding_completion_steps": [
                        {
                            "kind": preceding["schema"],
                            "branch": preceding.get("branch"),
                            "page": preceding.get("page"),
                            "pair": preceding.get("pair"),
                            "rejection": preceding.get("rejection"),
                            "navigation_nodes": preceding["navigation_nodes"],
                            "continuations_examined": preceding["continuations_examined"],
                        }
                        for preceding in preceding_steps(index, record)
                    ],
                }
            )
        total = sum(step + 1 for step in index.last_steps().values())
        return {
            "schema": "hop.interface-survey-inspection/v1",
            "validation": "index_integrity_only",
            "storage": index.storage_info(),
            "coverage": index.coverage(),
            "total_evaluations": total,
            "evaluations": rows,
            "next_offset": offset + len(rows) if offset + len(rows) < total else None,
        }
