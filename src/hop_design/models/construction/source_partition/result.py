"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/source_partition/result.py

Defines replay-verified source-partition candidate and search result authorities.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import combinations, islice
from typing import Literal

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.accounting import SearchCompletionStatus
from hop_design.models.construction.source_partition.replay import (
    SourcePartitionCandidateReplay,
    replay_source_partition_candidate,
)
from hop_design.models.construction.source_partition.request import (
    SourcePartitionDiscoveryRequest,
    _content_id,
)
from hop_design.models.construction.source_partition.types import (
    SourcePartitionDispositionKind,
    SourcePartitionFailure,
    SourcePartitionNickFunction,
    SourcePartitionTruncationReason,
)
from hop_design.models.method_states import (
    DenaturedFragmentSet,
    LengthSelectedFragmentSet,
    MultiSiteNickedDuplex,
)


def canonical_source_partition_candidates(
    request: SourcePartitionDiscoveryRequest,
) -> Iterator[tuple[str, ...]]:
    """Yield nonempty enzyme subsets in stable width-first lexical order."""
    ids = request.candidate_enzyme_ids
    for width in range(1, request.constraints.max_enzymes_per_program + 1):
        yield from combinations(ids, width)


def source_partition_truncation_reasons(
    request: SourcePartitionDiscoveryRequest,
    *,
    examined_nodes: int,
    realization_count: int,
) -> tuple[SourcePartitionTruncationReason, ...]:
    """Replay the first execution bound that stops canonical enumeration."""
    if examined_nodes >= request.candidate_space_size:
        return ()
    if realization_count >= request.enumeration.max_realizations:
        return (SourcePartitionTruncationReason.MAX_REALIZATIONS,)
    if examined_nodes >= request.enumeration.max_search_nodes:
        return (SourcePartitionTruncationReason.MAX_SEARCH_NODES,)
    return ()


def source_partition_candidate_id(
    request: SourcePartitionDiscoveryRequest,
    *,
    enzyme_ids: tuple[str, ...],
) -> str:
    return _content_id(
        "source-partition-candidate",
        {"problem_id": request.problem_id, "enzyme_ids": enzyme_ids},
    )


def source_partition_realization_id(
    request: SourcePartitionDiscoveryRequest,
    replay: SourcePartitionCandidateReplay,
) -> str:
    if (
        replay.failure_codes
        or replay.nicked_duplex is None
        or replay.denatured is None
        or replay.selected is None
    ):
        raise ValueError("Only an accepted source partition has a realization identity.")
    return _content_id(
        "source-partition-realization",
        {
            "problem_id": request.problem_id,
            "enzyme_ids": replay.enzyme_ids,
            "nicked_duplex": replay.nicked_duplex.model_dump(mode="json"),
            "denatured": replay.denatured.model_dump(mode="json"),
            "selected": replay.selected.model_dump(mode="json"),
            "nick_functions": tuple(item.model_dump(mode="json") for item in replay.nick_functions),
        },
    )


class SourcePartitionCandidateDisposition(HopModel):
    """Accepted or rejected outcome for one exact enzyme subset."""

    candidate_id: str = Field(pattern=r"^hop:source-partition-candidate/[0-9a-f]{64}@1$")
    enzyme_ids: tuple[str, ...] = Field(min_length=1)
    disposition: SourcePartitionDispositionKind
    failure_codes: tuple[SourcePartitionFailure, ...]
    realization_id: str | None = Field(
        default=None,
        pattern=r"^hop:source-partition-realization/[0-9a-f]{64}@1$",
    )

    @model_validator(mode="after")
    def validate_disposition(self) -> SourcePartitionCandidateDisposition:
        if self.enzyme_ids != tuple(sorted(set(self.enzyme_ids))):
            raise ValueError("Source-partition enzyme ids must be unique and canonical.")
        if self.failure_codes != tuple(
            sorted(set(self.failure_codes), key=lambda item: item.value)
        ):
            raise ValueError("Source-partition failure codes must be unique and canonical.")
        if self.disposition is SourcePartitionDispositionKind.ACCEPTED:
            if self.failure_codes or self.realization_id is None:
                raise ValueError(
                    "An accepted source partition requires one realization and no failures."
                )
        elif not self.failure_codes or self.realization_id is not None:
            raise ValueError("A rejected source partition requires failures and no realization.")
        return self


class SourcePartitionRealization(HopModel):
    """Exact multi-nick, denaturation, selection, and nick-function realization."""

    realization_id: str = Field(pattern=r"^hop:source-partition-realization/[0-9a-f]{64}@1$")
    enzyme_ids: tuple[str, ...] = Field(min_length=1)
    nicked_duplex: MultiSiteNickedDuplex
    denatured: DenaturedFragmentSet
    selected: LengthSelectedFragmentSet
    nick_functions: tuple[SourcePartitionNickFunction, ...] = Field(min_length=1)


class SourcePartitionDiscoveryResult(HopModel):
    """Replay-verified bounded search over canonical nickase subsets."""

    schema_id: Literal["hop.source-partition-result/v1"] = Field(
        default="hop.source-partition-result/v1", alias="schema"
    )
    request: SourcePartitionDiscoveryRequest
    problem_id: str = Field(pattern=r"^hop:source-partition-problem/[0-9a-f]{64}@1$")
    request_id: str = Field(pattern=r"^hop:source-partition-request/[0-9a-f]{64}@1$")
    result_id: str = Field(pattern=r"^hop:source-partition-result/[0-9a-f]{64}@1$")
    status: SearchCompletionStatus
    candidate_space_size: int = Field(ge=1)
    examined_nodes: int = Field(ge=0)
    dispositions: tuple[SourcePartitionCandidateDisposition, ...]
    realizations: tuple[SourcePartitionRealization, ...]
    truncation_reasons: tuple[SourcePartitionTruncationReason, ...]

    @model_validator(mode="after")
    def validate_result(self) -> SourcePartitionDiscoveryResult:
        if self.problem_id != self.request.problem_id or self.request_id != self.request.request_id:
            raise ValueError("Source-partition result must bind the exact request identities.")
        if self.candidate_space_size != self.request.candidate_space_size:
            raise ValueError("Source-partition candidate-space size must replay exactly.")
        if (
            self.examined_nodes != len(self.dispositions)
            or self.examined_nodes > self.candidate_space_size
        ):
            raise ValueError("Examined source-partition nodes must equal recorded dispositions.")
        observed_candidates = tuple(item.enzyme_ids for item in self.dispositions)
        expected_candidates = tuple(
            islice(
                canonical_source_partition_candidates(self.request),
                self.examined_nodes,
            )
        )
        if observed_candidates != expected_candidates:
            raise ValueError("Source-partition dispositions must form the canonical search prefix.")
        realization_by_id = {item.realization_id: item for item in self.realizations}
        if len(realization_by_id) != len(self.realizations):
            raise ValueError("Source-partition realization ids must be unique.")
        accepted_ids = tuple(
            item.realization_id
            for item in self.dispositions
            if item.disposition is SourcePartitionDispositionKind.ACCEPTED
        )
        if set(accepted_ids) != set(realization_by_id):
            raise ValueError("Accepted source-partition dispositions must bind every realization.")
        for disposition in self.dispositions:
            if disposition.candidate_id != source_partition_candidate_id(
                self.request,
                enzyme_ids=disposition.enzyme_ids,
            ):
                raise ValueError("Source-partition candidate identity must replay exactly.")
            replay = replay_source_partition_candidate(
                self.request,
                enzyme_ids=disposition.enzyme_ids,
            )
            if replay.failure_codes:
                if (
                    disposition.disposition is not SourcePartitionDispositionKind.REJECTED
                    or disposition.failure_codes != replay.failure_codes
                ):
                    raise ValueError("Rejected source-partition evidence must replay exactly.")
                continue
            if disposition.disposition is not SourcePartitionDispositionKind.ACCEPTED:
                raise ValueError("A replayable source partition must be accepted.")
            expected_id = source_partition_realization_id(self.request, replay)
            if disposition.realization_id != expected_id:
                raise ValueError("Source-partition realization identity must replay exactly.")
            realization = realization_by_id[expected_id]
            if (
                realization.enzyme_ids != replay.enzyme_ids
                or realization.nicked_duplex != replay.nicked_duplex
                or realization.denatured != replay.denatured
                or realization.selected != replay.selected
                or realization.nick_functions != replay.nick_functions
                or realization.realization_id != expected_id
            ):
                raise ValueError("Source-partition realization states must replay exactly.")

        domain_exhausted = self.examined_nodes == self.candidate_space_size
        expected_status = (
            SearchCompletionStatus.TRUNCATED
            if not domain_exhausted
            else SearchCompletionStatus.COMPLETE
            if self.realizations
            else SearchCompletionStatus.INFEASIBLE
        )
        if self.status is not expected_status:
            raise ValueError(
                "Source-partition completion status must follow exact search accounting."
            )
        expected_reasons = source_partition_truncation_reasons(
            self.request,
            examined_nodes=self.examined_nodes,
            realization_count=len(self.realizations),
        )
        if self.truncation_reasons != expected_reasons:
            raise ValueError("Source-partition truncation reasons must replay exactly.")
        expected_result_id = _content_id(
            "source-partition-result",
            {
                "request_id": self.request_id,
                "status": self.status,
                "candidate_space_size": self.candidate_space_size,
                "examined_nodes": self.examined_nodes,
                "dispositions": tuple(item.model_dump(mode="json") for item in self.dispositions),
                "realizations": tuple(item.model_dump(mode="json") for item in self.realizations),
                "truncation_reasons": self.truncation_reasons,
            },
        )
        if self.result_id != expected_result_id:
            raise ValueError("Source-partition result identity must replay exact result content.")
        return self


__all__ = [
    "SourcePartitionCandidateDisposition",
    "SourcePartitionDiscoveryResult",
    "SourcePartitionRealization",
    "canonical_source_partition_candidates",
    "source_partition_candidate_id",
    "source_partition_realization_id",
    "source_partition_truncation_reasons",
]
