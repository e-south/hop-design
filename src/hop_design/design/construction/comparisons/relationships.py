"""Stage-specific group relationships over verified complete molecular identities."""

from typing import Any

from hop_design.models.construction.comparisons.request import (
    ComparisonAssessment,
    ComparisonAssessmentRequest,
    GroupedComparisonBrief,
    StageComparisonBrief,
)


def group_declarations(brief: ComparisonAssessmentRequest) -> dict[str, Any]:
    if not isinstance(brief, (GroupedComparisonBrief, StageComparisonBrief, ComparisonAssessment)):
        return {}
    return {
        "groups": [
            {**g.model_dump(mode="json"), "members": sorted(g.members)}
            for g in sorted(brief.groups, key=lambda g: g.name)
        ],
        "between_groups": brief.between_groups,
    }


def relationship_rejection(
    brief: ComparisonAssessmentRequest,
    membership: dict[str, dict[str, Any]],
    references: dict[str, Any] | None = None,
) -> str | None:
    stage = brief.comparison_stage
    identities = {name: o["molecular_identity"][stage] for name, o in membership.items()}
    if (
        isinstance(brief, (GroupedComparisonBrief, StageComparisonBrief, ComparisonAssessment))
        and brief.groups
    ):
        group_identities = []
        for group in sorted(brief.groups, key=lambda g: g.name):
            values = {identities[name] for name in group.members}
            if len(values) != 1:
                return "different_products_within_group"
            identity = next(iter(values))
            if group.product_reference is not None:
                if references is None or group.name not in references:
                    raise ValueError("Product references must be verified before assessment.")
                if identity != references[group.name]["molecular_identity"]:
                    return "referenced_product_changed"
            group_identities.append(identity)
        if len(set(group_identities)) != len(group_identities):
            return "repeated_product_between_groups"
    elif brief.purpose == "distinct_substrates" and len(set(identities.values())) != len(
        identities
    ):
        return "repeated_molecular_substrate"
    elif brief.purpose == "preparation_alternatives" and len(set(identities.values())) != 1:
        return "different_molecular_products"
    return None
