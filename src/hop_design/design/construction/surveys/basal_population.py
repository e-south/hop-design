"""Admit coupled basal source/adapter populations before exact route compilation."""

import json
from dataclasses import dataclass

from hop_design.kernel.construction.basal.conditioned_population import ConditionedBasalPopulation
from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain
from hop_design.kernel.construction.basal.programs import (
    BasalPlacementFailure,
    BasalSequenceSolution,
)
from hop_design.kernel.construction.basal.sequence_index import BasalSequenceIndex
from hop_design.kernel.construction.basal.sequence_population import BasalSequencePopulation
from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.request import LocalNeighborhoodRequest
from hop_design.models.construction.sequence_sets import SequenceSpaceLimits

from ..basal.traversal import iter_basal_work_units
from ..basal_space_admission import admit_basal_source_assignments
from .coordinates import interleaved_at


@dataclass(frozen=True)
class BasalPopulation:
    """Joint local support with explicit program multiplicity, not whole-route support."""

    supports: tuple[BasalSequencePopulation | ConditionedBasalPopulation, ...]
    candidate_count: int
    program_count: int

    @property
    def program_cardinalities(self) -> tuple[int, ...]:
        """Sizes of admitted program populations in canonical interleaving order."""
        return tuple(s.cardinality for s in self.supports)

    @property
    def parts(self) -> int:
        return sum(s.cardinality for s in self.supports)

    def facts(self) -> dict[str, object]:
        return {
            "scope": "local_molecular_admission",
            "completion": "complete",
            "candidate_count": self.candidate_count,
            "program_count": self.program_count,
            "admitted_configurations": self.parts,
        }

    def member_at(
        self, rank: int
    ) -> tuple[BasalSequencePopulation | ConditionedBasalPopulation, BasalSequenceSolution]:
        """Recover the same joint source/adapter member used by exact selection."""
        if type(rank) is not int or not 0 <= rank < self.parts:
            raise ValueError("Basal member address lies outside the admitted population.")
        program_index, member_index = interleaved_at(
            tuple(s.cardinality for s in self.supports), rank
        )
        support = self.supports[program_index]
        return support, support.member_at(member_index)

    def method_at(self, rank: int) -> str:
        """Read the basal nickase, excluding any downstream release enzyme."""
        if type(rank) is not int or not 0 <= rank < self.parts:
            raise ValueError("Basal member address lies outside the admitted population.")
        index, _ = interleaved_at(self.program_cardinalities, rank)
        return str(self.supports[index].index.domain.program.nick_enzyme.enzyme_id)

    def select(self, product: ProductRequest, rank: int) -> ProductRequest:
        """Recover an admitted program/member through its ordinary exact raw address."""
        support, member = self.member_at(rank)
        domain = support.index.domain
        data = product.model_dump(mode="json", by_alias=True)
        data["basal"]["geometry"].update(
            nick_offsets_nt=[domain.target.nick_offset_nt],
            nick_strand=domain.target.nick_strand.value,
        )
        enzymes = data["basal"]["enzymes"]
        selected = {str(domain.program.nick_enzyme.enzyme_id)}
        if domain.program.future_release_enzyme is not None:
            selected.add(str(domain.program.future_release_enzyme.enzyme_id))
        enzymes["allowed_enzyme_ids"] = sorted(selected)
        for restriction in enzymes["role_restrictions"]:
            restriction["allowed_enzyme_ids"] = sorted(
                selected.intersection(restriction["allowed_enzyme_ids"])
            )
        data["basal"]["search"]["sequence_partition"] = {
            "part_count": max(2, support.index.cardinality),
            "part_index": support.index.rank_of(member),
        }
        return ProductRequest.model_validate_json(json.dumps(data))


def admit_population(
    local: LocalNeighborhoodRequest, limits: SequenceSpaceLimits
) -> BasalPopulation:
    """Solve complete local programs or raise explicitly at a computing limit."""
    supports = []
    programs = decisions = candidates = 0
    for overhead in range(local.search.max_retained_overhead_nt + 1):
        for unit in iter_basal_work_units(local, retained_overhead_nt=overhead):
            programs += 1
            if programs > limits.max_programs:
                raise SequenceSetLimitError("Basal joint-population program budget exhausted.")
            domain = solve_basal_sequence_domain(
                payload_sequence=unit.payload_sequence,
                target=unit.target,
                endpoint=local.endpoint,
                program=unit.program,
            )
            if isinstance(domain, BasalPlacementFailure):
                continue
            index = BasalSequenceIndex.create(domain)
            candidates += index.cardinality
            sources = admit_basal_source_assignments(
                domain=domain, policy=local.enzyme_provisioning, limits=limits
            )
            decisions += len(sources.decisions)
            if decisions > limits.max_result_decisions:
                raise SequenceSetLimitError("Basal joint-population result budget exhausted.")
            population = BasalSequencePopulation(
                index, sources, max_operations=limits.max_set_operations
            )
            if population.cardinality:
                supports.append(population)
    return BasalPopulation(tuple(supports), candidates, programs)
