"""Retrieval is a next action only when an admissible set exists."""

from hop_design.export.construction.comparisons.reports import assessment_report


def test_no_set_has_no_retrieval_invitation():
    report = assessment_report(
        {
            "status": "no_compatible_set_in_evaluated_pool",
            "purpose": "grouped_substrates",
            "comparison_stage": "endpoint",
            "distinct_molecules": {"hairpin": 4, "endpoint": 2},
            "sets": [],
            "members": [],
            "group_coverage": {},
            "coverage": {},
            "examined_failures": [],
            "conflicts": [],
        }
    )
    assert "select-comparison" not in report
    assert "No set is available for retrieval" in report
