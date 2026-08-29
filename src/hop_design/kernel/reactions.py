"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/reactions.py

Resolves characterized enzyme sites and validates concurrent reaction stages.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator

from pydantic import JsonValue

from hop_design.models.coordinates import Boundary, Span
from hop_design.models.diagnostics import CheckReport, Diagnostic, Severity
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    EnzymeClass,
    EnzymeProvisioningPolicy,
    RecognitionOrientationSemantics,
    SubstrateRequirement,
)
from hop_design.models.physical import SiteOrientation
from hop_design.models.reactions import (
    ActionableEnzymeBinding,
    ReactionMolecule,
    ReactionOperation,
    ReactionStage,
    ReactionStageAssessment,
    ReactionState,
)
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac


def _orientation_patterns(
    enzyme: CharacterizedEnzyme,
) -> Iterator[tuple[SiteOrientation, str]]:
    yield SiteOrientation.FORWARD, enzyme.recognition_pattern
    if (
        enzyme.recognition_orientation_semantics
        is RecognitionOrientationSemantics.BOTH_ORIENTATIONS
    ):
        yield SiteOrientation.REVERSE, reverse_complement_iupac(enzyme.recognition_pattern)


def _matches_pattern(sequence: str, pattern: str) -> bool:
    return all(base in iupac_bases(symbol) for base, symbol in zip(sequence, pattern, strict=True))


def _recognition_span_is_duplex(molecule: ReactionMolecule, *, start: int, end: int) -> bool:
    complement = molecule.complement_sequence_5prime
    if complement is None:
        return False
    sequence_nt = len(molecule.reference_sequence_5prime)
    aligned_complement = complement[sequence_nt - end : sequence_nt - start]
    return molecule.reference_sequence_5prime[start:end] == reverse_complement_iupac(
        aligned_complement
    )


def _cut_offsets(
    *,
    enzyme: CharacterizedEnzyme,
    orientation: SiteOrientation,
    start: int,
) -> tuple[int | None, int | None]:
    motif_nt = enzyme.recognition_length
    if orientation is SiteOrientation.FORWARD:
        reference_offset = enzyme.cut_offset_reference_strand
        complement_offset = enzyme.cut_offset_complement_strand
    elif enzyme.enzyme_class is EnzymeClass.NICKASE:
        reference_offset = None
        complement_offset = motif_nt - enzyme.cut_offset_reference_strand
    else:
        if enzyme.cut_offset_complement_strand is None:
            raise ValueError("A duplex restriction enzyme must define both strand cuts.")
        reference_offset = motif_nt - enzyme.cut_offset_complement_strand
        complement_offset = motif_nt - enzyme.cut_offset_reference_strand
    return (
        start + reference_offset if reference_offset is not None else None,
        start + complement_offset if complement_offset is not None else None,
    )


def _scan_molecule(
    *,
    molecule: ReactionMolecule,
    enzyme: CharacterizedEnzyme,
) -> tuple[ActionableEnzymeBinding, ...]:
    if (
        enzyme.substrate_requirement is SubstrateRequirement.DUPLEX_DNA
        and molecule.complement_sequence_5prime is None
    ):
        return ()
    sequence = molecule.reference_sequence_5prime
    bindings: list[ActionableEnzymeBinding] = []
    for orientation, pattern in _orientation_patterns(enzyme):
        for start in range(len(sequence) - len(pattern) + 1):
            end = start + len(pattern)
            if not _matches_pattern(sequence[start:end], pattern):
                continue
            if (
                enzyme.substrate_requirement is SubstrateRequirement.DUPLEX_DNA
                and not _recognition_span_is_duplex(molecule, start=start, end=end)
            ):
                continue
            reference_cut_offset, complement_cut_offset = _cut_offsets(
                enzyme=enzyme,
                orientation=orientation,
                start=start,
            )
            if any(
                offset is not None and not 0 <= offset <= len(sequence)
                for offset in (reference_cut_offset, complement_cut_offset)
            ):
                continue
            reference_cut = (
                Boundary(offset=reference_cut_offset) if reference_cut_offset is not None else None
            )
            complement_cut = (
                Boundary(offset=complement_cut_offset)
                if complement_cut_offset is not None
                else None
            )
            bindings.append(
                ActionableEnzymeBinding(
                    enzyme_id=enzyme.enzyme_id,
                    molecule_id=molecule.molecule_id,
                    recognition_span=Span(
                        start=Boundary(offset=start),
                        end=Boundary(offset=end),
                    ),
                    orientation=orientation,
                    reference_cut=reference_cut,
                    complement_cut=complement_cut,
                )
            )
    return tuple(bindings)


def scan_actionable_sites(
    *,
    state: ReactionState,
    enzyme: CharacterizedEnzyme,
) -> tuple[ActionableEnzymeBinding, ...]:
    """Return sites physically actionable in molecules present in one exact state."""
    bindings = tuple(
        binding
        for molecule in state.molecules
        for binding in _scan_molecule(molecule=molecule, enzyme=enzyme)
    )
    return tuple(
        sorted(
            bindings,
            key=lambda binding: (
                binding.molecule_id,
                binding.recognition_span.start.offset,
                binding.orientation,
            ),
        )
    )


def _matches_declaration(
    binding: ActionableEnzymeBinding,
    *,
    operation: ReactionOperation,
) -> bool:
    declared = operation.intended_binding
    return (
        binding.enzyme_id == operation.enzyme_id
        and binding.molecule_id == operation.molecule_id
        and binding.recognition_span == declared.recognition_span
        and binding.orientation is declared.orientation
        and binding.reference_cut == declared.reference_cut
        and binding.complement_cut == declared.complement_cut
    )


def _with_operation(
    binding: ActionableEnzymeBinding,
    *,
    operation_id: str,
) -> ActionableEnzymeBinding:
    return binding.model_copy(update={"operation_id": operation_id})


def _cut_keys(
    binding: ActionableEnzymeBinding,
) -> Iterator[tuple[str, str, int]]:
    if binding.reference_cut is not None:
        yield binding.molecule_id, "reference", binding.reference_cut.offset
    if binding.complement_cut is not None:
        yield binding.molecule_id, "complement", binding.complement_cut.offset


def _diagnostic(
    *,
    code: str,
    path: str,
    message: str,
    evidence: dict[str, JsonValue] | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        path=path,
        message=message,
        evidence={} if evidence is None else evidence,
        suggestions=(),
    )


def assess_reaction_stage(
    *,
    state: ReactionState,
    stage: ReactionStage,
    policy: EnzymeProvisioningPolicy,
) -> ReactionStageAssessment:
    """Resolve all concurrent operations and undeclared sites against one pre-state."""
    if stage.pre_state_id != state.state_id:
        raise ValueError("Reaction stage pre_state_id must equal the supplied state id.")

    diagnostics: list[Diagnostic] = []
    if policy.max_operations is not None and len(stage.operations) > policy.max_operations:
        diagnostics.append(
            _diagnostic(
                code="HOP-STAGE-001",
                path="operations",
                message="Reaction stage exceeds the provisioned operation limit.",
                evidence={
                    "operation_count": len(stage.operations),
                    "max_operations": policy.max_operations,
                },
            )
        )

    enzymes: dict[str, CharacterizedEnzyme] = {}
    for index, operation in enumerate(stage.operations):
        try:
            enzyme = policy.catalog.by_id(operation.enzyme_id)
        except KeyError:
            diagnostics.append(
                _diagnostic(
                    code="HOP-STAGE-002",
                    path=f"operations[{index}].enzyme_id",
                    message="Reaction operation references an enzyme outside the catalog snapshot.",
                    evidence={"enzyme_id": operation.enzyme_id},
                )
            )
            continue
        enzymes[enzyme.enzyme_id] = enzyme
        if not policy.permits(operation.enzyme_id, role=operation.role):
            diagnostics.append(
                _diagnostic(
                    code="HOP-STAGE-002",
                    path=f"operations[{index}].enzyme_id",
                    message="Reaction operation uses an enzyme unavailable for its declared role.",
                    evidence={"enzyme_id": operation.enzyme_id, "role": operation.role.value},
                )
            )

    all_bindings = tuple(
        binding
        for enzyme in enzymes.values()
        for binding in scan_actionable_sites(state=state, enzyme=enzyme)
    )
    intended_bindings: list[ActionableEnzymeBinding] = []
    for index, operation in enumerate(stage.operations):
        matching = tuple(
            binding
            for binding in all_bindings
            if _matches_declaration(binding, operation=operation)
        )
        if not matching:
            diagnostics.append(
                _diagnostic(
                    code="HOP-STAGE-003",
                    path=f"operations[{index}].intended_binding",
                    message="Intended enzyme binding is not actionable in the pre-stage state.",
                    evidence={
                        "operation_id": operation.operation_id,
                        "molecule_id": operation.molecule_id,
                    },
                )
            )
            continue
        intended_bindings.append(_with_operation(matching[0], operation_id=operation.operation_id))

    undeclared_bindings = tuple(
        binding
        for binding in all_bindings
        if not any(
            _matches_declaration(binding, operation=operation) for operation in stage.operations
        )
    )
    if undeclared_bindings:
        diagnostics.append(
            _diagnostic(
                code="HOP-STAGE-004",
                path="operations",
                message="The stage contains undeclared physically actionable cleavage sites.",
                evidence={"undeclared_site_count": len(undeclared_bindings)},
            )
        )

    cut_counts = Counter(cut_key for binding in intended_bindings for cut_key in _cut_keys(binding))
    conflicting_cuts = tuple(sorted(key for key, count in cut_counts.items() if count > 1))
    if conflicting_cuts:
        diagnostics.append(
            _diagnostic(
                code="HOP-STAGE-005",
                path="operations",
                message="Concurrent operations contain conflicting cuts on one strand boundary.",
                evidence={"conflicting_cut_count": len(conflicting_cuts)},
            )
        )

    return ReactionStageAssessment(
        stage_id=stage.stage_id,
        resolved_against_state_id=state.state_id,
        intended_bindings=tuple(intended_bindings),
        undeclared_bindings=undeclared_bindings,
        report=CheckReport(diagnostics=tuple(diagnostics)),
    )


__all__ = ["assess_reaction_stage", "scan_actionable_sites"]
