"""Prefer source-compatible contexts while preserving the full canonical domain."""

import json
from dataclasses import dataclass

from hop_design.kernel.construction.basal.programs import resolve_future_release_action
from hop_design.kernel.construction.context_order import SourceContextOrder
from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.kernel.construction.source_context import admit_source_contexts
from hop_design.models.construction.basal_release import (
    BasalFutureReleaseAction,
    BasalFutureReleaseRequirement,
)
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
    SourceSsdnaPolicy,
)
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.sequence_sets import SequenceSpaceLimits
from hop_design.models.enzymes import CharacterizedEnzyme
from hop_design.models.physical import Strand

from .basal_population import BasalPopulation
from .contexts import source_context_at, source_context_position, source_context_rank_at


@dataclass(frozen=True)
class SourceContextHint:
    """One exact local source and intended action, used only to prefer traversal."""

    source_sequence: str
    payload_boundary_nt: int
    enzyme: CharacterizedEnzyme
    action: BasalFutureReleaseAction


def basal_context_hint(
    product: ProductRequest, population: BasalPopulation, rank: int
) -> SourceContextHint | None:
    """Use one correlated source member; never assemble independent base marginals."""
    if (
        product.basal is None
        or product.ends is None
        or product.basal.geometry.nick_strand is not Strand.BOTTOM
    ):
        return None
    support, member = population.member_at(rank)
    enzyme = support.index.domain.program.future_release_enzyme
    if enzyme is None:
        return None
    requirement = BasalFutureReleaseRequirement.model_validate_json(
        json.dumps(
            {
                **product.ends.left.model_dump(mode="json"),
                "product_end": "left",
                "recognition_material": "source_duplex",
            }
        )
    )
    action = resolve_future_release_action(enzyme, requirement)
    if action is None:
        return None
    return SourceContextHint(
        member.source_precursor_sequence, member.payload_span.start.offset, enzyme, action
    )


class ContextPriority:
    """Invertible per-length preference; no assignment is excluded or added."""

    def __init__(
        self, policy: SourceSsdnaPolicy, hint: SourceContextHint | None, limits: SequenceSpaceLimits
    ) -> None:
        self.policy, self.hint, self.limits = policy, hint, limits
        self._orders: dict[int, SourceContextOrder | None] = {}

    def _order(self, length: int) -> SourceContextOrder | None:
        if self.hint is None or not isinstance(self.policy, ConstrainedSourceSsdnaPolicy):
            return None
        if length in self._orders:
            return self._orders[length]
        hint = self.hint
        # A later source window is not represented by this local hint. Fall back
        # to ordinary ordering; neither absent context nor a computing cap is an
        # exclusion of the complete preparation.
        start, word = hint.action.source_recognition_placement(
            payload_boundary=length + hint.payload_boundary_nt
        )
        if start + len(word) > length + len(hint.source_sequence):
            self._orders[length] = None
            return None
        try:
            preferred = admit_source_contexts(
                policy=self.policy,
                length_nt=length,
                local_source_sequence=hint.source_sequence,
                payload_boundary_nt=hint.payload_boundary_nt,
                enzyme=hint.enzyme,
                action=hint.action,
                max_decisions=self.limits.max_decisions,
                max_operations=self.limits.max_set_operations,
            )
            order = SourceContextOrder.create(
                preferred,
                max_decisions=self.limits.max_decisions,
                max_operations=self.limits.max_set_operations,
            )
        except SequenceSetLimitError:
            self._orders[length] = None
            return None
        self._orders[length] = order
        return order

    def rank_at(self, position: int) -> int:
        ordinary = source_context_rank_at(self.policy, position)
        word = source_context_at(self.policy, ordinary)
        order = None if word is None else self._order(len(word))
        if order is None:
            return ordinary
        return order.member_at(ordinary - order.preferred.canonical_origin)[1]

    def position(self, canonical_rank: int) -> int:
        word = source_context_at(self.policy, canonical_rank)
        order = None if word is None else self._order(len(word))
        if order is None:
            return source_context_position(self.policy, canonical_rank)
        assert word is not None
        ordinary = order.preferred.canonical_origin + order.position(word)
        return source_context_position(self.policy, ordinary)
