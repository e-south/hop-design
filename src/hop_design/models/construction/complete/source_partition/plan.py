"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/source_partition/plan.py

Binds a selected cleanup program to its exact replayable molecular inputs.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from pydantic import model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.source_partition.replay import replay_source_partition_candidate
from hop_design.models.construction.source_partition.request import SourcePartitionDiscoveryRequest
from hop_design.models.construction.source_partition.result import (
    SourcePartitionDiscoveryResult,
    SourcePartitionRealization,
    source_partition_realization_id,
)


class SourcePartitionPlan(HopModel):
    """One exact selected program, independent of its surrounding search ledger."""

    request: SourcePartitionDiscoveryRequest
    realization: SourcePartitionRealization

    @model_validator(mode="after")
    def validate_plan(self) -> "SourcePartitionPlan":
        SourcePartitionDiscoveryRequest.model_validate(self.request.model_dump(mode="python"))
        replay = replay_source_partition_candidate(
            self.request, enzyme_ids=self.realization.enzyme_ids
        )
        expected_id = source_partition_realization_id(self.request, replay)
        assert replay.nicked_duplex is not None
        assert replay.denatured is not None
        assert replay.selected is not None
        assert replay.fragment_certificate is not None
        expected = SourcePartitionRealization(
            realization_id=expected_id,
            enzyme_ids=replay.enzyme_ids,
            nicked_duplex=replay.nicked_duplex,
            denatured=replay.denatured,
            selected=replay.selected,
            nick_functions=replay.nick_functions,
            fragment_certificate=replay.fragment_certificate,
        )
        if self.realization != expected:
            raise ValueError("Selected partition states must replay their exact request.")
        return self


def selected_partition_plan(
    authority: SourcePartitionDiscoveryResult | None, realization_id: str | None
) -> SourcePartitionPlan | None:
    """Select a replayable program without copying the enumeration ledger into each route."""
    if authority is None:
        if realization_id is not None:
            raise ValueError("Selected partition requires its authority.")
        return None
    for realization in authority.realizations:
        if realization.realization_id == realization_id:
            return SourcePartitionPlan(request=authority.request, realization=realization)
    raise ValueError("Selected partition realization is absent from its authority.")
