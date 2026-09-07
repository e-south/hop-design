"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_local_neighborhood_public.py

Tests the file-oriented public seam for standalone local-neighborhood discovery.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import hop_design.construction as construction
from hop_design.design.construction import local_public
from hop_design.design.construction.foldback import discover_foldback_neighborhood
from hop_design.design.source_documents import SourceDocumentLimitError
from hop_design.models.construction import (
    ConstructionEndpoint,
    NeighborhoodDiscoveryResult,
    NeighborhoodProvenance,
)
from hop_design.models.construction.foldback import FoldbackNeighborhoodDiscoveryResult
from tests.contract.test_basal_construction_discovery import _request as basal_request
from tests.contract.test_foldback_construction_discovery import (
    _nickase,
    _terminus_enzyme,
)
from tests.contract.test_foldback_construction_discovery import (
    _request as foldback_request,
)


def _write_request(path: Path, request: object) -> Path:
    path.write_text(
        json.dumps(request.model_dump(mode="json", by_alias=True), sort_keys=True)  # type: ignore[attr-defined]
    )
    return path


@pytest.mark.parametrize(
    ("request_value", "expected_completion", "expected_feasibility"),
    (
        (foldback_request(_nickase(), _terminus_enzyme()), "complete", "feasible"),
        (
            foldback_request(_nickase(motif="GACA", cut_offset=4)),
            "complete",
            "infeasible",
        ),
        (
            foldback_request(
                _nickase(),
                _terminus_enzyme(),
                max_search_nodes=1,
                max_realizations=100,
            ),
            "truncated",
            "feasible",
        ),
    ),
)
def test_local_discovery_persists_truthful_completion_status(
    tmp_path: Path,
    request_value: object,
    expected_completion: str,
    expected_feasibility: str,
) -> None:
    source = _write_request(tmp_path / f"{expected_feasibility}.json", request_value)

    receipt = construction.discover_local_neighborhood(source)

    assert isinstance(receipt, construction.LocalNeighborhoodDiscovery)
    assert receipt.family == "foldback"
    assert receipt.completion == expected_completion
    assert receipt.feasibility == expected_feasibility
    assert receipt.result_id.startswith("hop:foldback-neighborhood-result/")
    assert receipt.json_bytes.endswith(b"\n")
    assert not hasattr(receipt, "request")
    assert not hasattr(receipt, "result")

    output = receipt.write(tmp_path / f"{expected_feasibility}-result")
    assert {item.name for item in output.iterdir()} == {"result.json"}
    loaded = construction.load_verified_local_neighborhood(output / "result.json")
    assert loaded.result_id == receipt.result_id
    assert loaded.completion == expected_completion
    assert loaded.feasibility == expected_feasibility
    assert loaded.json_bytes == receipt.json_bytes
    with pytest.raises(FileExistsError, match="Refusing to replace existing"):
        receipt.write(output)


def test_local_discovery_dispatches_basal_and_rejects_projection_family_mismatch(
    tmp_path: Path,
) -> None:
    source = _write_request(
        tmp_path / "basal.json",
        basal_request(ConstructionEndpoint.HAIRPIN_PCR_DUPLEX),
    )

    receipt = construction.discover_local_neighborhood(source)

    assert receipt.family == "basal"
    assert construction.project_basal_feasibility(receipt).source_result_id == receipt.result_id
    assert (
        construction.project_retained_overhead_frontier(receipt, family="basal").source_result_id
        == receipt.result_id
    )
    with pytest.raises(ValueError, match=r"contains basal.*not foldback"):
        construction.project_foldback_feasibility(receipt)
    with pytest.raises(ValueError, match=r"contains basal.*not foldback"):
        construction.project_retained_overhead_frontier(receipt, family="foldback")


def test_foldback_local_receipt_rejects_basal_projection(tmp_path: Path) -> None:
    source = _write_request(
        tmp_path / "foldback.json",
        foldback_request(_nickase(), _terminus_enzyme()),
    )
    receipt = construction.discover_local_neighborhood(source)

    assert construction.project_foldback_feasibility(receipt).source_result_id == receipt.result_id
    with pytest.raises(ValueError, match=r"contains foldback.*not basal"):
        construction.project_basal_feasibility(receipt)


def test_local_source_rejects_unknown_schema_and_fields(tmp_path: Path) -> None:
    request = foldback_request(_nickase(), _terminus_enzyme()).model_dump(
        mode="json", by_alias=True
    )
    request["schema"] = "hop.local-neighborhood-request/v2"
    source = tmp_path / "old-schema.json"
    source.write_text(json.dumps(request))

    with pytest.raises(ValueError, match="Unsupported HOP local-neighborhood schema"):
        construction.discover_local_neighborhood(source)

    request["schema"] = "hop.local-neighborhood-request/v4"
    request["unexpected"] = True
    source.write_text(json.dumps(request))
    with pytest.raises(ValueError, match="unexpected"):
        construction.discover_local_neighborhood(source)


@pytest.mark.parametrize("field", ("max_search_nodes", "max_realizations"))
def test_local_source_rejects_execution_bounds_above_the_public_envelope(
    tmp_path: Path,
    field: str,
) -> None:
    request = foldback_request(_nickase(), _terminus_enzyme()).model_dump(
        mode="json", by_alias=True
    )
    request["search"][field] = 100_001
    source = tmp_path / "oversized-execution.json"
    source.write_text(json.dumps(request))

    with pytest.raises(ValueError) as exc_info:
        construction.discover_local_neighborhood(source)

    message = str(exc_info.value)
    assert field in message
    assert "100000" in message


def test_local_result_loader_rejects_resealed_replay_forgery(tmp_path: Path) -> None:
    raw = discover_foldback_neighborhood(foldback_request(_nickase(), _terminus_enzyme()))
    forged_execution = raw.neighborhood.execution.model_copy(
        update={"hop_version": "forged-version"}
    )
    forged_neighborhood = NeighborhoodDiscoveryResult.model_validate(
        {
            **raw.neighborhood.model_dump(mode="python"),
            "execution": forged_execution,
            "execution_id": forged_execution.execution_id,
            "provenance": NeighborhoodProvenance(
                hop_version="forged-version",
                route_implementation_version=raw.neighborhood.provenance.route_implementation_version,
                enzyme_catalog_digest=raw.neighborhood.provenance.enzyme_catalog_digest,
            ),
        }
    )
    forged = FoldbackNeighborhoodDiscoveryResult.create(
        neighborhood=forged_neighborhood,
        realizations=raw.realizations,
    )
    result_path = tmp_path / "forged-result.json"
    result_path.write_text(
        json.dumps(forged.model_dump(mode="json", by_alias=True), sort_keys=True)
    )

    with pytest.raises(ValueError, match="deterministic discovery replay"):
        construction.load_verified_local_neighborhood(result_path)


@pytest.mark.parametrize("field", ("max_search_nodes", "max_realizations"))
def test_local_result_loader_rejects_execution_bounds_before_replay(
    tmp_path: Path,
    field: str,
) -> None:
    source = _write_request(
        tmp_path / "foldback.json",
        foldback_request(_nickase(), _terminus_enzyme()),
    )
    result = json.loads(construction.discover_local_neighborhood(source).json_bytes)
    result["neighborhood"]["request"]["search"][field] = 10**12
    result_path = tmp_path / "oversized-result.json"
    result_path.write_text(json.dumps(result))

    with pytest.raises(ValueError) as exc_info:
        construction.load_verified_local_neighborhood(result_path)

    message = str(exc_info.value)
    assert field in message
    assert "100000" in message


@pytest.mark.parametrize(
    ("nested_path", "replacement"),
    (
        (("neighborhood",), None),
        (("neighborhood", "request"), None),
        (("neighborhood", "request", "search"), None),
        (("neighborhood", "request", "search", "max_search_nodes"), True),
    ),
)
def test_local_result_loader_fails_closed_on_malformed_execution_envelopes(
    tmp_path: Path,
    nested_path: tuple[str, ...],
    replacement: object,
) -> None:
    source = _write_request(
        tmp_path / "foldback.json",
        foldback_request(_nickase(), _terminus_enzyme()),
    )
    result = json.loads(construction.discover_local_neighborhood(source).json_bytes)
    container = result
    for key in nested_path[:-1]:
        container = container[key]
    container[nested_path[-1]] = replacement
    result_path = tmp_path / "malformed-result.json"
    result_path.write_text(json.dumps(result))

    with pytest.raises(ValueError):
        construction.load_verified_local_neighborhood(result_path)


def test_local_result_loader_rejects_unknown_result_schema(tmp_path: Path) -> None:
    result_path = tmp_path / "result.json"
    result_path.write_text(json.dumps({"schema": "hop.neighborhood-result/unknown"}))

    with pytest.raises(ValueError, match="Unsupported HOP local-neighborhood result schema"):
        construction.load_verified_local_neighborhood(result_path)


def test_basal_local_result_uses_v4_and_rejects_v3_receipts(tmp_path: Path) -> None:
    source = _write_request(
        tmp_path / "basal.json",
        basal_request(
            ConstructionEndpoint.HAIRPIN_PCR_DUPLEX,
            max_nodes=1,
            max_realizations=1,
        ),
    )
    receipt = construction.discover_local_neighborhood(source)
    result = json.loads(receipt.json_bytes)

    assert result["schema"] == "hop.basal-neighborhood-result/v4"
    result_path = tmp_path / "basal-v4.json"
    result_path.write_bytes(receipt.json_bytes)
    loaded = construction.load_verified_local_neighborhood(result_path)
    assert loaded.family == "basal"
    assert loaded.problem_id == receipt.problem_id
    assert loaded.realization_count == receipt.realization_count

    result["schema"] = "hop.basal-neighborhood-result/v3"
    result_path = tmp_path / "basal-v3.json"
    result_path.write_text(json.dumps(result))
    with pytest.raises(ValueError, match="Unsupported HOP local-neighborhood result schema"):
        construction.load_verified_local_neighborhood(result_path)


def test_foldback_local_result_uses_v4_and_rejects_v3_receipts(tmp_path: Path) -> None:
    source = _write_request(
        tmp_path / "foldback.json",
        foldback_request(_nickase(), _terminus_enzyme()),
    )
    receipt = construction.discover_local_neighborhood(source)
    result = json.loads(receipt.json_bytes)

    assert result["schema"] == "hop.foldback-neighborhood-result/v4"

    result["schema"] = "hop.foldback-neighborhood-result/v3"
    result_path = tmp_path / "foldback-v3.json"
    result_path.write_text(json.dumps(result))
    with pytest.raises(ValueError, match="Unsupported HOP local-neighborhood result schema"):
        construction.load_verified_local_neighborhood(result_path)


def test_local_result_loader_accepts_generated_results_above_the_authored_source_limit(
    tmp_path: Path,
) -> None:
    source = _write_request(
        tmp_path / "foldback.json",
        foldback_request(_nickase(), _terminus_enzyme()),
    )
    receipt = construction.discover_local_neighborhood(source)
    result_path = tmp_path / "generated-result.json"
    result_path.write_bytes(receipt.json_bytes + b" " * 1_000_000)

    loaded = construction.load_verified_local_neighborhood(result_path)

    assert loaded.result_id == receipt.result_id
    assert loaded.json_bytes == receipt.json_bytes


def test_local_result_canonicalization_rejects_bytes_above_its_declared_envelope() -> None:
    result = discover_foldback_neighborhood(foldback_request(_nickase(), _terminus_enzyme()))

    with pytest.raises(SourceDocumentLimitError):
        local_public._canonical_local_result_bytes(result, max_bytes=1)

    with pytest.raises(ValueError, match="max_bytes must be at least 1"):
        local_public._canonical_local_result_bytes(result, max_bytes=0)
