# ruff: noqa: F811
"""A manufacturing change must not imply a second change to the chosen molecule."""

import json

import pytest

from hop_design import construction
from tests.integration.test_construction_family_report import family_capture  # noqa: F401


def test_loop_series_separates_molecule_preparation_and_coordinate_changes(family_capture):
    report = construction.project_construction_family_report(
        family_capture / "executed", baseline="loop3"
    )
    comparison = json.loads(report.json_bytes)["comparisons"][0]["molecular"]
    assessment = comparison["assessment"]
    assert assessment["scaffold_status"] == "comparable"
    assert assessment["non_loop_sequences_conserved"] is True
    assert set(assessment["changed_scaffold_fields"]) == {
        "hairpin.loop_nt",
        "hairpin.region.loop.sequence",
    }
    assert "hairpin.region.stem_return.span" in assessment["shifted_coordinate_fields"]
    assert "hairpin.region.stem_return.sequence" in assessment["shared_scaffold_fields"]
    assert set(assessment["changed_preparation_fields"]) == {
        "preparation.Source oligo",
        "preparation.Source reverse primer",
        "preparation.PCR strand lengths (nt)",
    }
    assert "hairpin.five_prime_end" in assessment["shared_scaffold_fields"]
    assert "preparation.Endpoint strand 1" in assessment["changed_endpoint_fields"]
    assert "Non-loop sequences: unchanged" in report.report_text
    assert "What changes in making it" in report.report_text


@pytest.fixture(scope="module")
def recorded_comparison(family_capture):
    from hop_design.models.construction.projections.comparison import (
        ConstructionComparisonProjection,
    )

    report = construction.project_construction_family_report(
        family_capture / "executed", baseline="loop3"
    )
    return ConstructionComparisonProjection.model_validate_json(
        json.dumps(json.loads(report.json_bytes)["comparisons"][0]["molecular"])
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("hairpin.region.open_primary.sequence", "GGTCTCAAGTCGCAACG"),
        ("hairpin.five_prime_end", "phosphate"),
        ("hairpin.region.open_primary.contacts", []),
        ("hairpin.region.closing_primary.joins", [1]),
    ],
)
def test_real_scaffold_changes_are_never_reported_as_shared(recorded_comparison, field, value):
    from hop_design.models.construction.projections.comparison import (
        ConstructionComparisonProjection,
    )

    content = recorded_comparison.model_dump(exclude={"schema_id", "projection_id", "assessment"})
    content.update(left=recorded_comparison.left, right=recorded_comparison.right)
    content["properties"] = tuple(
        p.model_copy(update={"right": value, "changed": p.left != value}) if p.field == field else p
        for p in recorded_comparison.properties
    )
    assessment = ConstructionComparisonProjection.create(**content).assessment
    assert field in assessment.changed_scaffold_fields
    assert field not in assessment.shared_scaffold_fields
    if field.endswith(".sequence"):
        assert assessment.non_loop_sequences_conserved is False


def test_missing_sequence_evidence_does_not_establish_conservation(recorded_comparison):
    from hop_design.models.construction.projections.comparison_assessment import assess_comparison

    facts = tuple(
        p
        for p in recorded_comparison.properties
        if p.field != "hairpin.region.open_primary.sequence"
    )
    assert assess_comparison(facts).non_loop_sequences_conserved is None


@pytest.mark.parametrize(
    "field,value,status",
    [
        ("hairpin.stage", "different-stage", "different_stages"),
        ("hairpin.availability", "unsupported", "unavailable"),
    ],
)
def test_incomparable_molecules_do_not_gain_shared_claims(
    recorded_comparison, field, value, status
):
    from hop_design.models.construction.projections.comparison_assessment import assess_comparison

    facts = tuple(
        p.model_copy(update={"right": value, "changed": True}) if p.field == field else p
        for p in recorded_comparison.properties
    )
    assessment = assess_comparison(facts)
    assert assessment.scaffold_status == status
    assert assessment.non_loop_sequences_conserved is None
    assert assessment.shared_scaffold_fields == ()


def test_comparison_plate_keeps_countable_molecules_and_truthful_endpoint(family_capture, tmp_path):
    from xml.etree import ElementTree as ET

    report = construction.project_construction_family_report(
        family_capture / "executed", baseline="loop3", selection=family_capture / "set.json"
    )
    output = report.write(tmp_path / "report")
    root = ET.parse(output / "report.svg").getroot()
    text = " ".join(root.itertext())
    assert "What changes in my molecule" in text
    assert "What changes in making it" in text
    assert "released duplex insert" in text
    assert "clone ready duplex" not in text
    assert "Destination compatibility" in text
    assert len([e for e in root.iter() if e.get("data-loop-index") is not None]) == 7
    assert "short-primer" in report.report_text
