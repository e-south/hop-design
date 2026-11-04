"""Use the ordinary complete compiler for each conditional auxiliary attempt."""

import json
from collections.abc import Iterator
from dataclasses import asdict
from functools import lru_cache
from typing import Any

from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
)
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.surveys.completion import (
    CompletionAttemptCursor,
    CompletionSeekCursor,
)
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits

from ...search.diversity import allocation_classes
from ..branches import SurveyBranches
from ..coordinates import coordinate_rank
from ..evaluate import LocalReceipts, compile_continuation
from ..index import SurveyIndex
from ..navigation.diversity import geometry_values, local_page_values
from ..partitions import ProductParts
from .binding import BoundContextCompletion, bind_context_completion
from .navigation import CompletionFrontierLimitError, CompletionNavigator
from .page_order import program_pages_at_depth
from .scheduling import schedule_followups


def _frame(
    locals_: LocalReceipts,
    branches: SurveyBranches,
    limits: SurveyEvaluationLimits,
    target: int,
    geometry_rank: int,
    page: int,
) -> tuple[ProductRequest, ProductParts, BoundContextCompletion | None]:
    product = branches.product(target, branch=geometry_rank, limits=limits)
    parts = locals_.partitions.get(product)
    bound = None
    if parts.conflict is None and not parts.empty_candidates:
        preparation = product.materialization.source_preparation.model_copy(
            update={
                "source_ssdna": branches.request.materialization.source_preparation.source_ssdna,
            }
        )
        envelope = product.model_copy(
            update={
                "materialization": product.materialization.model_copy(
                    update={
                        "source_preparation": preparation,
                    }
                ),
            }
        )
        bound = bind_context_completion(
            envelope,
            parts,
            page=page,
            limits=limits.sequence_space_limits,
            preferred_contexts=(
                tuple(
                    candidate.source_context
                    for candidate in locals_.preferred_candidates(branches, limits)
                    if (candidate.target, candidate.geometry_rank, candidate.page)
                    == (target, geometry_rank, page)
                )
                or branches.request.preferred_source_contexts
            )
            if isinstance(preparation.source_ssdna, ConstrainedSourceSsdnaPolicy)
            else (),
            handle_seed=branches.request.source_handle_seed or "",
        )
    return product, parts, bound


def _seek(
    locals_: LocalReceipts,
    branches: SurveyBranches,
    limits: SurveyEvaluationLimits,
    target: int,
    address: dict[str, Any],
) -> dict[str, Any]:
    cursor = CompletionSeekCursor.model_validate_json(json.dumps(address["completion_seek"]))

    @lru_cache(maxsize=8)
    def product(geometry: tuple[int, ...]) -> ProductRequest:
        return branches.product(
            target,
            branch=coordinate_rank(branches.geometry_sizes, geometry),
            limits=limits,
        )

    endpoint_admission: dict[str, dict[str, object]] = {}
    end_pair_admission: dict[str, dict[str, object]] = {}

    def admit_basal(geometry: tuple[int, ...]) -> bool:
        assessment = locals_.partitions.frame_admission(branches, limits, target, geometry)
        if assessment is None:
            return True  # Unsupported translation preserves ordinary full evaluation.
        rank = coordinate_rank(branches.geometry_sizes, geometry)
        end_pair_admission[str(rank)] = assessment.facts()
        return assessment.requested_pair_admitted

    def pages(geometry: tuple[int, ...], depth: int, after: int) -> Iterator[int]:
        parts = locals_.partitions.get(product(geometry))
        if parts.end_pair_admission is not None:
            rank = coordinate_rank(branches.geometry_sizes, geometry)
            end_pair_admission[str(rank)] = parts.end_pair_admission.facts()
        if parts.endpoint is not None:
            rank = coordinate_rank(branches.geometry_sizes, geometry)
            endpoint_admission[str(rank)] = parts.endpoint.facts()
        if limits.objective is not None and parts.conflict is None and not parts.empty_candidates:
            assert parts.foldback is not None and parts.basal_candidates is not None
            frame = (
                (target, geometry)
                if limits.objective.varies_foldback_members
                and geometry_values(branches, geometry)["loop_word"] is None
                else None
            )
            return program_pages_at_depth(
                parts.foldback.program_cardinalities,
                parts.basal_candidates.program_cardinalities,
                depth,
                after=after,
                maximum_frontier=limits.navigation_frontier,
                foldback_frame=frame,
            )
        return parts.pages_at_depth(depth, after=after)

    admission = {"pages": 0, "empty_pages": 0, "authored_contexts": 0, "admitted_contexts": 0}

    def counts(geometry: tuple[int, ...], page: int) -> int:
        _, parts, bound = _frame(
            locals_,
            branches,
            limits,
            target,
            coordinate_rank(branches.geometry_sizes, geometry),
            page,
        )
        if parts.empty_endpoint:
            return 0
        if bound is None:
            return 1
        admission["pages"] += 1
        admission["empty_pages"] += int(bound.plan.group_count == 0)
        admission["authored_contexts"] += bound.plan.raw_context_count
        admission["admitted_contexts"] += bound.plan.admitted_context_count
        return bound.plan.group_count

    objective = limits.objective

    @lru_cache(maxsize=4096)
    def class_key(geometry: tuple[int, ...], page: int | None) -> tuple[str | None, ...]:
        assert objective is not None
        values = geometry_values(branches, geometry)
        left, right = branches.request.targets.pair_at(target)
        values.update(left_end_word=left, right_end_word=right)
        page_parameters = tuple(
            key
            for key in ("foldback_method", "basal_method", "loop_word")
            if key in objective.parameters and values.get(key) is None
        )
        if page_parameters and page is not None:
            values.update(
                local_page_values(locals_.partitions.get(product(geometry)), page, page_parameters)
            )
        return allocation_classes(objective, values, allow_unknown=True)

    result = CompletionNavigator(
        locals_.search_order(branches, limits),
        pages,
        counts,
        admit_basal=admit_basal,
        class_key=class_key if objective else None,
    ).scan(
        cursor,
        empty_planes=locals_.proofs.planes(target),
        maximum_nodes=limits.navigation_nodes,
        maximum_frontier=limits.navigation_frontier,
    )
    following: dict[str, Any] | None = None
    if result.cursor is not None:
        following = {"exhaustion_proven": address["exhaustion_proven"]}
        if result.address is None:
            following["completion_seek"] = result.cursor.model_dump(mode="json", by_alias=True)
        else:
            geometry, page, group = result.address
            attempt = CompletionAttemptCursor(
                **result.work.model_dump(),
                geometry_rank=coordinate_rank(branches.geometry_sizes, geometry),
                page=page,
                group=group,
                depth=result.depth,
                after=result.cursor,
            )
            following["completion"] = attempt.model_dump(mode="json", by_alias=True)
    return {
        "schema": "hop.interface-survey-context-navigation/v1",
        "target": target,
        "completion_seek": address["completion_seek"],
        "next": following,
        "navigation_nodes": result.examined_nodes,
        "navigation_nodes_complete": True,
        "continuations_examined": 0,
        "exhaustion_proven": address["exhaustion_proven"],
        "witnesses": [],
        "bundle": None,
        "projections": [],
        "product_request": None,
        "empty_basal_planes": [],
        "limits": limits.model_dump(mode="json"),
        "enumeration_scope": "paired_scaffold_completions",
        "release_context_admission": admission,
        "endpoint_population_admission": endpoint_admission,
        "end_pair_admission": end_pair_admission,
    }


def evaluate_completion_step(
    index: SurveyIndex,
    locals_: LocalReceipts,
    branches: SurveyBranches,
    limits: SurveyEvaluationLimits,
    *,
    target: int,
    address: dict[str, Any],
) -> dict[str, Any]:
    if "completion_seek" in address:
        return _seek(locals_, branches, limits, target, address)
    attempt = CompletionAttemptCursor.model_validate_json(json.dumps(address["completion"]))
    product, _, bound = _frame(
        locals_,
        branches,
        limits,
        target,
        attempt.geometry_rank,
        attempt.page,
    )
    count, context, domain = 1, 0, None
    if bound is not None:
        domain = bound.plan.group_at(attempt.group)
        if domain.length_nt is not None:
            policy = branches.request.materialization.source_preparation.source_ssdna
            preferred = locals_.partitions.context_priority(product, attempt.page, policy)._order(
                domain.length_nt
            )
            if preferred is not None:
                domain = bound.plan.group_at(attempt.group, preferred=preferred.preferred.sequences)
        _, context = domain.member_at(attempt.member)
        count = domain.completion_count
    elif attempt.group or attempt.member:
        raise ValueError("A local exclusion has only one context-independent evidence address.")
    ordinary = {
        "branch": context * branches.geometry_count + attempt.geometry_rank,
        "page": attempt.page,
        "pair": attempt.pair,
        "exhaustion_proven": address["exhaustion_proven"],
    }
    result, request_bytes, _empty = compile_continuation(
        index,
        locals_,
        branches,
        limits,
        target=target,
        address=ordinary,
    )
    index.put_object(request_bytes)
    exclusions = tuple(
        sorted(
            set(attempt.excluded_context_patterns)
            | {item["context_pattern"] for item in result.get("context_site_exclusions", ())}
        )
    )
    next_member = attempt.member + 1 if attempt.member + 1 < count else None
    if domain is not None and next_member is not None and not result["witnesses"]:
        next_member = domain.next_unexcluded(
            next_member, exclusions, limits=limits.sequence_space_limits
        )
    finished_pair = bool(result["witnesses"]) or next_member is None
    # A stopped local search cannot resolve any unreported pair. Preserve that
    # unresolved scope while moving to other groups instead of pretending empty.
    if result["recorded_pairs"] == 0:
        finished_pair = True
    queued = schedule_followups(
        attempt,
        order=locals_.search_order(branches, limits),
        recorded_pairs=result["recorded_pairs"],
        next_member=None if finished_pair else next_member,
        exclusions=exclusions,
        maximum_frontier=limits.navigation_frontier,
    )
    if limits.objective and queued.schema_name in {
        "hop.context-group-seek/v7",
        "hop.context-group-seek/v8",
    }:
        observed = set(queued.observed_classes)
        for projection in result["projections"]:
            for key in allocation_classes(limits.objective, projection["values"]):
                assert key is not None  # Complete feedback rejects missing coordinates above.
                observed.add(key)
        if len(observed) > 100_000:
            raise CompletionFrontierLimitError("Observed diversity exceeds the saved cursor bound.")
        queued = queued.model_copy(update={"observed_classes": tuple(sorted(observed))})
    following: dict[str, Any] = {
        "exhaustion_proven": result["exhaustion_proven"],
        "completion_seek": queued.model_dump(mode="json", by_alias=True),
    }
    result.update(
        {
            "next": following,
            "completion": attempt.model_dump(mode="json", by_alias=True),
            "enumeration_scope": "paired_scaffold_completions",
            "context_protection": {"scope": "empty_local_population"}
            if bound is None
            else asdict(bound.protection),
            "group_completion_count": count,
            "group_pair_resolved": bool(result["witnesses"])
            or (finished_pair and result["exhaustion_proven"]),
            "continuations_examined": 1,
            "navigation_nodes": 0,
            "navigation_nodes_complete": True,
        }
    )
    return result
