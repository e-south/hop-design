"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_construction_partition_search.py

Tests source-removal searches derived from a selected complete construction.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

import hop_design as hop
import hop_design.construction as construction
from hop_design.cli import app
from hop_design.design.construction.source_partition import public as partition_public
from hop_design.design.source_documents import SourceDocumentLimitError
from hop_design.serialization import canonical_json_bytes
from tests.integration.test_construction_cli import _write_bundle
from tests.integration.test_source_partition_discovery import _request as partition_request


def test_partition_result_above_authored_source_limit_replays_exactly(tmp_path: Path) -> None:
    source = tmp_path / "request.json"
    source.write_bytes(canonical_json_bytes(partition_request(absolute_maximum_nt=10_000)))
    assert source.stat().st_size < 1_000_000
    receipt = construction.discover_source_partition(source)
    output = receipt.write(tmp_path / "result")
    assert (output / "result.json").stat().st_size > 1_000_000
    loaded = construction.load_verified_source_partition(output / "result.json")
    assert loaded.json_bytes == receipt.json_bytes
    assert loaded.csv_bytes == receipt.csv_bytes
    assert loaded.result_id == receipt.result_id


def test_partition_request_retains_authored_source_limit(tmp_path: Path) -> None:
    source = tmp_path / "request.json"
    source.write_bytes(canonical_json_bytes(partition_request()) + b" " * 1_000_000)
    with pytest.raises(SourceDocumentLimitError):
        construction.discover_source_partition(source)


def test_partition_result_limit_applies_before_publication_and_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "request.json"
    source.write_bytes(canonical_json_bytes(partition_request()))
    receipt = construction.discover_source_partition(source)
    existing = receipt.write(tmp_path / "existing") / "result.json"
    monkeypatch.setattr(partition_public, "DEFAULT_RESULT_MAX_BYTES", 1, raising=False)
    output = tmp_path / "oversized"
    result = CliRunner().invoke(
        app, ["construction", "discover-partition", str(source), "--out", str(output)]
    )
    assert result.exit_code != 0
    assert result.stdout == ""
    assert "max_bytes exceeded" in " ".join(result.output.split())
    assert not output.exists()
    with pytest.raises(SourceDocumentLimitError):
        construction.load_verified_source_partition(existing)


@pytest.fixture(scope="module")
def constructed_source(tmp_path_factory):
    root = tmp_path_factory.mktemp("constructed-source")
    examples = Path(__file__).parents[2] / "examples"
    payload = "GACAGACAGACAGACAGACA"
    design = yaml.safe_load((examples / "construction-exact-design.yaml").read_text())
    design["payload"]["sequence"] = payload
    design_path = root / "design.json"
    design_path.write_text(json.dumps(design))
    design_bundle = hop.compile(hop.load_spec(design_path)).write(root / "design")
    source = yaml.safe_load((examples / "construction-exact.yaml").read_text())
    source["foldback"]["payload"]["payload"]["sequence"] = payload
    source["foldback"]["payload"]["foldback_boundary"]["offset"] = len(payload)
    source_path = root / "source.json"
    source_path.write_text(json.dumps(source))
    receipt = construction.compile_construction(source_path, design_bundle_path=design_bundle)
    policy = source["foldback"]["enzyme_provisioning"]
    nickase_id = policy["allowed_enzyme_ids"][0]
    policy["allowed_enzyme_ids"] = [nickase_id]
    policy["role_restrictions"] = [{"role": "strand_exposure", "allowed_enzyme_ids": [nickase_id]}]
    search = {
        "schema": "hop.source-partition-policy/v1",
        "enzyme_provisioning": policy,
        "fragment_policy": {"preferred_maximum_nt": 11, "absolute_maximum_nt": 11},
        "max_enzymes_per_program": 1,
        "enumeration": {"max_search_nodes": 1, "max_realizations": 1},
    }
    return receipt, search


def test_partition_command_keeps_outputs_outside_its_verified_bundle(
    tmp_path: Path, constructed_source
) -> None:
    _, policy = constructed_source
    bundle, _ = _write_bundle(tmp_path / "case")
    receipt = construction.load_verified_construction_bundle(bundle)
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy))
    arguments = [
        "construction",
        "discover-construction-partition",
        str(bundle),
        str(policy_path),
        "--combination-ordinal",
        "0",
        "--out",
    ]
    control = CliRunner().invoke(app, [*arguments, str(tmp_path / "partition")])
    assert control.exit_code == 0, control.output
    output = bundle / "partition"
    result = CliRunner().invoke(
        app,
        [*arguments, str(output)],
    )
    assert result.exit_code != 0, result.output
    assert "outside the verified" in " ".join(result.output.split())
    assert not output.exists()
    assert construction.load_verified_construction_bundle(bundle).bundle_id == receipt.bundle_id


def test_partition_command_rejects_parent_redirected_after_cli_check(
    tmp_path: Path, constructed_source, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, policy = constructed_source
    bundle, _ = _write_bundle(tmp_path / "case")
    bundle_id = construction.load_verified_construction_bundle(bundle).bundle_id
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy))
    parent = tmp_path / "exports"
    parent.mkdir()
    original = construction.discover_construction_source_partition

    def redirect_after_discovery(*args, **kwargs):
        receipt = original(*args, **kwargs)
        parent.rename(tmp_path / "original-exports")
        parent.symlink_to(bundle, target_is_directory=True)
        return receipt

    monkeypatch.setattr(
        construction, "discover_construction_source_partition", redirect_after_discovery
    )
    result = CliRunner().invoke(
        app,
        [
            "construction",
            "discover-construction-partition",
            str(bundle),
            str(policy_path),
            "--combination-ordinal",
            "0",
            "--out",
            str(parent / "partition"),
        ],
    )
    assert result.exit_code != 0, result.output
    assert result.stdout == ""
    assert not (bundle / "partition").exists()
    assert construction.load_verified_construction_bundle(bundle).bundle_id == bundle_id


def test_partition_search_uses_the_selected_prepared_source_and_survivors(
    tmp_path: Path, constructed_source
) -> None:
    receipt, search = constructed_source
    policy_path = tmp_path / "partition-policy.json"
    policy_path.write_text(json.dumps(search))
    result_id = receipt.result_id
    selected_id = receipt.materialized_realization_ids[0]

    partition = construction.discover_construction_source_partition(
        receipt, policy_path, materialized_realization_id=selected_id
    )

    result = json.loads(partition.json_bytes)
    request = result["request"]
    # The example design contributes a four-base basal arm before the payload.
    assert request["source"]["top_sequence_5prime"] == (
        "AAAA" + "GACAGACAGACAGACAGACA" + "TCAGATGCTGA"
    )
    assert request["payload_source_map"]["segments"][0]["source_span"] == {
        "start": {"offset": 4},
        "end": {"offset": 24},
    }
    survivors = {
        (
            item["precursor_strand"],
            item["source_span"]["start"]["offset"],
            item["source_span"]["end"]["offset"],
        )
        for item in request["constraints"]["required_survivors"]
    }
    assert survivors == {("top", 0, 24), ("bottom", 0, 35)}
    assert request["source"]["top_five_prime_end"] == "hydroxyl"
    assert request["source"]["bottom_five_prime_end"] == "phosphate"
    assert request["source"]["top_three_prime_end"] == "hydroxyl"
    assert request["source"]["bottom_three_prime_end"] == "hydroxyl"
    assert partition.status == "complete"
    assert partition.accepted_realizations == 1
    assert receipt.result_id == result_id
    assert receipt.materialized_realization_ids[0] == selected_id


def test_removal_rule_does_not_adapt_itself_to_the_source(
    tmp_path: Path, constructed_source
) -> None:
    receipt, search = constructed_source
    policy = deepcopy(search)
    policy["fragment_policy"] = {"preferred_maximum_nt": 10, "absolute_maximum_nt": 10}
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy))

    partition = construction.discover_construction_source_partition(
        receipt, path, materialized_realization_id=receipt.materialized_realization_ids[0]
    )

    assert partition.status == "infeasible"
    assert partition.examined_nodes == 1
    assert partition.accepted_realizations == 0
    assert (
        json.loads(partition.json_bytes)["request"]["constraints"]["fragment_policy"]
        == (policy["fragment_policy"])
    )


@pytest.mark.parametrize("override", ["source", "payload", "required_survivors"])
def test_partition_policy_cannot_override_derived_molecular_facts(
    tmp_path: Path, constructed_source, override: str
) -> None:
    receipt, search = constructed_source
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(search | {override: {}}))

    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        construction.discover_construction_source_partition(
            receipt, path, materialized_realization_id=receipt.materialized_realization_ids[0]
        )


def test_partition_search_requires_an_explicit_accepted_selection(
    tmp_path: Path, constructed_source
) -> None:
    receipt, _ = constructed_source
    path = tmp_path / "policy.json"
    with pytest.raises(TypeError, match="verified construction receipt"):
        construction.discover_construction_source_partition(
            object(),
            path,
            materialized_realization_id="not-a-route",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="not an accepted construction realization"):
        construction.discover_construction_source_partition(
            receipt, path, materialized_realization_id="not-a-route"
        )


@pytest.mark.parametrize("ordinal", [-1, "past_end", True, "0"])
def test_partition_search_cannot_select_an_unexamined_combination(
    tmp_path: Path, constructed_source, ordinal
) -> None:
    receipt, _ = constructed_source
    if ordinal == "past_end":
        ordinal = receipt.examined_combinations
    with pytest.raises(ValueError, match="examined combination ordinal"):
        construction.discover_construction_source_partition(
            receipt, tmp_path / "absent.json", combination_ordinal=ordinal
        )


def test_partition_search_requires_exactly_one_selection(
    tmp_path: Path, constructed_source
) -> None:
    receipt, _ = constructed_source
    with pytest.raises(ValueError, match="exactly one"):
        construction.discover_construction_source_partition(receipt, tmp_path / "absent.json")
    with pytest.raises(ValueError, match="exactly one"):
        construction.discover_construction_source_partition(
            receipt,
            tmp_path / "absent.json",
            materialized_realization_id=receipt.materialized_realization_ids[0],
            combination_ordinal=0,
        )


def test_combination_selection_does_not_invent_a_pcr_endpoint(
    tmp_path: Path, constructed_source
) -> None:
    receipt, _ = constructed_source
    with pytest.raises(ValueError, match="PCR-bearing endpoint"):
        construction.discover_construction_source_partition(
            receipt, tmp_path / "absent.json", combination_ordinal=0
        )


@pytest.mark.parametrize("schema", [None, "hop.source-partition-request/v2"])
def test_partition_policy_requires_its_declared_schema(
    tmp_path: Path, constructed_source, schema: str | None
) -> None:
    receipt, search = constructed_source
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(search | {"schema": schema}))
    with pytest.raises(ValueError, match="Unsupported HOP source-partition policy schema"):
        construction.discover_construction_source_partition(
            receipt, path, materialized_realization_id=receipt.materialized_realization_ids[0]
        )


def test_partition_search_is_identical_after_portable_construction_replay(
    tmp_path: Path, constructed_source
) -> None:
    receipt, search = constructed_source
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(search))
    loaded = construction.load_verified_construction_bundle(receipt.write(tmp_path / "route"))
    selected_id = receipt.materialized_realization_ids[0]

    original = construction.discover_construction_source_partition(
        receipt, path, materialized_realization_id=selected_id
    )
    transferred = construction.discover_construction_source_partition(
        loaded, path, materialized_realization_id=selected_id
    )
    reloaded = construction.load_verified_source_partition(
        transferred.write(tmp_path / "partition") / "result.json"
    )

    assert original.json_bytes == transferred.json_bytes == reloaded.json_bytes
    assert original.csv_bytes == transferred.csv_bytes == reloaded.csv_bytes


def test_unexamined_enzyme_alternatives_remain_truncated(
    tmp_path: Path, constructed_source
) -> None:
    receipt, search = constructed_source
    policy = deepcopy(search)
    enzymes = policy["enzyme_provisioning"]["catalog"]["enzymes"]
    absent = deepcopy(enzymes[0])
    absent.update(
        {
            "enzyme_id": "example:enzyme/absent-site@1",
            "canonical_name": "absent-site",
            "recognition_pattern": "CCCC",
            "recognition_length": 4,
        }
    )
    enzymes.append(absent)
    ids = policy["enzyme_provisioning"]["allowed_enzyme_ids"]
    ids.append(absent["enzyme_id"])
    policy["enzyme_provisioning"]["role_restrictions"][0]["allowed_enzyme_ids"] = ids
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(policy))

    partition = construction.discover_construction_source_partition(
        receipt, path, materialized_realization_id=receipt.materialized_realization_ids[0]
    )

    assert partition.candidate_space_size == 2
    assert partition.examined_nodes == 1
    assert partition.status == "truncated"
    assert partition.accepted_realizations == 0
