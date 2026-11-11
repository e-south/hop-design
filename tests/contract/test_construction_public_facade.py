"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_construction_public_facade.py

Tests the narrow file-oriented public construction facade and opaque receipts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

import hop_design.construction as construction
from hop_design.design.construction.complete.bundle import compile_construction_bundle
from tests.integration.test_complete_construction_bundle import _verified_construction
from tests.integration.test_source_partition_discovery import _request as source_partition_request
from tests.support.documentation import read_documentation

PUBLIC_NAMES = [
    "AtlasEdition",
    "BasalSequenceSpace",
    "ConstructionComparison",
    "ConstructionCompilation",
    "ConstructionFamilyExecution",
    "ConstructionFamilyReport",
    "ConstructionOptionSets",
    "ConstructionOptions",
    "ConstructionProjection",
    "ConstructionRequestExecution",
    "ConstructionSelection",
    "ConstructionSet",
    "DesignChoices",
    "DesignRevisionPreview",
    "DiscoveryCancelled",
    "DiscoveryProgress",
    "FoldbackSequenceSpace",
    "InterfaceSurveyAtlas",
    "InterfaceSurveyChoices",
    "LocalNeighborhoodBatch",
    "LocalNeighborhoodDiscovery",
    "LocalRealizationChoice",
    "MatchedConstructionFamily",
    "MolecularEditEvaluation",
    "PreparedConstructionFamily",
    "PreparedConstructionRequest",
    "PreparedMolecularEdit",
    "PreparedScaffoldComparison",
    "PreparedScaffoldDiscovery",
    "PreparedSequenceFamily",
    "PriorMaterialReuse",
    "ProtectedRoot",
    "ReconciledConstructionFamily",
    "ResolvedDesignRequest",
    "ResolvedStageControl",
    "ScaffoldAtlas",
    "ScaffoldComparison",
    "ScaffoldDiscovery",
    "ScaffoldEnvelopeEvaluation",
    "ScaffoldEnvelopePreview",
    "ScaffoldExploration",
    "ScaffoldInspection",
    "ScaffoldParameterDomain",
    "ScaffoldParameterEvaluation",
    "ScaffoldVariantChoices",
    "ScaffoldVariantComparison",
    "ScaffoldVariantPreview",
    "ScaffoldVariantView",
    "SelectedPreparationReference",
    "SequenceFamilyEvaluation",
    "SourcePartitionDiscovery",
    "VerifiedConstructionBundle",
    "assess_scaffold_comparison",
    "author_construction_family",
    "author_molecular_edit",
    "combine_design_discoveries",
    "compare_constructions",
    "compare_scaffold_variants",
    "compile_construction",
    "compile_construction_from_local_realizations",
    "compile_design_from_local_realizations",
    "continue_construction_request",
    "continue_design_discovery",
    "discover_basal_sequence_space",
    "discover_construction_source_partition",
    "discover_designs",
    "discover_foldback_sequence_space",
    "discover_local_neighborhood",
    "discover_local_neighborhoods",
    "discover_scaffolds",
    "discover_source_partition",
    "evaluate_interface_survey",
    "evaluate_scaffold_envelope_revision",
    "evaluate_scaffold_parameters",
    "execute_construction_family",
    "execute_construction_request",
    "execute_molecular_edit",
    "execute_scaffold_comparison",
    "execute_sequence_family",
    "explore_construction_options",
    "find_construction_option_sets",
    "freeze_design_choices",
    "inspect_interface_survey",
    "inspect_interface_survey_atlas",
    "inspect_scaffold_atlas",
    "inspect_scaffold_variant",
    "list_local_realizations",
    "load_atlas_edition",
    "load_construction_selection",
    "load_design_choices",
    "load_design_revision",
    "load_interface_survey_choices",
    "load_scaffold_envelope_revision",
    "load_scaffold_exploration",
    "load_scaffold_variant_choices",
    "load_verified_basal_sequence_space",
    "load_verified_construction_bundle",
    "load_verified_foldback_sequence_space",
    "load_verified_local_neighborhood",
    "load_verified_source_partition",
    "match_construction_family",
    "migrate_interface_survey",
    "prepare_construction_family",
    "prepare_construction_request",
    "prepare_molecular_edit",
    "prepare_scaffold_comparison",
    "prepare_scaffold_discovery",
    "prepare_sequence_family",
    "preview_design_revision",
    "preview_scaffold_envelope_revision",
    "preview_scaffold_variant",
    "project_basal_feasibility",
    "project_basal_minimum_overhead_matrix",
    "project_basal_source_panel",
    "project_complete_construction_summary",
    "project_construction_comparison",
    "project_construction_family_report",
    "project_construction_navigation",
    "project_construction_trajectory",
    "project_foldback_feasibility",
    "project_hairpin_portrait",
    "project_retained_overhead_frontier",
    "project_scaffold_variant",
    "project_source_partition_certificate",
    "query_interface_survey",
    "query_scaffold_parameter_domain",
    "query_scaffold_variants",
    "reconcile_construction_family",
    "resolve_design_request",
    "retrieve_interface_survey_witness",
    "select_construction_options",
    "select_construction_realization",
    "select_construction_set",
    "select_molecular_edit",
    "select_scaffold_comparison",
    "select_scaffold_options",
    "select_scaffold_variant_comparison",
    "select_scaffold_variants",
    "select_sequence_family",
    "upgrade_interface_survey",
    "verify_interface_survey",
]


def test_construction_facade_is_an_exact_allowlist() -> None:
    assert construction.__all__ == PUBLIC_NAMES
    assert all(hasattr(construction, name) for name in PUBLIC_NAMES)
    for internal_name in (
        "ConstructionBundle",
        "ConstructionDiscoveryRequest",
        "ConstructionSpaceResult",
        "CompleteConstructionSummaryProjection",
        "project_complete_construction_navigation",
        "render_projection_svg",
        "verify_construction_bundle",
    ):
        assert not hasattr(construction, internal_name)
    for receipt_type in (
        construction.ConstructionOptions,
        construction.ConstructionOptionSets,
        construction.BasalSequenceSpace,
        construction.ConstructionFamilyExecution,
        construction.ConstructionSet,
        construction.PreparedConstructionFamily,
        construction.MatchedConstructionFamily,
        construction.ReconciledConstructionFamily,
        construction.ConstructionCompilation,
        construction.ConstructionComparison,
        construction.ConstructionProjection,
        construction.ConstructionRequestExecution,
        construction.ConstructionSelection,
        construction.FoldbackSequenceSpace,
        construction.LocalNeighborhoodDiscovery,
        construction.LocalNeighborhoodBatch,
        construction.PreparedConstructionRequest,
        construction.PreparedMolecularEdit,
        construction.MolecularEditEvaluation,
        construction.PreparedSequenceFamily,
        construction.SequenceFamilyEvaluation,
        construction.SourcePartitionDiscovery,
        construction.VerifiedConstructionBundle,
    ):
        assert tuple(inspect.signature(receipt_type).parameters) == ()


def test_construction_selection_is_a_stable_non_authoritative_reference(
    tmp_path: Path,
) -> None:
    receipt = compile_construction_bundle(_verified_construction(tmp_path))
    realization_id = receipt.materialized_realization_ids[0]

    selection = construction.select_construction_realization(
        receipt,
        materialized_realization_id=realization_id,
    )

    assert isinstance(selection, construction.ConstructionSelection)
    assert selection.schema_id == "hop.construction-selection/v1"
    assert selection.source_result_id == receipt.result_id
    assert selection.materialized_realization_id == realization_id
    assert json.loads(selection.json_bytes) == {
        "schema": "hop.construction-selection/v1",
        "source_result_id": receipt.result_id,
        "materialized_realization_id": realization_id,
    }
    assert selection.json_bytes.endswith(b"\n")
    assert not hasattr(selection, "authority")
    assert "ConstructionSpaceResult" not in repr(selection)


def test_construction_selection_rejects_unverified_receipts_and_nonmembers(
    tmp_path: Path,
) -> None:
    receipt = compile_construction_bundle(_verified_construction(tmp_path))

    with pytest.raises(TypeError, match="verified construction receipt"):
        construction.select_construction_realization(  # type: ignore[arg-type]
            object(),
            materialized_realization_id=receipt.materialized_realization_ids[0],
        )
    with pytest.raises(ValueError, match="not an accepted realization"):
        construction.select_construction_realization(
            receipt,
            materialized_realization_id=f"hop:materialized-construction/{'0' * 64}@1",
        )


def test_construction_selection_file_is_exact_create_only_and_receipt_bound(
    tmp_path: Path,
) -> None:
    receipt = compile_construction_bundle(_verified_construction(tmp_path))
    selection = construction.select_construction_realization(
        receipt,
        materialized_realization_id=receipt.materialized_realization_ids[0],
    )

    output = selection.write(tmp_path / "references" / "selected.json")

    assert output == tmp_path / "references" / "selected.json"
    assert output.is_file()
    assert output.read_bytes() == selection.json_bytes
    with pytest.raises(FileExistsError, match="Refusing to replace existing selection path"):
        selection.write(output)

    loaded = construction.load_construction_selection(output, receipt=receipt)
    assert loaded.json_bytes == selection.json_bytes
    assert loaded.source_result_id == receipt.result_id
    assert loaded.materialized_realization_id == selection.materialized_realization_id


def test_construction_selection_uses_one_json_file_contract(tmp_path: Path) -> None:
    receipt = compile_construction_bundle(_verified_construction(tmp_path))
    selection = construction.select_construction_realization(
        receipt,
        materialized_realization_id=receipt.materialized_realization_ids[0],
    )

    for unsupported in (tmp_path / "selected", tmp_path / "selected.yaml"):
        with pytest.raises(ValueError, match=r"must use the \.json extension"):
            selection.write(unsupported)
        assert not unsupported.exists()

    yaml_document = tmp_path / "selection.yaml"
    yaml_document.write_bytes(selection.json_bytes)
    with pytest.raises(ValueError, match=r"must use the \.json extension"):
        construction.load_construction_selection(yaml_document, receipt=receipt)


def test_construction_selection_loader_fails_closed(
    tmp_path: Path,
) -> None:
    receipt = compile_construction_bundle(_verified_construction(tmp_path))
    selection = construction.select_construction_realization(
        receipt,
        materialized_realization_id=receipt.materialized_realization_ids[0],
    )
    valid = selection.write(tmp_path / "selected.json")

    with pytest.raises(TypeError, match="verified construction receipt"):
        construction.load_construction_selection(valid, receipt=object())  # type: ignore[arg-type]

    mismatched = json.loads(selection.json_bytes)
    mismatched["source_result_id"] = f"hop:construction-space-result/{'0' * 64}@1"
    mismatched_path = tmp_path / "mismatched.json"
    mismatched_path.write_text(json.dumps(mismatched), encoding="utf-8")
    with pytest.raises(
        ValueError,
        match="does not belong to this verified construction result",
    ):
        construction.load_construction_selection(mismatched_path, receipt=receipt)

    unknown = json.loads(selection.json_bytes)
    unknown["note"] = "not part of the selection contract"
    unknown_path = tmp_path / "unknown.json"
    unknown_path.write_text(json.dumps(unknown), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid"):
        construction.load_construction_selection(unknown_path, receipt=receipt)

    linked = tmp_path / "linked.json"
    linked.symlink_to(valid)
    with pytest.raises(ValueError, match="must not be a symlink"):
        construction.load_construction_selection(linked, receipt=receipt)

    directory = tmp_path / "directory.json"
    directory.mkdir()
    with pytest.raises(ValueError, match="is not a regular file"):
        construction.load_construction_selection(directory, receipt=receipt)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * 16_385)
    with pytest.raises(ValueError, match="max_bytes exceeded"):
        construction.load_construction_selection(oversized, receipt=receipt)


def test_construction_facade_decision_records_the_exact_allowlist() -> None:
    decision = read_documentation(
        "docs/architecture/decisions/0027-file-oriented-construction-facade.md"
    )

    for name in PUBLIC_NAMES:
        assert f"`{name}`" in decision


def test_construction_receipts_expose_scientific_accounting_not_authority_models(
    tmp_path: Path,
) -> None:
    verified = _verified_construction(tmp_path)
    compilation = compile_construction_bundle(verified)

    assert isinstance(compilation, construction.ConstructionCompilation)
    assert compilation.bundle_id.startswith("hop:construction-bundle/")
    assert compilation.result_id == verified.result.result_id
    assert compilation.design_bundle_id == verified.design.bundle.bundle_id
    assert compilation.status == verified.result.status.value
    assert compilation.endpoint == verified.result.request.endpoint.value
    assert compilation.valid_realizations == verified.result.accounting.valid_realizations
    assert compilation.examined_combinations == verified.result.accounting.examined_combinations
    assert compilation.nominal_combinations == verified.result.accounting.nominal_combinations
    assert compilation.materialized_realization_ids == tuple(
        item.materialized_realization_id for item in verified.result.realizations
    )
    assert not hasattr(compilation, "bundle")
    assert not hasattr(compilation, "construction")
    assert not hasattr(compilation, "artifacts")
    assert "VerifiedConstructionSpaceResult" not in repr(compilation)
    assert "ConstructionBundle(" not in repr(compilation)

    output = compilation.write(tmp_path / "construction")
    loaded = construction.load_verified_construction_bundle(output)

    assert isinstance(loaded, construction.VerifiedConstructionBundle)
    assert loaded.bundle_id == compilation.bundle_id
    assert loaded.result_id == compilation.result_id
    assert loaded.materialized_realization_ids == compilation.materialized_realization_ids
    assert not hasattr(loaded, "bundle")
    assert not hasattr(loaded, "construction")
    assert not hasattr(loaded, "artifacts")
    assert "VerifiedConstructionSpaceResult" not in repr(loaded)


def test_construction_projection_packet_is_portable_and_create_only(tmp_path: Path) -> None:
    compilation = compile_construction_bundle(_verified_construction(tmp_path))
    realization_id = compilation.materialized_realization_ids[0]

    summary = construction.project_complete_construction_summary(compilation)
    trajectory = construction.project_construction_trajectory(
        compilation,
        materialized_realization_id=realization_id,
    )

    assert isinstance(summary, construction.ConstructionProjection)
    assert summary.schema_id == "hop.complete-construction-summary/v5"
    assert summary.projection_id.startswith("hop:complete-construction-summary/")
    assert summary.source_result_id == compilation.result_id
    assert summary.json_bytes.endswith(b"\n")
    assert summary.csv_bytes is not None
    assert summary.svg_bytes.startswith(b"<svg")
    assert trajectory.schema_id == "hop.complete-construction-trajectory/v5"
    assert trajectory.csv_bytes is None

    output = summary.write(tmp_path / "summary")
    assert {item.name for item in output.iterdir()} == {
        "projection.csv",
        "projection.json",
        "projection.svg",
    }
    with pytest.raises(FileExistsError, match="Refusing to replace existing projection path"):
        summary.write(output)


def test_construction_local_projections_require_explicit_family_selection(
    tmp_path: Path,
) -> None:
    compilation = compile_construction_bundle(_verified_construction(tmp_path, include_basal=True))

    foldback = construction.project_foldback_feasibility(compilation)
    basal = construction.project_basal_feasibility(compilation)
    foldback_frontier = construction.project_retained_overhead_frontier(
        compilation,
        family="foldback",
    )
    basal_frontier = construction.project_retained_overhead_frontier(
        compilation,
        family="basal",
    )

    assert foldback.schema_id == "hop.foldback-feasibility-landscape/v5"
    assert basal.schema_id == "hop.basal-feasibility-landscape/v6"
    assert foldback_frontier.schema_id == "hop.foldback-overhead-frontier/v1"
    assert basal_frontier.schema_id == "hop.basal-overhead-frontier/v1"
    with pytest.raises(ValueError, match="family must be foldback or basal"):
        construction.project_retained_overhead_frontier(
            compilation,
            family="unknown",  # type: ignore[arg-type]
        )


def test_basal_projection_rejects_a_route_without_basal_authority(tmp_path: Path) -> None:
    compilation = compile_construction_bundle(_verified_construction(tmp_path))

    with pytest.raises(ValueError, match="does not contain a basal authority"):
        construction.project_basal_feasibility(compilation)


def test_source_partition_discovery_is_file_oriented_and_portable(tmp_path: Path) -> None:
    source = tmp_path / "source-partition.json"
    source.write_text(
        json.dumps(
            source_partition_request().model_dump(mode="json", by_alias=True),
            sort_keys=True,
        )
    )

    discovery = construction.discover_source_partition(source)

    assert isinstance(discovery, construction.SourcePartitionDiscovery)
    assert discovery.status == "complete"
    assert discovery.candidate_space_size == 3
    assert discovery.examined_nodes == 3
    assert discovery.accepted_realizations == 1
    assert len(discovery.realization_ids) == 1
    assert discovery.problem_id.startswith("hop:source-partition-problem/")
    assert discovery.request_id.startswith("hop:source-partition-request/")
    assert discovery.result_id.startswith("hop:source-partition-result/")
    assert discovery.json_bytes.endswith(b"\n")
    assert discovery.csv_bytes.startswith(b"candidate_id,enzyme_ids,disposition")
    assert not hasattr(discovery, "request")
    assert not hasattr(discovery, "result")
    assert repr(discovery).startswith("SourcePartitionDiscovery(status='complete'")

    output = discovery.write(tmp_path / "partition")
    assert {item.name for item in output.iterdir()} == {
        "data.csv",
        "fragments.csv",
        "result.json",
        "thresholds.csv",
    }
    loaded = construction.load_verified_source_partition(output / "result.json")
    assert loaded.result_id == discovery.result_id
    assert loaded.json_bytes == discovery.json_bytes
    assert loaded.csv_bytes == discovery.csv_bytes
    with pytest.raises(FileExistsError, match="Refusing to replace existing"):
        discovery.write(output)
