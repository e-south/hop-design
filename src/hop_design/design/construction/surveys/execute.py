"""Incremental complete-interface evaluation with separate marginal and pair coverage."""

import json
import sqlite3
from pathlib import Path
from typing import Any

from hop_design.design.runtime import producer_identity
from hop_design.design.source_documents import load_source_mapping
from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction.intents.progress import DiscoveryProgress
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.serialization import canonical_json_bytes

from ..execution.feedback import (
    DiscoveryCancelled,
    DiscoveryFeedback,
    ProgressObserver,
    StopRequest,
)
from ..search.diversity import diversity_class
from .admission.preference import create_survey_index, read_preference_files
from .branches import SurveyBranches
from .completion.navigation import CompletionFrontierLimitError
from .completion.preferred import has_preferred_work
from .evaluate import LocalReceipts, evaluate_step
from .index import SurveyIndex
from .navigation.history import proof_references
from .navigation.target_seeds import propose_interface_targets
from .schedule import (
    CoverageSchedule,
    DiscoverySchedule,
    DiversitySchedule,
    InterfaceDiversitySchedule,
)


def load_request(path: str | Path) -> InterfaceSurveyRequest:
    return InterfaceSurveyRequest.model_validate_json(json.dumps(load_source_mapping(path)))


def evaluate_interface_survey(
    request_path: str | Path,
    index_path: str | Path,
    *,
    limits: SurveyEvaluationLimits,
    max_evaluations: int,
    resume: bool = False,
    max_checkpoint_bytes: int = 1_073_741_824,
    on_progress: ProgressObserver | None = None,
    should_stop: StopRequest | None = None,
) -> dict[str, Any]:
    """Advance a finite batch without omitting any declared target from coverage.

    Computation limits bind this execution index, independently of molecular
    scope. A target with exhausted computational limits remains unresolved.
    """
    if type(max_evaluations) is not int or max_evaluations < 1 or type(resume) is not bool:
        raise ValueError("Provide a positive evaluation budget and a Boolean resume flag.")
    feedback = DiscoveryFeedback(on_progress, should_stop)
    request = load_request(request_path)
    producer = producer_identity()
    branches = SurveyBranches(request)
    if branches.count == 0:
        raise ValueError(
            "Survey has no foldback geometry or jointly permitted basal/release method."
        )
    branches.search_order(limits)
    preference_files = (
        read_preference_files(
            Path(request_path).parent / "preferred-preparation", request.preferred_preparation
        )
        if request.preferred_preparation is not None and not resume
        else {}
    )
    opened = (
        SurveyIndex.open(
            Path(index_path),
            request=request,
            producer=producer,
            limits=limits.model_dump(mode="json"),
        )
        if resume
        else create_survey_index(
            Path(index_path),
            request=request,
            producer=producer,
            limits=limits.model_dump(mode="json"),
            maximum_bytes=max_checkpoint_bytes,
            files=preference_files,
        )
    )
    with opened as index:
        index.set_storage_limit(max_checkpoint_bytes)
        last = index.last_steps()
        previous_evaluations = sum(step + 1 for step in last.values())
        initial = DiscoveryProgress(
            product="released_insert",
            phase="searching",
            evaluations=previous_evaluations,
            new_evaluations=0,
            evaluation_budget=max_evaluations,
        )
        feedback.emit(initial)
        cancelled_before_search = feedback.stop_requested()
        cursors: dict[int, dict[str, Any] | None] = {}
        locals_ = LocalReceipts(index, limits, should_stop=feedback.stop_requested)
        preferred_targets = sorted(
            {
                candidate.target
                for candidate in (
                    ()
                    if cancelled_before_search
                    else locals_.preferred_candidates(branches, limits)
                )
            }
        )
        objective = limits.objective
        seeds = (
            propose_interface_targets(branches, limits)
            if objective is not None
            and objective.explores_interfaces
            and not cancelled_before_search
            else None
        )
        relevant = frozenset().union(*seeds.candidate_classes.values()) if seeds else frozenset()
        observed: set[str] = set()
        supported = set()
        continuations = 0
        for ordinal in last:
            for step in range(last[ordinal] + 1):
                saved = json.loads(index.record(ordinal, step=step))
                if step == last[ordinal]:
                    cursors[ordinal] = saved["next"]
                continuations += saved["continuations_examined"]
                for digest in proof_references(saved):
                    locals_.proofs.restore(ordinal, digest)
                if saved["witnesses"]:
                    supported.add(ordinal)
                    if objective is not None and relevant:
                        observed.update(
                            relevant.intersection(
                                diversity_class(objective, p["values"])
                                for p in saved["projections"]
                            )
                        )
        scheduler = (
            DiversitySchedule
            if limits.objective is not None
            else DiscoverySchedule
            if limits.scheduling == "discovery"
            else CoverageSchedule
        )
        ended = {target for target, cursor in cursors.items() if cursor is None}
        schedule: CoverageSchedule
        allocation = {}
        if seeds is not None and objective is not None:
            allocation = {
                "search_allocation": {
                    "policy": objective.target_policy,
                    "seeded_targets": len(seeds.targets),
                    "examined_frames": seeds.examined_frames,
                    "unknown_frames": seeds.unknown_frames,
                    "resource_stopped": seeds.resource_stopped,
                }
            }
            schedule = InterfaceDiversitySchedule(
                request.targets,
                last=last,
                supported=supported,
                ended=ended,
                preferred=seeds.targets,
                candidate_classes=seeds.candidate_classes,
                observed_classes=frozenset(observed),
            )
        else:
            schedule = scheduler(request.targets, last=last, supported=supported, ended=ended)
        certified_coverage = locals_.proofs.coverage()
        evaluated = new_continuations = 0
        stopped = "evaluation_budget"
        for _ in range(max_evaluations):
            if cancelled_before_search or feedback.stop_requested():
                stopped = "cancelled"
                break
            preferred = next(
                (
                    t
                    for t in preferred_targets
                    if t not in cursors or has_preferred_work(cursors[t], branches)
                ),
                None,
            )
            if preferred is not None:
                schedule.prefer_next(preferred)
            target = schedule.pop()
            if target is None:
                stopped = "exhausted_enumeration"
                break
            step = last.get(target, -1) + 1
            try:
                with index.evaluation(), index.origins.permitted():
                    address = (
                        cursors[target]
                        if target in cursors
                        else locals_.first_address(branches, limits, target)
                    )
                    assert address is not None, "Survey schedule emitted a finished target."
                    record = evaluate_step(
                        index, locals_, branches, limits, target=target, address=address
                    )
                    if producer_identity() != producer:
                        raise ValueError(
                            "Survey producer changed during evaluation; step was not committed."
                        )
                    index.append(
                        target,
                        step=step,
                        record=canonical_json_bytes(record),
                        witness_count=len(record["witnesses"]),
                        exhausted=record["next"] is None and record["exhaustion_proven"],
                    )
            except DiscoveryCancelled:
                stopped = "cancelled"
                break
            except SequenceSetLimitError:
                stopped = "sequence_space_budget"
                break
            except CompletionFrontierLimitError:
                stopped = "navigation_frontier_budget"
                break
            except sqlite3.OperationalError as error:
                if error.sqlite_errorcode != sqlite3.SQLITE_FULL:
                    raise
                stopped = "checkpoint_storage_limit"
                break
            # The checkpoint owns the full record; scheduling needs only its cursor.
            cursors[target], last[target] = record["next"], step
            certified_coverage = locals_.proofs.coverage()
            if isinstance(schedule, InterfaceDiversitySchedule) and objective is not None:
                schedule.observe_classes(
                    diversity_class(objective, p["values"]) for p in record["projections"]
                )
            schedule.update(
                target, step=step, supported=bool(record["witnesses"]), ended=record["next"] is None
            )
            evaluated += 1
            new_continuations += record["continuations_examined"]
            if on_progress is not None:
                feedback.emit(
                    initial.model_copy(
                        update={
                            "phase": "checkpointed",
                            "evaluations": previous_evaluations + evaluated,
                            "new_evaluations": evaluated,
                        }
                    )
                )
        if on_progress is not None:
            feedback.emit(
                initial.model_copy(
                    update={
                        "phase": "stopped",
                        "evaluations": previous_evaluations + evaluated,
                        "new_evaluations": evaluated,
                        "termination_reason": stopped,
                    }
                )
            )
        return {
            "schema": "hop.interface-survey-progress/v1",
            **allocation,
            **locals_.screen_facts,
            "termination_reason": stopped,
            "enumeration_scope": request.source_context_objective,
            "coverage_validation": "recorded_evaluations; aggregate_replay_not_requested",
            "coverage": index.coverage(),
            "new_evaluations": evaluated,
            "new_continuations_examined": new_continuations,
            "continuations_examined": continuations + new_continuations,
            **certified_coverage,
            "evaluations": sum(step + 1 for step in last.values()),
            "record_objects": index.object_count,
            "unfinished_targets": request.targets.pair_count
            - sum(cursor is None for cursor in cursors.values()),
        }
