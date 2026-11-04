"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/basal_space_admission.py

Admits canonical basal source sets using the shared molecular reaction rules.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from hop_design.kernel.construction.basal.domains import BasalSequenceDomain
from hop_design.kernel.construction.basal.programs import BasalSequenceSolution
from hop_design.kernel.construction.basal.sequence_index import BasalSequenceIndex
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder, SequenceSetLimitError
from hop_design.models.construction.sequence_sets import SequenceSet, SequenceSpaceLimits
from hop_design.models.enzymes import EnzymeProvisioningPolicy
from hop_design.models.reaction_replay import assess_reaction_program
from hop_design.models.reaction_replay.sites import (
    _binding_at,
    _matches_declaration,
    _orientation_patterns,
)
from hop_design.models.sequence import iupac_bases

from .basal.reactions import _nick_program


def admit_basal_sources(
    *, domain: BasalSequenceDomain, policy: EnzymeProvisioningPolicy, limits: SequenceSpaceLimits
) -> SequenceSet:
    """Check the whole source before projecting away surrounding construction context."""
    return _admit_source_domains(
        domain=domain, domains=domain.canonical_source_domains(), policy=policy, limits=limits
    )


def admit_basal_source_assignments(
    *, domain: BasalSequenceDomain, policy: EnzymeProvisioningPolicy, limits: SequenceSpaceLimits
) -> SequenceSet:
    """Retain full-source site constraints before joint adapter/pair-budget admission."""
    return _admit_source_domains(
        domain=domain,
        domains=BasalSequenceIndex.create(domain).source_domains(),
        policy=policy,
        limits=limits,
    )


def _admit_source_domains(
    *,
    domain: BasalSequenceDomain,
    domains: tuple[tuple[str, ...], ...],
    policy: EnzymeProvisioningPolicy,
    limits: SequenceSpaceLimits,
) -> SequenceSet:
    masks = tuple(set(bases) for bases in domains)
    builder = SequenceSetBuilder(
        length_nt=len(domains),
        max_nodes=limits.max_decisions,
        max_operations=limits.max_set_operations,
    )
    if any(not bases for bases in domains):
        return builder.freeze(0)
    required_operations = 1 + int(domain.program.future_release_action is not None)
    if policy.max_operations is not None and required_operations > policy.max_operations:
        return builder.freeze(0)
    enzyme = domain.program.nick_enzyme
    patterns = tuple(_orientation_patterns(enzyme))
    windows = len(patterns) * max(0, len(domains) - enzyme.recognition_length + 1)
    if windows > limits.max_site_checks:
        raise SequenceSetLimitError("Basal recognition-window budget exhausted.")
    source = "".join(next(base for base in "ACGT" if base in bases) for bases in domains)
    # Nick admission depends on the source only. Adapter choices and their global
    # pair cap are retained jointly by the population, not guessed from one member.
    solution = BasalSequenceSolution(
        source_precursor_sequence=source,
        adapter_sequence=None,
        payload_span=domain.payload_span,
        pairing_state=None,
        enzyme_bindings=domain.enzyme_bindings,
    )
    program = _nick_program(solution, domain.program)
    if len(program.stages) != 1 or len(program.stages[0].operations) != 1:
        raise ValueError("Compact basal admission requires one molecular nicking operation.")
    assessment = assess_reaction_program(program=program, policy=policy)
    codes = {diagnostic.code for diagnostic in assessment.report.diagnostics}
    constant_rejections = {"HOP-PROGRAM-001", "HOP-STAGE-002", "HOP-STAGE-006"}
    if codes - constant_rejections - {"HOP-STAGE-003", "HOP-STAGE-004"}:
        raise ValueError("Unsupported basal reaction-assessment diagnostic.")
    if codes & constant_rejections:
        return builder.freeze(0)
    operation = program.stages[0].operations[0]
    admitted = builder.from_domains(masks)
    intended = 0
    for orientation, pattern in patterns:
        for start in range(len(domains) - len(pattern) + 1):
            matching_domains = list(masks)
            for offset, symbol in enumerate(pattern):
                matching_domains[start + offset] = masks[start + offset] & iupac_bases(symbol)
            if any(not mask for mask in matching_domains):
                continue
            binding = _binding_at(
                enzyme=enzyme,
                molecule_id=operation.molecule_id,
                sequence_nt=len(domains),
                orientation=orientation,
                start=start,
            )
            if binding is None:
                continue
            matching = builder.from_domains(matching_domains)
            if _matches_declaration(binding, operation=operation):
                intended = builder.union(intended, matching)
            else:
                admitted = builder.difference(admitted, matching)
    return builder.freeze(builder.intersection(admitted, intended))
