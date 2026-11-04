"""Resolve display names from the same verified catalogs that authorize operations."""

from hop_design.models.construction.complete.provisioning import resolve_program_enzyme_definitions
from hop_design.models.construction.projections import CompleteConstructionTrajectoryProjection

from .complete.discovery import VerifiedConstructionSpaceResult


def trajectory_enzyme_labels(
    source: VerifiedConstructionSpaceResult, projection: CompleteConstructionTrajectoryProjection
) -> tuple[tuple[str, str], ...]:
    release = source.result.request.release
    policies = (
        source.foldback.result.neighborhood.request.enzyme_provisioning,
        *(
            ()
            if source.basal is None
            else (source.basal.result.discovery.request.enzyme_provisioning,)
        ),
        *(() if release is None else (release.enzyme_provisioning,)),
    )
    names = {
        enzyme.enzyme_id: enzyme.canonical_name
        for program in projection.realization.construction_program.reaction_programs
        for enzyme in resolve_program_enzyme_definitions(program=program, policies=policies)
    }
    return tuple(sorted(names.items()))
