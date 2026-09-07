"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_complete_construction_navigation.py

Tests non-authoritative navigation over verified whole-route construction results.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import hop_design.construction as construction
from hop_design.design.construction.complete import discover_constructions
from hop_design.design.construction.complete.bundle import compile_construction_bundle
from hop_design.design.construction.verification import (
    verify_basal_neighborhood_result,
    verify_foldback_neighborhood_result,
)
from hop_design.models.construction import ConstructionEndpoint
from hop_design.models.construction.complete import FixedEndpointPrimerPolicy
from hop_design.models.sequence import reverse_complement_iupac
from tests.integration.test_complete_construction_clone import _clone_request
from tests.integration.test_complete_construction_projections import _verified_result


def _csv_rows(content: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(content.decode("utf-8"))))


def _navigation(
    tmp_path: Path,
    *,
    incompatible: bool = False,
):
    verified = _verified_result(
        tmp_path,
        ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
        incompatible=incompatible,
    )
    compilation = compile_construction_bundle(verified)
    packet = construction.project_construction_navigation(compilation)
    return verified, compilation, packet


def _truncated_navigation(tmp_path: Path):
    request, foldback, basal, design, _, _ = _clone_request(tmp_path)
    auxiliaries = request.materialization.endpoint_auxiliaries
    assert auxiliaries is not None and request.release is not None
    reverse_policy = auxiliaries.reverse_primer
    assert isinstance(reverse_policy, FixedEndpointPrimerPolicy)
    reverse = reverse_policy.primer
    data = request.model_dump(by_alias=True)
    primer = data["materialization"]["endpoint_auxiliaries"]["reverse_primer"]["primer"]
    primer["oligo"]["sequence_5prime"] = (
        reverse_complement_iupac("AGAGACCAGAGACC") + reverse.annealing_sequence
    )
    del primer["oligo"]["material_id"]
    data["release"]["max_site_pairs"] = 1
    bounded = type(request).model_validate(data)
    verified = discover_constructions(
        bounded,
        foldback=verify_foldback_neighborhood_result(foldback),
        basal=verify_basal_neighborhood_result(basal),
        design=design,
    )
    compilation = compile_construction_bundle(verified)
    return construction.project_construction_navigation(compilation)


def test_navigation_adds_route_facts_without_resealing_or_repeating_summary(
    tmp_path: Path,
) -> None:
    verified = _verified_result(tmp_path, ConstructionEndpoint.HAIRPIN_PCR_DUPLEX)
    compilation = compile_construction_bundle(verified)
    result_bytes = compilation._artifacts["construction-result.json"]
    result_digest = compilation._bundle.result_digest
    manifest_digest = compilation._bundle.manifest_digest
    result_id = compilation.result_id
    bundle_id = compilation.bundle_id
    artifact_inventory = compilation._bundle.artifacts

    packet = construction.project_construction_navigation(compilation)

    assert isinstance(packet, construction.ConstructionProjection)
    assert packet.schema_id == "hop.construction-navigation/v1"
    assert packet.source_result_id == result_id
    assert packet.json_bytes.endswith(b"\n")
    assert packet.csv_bytes is not None
    assert packet.svg_bytes.startswith(b"<svg")
    rendered = json.loads(packet.json_bytes)
    assert set(rendered) == {
        "schema",
        "projection_id",
        "source_result_id",
        "renderer_version",
        "summary",
        "accepted_routes",
        "geometry_groups",
    }
    assert rendered["renderer_version"] == "construction-navigation/1"
    assert rendered["source_result_id"] == result_id
    summary = rendered["summary"]
    assert summary["schema"] == "hop.complete-construction-summary/v2"
    assert summary["source_result_id"] == result_id
    assert summary["status"] == "complete"

    realizations = {item.materialized_realization_id: item for item in verified.result.realizations}
    accepted_routes = rendered["accepted_routes"]
    assert tuple(route["materialized_realization_id"] for route in accepted_routes) == tuple(
        realizations
    )
    for route in accepted_routes:
        realization = realizations[route["materialized_realization_id"]]
        foldback_geometry = realization.foldback_authority.local_realization.achieved_geometry
        basal_authority = realization.basal_authority
        assert basal_authority is not None
        basal_geometry = basal_authority.local_realization.achieved_geometry
        assert route["foldback_geometry"] == foldback_geometry.model_dump(mode="json")
        assert route["basal_geometry"] == basal_geometry.model_dump(mode="json")
        assert route["foldback_retained_overhead_nt"] == (
            realization.foldback_authority.retained_overhead.retained_overhead_nt
        )
        assert route["basal_retained_overhead_nt"] == (
            basal_authority.retained_overhead.retained_overhead_nt
        )
        expected_enzymes = sorted(
            {
                operation.enzyme_id
                for program in realization.construction_program.reaction_programs
                for stage in program.stages
                for operation in stage.operations
            }
        )
        assert route["cleavage_enzyme_ids"] == expected_enzymes
        assert route["retained_non_payload_nt"] == (
            len(realization.design.encoding_sequence) - 2 * len(realization.design.payload_sequence)
        )
        assert route["final_product_topology"] == realization.final_product.reference.topology

    groups = rendered["geometry_groups"]
    assert groups
    assert all(group["foldback_geometry"] for group in groups)
    assert all(group["basal_geometry"] for group in groups)
    grouped_ids = [
        realization_id for group in groups for realization_id in group["realization_ids"]
    ]
    assert sorted(grouped_ids) == sorted(realizations)
    assert len(grouped_ids) == len(set(grouped_ids))

    csv_rows = _csv_rows(packet.csv_bytes)
    assert [int(row["ordinal"]) for row in csv_rows] == list(range(len(csv_rows)))
    assert all(row["source_result_id"] == result_id for row in csv_rows)
    assert all(int(row["foldback_retained_overhead_nt"]) >= 0 for row in csv_rows)
    assert all(int(row["basal_retained_overhead_nt"]) >= 0 for row in csv_rows)
    assert all(row["cleavage_enzyme_ids"] for row in csv_rows)
    assert all(int(row["required_external_material_count"]) >= 3 for row in csv_rows)
    svg = packet.svg_bytes.decode("utf-8")
    assert f'data-result-id="{result_id}"' in svg
    assert "Foldback geometry" in svg
    assert "loop 3 nt" in svg
    assert "data-foldback-retained-overhead-nt" in svg
    assert "data-basal-retained-overhead-nt" in svg
    assert "physical construction was not recorded" in svg
    assert "dashboard" not in svg.lower()
    assert "rank" not in svg.lower()

    assert compilation._artifacts["construction-result.json"] == result_bytes
    assert compilation._bundle.result_digest == result_digest
    assert compilation._bundle.manifest_digest == manifest_digest
    assert compilation.result_id == result_id
    assert compilation.bundle_id == bundle_id
    assert compilation._bundle.artifacts == artifact_inventory
    replay = compile_construction_bundle(verified)
    assert replay._artifacts["construction-result.json"] == result_bytes
    assert replay._bundle.result_digest == result_digest
    assert replay._bundle.manifest_digest == manifest_digest
    assert replay.result_id == result_id
    assert replay.bundle_id == bundle_id
    assert replay._bundle.artifacts == artifact_inventory


def test_navigation_leaves_rejected_and_truncated_evidence_in_summary_only(
    tmp_path: Path,
) -> None:
    _, _, infeasible = _navigation(tmp_path / "infeasible", incompatible=True)
    truncated = _truncated_navigation(tmp_path / "truncated")

    infeasible_data = json.loads(infeasible.json_bytes)
    truncated_data = json.loads(truncated.json_bytes)
    assert infeasible_data["summary"]["status"] == "infeasible"
    assert truncated_data["summary"]["status"] == "truncated"
    assert infeasible_data["accepted_routes"] == []
    assert truncated_data["accepted_routes"] == []
    assert all(
        row["truncation_reason"] == "endpoint:max_site_pairs"
        for row in truncated_data["summary"]["rows"]
    )
    rows = (
        *infeasible_data["summary"]["rows"],
        *truncated_data["summary"]["rows"],
    )
    assert rows
    for row in rows:
        assert row["status"] in {"rejected", "truncated"}
        assert row["materialized_realization_id"] is None
        assert row["achieved_geometry_group_key"] is None
        assert row["final_product_group_key"] is None
    assert _csv_rows(infeasible.csv_bytes) == []
    assert _csv_rows(truncated.csv_bytes) == []
    assert "after exhaustive composition" in infeasible.svg_bytes.decode("utf-8")
    assert "stopped before" in truncated.svg_bytes.decode("utf-8")


def test_navigation_has_one_public_name_and_no_compatibility_alias() -> None:
    assert "project_construction_navigation" in construction.__all__
    assert hasattr(construction, "project_construction_navigation")
    assert not hasattr(construction, "project_complete_construction_navigation")
