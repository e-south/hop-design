"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/kernel/reactions/assessment.py

Evaluates characterized enzyme sites against ordered reaction states.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections import Counter

from pydantic import JsonValue

from hop_design.models.diagnostics import CheckReport, Diagnostic, Severity
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    EnzymeClass,
    EnzymeProvisioningPolicy,
    EnzymeRole,
)
from hop_design.models.reactions import (
    ActionableEnzymeBinding,
    ReactionProgram,
    ReactionProgramAssessment,
    ReactionStage,
    ReactionStageAssessment,
    ReactionState,
)

from .sites import _cut_keys, _matches_declaration, _with_operation, scan_actionable_sites


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
        required_class = {
            EnzymeRole.TERMINUS_DEFINITION: EnzymeClass.DUPLEX_RESTRICTION,
            EnzymeRole.STRAND_EXPOSURE: EnzymeClass.NICKASE,
            EnzymeRole.BASAL_NICK: EnzymeClass.NICKASE,
            EnzymeRole.FOLDBACK_NICK: EnzymeClass.NICKASE,
            EnzymeRole.END_GENERATION: EnzymeClass.DUPLEX_RESTRICTION,
        }[operation.role]
        if enzyme.enzyme_class is not required_class:
            diagnostics.append(
                _diagnostic(
                    code="HOP-STAGE-006",
                    path=f"operations[{index}].role",
                    message="Reaction operation role conflicts with the enzyme cleavage class.",
                    evidence={
                        "enzyme_id": operation.enzyme_id,
                        "enzyme_class": enzyme.enzyme_class.value,
                        "role": operation.role.value,
                        "required_enzyme_class": required_class.value,
                    },
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


def assess_reaction_program(
    *,
    program: ReactionProgram,
    policy: EnzymeProvisioningPolicy,
) -> ReactionProgramAssessment:
    """Assess all stages and enforce execution-wide provisioning limits."""
    states = {state.state_id: state for state in program.states}
    stage_assessments = tuple(
        assess_reaction_stage(
            state=states[stage.pre_state_id],
            stage=stage,
            policy=policy,
        )
        for stage in program.stages
    )
    diagnostics = [
        diagnostic
        for assessment in stage_assessments
        for diagnostic in assessment.report.diagnostics
    ]
    operation_count = sum(len(stage.operations) for stage in program.stages)
    if policy.max_operations is not None and operation_count > policy.max_operations:
        diagnostics.insert(
            0,
            _diagnostic(
                code="HOP-PROGRAM-001",
                path="stages",
                message="Reaction program exceeds the provisioned operation limit.",
                evidence={
                    "operation_count": operation_count,
                    "max_operations": policy.max_operations,
                },
            ),
        )
    return ReactionProgramAssessment(
        program_id=program.program_id,
        stage_assessments=stage_assessments,
        report=CheckReport(diagnostics=tuple(diagnostics)),
    )
