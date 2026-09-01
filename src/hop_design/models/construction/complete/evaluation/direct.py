"""Direct single-stranded endpoint evaluation."""

from __future__ import annotations

from hop_design.models.reaction_replay import assess_reaction_program

from ..route_schedule import derive_direct_reaction_program
from .context import PreparedContext, merged_provisioning_policy
from .result import EndpointEvaluation


def evaluate_direct_endpoint(context: PreparedContext) -> EndpointEvaluation:
    """Evaluate the exact direct-route reaction program."""
    combination = context.combination
    program = derive_direct_reaction_program(
        foldback=combination.foldback,
        basal=combination.basal,
        prefix=context.prefix,
        source_return_arm=context.source_return_arm,
        source=context.source,
        source_complement=context.source_complement,
    )
    assessment = assess_reaction_program(
        program=program,
        policy=merged_provisioning_policy(context),
    )
    return EndpointEvaluation(
        endpoint_auxiliaries=None,
        reaction_program=program,
        stage_assessments=assessment.stage_assessments,
        reaction_report_has_errors=assessment.report.has_errors,
        pcr_template_sequence=None,
        design_parent_span=None,
        final_sequence=context.pcr_core_sequence + context.source_return_arm,
    )
