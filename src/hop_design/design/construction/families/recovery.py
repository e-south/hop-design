"""Explain an admitted continuation using its recorded choices, not an inferred rationale."""

from typing import Any

from hop_design.models.construction.projections.family_report import (
    FamilyRecoveryProjection,
    RecoveryLocalChoice,
)
from hop_design.models.construction.targets import FoldbackTarget

from .member_admission import AdmittedMember


def describe_recovery(
    revision: dict[str, Any] | None, members: tuple[AdmittedMember, ...]
) -> FamilyRecoveryProjection | None:
    if revision is None:
        return None
    target = next(m for m in members if m.name == revision["target_member"])
    if target.receipt is None:
        raise ValueError("A family revision must retain its complete target authority.")
    result = target.receipt._verified_source().result
    choices = []
    for item in result.foldback_authority.realizations:
        geometry = item.local_realization.achieved_geometry
        if not isinstance(geometry, FoldbackTarget):
            raise ValueError("A closing-region choice must have foldback geometry.")
        choices.append(
            RecoveryLocalChoice(
                realization_id=item.foldback_realization_id,
                loop_nt=geometry.loop_length_nt,
                loop_side_paired_bp=geometry.annealing_arm_length_bp,
                selected=item.foldback_realization_id
                == result.request.selected_foldback_realization_id,
            )
        )
    return FamilyRecoveryProjection(
        source_member=revision["source_member"],
        target_member=target.name,
        kind=revision["kind"],
        prior_status=revision["prior_status"],
        preferred_loop_nt=revision.get("preferred_loop_nt"),
        foldback_choices=tuple(choices),
        basal_choice_count=None
        if result.basal_authority is None
        else len(result.basal_authority.realizations),
    )
