"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/construction/foldback/admission.py

Admits exact foldback sequence sets under ordered molecular cleavage constraints.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder, SequenceSetLimitError
from hop_design.models.construction import FoldbackTarget
from hop_design.models.construction.foldback import FoldbackCleavageProgramKind
from hop_design.models.construction.foldback_replay import replay_foldback_route
from hop_design.models.construction.foldback_replay.substrates import foldback_reaction_substrates
from hop_design.models.construction.sequence_sets import SequenceSet
from hop_design.models.enzymes import EnzymeProvisioningPolicy
from hop_design.models.physical import Strand
from hop_design.models.reaction_replay import assess_reaction_program
from hop_design.models.reaction_replay.sites import (
    _binding_at,
    _matches_declaration,
    _orientation_patterns,
)
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac

from .domains import FoldbackSequenceDomain, SequenceExpression


def _recognition_set(
    *,
    domain: FoldbackSequenceDomain,
    expression: SequenceExpression,
    pattern: str,
    builder: SequenceSetBuilder,
) -> int:
    domains = [set(bases) for bases in domain.independent_domains]
    for base, symbol in zip(expression, pattern, strict=True):
        allowed = iupac_bases(symbol)
        if isinstance(base, str):
            if base not in allowed:
                return 0
        else:
            domains[base.index] &= (
                {reverse_complement_iupac(value) for value in allowed}
                if base.complemented
                else allowed
            )
            if not domains[base.index]:
                return 0
    return builder.from_domains(domains)


def admit_foldback_precursors(
    *,
    domain: FoldbackSequenceDomain,
    target: FoldbackTarget,
    program_kind: FoldbackCleavageProgramKind,
    policy: EnzymeProvisioningPolicy,
    max_nodes: int,
    max_operations: int,
    max_site_checks: int,
) -> SequenceSet:
    """Admit joint retained and cleaved-tail assignments through every local stage."""
    if type(max_site_checks) is not int or not 1 <= max_site_checks <= 1_000_000:
        raise ValueError("max_site_checks must be an integer between 1 and 1000000.")
    if not isinstance(target.nick_strand, Strand):
        raise ValueError("Compact foldback admission requires one exact nick strand.")
    builder = SequenceSetBuilder(
        length_nt=len(domain.independent_domains),
        max_nodes=max_nodes,
        max_operations=max_operations,
    )
    admitted = builder.from_domains(domain.independent_domains)
    solution = domain.materialize("".join(bases[0] for bases in domain.independent_domains))
    replay = replay_foldback_route(
        payload_sequence=domain.payload_sequence,
        target=target,
        program_kind=program_kind,
        source_reference_sequence=solution.source_reference_sequence,
        enzyme_bindings=solution.enzyme_bindings,
    )
    if replay.ligated_strand.sequence != solution.retained_sequence:
        raise ValueError("Foldback domain and molecular replay disagree on retained sequence.")
    program = replay.reaction_program
    if any(len(stage.operations) != 1 for stage in program.stages):
        raise ValueError("Compact foldback admission requires sequential single-operation stages.")
    states = {state.state_id: state for state in program.states}
    site_checks = 0
    for stage in program.stages:
        try:
            enzyme = policy.catalog.by_id(stage.operations[0].enzyme_id)
        except KeyError:
            continue
        site_checks += len(tuple(_orientation_patterns(enzyme))) * sum(
            max(0, len(molecule.reference_sequence_5prime) - enzyme.recognition_length + 1)
            for molecule in states[stage.pre_state_id].molecules
        )
        if site_checks > max_site_checks:
            raise SequenceSetLimitError("Foldback recognition-window budget exhausted.")
    assessment = assess_reaction_program(program=program, policy=policy)
    codes = {diagnostic.code for diagnostic in assessment.report.diagnostics}
    constant_rejections = {"HOP-PROGRAM-001", "HOP-STAGE-002", "HOP-STAGE-006"}
    if codes - constant_rejections - {"HOP-STAGE-003", "HOP-STAGE-004"}:
        raise ValueError("Unsupported foldback reaction assessment diagnostic.")
    if codes & constant_rejections:
        return builder.freeze(0)

    substrates = foldback_reaction_substrates(
        source_nt=len(domain.source_expression),
        program_kind=program_kind,
        nick_strand=target.nick_strand,
        terminus=domain.terminus_boundary,
    )
    spans = {(item.state_id, item.molecule_id): item.source_span for item in substrates}
    if set(spans) != {
        (stage.pre_state_id, molecule.molecule_id)
        for stage in program.stages
        for molecule in states[stage.pre_state_id].molecules
    }:
        raise ValueError("Compact foldback substrates do not cover the complete reaction program.")

    for stage in program.stages:
        operation = stage.operations[0]
        enzyme = policy.catalog.by_id(operation.enzyme_id)
        patterns = tuple(_orientation_patterns(enzyme))
        intended = 0
        for molecule in states[stage.pre_state_id].molecules:
            span = spans[stage.pre_state_id, molecule.molecule_id]
            expression = domain.source_expression[span.start.offset : span.end.offset]
            for orientation, pattern in patterns:
                for start in range(len(expression) - len(pattern) + 1):
                    binding = _binding_at(
                        enzyme=enzyme,
                        molecule_id=molecule.molecule_id,
                        sequence_nt=len(expression),
                        orientation=orientation,
                        start=start,
                    )
                    if binding is None:
                        continue
                    matching = _recognition_set(
                        domain=domain,
                        expression=expression[start : start + len(pattern)],
                        pattern=pattern,
                        builder=builder,
                    )
                    if _matches_declaration(binding, operation=operation):
                        intended = builder.union(intended, matching)
                    else:
                        admitted = builder.difference(admitted, matching)
        admitted = builder.intersection(admitted, intended)
    return builder.freeze(admitted)


def retained_sequences(
    precursors: SequenceSet,
    *,
    retained_length_nt: int,
    max_nodes: int,
    max_operations: int,
) -> SequenceSet:
    """Project admitted precursors onto retained bases without counting tail multiplicity."""
    if precursors.length_nt == retained_length_nt:
        return precursors
    builder = SequenceSetBuilder(
        length_nt=retained_length_nt, max_nodes=max_nodes, max_operations=max_operations
    )
    return builder.freeze(builder.project_window(precursors, start=0, end=retained_length_nt))


def admit_foldback_sequences(
    *,
    domain: FoldbackSequenceDomain,
    target: FoldbackTarget,
    program_kind: FoldbackCleavageProgramKind,
    policy: EnzymeProvisioningPolicy,
    max_nodes: int,
    max_operations: int,
    max_site_checks: int,
) -> SequenceSet:
    """Keep each retained word with at least one locally admitted source completion."""
    precursors = admit_foldback_precursors(
        domain=domain,
        target=target,
        program_kind=program_kind,
        policy=policy,
        max_nodes=max_nodes,
        max_operations=max_operations,
        max_site_checks=max_site_checks,
    )
    return retained_sequences(
        precursors,
        retained_length_nt=domain.retained_length_nt,
        max_nodes=max_nodes,
        max_operations=max_operations,
    )
