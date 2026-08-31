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

PUBLIC_NAMES = [
    "ConstructionCompilation",
    "ConstructionProjection",
    "LocalNeighborhoodDiscovery",
    "SourcePartitionDiscovery",
    "VerifiedConstructionBundle",
    "compile_construction",
    "compile_construction_from_local_realizations",
    "compile_design_from_local_realizations",
    "discover_local_neighborhood",
    "discover_source_partition",
    "load_verified_construction_bundle",
    "load_verified_local_neighborhood",
    "load_verified_source_partition",
    "project_basal_feasibility",
    "project_complete_construction_summary",
    "project_construction_trajectory",
    "project_foldback_feasibility",
    "project_relaxation_frontier",
]


def test_construction_facade_is_an_exact_allowlist() -> None:
    assert construction.__all__ == PUBLIC_NAMES
    assert all(hasattr(construction, name) for name in PUBLIC_NAMES)
    for internal_name in (
        "ConstructionBundle",
        "ConstructionDiscoveryRequest",
        "ConstructionSpaceResult",
        "CompleteConstructionSummaryProjection",
        "render_projection_svg",
        "verify_construction_bundle",
    ):
        assert not hasattr(construction, internal_name)
    for receipt_type in (
        construction.ConstructionCompilation,
        construction.ConstructionProjection,
        construction.LocalNeighborhoodDiscovery,
        construction.SourcePartitionDiscovery,
        construction.VerifiedConstructionBundle,
    ):
        assert tuple(inspect.signature(receipt_type).parameters) == ()


def test_construction_facade_decision_records_the_exact_allowlist() -> None:
    decision = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "architecture"
        / "decisions"
        / "0027-file-oriented-construction-facade.md"
    ).read_text(encoding="utf-8")

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
    assert summary.schema_id == "hop.complete-construction-summary/v1"
    assert summary.projection_id.startswith("hop:complete-construction-summary/")
    assert summary.source_result_id == compilation.result_id
    assert summary.json_bytes.endswith(b"\n")
    assert summary.csv_bytes is not None
    assert summary.svg_bytes.startswith(b"<svg")
    assert trajectory.schema_id == "hop.complete-construction-trajectory/v2"
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
    foldback_frontier = construction.project_relaxation_frontier(
        compilation,
        family="foldback",
    )
    basal_frontier = construction.project_relaxation_frontier(
        compilation,
        family="basal",
    )

    assert foldback.schema_id == "hop.foldback-feasibility-landscape/v3"
    assert basal.schema_id == "hop.basal-feasibility-landscape/v2"
    assert foldback_frontier.schema_id == "hop.foldback-relaxation-frontier/v2"
    assert basal_frontier.schema_id == "hop.basal-relaxation-frontier/v1"
    with pytest.raises(ValueError, match="family must be foldback or basal"):
        construction.project_relaxation_frontier(
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
    assert {item.name for item in output.iterdir()} == {"data.csv", "result.json"}
    loaded = construction.load_verified_source_partition(output / "result.json")
    assert loaded.result_id == discovery.result_id
    assert loaded.json_bytes == discovery.json_bytes
    assert loaded.csv_bytes == discovery.csv_bytes
    with pytest.raises(FileExistsError, match="Refusing to replace existing"):
        discovery.write(output)
