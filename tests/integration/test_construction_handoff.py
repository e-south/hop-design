"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_construction_handoff.py

Tests orderable material handoffs from verified construction projections.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.design.construction.complete import discover_constructions
from hop_design.design.construction.complete.bundle import compile_construction_bundle
from hop_design.design.construction.verification import verify_foldback_neighborhood_result
from hop_design.models.construction import ConstructionEndpoint
from tests.integration.test_complete_construction_projections import _verified_result
from tests.integration.test_complete_construction_source_partition import _case


@pytest.mark.parametrize("endpoint", tuple(ConstructionEndpoint))
def test_handoff_lists_external_oligos_and_preserves_molecular_authority(
    tmp_path: Path, endpoint: ConstructionEndpoint
) -> None:
    verified = _verified_result(tmp_path / "source", endpoint)
    realization = verified.result.realizations[0]
    bundle = compile_construction_bundle(verified).write(tmp_path / "bundle")
    receipt = construction.load_verified_construction_bundle(bundle)
    trajectory = construction.project_construction_trajectory(
        receipt, materialized_realization_id=realization.materialized_realization_id
    )
    before = trajectory.json_bytes
    output = trajectory.write(
        tmp_path / "handoff", selection_reason="Uses the caller's available enzyme set."
    )

    assert (output / "projection.json").read_bytes() == before == trajectory.json_bytes
    with (output / "oligos.csv").open(newline="") as stream:
        oligos = list(csv.DictReader(stream))
    preparation = realization.source_preparation
    materials = (
        preparation.source_ssdna,
        preparation.forward_primer.oligo,
        preparation.reverse_primer.oligo,
        *realization.materials[2:],
    )
    expected = {item.material_id: item for item in materials}
    assert len(oligos) == len(expected)
    assert {row["material_id"] for row in oligos} == set(expected)
    fasta = (output / "oligos.fasta").read_text()
    for row in oligos:
        material = expected[row["material_id"]]
        assert row["sequence_5prime"] == material.sequence_5prime
        assert int(row["length_nt"]) == len(material.sequence_5prime)
        assert row["five_prime_end"] == material.five_prime_end.value
        assert row["three_prime_end"] == material.three_prime_end.value
        assert f">{row['name']} symbolic=false\n{material.sequence_5prime}\n" in fasta
    report = (output / "report.md").read_text()
    assert "Uses the caller&#x27;s available enzyme set." in report
    assert realization.design.payload_sequence in report
    assert "not a ranking" in report
    assert "Unwanted-fragment removal is not verified" in report
    assert "not an experimental protocol" in report
    assert "Source copying" in report
    assert "oligos.csv" in report and "oligos.fasta" in report
    for end in realization.final_product.cohesive_ends:
        assert end.sequence in report
        assert f"{end.product_end.capitalize()} cohesive end:" in report
    assert realization.materialized_realization_id in report


def test_handoff_requires_nonblank_selection_reason_before_writing(tmp_path: Path) -> None:
    verified = _verified_result(tmp_path / "source", ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    bundle = compile_construction_bundle(verified).write(tmp_path / "bundle")
    receipt = construction.load_verified_construction_bundle(bundle)
    trajectory = construction.project_construction_trajectory(
        receipt,
        materialized_realization_id=verified.result.realizations[0].materialized_realization_id,
    )
    output = tmp_path / "handoff"
    with pytest.raises(ValueError, match="Selection reason must contain text"):
        trajectory.write(output, selection_reason=" \n ")
    assert not output.exists()
    output = trajectory.write(output)
    assert "No selection preference was supplied" in (output / "report.md").read_text()

    summary = construction.project_complete_construction_summary(receipt)
    with pytest.raises(ValueError, match="only applies to a selected trajectory"):
        summary.write(tmp_path / "summary", selection_reason="A chosen route")
    assert not (tmp_path / "summary").exists()


def test_handoff_explains_verified_fragment_removal_and_escapes_caller_text(tmp_path: Path) -> None:
    request, foldback, design, partition, _ = _case(tmp_path / "source")
    verified = discover_constructions(
        request,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=None,
        design=design,
        source_partition=partition,
    )
    bundle = compile_construction_bundle(verified).write(tmp_path / "bundle")
    receipt = construction.load_verified_construction_bundle(bundle)
    trajectory = construction.project_construction_trajectory(
        receipt,
        materialized_realization_id=verified.result.realizations[0].materialized_realization_id,
    )
    output = trajectory.write(
        tmp_path / "handoff", selection_reason="<script>alert(1)</script>\n[choice](link)"
    )
    report = (output / "report.md").read_text()
    assert "<script>" not in report and "[choice](link)" not in report
    assert "&lt;script&gt;" in report
    assert "Unwanted-fragment removal is not verified" not in report
    assert "The bound fragment-removal rule is satisfied in the model" in report
    certificate = partition.realizations[0].fragment_certificate
    for disposition, label in (("required", "Retained"), ("sacrificial", "Unwanted")):
        lengths = ", ".join(
            str(fragment.length_nt)
            for fragment in certificate.fragments
            if fragment.disposition.value == disposition
        )
        assert f"{label} separated fragment lengths: {lengths} nt." in report

    inspected = CliRunner().invoke(app, ["construction", "inspect", str(bundle), "--ordinal", "0"])
    assert inspected.exit_code == 0, inspected.output
    assert "Source-fragment removal: specified and verified in the model" in inspected.output
    assert "Cleanup recovery: not predicted" in inspected.output
    assert "unresolved" not in inspected.output
    comparison = construction.compare_constructions(
        receipt,
        receipt,
        left_realization_id=receipt.materialized_realization_ids[0],
        right_realization_id=receipt.materialized_realization_ids[0],
    )
    assert "unresolved" not in comparison
    assert "| Removal-rule allowance (nt) | same |" in comparison


def test_comparison_exposes_molecular_changes_without_replacing_authorities(tmp_path: Path) -> None:
    left = compile_construction_bundle(
        _verified_result(tmp_path / "pcr", ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    )
    right = compile_construction_bundle(
        _verified_result(tmp_path / "release", ConstructionEndpoint.CLONE_READY_DUPLEX)
    )
    left_id = left.materialized_realization_ids[0]
    right_id = right.materialized_realization_ids[0]
    before = construction.project_construction_trajectory(
        left, materialized_realization_id=left_id
    ).json_bytes

    report = construction.compare_constructions(
        left, right, left_realization_id=left_id, right_realization_id=right_id
    )

    assert "| Payload | same | GACA | GACA |" in report
    assert "| Source oligo | same |" in report
    assert "| Adapter | same |" in report
    assert "| Endpoint forward primer | changed |" in report
    assert "| Endpoint reverse primer | changed |" in report
    assert "GGTCTCAAAA" in report
    assert "| Endpoint strand 1 | changed |" in report
    assert "| Left cohesive end | changed | not generated | AAAA" in report
    assert "| Right cohesive end | changed | not generated | AAAA" in report
    assert "| Operation/enzyme order | changed |" in report
    assert "Composition coverage: left complete; right complete." in report
    assert "does not describe upstream scaffold-generation coverage" in report
    assert "unresolved" in report
    assert "not a ranking" in report
    assert left_id in report and right_id in report
    assert (
        construction.project_construction_trajectory(
            left, materialized_realization_id=left_id
        ).json_bytes
        == before
    )
    assert report == construction.compare_constructions(
        left, right, left_realization_id=left_id, right_realization_id=right_id
    )

    left_path = left.write(tmp_path / "left-bundle")
    right_path = right.write(tmp_path / "right-bundle")
    compared = CliRunner().invoke(
        app,
        [
            "construction",
            "compare",
            str(left_path),
            str(right_path),
            "--left-ordinal",
            "0",
            "--right-ordinal",
            "0",
        ],
    )
    assert compared.exit_code == 0, compared.output
    assert compared.output == report
    invalid = CliRunner().invoke(
        app,
        [
            "construction",
            "compare",
            str(left_path),
            str(right_path),
            "--left-ordinal",
            "0",
            "--right-ordinal",
            "99",
        ],
    )
    assert invalid.exit_code == 2
    assert "No accepted route has ordinal 99" in invalid.output


def test_comparison_preserves_coverage_and_requires_verified_selections(tmp_path: Path) -> None:
    receipt = compile_construction_bundle(
        _verified_result(tmp_path / "source", ConstructionEndpoint.SSDNA_HAIRPIN, truncated=True)
    )
    selected_id = receipt.materialized_realization_ids[0]
    report = construction.compare_constructions(
        receipt, receipt, left_realization_id=selected_id, right_realization_id=selected_id
    )
    assert "| changed |" not in report
    assert "Composition coverage: left truncated; right truncated." in report
    assert "| Left cohesive end | same | not generated | not generated |" in report
    with pytest.raises(ValueError, match="Unknown accepted"):
        construction.compare_constructions(
            receipt, receipt, left_realization_id=selected_id, right_realization_id="missing"
        )
    with pytest.raises(TypeError, match="verified construction receipt"):
        construction.compare_constructions(
            object(), receipt, left_realization_id=selected_id, right_realization_id=selected_id
        )
