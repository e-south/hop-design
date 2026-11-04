"""Per-target committed exclusion history, independent of admission-cache warmth."""

from collections.abc import Iterator
from typing import Any

from hop_design.design.runtime import producer_identity
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.proofs import EmptyBasalPlane
from hop_design.serialization import canonical_json_bytes

from ..basal_population import BasalPopulation
from ..branches import SurveyBranches
from ..index import SurveyIndex
from .pages import Plane
from .proofs import certify_empty_basal, verify_empty_basal


def proof_references(record: dict[str, Any]) -> Iterator[str]:
    for skipped in record.get("skipped_empty", []):
        yield from skipped.get("empty_basal_planes", [])
    yield from record.get("empty_basal_planes", [])


class EmptyPlaneHistory:
    def __init__(self, index: SurveyIndex, limits: SurveyEvaluationLimits):
        self.index, self.limits = index, limits
        self.branches = SurveyBranches(index.request)
        self.producer = producer_identity()
        self._planes: dict[int, set[Plane]] = {}

    def planes(self, target: int) -> frozenset[Plane]:
        return frozenset(self._planes.get(target, set()))

    def coverage(self) -> dict[str, int]:
        count = sum(len(planes) for planes in self._planes.values())
        return {
            "certified_empty_planes": count,
            "certified_empty_branch_cells": (
                count * self.branches.context_count * self.branches.geometry_sizes[4]
            ),
        }

    def record(self, target: int, branch: int, population: BasalPopulation) -> str | None:
        proof = certify_empty_basal(
            self.branches,
            self.limits,
            target=target,
            branch=branch,
            population=population,
            producer=self.producer,
        )
        if proof is None or proof.coordinates in self.planes(target):
            return None
        digest = self.index.put_object(canonical_json_bytes(proof))
        self._planes.setdefault(target, set()).add(proof.coordinates)
        return digest

    def restore(self, target: int, digest: str) -> None:
        proof = EmptyBasalPlane.model_validate_json(self.index.get_object(digest))
        if proof.target != target or proof.coordinates in self.planes(target):
            raise ValueError(
                "A committed empty-plane proof is duplicated or assigned to another target."
            )
        coordinates = verify_empty_basal(proof, self.branches, self.limits, producer=self.producer)
        self._planes.setdefault(target, set()).add(coordinates)
