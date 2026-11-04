"""Lead a verified handoff with achieved ends, flank distances and material changes."""

from hop_design import construction
from hop_design.design.construction.complete.bundle import compile_construction_bundle
from hop_design.models.construction import ConstructionEndpoint
from tests.integration.test_complete_construction_projections import _verified_result


def test_handoff_and_inspection_lead_with_product_and_remaining_conditions(tmp_path):
    compiled = compile_construction_bundle(
        _verified_result(tmp_path / "source", ConstructionEndpoint.CLONE_READY_DUPLEX)
    )
    trajectory = construction.project_construction_trajectory(
        compiled, materialized_realization_id=compiled.materialized_realization_ids[0]
    )
    report = (trajectory.write(tmp_path / "handoff") / "report.md").read_text()
    inspection = trajectory.inspection_text
    for text in (report, inspection):
        assert "Achieved product" in text
        assert "Achieved product: released duplex insert" in text
        assert "Paired flank distances" in text
        assert "Laboratory stock: not supplied" in text
        assert "Enzyme reaction prerequisites: not evaluated" in text
        assert text.index("Achieved product") < text.index("Source")
    assert report.index("Paired flank distances") < report.index("Required oligonucleotides")
    assert "Changed oligos: compare this selection with an explicit reference" in report


def test_comparison_leads_with_changed_and_preserved_material_roles(tmp_path):
    compiled = compile_construction_bundle(
        _verified_result(tmp_path / "source", ConstructionEndpoint.CLONE_READY_DUPLEX)
    )
    comparison = construction.compare_constructions(
        compiled,
        compiled,
        left_realization_id=compiled.materialized_realization_ids[0],
        right_realization_id=compiled.materialized_realization_ids[0],
    )
    assert "Changed external oligo roles: none" in comparison
    assert "Same sequence and terminal chemistry" in comparison
    assert comparison.index("Changed external oligo roles") < comparison.index("| Property |")
    assert "released duplex insert" in comparison


def test_same_source_sequence_with_different_chemistry_counts_as_changed(tmp_path):
    import json

    from hop_design.design.construction.complete import discover_constructions
    from hop_design.design.construction.verification import (
        verify_basal_neighborhood_result,
        verify_foldback_neighborhood_result,
    )
    from tests.integration.test_complete_construction_clone import _clone_request

    request, foldback, basal, design, _, _ = _clone_request(tmp_path / "source")
    data = request.model_dump(mode="json", by_alias=True)
    source = data["materialization"]["source_preparation"]["source_ssdna"]
    assert source["five_prime_end"] == "hydroxyl"
    source["five_prime_end"] = "phosphate"
    edited = type(request).model_validate_json(json.dumps(data))
    results = [
        compile_construction_bundle(
            discover_constructions(
                intent,
                foldback=verify_foldback_neighborhood_result(foldback),
                basal=verify_basal_neighborhood_result(basal),
                design=design,
            )
        )
        for intent in (request, edited)
    ]
    comparison = construction.compare_constructions(
        results[0],
        results[1],
        left_realization_id=results[0].materialized_realization_ids[0],
        right_realization_id=results[1].materialized_realization_ids[0],
    )
    assert "Changed external oligo roles: Source oligo." in comparison
