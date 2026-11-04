"""Bind regional sequence comparisons to an explicitly named complete reference."""

from typing import cast

from hop_design.models.construction.projections.family_report import FamilyReportComparison

from ..comparison import project_construction_comparison
from ..projections.sequence_difference import compare_sequence_region
from .member_admission import AdmittedMember


def compare_family_members(
    members: tuple[AdmittedMember, ...],
    baseline: str | None,
    selected: set[tuple[str, str]],
) -> tuple[FamilyReportComparison, ...]:
    if baseline is None:
        return ()
    references = [m for m in members if m.name == baseline and m.receipt is not None]
    if len(references) != 1 or references[0].receipt is None:
        raise ValueError("Baseline must name one complete family member.")
    reference = references[0].receipt
    ids = reference.materialized_realization_ids
    if len(ids) != 1:
        ids = tuple(i for i in ids if (reference.result_id, i) in selected)
    if len(ids) != 1:
        raise ValueError("Baseline with multiple choices needs one explicit set selection.")
    comparisons = []
    for member in members:
        if member.name == baseline or member.receipt is None:
            continue
        for identity in member.receipt.materialized_realization_ids:
            molecular = project_construction_comparison(
                reference,
                member.receipt,
                left_realization_id=ids[0],
                right_realization_id=identity,
            )._projection
            facts = {row.field: row for row in molecular.properties}
            regions = []
            for key, fact in facts.items():
                if not key.startswith("hairpin.region.") or not key.endswith(".sequence"):
                    continue
                if not isinstance(fact.left, str) or not isinstance(fact.right, str):
                    continue
                span = facts[key.removesuffix(".sequence") + ".span"]
                a, b = cast(list[int], span.left), cast(list[int], span.right)
                regions.append(
                    compare_sequence_region(
                        key.split(".")[2],
                        fact.left,
                        fact.right,
                        (a[0], a[1]),
                        (b[0], b[1]),
                    )
                )
            comparisons.append(
                FamilyReportComparison(
                    baseline_member=baseline,
                    member=member.name,
                    molecular=molecular,
                    regions=tuple(regions),
                )
            )
    return tuple(comparisons)
