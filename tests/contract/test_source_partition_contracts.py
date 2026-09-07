"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_source_partition_contracts.py

Tests source-partition identity, validation, and replay-hardening contracts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import hop_design.construction as construction
from hop_design.design.construction.source_partition import discover_source_partitions
from hop_design.models.construction import SearchCompletionStatus
from hop_design.models.construction.source_partition import (
    SourcePartitionDiscoveryResult,
    SourcePartitionDispositionKind,
    SourcePartitionFailure,
    SourcePartitionTruncationReason,
)
from hop_design.models.construction.source_partition.replay import (
    replay_source_partition_candidate,
)
from hop_design.models.construction.source_partition.result import (
    source_partition_realization_id,
)
from hop_design.models.enzymes import VendorMetadata
from hop_design.serialization import canonical_json_bytes
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

    forged_certificate = realization.fragment_certificate.model_copy(
        update={"selected_maximum_sacrificial_fragment_nt": 13}
    )
    forged_realization = realization.model_copy(update={"fragment_certificate": forged_certificate})
    forged = result.model_copy(update={"realizations": (forged_realization,)})
    with pytest.raises(
        ValidationError,
        match="Selected fragment threshold must be the least permissive success",
    ):
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


def test_disposition_contract_rejects_noncanonical_and_incoherent_states() -> None:
    result = discover_source_partitions(_request())
    rejected = result.dispositions[0]
    accepted = result.dispositions[-1]

    with pytest.raises(ValidationError, match="enzyme ids must be unique and canonical"):
        rejected.__class__.model_validate(
            rejected.model_copy(update={"enzyme_ids": rejected.enzyme_ids * 2}).model_dump(
                mode="python"
            )
        )
    with pytest.raises(ValidationError, match="failure codes must be unique and canonical"):
        rejected.__class__.model_validate(
            rejected.model_copy(update={"failure_codes": rejected.failure_codes * 2}).model_dump(
                mode="python"
            )
        )
    with pytest.raises(ValidationError, match="accepted source partition requires"):
        accepted.__class__.model_validate(
            accepted.model_copy(update={"failure_codes": rejected.failure_codes}).model_dump(
                mode="python"
            )
        )
    with pytest.raises(ValidationError, match="rejected source partition requires"):
        rejected.__class__.model_validate(
            rejected.model_copy(update={"failure_codes": ()}).model_dump(mode="python")
        )


def test_result_contract_rejects_authority_inventory_and_replay_forgeries() -> None:
    result = discover_source_partitions(_request())
    rejected = result.dispositions[0]
    accepted = result.dispositions[-1]
    realization = result.realizations[0]
    forged_id = "hop:source-partition-realization/" + "0" * 64 + "@1"

    for forged, message in (
        (
            result.model_copy(
                update={"problem_id": "hop:source-partition-problem/" + "0" * 64 + "@1"}
            ),
            "bind the exact request identities",
        ),
        (
            result.model_copy(update={"candidate_space_size": result.candidate_space_size + 1}),
            "candidate-space size must replay exactly",
        ),
        (
            result.model_copy(update={"examined_nodes": result.examined_nodes - 1}),
            "nodes must equal recorded dispositions",
        ),
        (
            result.model_copy(
                update={"dispositions": (result.dispositions[1], result.dispositions[0], accepted)}
            ),
            "canonical search prefix",
        ),
        (
            result.model_copy(update={"realizations": (realization, realization)}),
            "realization ids must be unique",
        ),
        (
            result.model_copy(update={"realizations": ()}),
            "bind every realization",
        ),
        (
            result.model_copy(
                update={
                    "dispositions": (
                        rejected.model_copy(
                            update={
                                "candidate_id": "hop:source-partition-candidate/" + "0" * 64 + "@1"
                            }
                        ),
                        *result.dispositions[1:],
                    )
                }
            ),
            "candidate identity must replay exactly",
        ),
        (
            result.model_copy(
                update={
                    "dispositions": (
                        rejected.model_copy(
                            update={
                                "failure_codes": (
                                    SourcePartitionFailure.NONPARTITIONING_TERMINAL_CUT,
                                )
                            }
                        ),
                        *result.dispositions[1:],
                    )
                }
            ),
            "Rejected source-partition evidence must replay exactly",
        ),
        (
            result.model_copy(
                update={
                    "dispositions": (
                        *result.dispositions[:-1],
                        accepted.model_copy(
                            update={
                                "disposition": SourcePartitionDispositionKind.REJECTED,
                                "failure_codes": (
                                    SourcePartitionFailure.RETAINED_FRAGMENT_SET_MISMATCH,
                                ),
                                "realization_id": None,
                            }
                        ),
                    ),
                    "realizations": (),
                }
            ),
            "replayable source partition must be accepted",
        ),
        (
            result.model_copy(
                update={
                    "dispositions": (
                        *result.dispositions[:-1],
                        accepted.model_copy(update={"realization_id": forged_id}),
                    ),
                    "realizations": (realization.model_copy(update={"realization_id": forged_id}),),
                }
            ),
            "realization identity must replay exactly",
        ),
        (
            result.model_copy(update={"status": SearchCompletionStatus.INFEASIBLE}),
            "completion status must follow exact search accounting",
        ),
        (
            result.model_copy(
                update={"result_id": "hop:source-partition-result/" + "0" * 64 + "@1"}
            ),
            "result identity must replay exact result content",
        ),
    ):
        with pytest.raises(ValidationError, match=message):
            _revalidate(forged)


def test_realization_identity_rejects_a_failed_candidate_replay() -> None:
    request = _request()
    failed = replay_source_partition_candidate(
        request,
        enzyme_ids=("example:enzyme/bottom-repeat@1",),
    )

    with pytest.raises(ValueError, match="Only an accepted source partition"):
        source_partition_realization_id(request, failed)


def test_public_loader_rejects_unsupported_schema_and_symlink(tmp_path: Path) -> None:
    source = tmp_path / "request.json"
    mapping = _request().model_dump(mode="json", by_alias=True)
    mapping["schema"] = "hop.source-partition-request/v1"
    source.write_text(json.dumps(mapping))
    with pytest.raises(ValueError, match="Unsupported HOP source-partition schema"):
        construction.discover_source_partition(source)

    target = tmp_path / "target.json"
    target.write_text(json.dumps(_request().model_dump(mode="json", by_alias=True)))
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="must not be a symlink"):
        construction.discover_source_partition(link)


def test_public_result_loader_rejects_schema_symlink_and_resealed_forgery(
    tmp_path: Path,
) -> None:
    result = discover_source_partitions(_request())
    mapping = result.model_dump(mode="json", by_alias=True)

    unsupported = tmp_path / "unsupported-result.json"
    unsupported.write_text(json.dumps({**mapping, "schema": "hop.source-partition-result/v1"}))
    with pytest.raises(ValueError, match="Unsupported HOP source-partition result schema"):
        construction.load_verified_source_partition(unsupported)

    valid = tmp_path / "valid-result.json"
    valid.write_text(json.dumps(mapping))
    link = tmp_path / "result-link.json"
    link.symlink_to(valid)
    with pytest.raises(ValueError, match="must not be a symlink"):
        construction.load_verified_source_partition(link)

    mapping["result_id"] = "hop:source-partition-result/" + "0" * 64 + "@1"
    forged = tmp_path / "forged-result.json"
    forged.write_text(json.dumps(mapping))
    with pytest.raises(ValidationError, match="result identity must replay exact result content"):
        construction.load_verified_source_partition(forged)


def test_opaque_receipt_exposes_only_revalidated_source_authority(tmp_path: Path) -> None:
    result = discover_source_partitions(_request())
    result_path = tmp_path / "result.json"
    result_path.write_bytes(canonical_json_bytes(result))

    receipt = construction.load_verified_source_partition(result_path)

    assert canonical_json_bytes(receipt._verified_source()) == canonical_json_bytes(result)


def test_public_receipt_writes_tidy_fragment_and_threshold_certificates(
    tmp_path: Path,
) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(_request().model_dump(mode="json", by_alias=True)),
        encoding="utf-8",
    )

    receipt = construction.discover_source_partition(request_path)
    output = receipt.write(tmp_path / "partition")

    assert {path.name for path in output.iterdir()} == {
        "data.csv",
        "fragments.csv",
        "result.json",
        "thresholds.csv",
    }
    with (output / "fragments.csv").open(newline="", encoding="utf-8") as handle:
        fragments = tuple(csv.DictReader(handle))
    assert len(fragments) == 6
    assert {
        (
            row["strand"],
            row["source_start"],
            row["source_end"],
            row["length_nt"],
            row["disposition"],
        )
        for row in fragments
    } == {
        ("top", "0", "58", "58", "required"),
        ("top", "58", "70", "12", "sacrificial"),
        ("bottom", "0", "11", "11", "sacrificial"),
        ("bottom", "11", "23", "12", "sacrificial"),
        ("bottom", "23", "35", "12", "sacrificial"),
        ("bottom", "35", "70", "35", "required"),
    }
    with (output / "thresholds.csv").open(newline="", encoding="utf-8") as handle:
        thresholds = tuple(csv.DictReader(handle))
    assert tuple(
        (row["maximum_sacrificial_fragment_nt"], row["feasible"]) for row in thresholds
    ) == (
        ("11", "false"),
        ("12", "true"),
        ("13", "true"),
        ("14", "true"),
        ("15", "true"),
    )


def test_opaque_receipt_rejects_content_that_disagrees_with_canonical_bytes(
    tmp_path: Path,
) -> None:
    result = discover_source_partitions(_request())
    result_path = tmp_path / "result.json"
    result_path.write_bytes(canonical_json_bytes(result))
    receipt = construction.load_verified_source_partition(result_path)
    object.__setattr__(
        receipt,
        "_result",
        result.model_copy(update={"examined_nodes": result.examined_nodes + 1}),
    )

    with pytest.raises(ValueError, match="receipt content disagrees with its authority"):
        receipt._verified_source()
