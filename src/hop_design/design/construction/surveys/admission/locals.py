"""Invocation-owned local admission, reference lookup and replay caches."""

import json
from collections import OrderedDict
from typing import Any

from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction.request import LocalNeighborhoodRequest
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ...local_public import LocalNeighborhoodDiscovery, _discover_request, _verify_result_mapping
from ..branches import SurveyBranches
from ..geometry_order import GeometryOrder
from ..index import SurveyIndex
from ..navigation.admission_order import admitted_geometry_order
from ..navigation.history import EmptyPlaneHistory
from ..partitions import PartitionPlans
from ..preference_addressing import PreparationAddress, addresses_for_preparation
from .preference import load_preferred_preparation


class LocalReceipts:
    """Full local-request dependency keys; saved bytes are replayed before use."""

    def __init__(self, index: SurveyIndex, limits: SurveyEvaluationLimits):
        self.index = index
        self._warm: OrderedDict[str, LocalNeighborhoodDiscovery] = OrderedDict()
        self.partitions = PartitionPlans(index, limits.sequence_space_limits)
        self.proofs = EmptyPlaneHistory(index, limits)
        self._limits = limits
        self._order: GeometryOrder | None = None
        self._preferred: tuple[PreparationAddress, ...] | None = None

    def preferred_candidates(
        self, branches: SurveyBranches, limits: SurveyEvaluationLimits
    ) -> tuple[PreparationAddress, ...]:
        if branches.request != self.index.request or limits != self._limits:
            raise ValueError("Preparation preference must use its invocation's request and limits.")
        if self._preferred is None:
            reference = branches.request.preferred_preparation
            if reference is None:
                self._preferred = ()
            else:
                receipt = load_preferred_preparation(self.index)
                result = receipt._verified_source().result
                route = next(
                    r
                    for r in result.realizations
                    if r.materialized_realization_id == reference.materialized_realization_id
                )
                candidates = addresses_for_preparation(
                    result=result,
                    preparation=route,
                    branches=branches,
                    limits=limits,
                    partitions=self.partitions,
                )
                if len(candidates) > 16:
                    raise SequenceSetLimitError(
                        "Preparation preference exceeds 16 admitted frames."
                    )
                self._preferred = candidates
        return self._preferred

    def search_order(
        self, branches: SurveyBranches, limits: SurveyEvaluationLimits
    ) -> GeometryOrder:
        """Retain one admitted order for this immutable execution or replay invocation."""
        if branches.request != self.index.request or limits != self._limits:
            raise ValueError("Search order must use its invocation's request and limits.")
        if self._order is None:
            self._order = admitted_geometry_order(branches, limits, self.partitions)
        return self._order

    def first_address(
        self, branches: SurveyBranches, limits: SurveyEvaluationLimits, target: int
    ) -> dict[str, Any]:
        """Use the same conditioned initial cursor for execution and replay."""
        if branches.request.source_context_objective == "paired_scaffold_completions":
            from hop_design.models.construction.surveys.completion import CompletionSeekCursor

            from ..completion.preferred import preferred_groups_for

            preferred = preferred_groups_for(self, branches, limits, target)

            return {
                "completion_seek": CompletionSeekCursor(
                    schema=(
                        "hop.context-group-seek/v8"
                        if preferred
                        else "hop.context-group-seek/v7"
                        if limits.objective
                        else "hop.context-group-seek/v4"
                    ),
                    preferred_groups=preferred,
                ).model_dump(mode="json", by_alias=True),
                "exhaustion_proven": True,
            }
        branch, page = self.partitions.first_page(branches, limits, target)
        return {"branch": branch, "page": page, "pair": 0, "exhaustion_proven": True}

    def get(self, request: LocalNeighborhoodRequest) -> LocalNeighborhoodDiscovery:
        key = sha256_digest(canonical_json_bytes(request))
        if key in self._warm:
            self._warm.move_to_end(key)
            return self._warm[key]
        content = self.index.cached(key)
        if content is None:
            receipt = _discover_request(request)
            self.index.cache(key, receipt.json_bytes)
        else:
            receipt = _verify_result_mapping(json.loads(content))
            result = json.loads(receipt.json_bytes)
            embedded = result["neighborhood" if receipt.family == "foldback" else "discovery"][
                "request"
            ]
            if canonical_json_bytes(embedded) != canonical_json_bytes(request):
                raise ValueError("Survey local cache does not match its complete dependency key.")
        self._warm[key] = receipt
        while len(self._warm) > 8:
            self._warm.popitem(last=False)
        return receipt
