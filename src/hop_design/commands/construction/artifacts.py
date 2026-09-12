"""File-oriented discovery, replay, and projection commands for external consumers."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

import typer

from hop_design import construction

from .common import require_output_outside_bundle


def _local_report(receipt: construction.LocalNeighborhoodDiscovery) -> dict[str, object]:
    return {
        "schema": "hop/local-result-report/v1",
        "verification": "deterministic_discovery",
        "result_sha256": "sha256:" + hashlib.sha256(receipt.json_bytes).hexdigest(),
        "result_id": receipt.result_id,
        "problem_id": receipt.problem_id,
        "family": receipt.family,
        "completion": receipt.completion,
        "feasibility": receipt.feasibility,
        "termination_reason": receipt.termination_reason,
        "realization_count": receipt.realization_count,
        "result": json.loads(receipt.json_bytes),
    }


def discover_local_command(
    request: Path,
    output: Annotated[Path, typer.Option("--out", help="New local-authority directory.")],
) -> None:
    """Discover a bounded local neighborhood and publish its existing authority format."""
    try:
        receipt = construction.discover_local_neighborhood(request)
        receipt.write(output)
        typer.echo(json.dumps(_local_report(receipt), sort_keys=True))
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


def verify_local_command(result: Path) -> None:
    """Replay an existing local result and emit its authority-bound JSON report."""
    try:
        receipt = construction.load_verified_local_neighborhood(result)
        typer.echo(json.dumps(_local_report(receipt), sort_keys=True))
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


def discover_batch_command(
    requests: list[Path],
    checkpoint: Annotated[Path, typer.Option("--checkpoint")],
    resume: Annotated[bool, typer.Option("--resume")] = False,
) -> None:
    """Execute explicit local request files using producer-owned durable checkpoints."""
    try:
        batch = construction.discover_local_neighborhoods(requests, checkpoint, resume=resume)
        typer.echo(
            json.dumps(
                {
                    "schema": "hop/local-batch-report/v1",
                    "finished": batch.finished,
                    "planned_requests": batch.planned_requests,
                    "completed_requests": batch.completed_requests,
                    "results": [_local_report(result) for result in batch.iter_results()],
                },
                sort_keys=True,
            )
        )
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


def _partition_report(receipt: construction.SourcePartitionDiscovery) -> dict[str, object]:
    return {
        "schema": "hop/source-partition-report/v1",
        "verification": "deterministic_derivation",
        "result_sha256": "sha256:" + hashlib.sha256(receipt.json_bytes).hexdigest(),
        "result_id": receipt.result_id,
        "problem_id": receipt.problem_id,
        "request_id": receipt.request_id,
        "status": receipt.status,
        "candidate_space_size": receipt.candidate_space_size,
        "examined_nodes": receipt.examined_nodes,
        "accepted_realizations": receipt.accepted_realizations,
        "realization_ids": receipt.realization_ids,
        "result": json.loads(receipt.json_bytes),
        "candidate_csv": receipt.csv_bytes.decode("utf-8"),
    }


def discover_partition_command(
    request: Path,
    output: Annotated[Path, typer.Option("--out")],
) -> None:
    """Discover source partitions and publish the existing result and candidate tables."""
    try:
        receipt = construction.discover_source_partition(request)
        receipt.write(output)
        typer.echo(json.dumps(_partition_report(receipt), sort_keys=True))
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


def verify_partition_command(result: Path) -> None:
    """Replay one source-partition authority without running a study."""
    try:
        receipt = construction.load_verified_source_partition(result)
        typer.echo(json.dumps(_partition_report(receipt), sort_keys=True))
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


def discover_construction_partition_command(
    bundle: Path,
    policy: Path,
    combination_ordinal: Annotated[int, typer.Option("--combination-ordinal")],
    output: Annotated[Path, typer.Option("--out")],
) -> None:
    """Discover source removal for an explicitly selected complete-construction disposition."""
    try:
        require_output_outside_bundle(bundle, output)
        receipt = construction.load_verified_construction_bundle(bundle)
        partition = construction.discover_construction_source_partition(
            receipt, policy, combination_ordinal=combination_ordinal
        )
        partition.write(output)
        typer.echo(json.dumps(_partition_report(partition), sort_keys=True))
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


class ProjectionKind(StrEnum):
    FOLDBACK_FEASIBILITY = "foldback-feasibility"
    BASAL_FEASIBILITY = "basal-feasibility"
    BASAL_MINIMUM_OVERHEAD = "basal-minimum-overhead"
    FOLDBACK_RETAINED_OVERHEAD = "foldback-retained-overhead"
    BASAL_RETAINED_OVERHEAD = "basal-retained-overhead"
    SOURCE_PARTITION_CERTIFICATE = "source-partition-certificate"
    CONSTRUCTION_NAVIGATION = "construction-navigation"
    CONSTRUCTION_TRAJECTORY = "construction-trajectory"
    CONSTRUCTION_SUMMARY = "construction-summary"


def project_command(
    source: Path,
    kind: Annotated[ProjectionKind, typer.Option("--kind")],
    output: Annotated[Path, typer.Option("--out")],
    realization_id: Annotated[str | None, typer.Option("--realization-id")] = None,
    selection_reason: Annotated[str | None, typer.Option("--selection-reason")] = None,
) -> None:
    """Publish one existing JSON/CSV/SVG projection from a replay-verified authority."""
    try:
        if kind is ProjectionKind.SOURCE_PARTITION_CERTIFICATE:
            if realization_id is None:
                raise ValueError("Source-partition certificate requires --realization-id")
            partition = construction.load_verified_source_partition(source)
            projection = construction.project_source_partition_certificate(
                partition, realization_id=realization_id
            )
        elif kind in {
            ProjectionKind.CONSTRUCTION_NAVIGATION,
            ProjectionKind.CONSTRUCTION_TRAJECTORY,
            ProjectionKind.CONSTRUCTION_SUMMARY,
        }:
            require_output_outside_bundle(source, output)
            complete = construction.load_verified_construction_bundle(source)
            if kind is ProjectionKind.CONSTRUCTION_TRAJECTORY:
                if realization_id is None:
                    raise ValueError("Construction trajectory requires --realization-id")
                projection = construction.project_construction_trajectory(
                    complete, materialized_realization_id=realization_id
                )
            else:
                if realization_id is not None:
                    raise ValueError("Construction navigation does not accept --realization-id")
                projection = (
                    construction.project_complete_construction_summary(complete)
                    if kind is ProjectionKind.CONSTRUCTION_SUMMARY
                    else construction.project_construction_navigation(complete)
                )
        else:
            if realization_id is not None:
                raise ValueError("Local landscape projections do not accept --realization-id")
            local = construction.load_verified_local_neighborhood(source)
            if kind is ProjectionKind.FOLDBACK_FEASIBILITY:
                projection = construction.project_foldback_feasibility(local)
            elif kind is ProjectionKind.BASAL_FEASIBILITY:
                projection = construction.project_basal_feasibility(local)
            elif kind is ProjectionKind.BASAL_MINIMUM_OVERHEAD:
                projection = construction.project_basal_minimum_overhead_matrix(local)
            else:
                family: Literal["basal", "foldback"] = (
                    "basal" if kind is ProjectionKind.BASAL_RETAINED_OVERHEAD else "foldback"
                )
                projection = construction.project_retained_overhead_frontier(local, family=family)
        projection.write(output, selection_reason=selection_reason)
        typer.echo(
            json.dumps(
                {
                    "projection_id": projection.projection_id,
                    "source_result_id": projection.source_result_id,
                },
                sort_keys=True,
            )
        )
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


def local_choices_command(
    result: Path,
    sort_by: Annotated[list[str] | None, typer.Option("--sort-by")] = None,
) -> None:
    """Export declared inspection facts from verified local realizations."""
    try:
        receipt = construction.load_verified_local_neighborhood(result)
        # The facade validates the closed ordered preference vocabulary.
        rows = construction.list_local_realizations(receipt, sort_by=tuple(sort_by or ()))  # type: ignore[arg-type]
        typer.echo(
            json.dumps(
                {
                    "schema": "hop/local-choices-report/v1",
                    "source_result_id": receipt.result_id,
                    "choices": [
                        {
                            "source_result_id": row.source_result_id,
                            "realization_id": row.realization_id,
                            "geometry": row.geometry.model_dump(mode="json", by_alias=True),
                            "retained_overhead_nt": row.retained_overhead_nt,
                            "enzyme_ids": row.enzyme_ids,
                            "cohesive_end": row.cohesive_end,
                            "pairing_classes": row.pairing_classes,
                            "required_annealing_nt": row.required_annealing_nt,
                            "annealing_completion_nt": row.annealing_completion_nt,
                            "material_requirements": row.material_requirements,
                            "noncanonical_pairs": row.noncanonical_pairs,
                        }
                        for row in rows
                    ],
                },
                sort_keys=True,
            )
        )
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


def basal_panel_command(
    result: Path,
    realization_id: Annotated[str, typer.Option("--realization-id")],
) -> None:
    """Export a neutral molecular panel for one exact basal realization."""
    try:
        receipt = construction.load_verified_local_neighborhood(result)
        panel = construction.project_basal_source_panel(receipt, realization_id=realization_id)
        typer.echo(
            json.dumps(
                {
                    "schema": "hop/basal-panel-report/v1",
                    "source_result_id": receipt.result_id,
                    "realization_id": realization_id,
                    "panel": json.loads(panel),
                },
                sort_keys=True,
            )
        )
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
