"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_source_partition_projection.py

Tests the exact, publication-oriented source-partition certificate projection.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import csv
import io
import json

import pytest
from pydantic import ValidationError

import hop_design.construction as construction
from hop_design.models.construction import SearchCompletionStatus
from hop_design.models.construction.accounting import MethodResolutionStatus
from hop_design.models.construction.projections import SourcePartitionCertificateProjection
from tests.integration.test_source_partition_discovery import _request


def _receipt(tmp_path):
    source = tmp_path / "source-partition.json"
    source.write_text(
        json.dumps(_request().model_dump(mode="json", by_alias=True)),
        encoding="utf-8",
    )
    return construction.discover_source_partition(source)


def test_source_partition_projection_preserves_exact_certificate_and_boundaries(
    tmp_path,
) -> None:
    receipt = _receipt(tmp_path)

    projection = construction.project_source_partition_certificate(
        receipt,
        realization_id=receipt.realization_ids[0],
    )

    assert projection.schema_id == "hop.source-partition-certificate/v1"
    assert projection.source_result_id == receipt.result_id
    assert projection.renderer_version == "source-partition-certificate/1"
    content = json.loads(projection.json_bytes)
    assert content["realization_id"] == receipt.realization_ids[0]
    assert content["certificate"]["selected_maximum_sacrificial_fragment_nt"] == 12
    assert len(content["certificate"]["fragments"]) == 6

    rows = tuple(csv.DictReader(io.StringIO(projection.csv_bytes.decode("utf-8"))))
    assert len(rows) == 6
    assert {row["disposition"] for row in rows} == {"required", "sacrificial"}
    assert {row["selected_maximum_sacrificial_fragment_nt"] for row in rows} == {"12"}

    svg = projection.svg_bytes.decode("utf-8")
    assert "One program accounts for every source fragment" in svg
    assert "Required fragment" in svg
    assert "Sacrificial fragment" in svg
    assert "5&#x2032;" in svg and "3&#x2032;" in svg
    assert "12 nt" in svg
    assert "3 of 3 enzyme programs examined" in svg
    assert "declared cut geometry" in svg
    assert f'data-result-id="{receipt.result_id}"' in svg
    assert f'data-realization-id="{receipt.realization_ids[0]}"' in svg
    assert "physical cleavage and recovery are not established" in svg


def test_source_partition_projection_requires_an_accepted_realization(tmp_path) -> None:
    receipt = _receipt(tmp_path)

    with pytest.raises(ValueError, match="not present in the verified source partition"):
        construction.project_source_partition_certificate(
            receipt,
            realization_id=f"hop:source-partition-realization/{'0' * 64}@1",
        )


def test_source_partition_projection_writes_one_portable_vector_packet(tmp_path) -> None:
    receipt = _receipt(tmp_path)
    projection = construction.project_source_partition_certificate(
        receipt,
        realization_id=receipt.realization_ids[0],
    )

    output = projection.write(tmp_path / "projection")

    assert {path.name for path in output.iterdir()} == {
        "projection.csv",
        "projection.json",
        "projection.svg",
    }


def test_source_partition_projection_rejects_forged_scope_and_identity(tmp_path) -> None:
    receipt = _receipt(tmp_path)
    projection = construction.project_source_partition_certificate(
        receipt,
        realization_id=receipt.realization_ids[0],
    )
    typed_projection = SourcePartitionCertificateProjection.model_validate_json(
        projection.json_bytes
    )
    mapping = typed_projection.model_dump(mode="python", by_alias=True)

    for update, message in (
        (
            {"status": SearchCompletionStatus.INFEASIBLE},
            "infeasible partition result cannot have",
        ),
        (
            {"examined_nodes": typed_projection.candidate_space_size + 1},
            "cannot exceed the candidate space",
        ),
        (
            {"enzyme_ids": tuple(reversed(typed_projection.enzyme_ids))},
            "must be unique and canonical",
        ),
        (
            {"enzyme_ids": typed_projection.enzyme_ids[:1]},
            "must equal the fragment-boundary causes",
        ),
        (
            {
                "claim_boundary": typed_projection.claim_boundary.model_copy(
                    update={"method": MethodResolutionStatus.RESOLVED}
                )
            },
            "claim boundaries are fixed",
        ),
        (
            {"projection_id": f"hop:projection/{'0' * 64}@1"},
            "identity must replay exact content",
        ),
    ):
        with pytest.raises(ValidationError, match=message):
            SourcePartitionCertificateProjection.model_validate({**mapping, **update})
