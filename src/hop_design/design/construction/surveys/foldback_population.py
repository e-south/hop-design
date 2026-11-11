"""Compact local admission with exact addressing into ordinary molecular replay."""

import json
from dataclasses import dataclass, replace
from functools import cached_property

from hop_design.kernel.construction.foldback.domains import (
    FoldbackSequenceDomain,
    solve_foldback_sequence_domain,
)
from hop_design.kernel.construction.foldback.programs import FoldbackProgramCandidate
from hop_design.kernel.construction.foldback.solutions import FoldbackSequenceSolution
from hop_design.models.construction.complete.source_preparation.policy import (
    SourceDuplexPreparationPolicy,
    primer_required_length,
)
from hop_design.models.construction.foldback import FoldbackCleavageProgramKind
from hop_design.models.construction.foldback_space import (
    FoldbackProgramSupport,
    FoldbackSequenceCase,
    FoldbackSequenceRequest,
    FoldbackSequenceResult,
)
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.request import LocalNeighborhoodRequest
from hop_design.models.construction.sequence_sets import SequenceSpaceLimits
from hop_design.models.construction.surveys.execution import DEFAULT_SEQUENCE_LIMITS
from hop_design.models.physical import Strand
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..foldback_space import discover_sequence_space, verify_sequence_space
from .coordinates import interleaved_at, interleaved_rank
from .index import SurveyIndex


def default_sequence_limits() -> SequenceSpaceLimits:
    return DEFAULT_SEQUENCE_LIMITS


@dataclass(frozen=True)
class _ProgramAdmission:
    case: FoldbackSequenceCase
    support: FoldbackProgramSupport
    domain: FoldbackSequenceDomain
    primer_role: str
    available_nt: int
    required_nt: int

    @property
    def admitted(self) -> bool:
        return self.available_nt >= self.required_nt

    def facts(self) -> dict[str, object]:
        return {
            "case_id": self.case.case_id,
            "kind": self.support.kind.value,
            "nick_enzyme_id": str(self.support.nick_enzyme_id),
            "nick_orientation": self.support.nick_orientation.value,
            "terminus_enzyme_id": self.support.terminus_enzyme_id,
            "terminus_orientation": self.support.terminus_orientation,
            "primer_role": self.primer_role,
            "available_nt": self.available_nt,
            "required_nt": self.required_nt,
            "program_supported_members": self.support.sequences.cardinality,
            "program_supported_precursors": self.support.source_assignments.cardinality,
            "admitted": self.admitted,
        }


def _admit_programs(
    result: FoldbackSequenceResult, policy: SourceDuplexPreparationPolicy | None
) -> tuple[_ProgramAdmission, ...]:
    """Keep exact local admission intact and assess an additional necessary condition.

    The source expression has a fixed length for every member of one program.
    TOP sources start with the payload; mirrored BOTTOM sources end with it.
    The remaining local source interval is consequently the foldback-side
    primer footprint, regardless of the independently added basal-side context.
    Sequential terminus programs may add source bases: use their full expression,
    never an A/D/C approximation. Admission here is not complete-route support.
    """
    catalog = result.request.enzyme_provisioning.catalog
    entries = []
    for case in result.cases:
        for support in case.programs:
            if not support.sequences.cardinality:
                continue
            program = FoldbackProgramCandidate(
                kind=support.kind,
                nick_enzyme=catalog.by_id(support.nick_enzyme_id),
                nick_orientation=support.nick_orientation,
                terminus_enzyme=(
                    None
                    if support.terminus_enzyme_id is None
                    else catalog.by_id(support.terminus_enzyme_id)
                ),
                terminus_orientation=support.terminus_orientation,
            )
            domain = solve_foldback_sequence_domain(
                payload_sequence=case.payload_sequence, target=case.target, program=program
            )
            if not isinstance(domain, FoldbackSequenceDomain):
                raise ValueError("Admitted foldback program has no exact placement domain.")
            role = "reverse_primer" if case.target.nick_strand is Strand.TOP else "forward_primer"
            required = 0 if policy is None else primer_required_length(getattr(policy, role))
            entries.append(
                _ProgramAdmission(
                    case,
                    support,
                    domain,
                    role,
                    len(domain.source_expression) - len(case.payload_sequence),
                    required,
                )
            )
    return tuple(entries)


@dataclass(frozen=True)
class FoldbackPopulation:
    """Complete local populations; admission is not a complete-route claim."""

    result: FoldbackSequenceResult
    source_preparation: SourceDuplexPreparationPolicy | None = None

    def for_source_preparation(self, policy: SourceDuplexPreparationPolicy) -> "FoldbackPopulation":
        return replace(self, source_preparation=policy)

    @cached_property
    def _programs(self) -> tuple[_ProgramAdmission, ...]:
        return _admit_programs(self.result, self.source_preparation)

    @cached_property
    def _admitted(self) -> tuple[_ProgramAdmission, ...]:
        return tuple(p for p in self._programs if p.admitted)

    @property
    def program_cardinalities(self) -> tuple[int, ...]:
        """Sizes after source-primer admission, in canonical interleaving order."""
        return tuple(p.support.source_assignments.cardinality for p in self._admitted)

    @property
    def parts(self) -> int:
        # Programs remain separate preparation choices. Distinct molecular products
        # must be counted from their identities, not from this enumeration size.
        return sum(self.program_cardinalities)

    def facts(self) -> dict[str, object]:
        local_members = sum(p.sequences.cardinality for c in self.result.cases for p in c.programs)
        local_precursors = sum(
            p.source_assignments.cardinality for c in self.result.cases for p in c.programs
        )
        facts: dict[str, object] = {
            "scope": self.result.claim_scope,
            "completion": self.result.completion,
            "result_id": self.result.result_id,
            "candidate_count": self.result.candidate_count,
            "admitted_configurations": self.result.admitted_count,
            "program_supported_members": local_members,
            "program_supported_precursors": local_precursors,
        }
        if self.source_preparation is not None:
            facts["source_primer_admission"] = {
                "scope": "foldback_source_primer_span",
                "admitted_members": self.parts,
                "excluded_members": local_precursors - self.parts,
                "programs": [p.facts() for p in self._programs],
            }
        return facts

    def _member(self, rank: int) -> tuple[_ProgramAdmission, str]:
        if type(rank) is not int or not 0 <= rank < self.parts:
            raise ValueError("Foldback member address lies outside the admitted population.")
        index, member = interleaved_at(self.program_cardinalities, rank)
        selected_program = self._admitted[index]
        return selected_program, selected_program.support.source_assignments.member_at(member)

    def method_at(self, rank: int) -> str:
        """Read the foldback nickase without materializing a sequence member."""
        if type(rank) is not int or not 0 <= rank < self.parts:
            raise ValueError("Foldback member address lies outside the admitted population.")
        index, _ = interleaved_at(self.program_cardinalities, rank)
        return str(self._admitted[index].support.nick_enzyme_id)

    def ranks_of(
        self, solution: FoldbackSequenceSolution, *, program_kind: FoldbackCleavageProgramKind
    ) -> tuple[int, ...]:
        """Find exact oriented programs and correlated words without a population scan."""
        ranks = []
        for index, program in enumerate(self._admitted):
            if program.support.kind != program_kind:
                continue
            try:
                word = program.domain.assignment_of(solution)
                member = program.support.source_assignments.rank_of(word)
            except ValueError:
                continue
            ranks.append(interleaved_rank(self.program_cardinalities, index, member))
        if not ranks:
            raise ValueError("Foldback solution is not in the admitted oriented population.")
        return tuple(sorted(ranks))

    def loop_sequence(self, rank: int) -> str:
        """Inspect one admitted arm/cap word without compiling or expanding the domain."""
        program, word = self._member(rank)
        # Independent variables describe the final arm followed by the cap,
        # including when the source expression is mirrored.
        return word[program.domain.arm_length_bp : program.domain.retained_length_nt]

    def select(self, product: ProductRequest, rank: int) -> ProductRequest:
        """Recover one admitted word without visiting preceding placement candidates."""
        selected_program, word = self._member(rank)
        case, support, domain = (
            selected_program.case,
            selected_program.support,
            selected_program.domain,
        )
        raw_rank = 0
        for base, choices in zip(word, domain.independent_domains, strict=True):
            raw_rank = raw_rank * len(choices) + choices.index(base)
        data = product.model_dump(mode="json", by_alias=True)
        geometry = data["foldback"]["geometry"]
        geometry.update(
            annealing_arm_lengths_bp=[case.target.annealing_arm_length_bp],
            junction_offsets_nt=[case.target.junction_offset_nt],
            loop_lengths_nt=[case.target.loop_length_nt],
            nick_strand=case.target.nick_strand.value,
        )
        if case.target.loop_sequence is not None:
            geometry["loop_sequences"] = [case.target.loop_sequence]
        enzymes = data["foldback"]["enzymes"]
        selected = {str(support.nick_enzyme_id)}
        if support.terminus_enzyme_id is not None:
            selected.add(str(support.terminus_enzyme_id))
        enzymes["allowed_enzyme_ids"] = sorted(selected)
        for restriction in enzymes["role_restrictions"]:
            restriction["allowed_enzyme_ids"] = sorted(
                selected.intersection(restriction["allowed_enzyme_ids"])
            )
        # A single-nick member does not use the optional terminus cutter.
        # The global selected-enzyme list still excludes that cutter, so omitting
        # its now-empty role cannot admit another cleavage operation.
        enzymes["role_restrictions"] = [
            restriction
            for restriction in enzymes["role_restrictions"]
            if restriction["allowed_enzyme_ids"]
        ]
        data["foldback"]["search"]["sequence_partition"] = {
            "part_count": max(2, domain.precursor_cardinality),
            "part_index": raw_rank,
        }
        return ProductRequest.model_validate_json(json.dumps(data))


def population_request(
    local: LocalNeighborhoodRequest,
    limits: SequenceSpaceLimits,
) -> FoldbackSequenceRequest:
    return FoldbackSequenceRequest.model_validate_json(
        json.dumps(
            {
                "schema": "hop.foldback-sequence-request/v1",
                "payload": local.payload.model_dump(mode="json", by_alias=True),
                "route_family": local.route_family.value,
                "geometry_domain": local.geometry_domain.model_dump(mode="json"),
                "enzyme_provisioning": local.enzyme_provisioning.model_dump(
                    mode="json", by_alias=True
                ),
                "max_retained_overhead_nt": local.search.max_retained_overhead_nt,
                "limits": limits.model_dump(mode="json"),
            }
        )
    )


def admit_population(
    request: FoldbackSequenceRequest,
    index: SurveyIndex | None,
) -> FoldbackPopulation:
    key = sha256_digest(canonical_json_bytes(request))
    content = None if index is None else index.cached(key)
    if content is None:
        result = discover_sequence_space(request)
        if index is not None:
            index.cache(key, canonical_json_bytes(result))
    else:
        assert index is not None
        with index.origins.replay(index.cache_creator(key)):
            result = verify_sequence_space(FoldbackSequenceResult.model_validate_json(content))
        if result.request != request:
            raise ValueError("Cached foldback population does not match its request.")
    return FoldbackPopulation(result)
