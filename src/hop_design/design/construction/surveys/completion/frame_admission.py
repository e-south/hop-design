"""Reuse a necessary joint relation before lowering another exact end pair."""

from collections import OrderedDict

from hop_design.models.construction.sequence_sets import SequenceSet
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..branches import SurveyBranches
from ..coordinates import coordinate_rank
from .interfaces import EndPairAdmission, EndPairRelations

MAX_FRAME_ENTRIES = 4096
# This additional invocation index charges canonical bytes; Python overhead is extra.
MAX_FRAME_BYTES = 2 * 1024 * 1024


class BasalAdmissions:
    """Request and limits are fixed; target membership is never cached as a fact.

    Only established relations are reusable. An exact target can make lowering
    unsupported, so None must not poison the frame for another target.
    """

    def __init__(
        self, branches: SurveyBranches, limits: SurveyEvaluationLimits, relations: EndPairRelations
    ) -> None:
        if relations.policy != branches.request.materialization.source_preparation.source_ssdna:
            raise ValueError("Basal admission source permissions differ from the bound request.")
        if relations.limits != limits.sequence_space_limits:
            raise ValueError("Basal admission sequence limits differ from the bound evaluation.")
        self.branches, self.limits, self.relations = branches, limits, relations
        self._frames: OrderedDict[tuple[int, ...], tuple[SequenceSet, str, int]] = OrderedDict()
        self._bytes = 0

    def assess(self, target: int, geometry: tuple[int, ...]) -> EndPairAdmission | None:
        words = self.branches.request.targets.pair_at(target)
        # Even the omitted foldback coordinate must be valid before a warm lookup.
        rank = coordinate_rank(self.branches.geometry_sizes, geometry)
        key = (*geometry[:4], geometry[5])
        if key in self._frames:
            self._frames.move_to_end(key)
            relation, digest, _ = self._frames[key]
        else:
            product = self.branches.product(target, branch=rank, limits=self.limits)
            found = self.relations.relation(product)
            if found is None:
                return None
            relation = found
            content = canonical_json_bytes(relation)
            digest = sha256_digest(content)
            if len(content) <= MAX_FRAME_BYTES:
                self._frames[key] = relation, digest, len(content)
                self._bytes += len(content)
                while len(self._frames) > MAX_FRAME_ENTRIES or self._bytes > MAX_FRAME_BYTES:
                    _, (_, _, removed) = self._frames.popitem(last=False)
                    self._bytes -= removed
        return EndPairAdmission(relation.contains("".join(words)), relation.cardinality, digest)
