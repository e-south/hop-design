"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_source_partition_contracts.py

Tests source-partition identity, validation, and replay-hardening contracts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import hop_design.construction as construction
from hop_design.design.construction.source_partition import discover_source_partitions
from hop_design.models.construction.source_partition import (
    SourcePartitionDiscoveryResult,
    SourcePartitionTruncationReason,
)
from hop_design.models.enzymes import VendorMetadata
from tests.integration.test_source_partition_discovery import _request


def _revalidate(result: SourcePartitionDiscoveryResult) -> SourcePartitionDiscoveryResult:
    return SourcePartitionDiscoveryResult.model_validate(
        result.model_dump(mode="python", by_alias=True)
    )


def test_identity_excludes_display_procurement_and_execution_metadata() -> None:
    request = _request()
    renamed = request.model_copy(
        update={
            "payload": request.payload.model_copy(update={"display_name": "another label"}),
        }
    )
    enzyme = request.enzyme_provisioning.catalog.enzymes[0]
    vendor_changed = request.model_copy(
        update={
            "enzyme_provisioning": request.enzyme_provisioning.model_copy(
                update={
                    "catalog": request.enzyme_provisioning.catalog.model_copy(
                        update={
                            "enzymes": (
                                enzyme.model_copy(
                                    update={
                                        "vendor_metadata": (
                                            VendorMetadata(vendor_name="Another supplier"),
                                        )
                                    }
                                ),
                                request.enzyme_provisioning.catalog.enzymes[1],
                            )
                        }
                    )
                }
            )
        }
    )
    bounded = request.model_copy(
        update={"enumeration": request.enumeration.model_copy(update={"max_search_nodes": 2})}
    )

    assert renamed.problem_id == request.problem_id
    assert renamed.request_id == request.request_id
    assert vendor_changed.problem_id == request.problem_id
    assert vendor_changed.request_id == request.request_id
    assert bounded.problem_id == request.problem_id
    assert bounded.request_id != request.request_id


def test_problem_identity_treats_provisioning_collections_as_sets() -> None:
    request = _request()
    mapping = request.model_dump(mode="python", by_alias=True)
    provisioning = mapping["enzyme_provisioning"]
    provisioning["catalog"]["enzymes"] = tuple(reversed(provisioning["catalog"]["enzymes"]))
    provisioning["allowed_enzyme_ids"] = tuple(reversed(provisioning["allowed_enzyme_ids"]))
    provisioning["role_restrictions"][0]["allowed_enzyme_ids"] = tuple(
        reversed(provisioning["role_restrictions"][0]["allowed_enzyme_ids"])
    )
    reordered = request.__class__.model_validate(mapping)

    assert reordered.problem_id == request.problem_id
    assert reordered.request_id == request.request_id


def test_problem_identity_uses_effective_strand_exposure_domain() -> None:
    request = _request()
    mapping = request.model_dump(mode="python", by_alias=True)
    mapping["enzyme_provisioning"]["allowed_enzyme_ids"] = ()
    implicit_all = request.__class__.model_validate(mapping)

    assert implicit_all.candidate_enzyme_ids == request.candidate_enzyme_ids
    assert implicit_all.problem_id == request.problem_id
    assert implicit_all.request_id != request.request_id


def test_request_rejects_source_payload_and_survivor_mismatches() -> None:
    request = _request()
    mapping = request.model_dump(mode="python", by_alias=True)
    mapping["payload_source_map"]["segments"][0]["source_material_id"] = "another-source"
    with pytest.raises(ValidationError, match="must reference the supplied source duplex"):
        request.__class__.model_validate(mapping)

    mapping = request.model_dump(mode="python", by_alias=True)
    mapping["constraints"]["required_survivors"][0]["source_span"]["end"]["offset"] = 71
    with pytest.raises(ValidationError, match="must stay inside the source duplex"):
        request.__class__.model_validate(mapping)

    mapping = request.model_dump(mode="python", by_alias=True)
    mapping["constraints"]["max_enzymes_per_program"] = 3
    with pytest.raises(ValidationError, match="must not exceed the provisioned nickase count"):
        request.__class__.model_validate(mapping)

    mapping = request.model_dump(mode="python", by_alias=True)
    mapping["constraints"]["required_survivors"][1]["source_span"] = {
        "start": {"offset": 36},
        "end": {"offset": 50},
    }
    with pytest.raises(ValidationError, match="payload source span must be retained"):
        request.__class__.model_validate(mapping)


def test_result_rejects_forged_fragment_selection_and_nick_function() -> None:
    result = discover_source_partitions(_request())
    realization = result.realizations[0]
    forged_selection = realization.selected.model_copy(
        update={"retained_fragment_ids": ("top-0-70", "bottom-35-70")}
    )
    forged_realization = realization.model_copy(update={"selected": forged_selection})
    forged = result.model_copy(update={"realizations": (forged_realization,)})
    with pytest.raises(ValidationError, match="realization states must replay exactly"):
        _revalidate(forged)

    function = realization.nick_functions[0]
    forged_function = function.model_copy(
        update={"function": realization.nick_functions[-1].function}
    )
    forged_realization = realization.model_copy(
        update={"nick_functions": (forged_function, *realization.nick_functions[1:])}
    )
    forged = result.model_copy(update={"realizations": (forged_realization,)})
    with pytest.raises(ValidationError, match="realization states must replay exactly"):
        _revalidate(forged)


def test_result_rejects_inexact_truncation_reason() -> None:
    result = discover_source_partitions(_request(max_search_nodes=2))
    forged = result.model_copy(
        update={"truncation_reasons": (SourcePartitionTruncationReason.MAX_REALIZATIONS,)}
    )

    with pytest.raises(ValidationError, match="truncation reasons must replay exactly"):
        _revalidate(forged)


def test_public_loader_rejects_unsupported_schema_and_symlink(tmp_path: Path) -> None:
    source = tmp_path / "request.json"
    mapping = _request().model_dump(mode="json", by_alias=True)
    mapping["schema"] = "hop.source-partition-request/v2"
    source.write_text(json.dumps(mapping))
    with pytest.raises(ValueError, match="Unsupported HOP source-partition schema"):
        construction.discover_source_partition(source)

    target = tmp_path / "target.json"
    target.write_text(json.dumps(_request().model_dump(mode="json", by_alias=True)))
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="must not be a symlink"):
        construction.discover_source_partition(link)
