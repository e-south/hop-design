"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/source_partition/discovery.py

Enumerates bounded nickase programs and returns replay-verified source partitions.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction import SearchCompletionStatus
from hop_design.models.construction.source_partition import (
    SourcePartitionCandidateDisposition,
    SourcePartitionDiscoveryRequest,
    SourcePartitionDiscoveryResult,
    SourcePartitionDispositionKind,
    SourcePartitionRealization,
    SourcePartitionTruncationReason,
)
from hop_design.models.construction.source_partition.replay import (
    replay_source_partition_candidate,
)
from hop_design.models.construction.source_partition.request import _content_id
from hop_design.models.construction.source_partition.result import (
    canonical_source_partition_candidates,
    source_partition_candidate_id,
    source_partition_realization_id,
)


def discover_source_partitions(
    request: SourcePartitionDiscoveryRequest,
) -> SourcePartitionDiscoveryResult:
    """Exhaust or truthfully truncate canonical enzyme-subset discovery."""
    candidates = canonical_source_partition_candidates(request)
    dispositions: list[SourcePartitionCandidateDisposition] = []
    realizations: list[SourcePartitionRealization] = []
    truncation_reasons: list[SourcePartitionTruncationReason] = []
    for enzyme_ids in candidates:
        if len(dispositions) >= request.enumeration.max_search_nodes:
            truncation_reasons.append(SourcePartitionTruncationReason.MAX_SEARCH_NODES)
            break
        replay = replay_source_partition_candidate(request, enzyme_ids=enzyme_ids)
        candidate_id = source_partition_candidate_id(request, enzyme_ids=enzyme_ids)
        if replay.failure_codes:
            dispositions.append(
                SourcePartitionCandidateDisposition(
                    candidate_id=candidate_id,
                    enzyme_ids=enzyme_ids,
                    disposition=SourcePartitionDispositionKind.REJECTED,
                    failure_codes=replay.failure_codes,
                )
            )
            continue
        realization_id = source_partition_realization_id(request, replay)
        dispositions.append(
            SourcePartitionCandidateDisposition(
                candidate_id=candidate_id,
                enzyme_ids=enzyme_ids,
                disposition=SourcePartitionDispositionKind.ACCEPTED,
                failure_codes=(),
                realization_id=realization_id,
            )
        )
        if replay.nicked_duplex is None or replay.denatured is None or replay.selected is None:
            raise AssertionError("Accepted source-partition replay omitted molecular states.")
        realizations.append(
            SourcePartitionRealization(
                realization_id=realization_id,
                enzyme_ids=enzyme_ids,
                nicked_duplex=replay.nicked_duplex,
                denatured=replay.denatured,
                selected=replay.selected,
                nick_functions=replay.nick_functions,
            )
        )
        if len(realizations) >= request.enumeration.max_realizations and len(dispositions) < len(
            candidates
        ):
            truncation_reasons.append(SourcePartitionTruncationReason.MAX_REALIZATIONS)
            break

    examined_nodes = len(dispositions)
    status = (
        SearchCompletionStatus.TRUNCATED
        if examined_nodes < len(candidates)
        else SearchCompletionStatus.COMPLETE
        if realizations
        else SearchCompletionStatus.INFEASIBLE
    )
    canonical_reasons = tuple(sorted(set(truncation_reasons), key=lambda item: item.value))
    result_seed = {
        "request_id": request.request_id,
        "status": status,
        "candidate_space_size": len(candidates),
        "examined_nodes": examined_nodes,
        "dispositions": tuple(item.model_dump(mode="json") for item in dispositions),
        "realizations": tuple(item.model_dump(mode="json") for item in realizations),
        "truncation_reasons": canonical_reasons,
    }
    return SourcePartitionDiscoveryResult(
        schema="hop.source-partition-result/v1",
        request=request,
        problem_id=request.problem_id,
        request_id=request.request_id,
        result_id=_content_id("source-partition-result", result_seed),
        status=status,
        candidate_space_size=len(candidates),
        examined_nodes=examined_nodes,
        dispositions=tuple(dispositions),
        realizations=tuple(realizations),
        truncation_reasons=canonical_reasons,
    )


__all__ = ["discover_source_partitions"]
