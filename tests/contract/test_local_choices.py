"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_local_choices.py

Checks local choice inspection against public loxP junction discoveries.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

from hop_design import construction


@pytest.fixture(scope="module")
def basal(tmp_path_factory: pytest.TempPathFactory) -> construction.LocalNeighborhoodDiscovery:
    source = Path(__file__).parents[2] / "examples/basal-junction/request.yaml"
    request = yaml.safe_load(source.read_text())
    for pair in request["geometry_domain"]["pairing_constraints"][1:]:
        pair["allowed_class"] = "any"
    request["geometry_domain"]["max_noncanonical_pairs"] = 2
    path = tmp_path_factory.mktemp("local-choices") / "request.json"
    path.write_text(json.dumps(request))
    return construction.discover_local_neighborhood(path)


def test_local_choices_expose_compilable_id_and_unfinished_materials(basal) -> None:
    before = basal.json_bytes
    choices = construction.list_local_realizations(basal, cohesive_end="ATAA")
    assert choices
    assert {item.cohesive_end for item in choices} == {"ATAA"}
    assert {item.noncanonical_pairs for item in choices} == {2}
    assert {item.annealing_completion_nt for item in choices} == {11}
    exact = json.loads(before)["realizations"]
    assert {item.realization_id for item in choices} <= {
        item["basal_realization_id"] for item in exact
    }
    assert all(item.source_result_id == basal.result_id for item in choices)
    assert all(item.geometry.family == "basal" for item in choices)
    assert basal.json_bytes == before
    with pytest.raises(FrozenInstanceError):
        choices[0].retained_overhead_nt = 0


def test_basal_choices_include_the_required_future_release_enzyme(basal) -> None:
    before = basal.json_bytes
    choices = construction.list_local_realizations(basal, cohesive_end="ATAA")
    assert choices
    assert all(row.enzyme_count == 2 for row in choices)
    assert all(row.enzyme_ids == ("enzyme:bbsi@1", "enzyme:nt-bsmai@1") for row in choices)
    assert basal.json_bytes == before


def test_local_choices_preserve_ties_and_explicit_lexicographic_preferences(basal) -> None:
    choices = construction.list_local_realizations(basal)
    assert len(choices) == basal.realization_count
    assert len({item.realization_id for item in choices}) == len(choices)
    ordered = construction.list_local_realizations(
        basal, sort_by=("noncanonical_pairs", "retained_overhead_nt")
    )
    assert ordered == tuple(
        sorted(choices, key=lambda row: (row.noncanonical_pairs, row.retained_overhead_nt))
    )
    assert {row.realization_id for row in ordered} == {row.realization_id for row in choices}
    matches = construction.list_local_realizations(basal, max_noncanonical_pairs=0)
    assert {row.cohesive_end for row in matches} == {"CTCA", "CTCC", "CTCG", "CTCT"}
    assert construction.list_local_realizations(basal, max_retained_overhead_nt=3) == ()


@pytest.mark.parametrize(
    "options",
    [
        {"sort_by": ("efficiency",)},
        {"sort_by": ("enzyme_count", "enzyme_count")},
        {"max_retained_overhead_nt": -1},
        {"max_noncanonical_pairs": True},
        {"cohesive_end": "NNNN"},
    ],
)
def test_local_choices_reject_ambiguous_or_invalid_preferences(basal, options) -> None:
    with pytest.raises(ValueError):
        construction.list_local_realizations(basal, **options)


def test_foldback_choices_preserve_geometry_and_reject_basal_filters() -> None:
    source = Path(__file__).parents[2] / "examples/foldback-local-partition.yaml"
    receipt = construction.discover_local_neighborhood(source)
    choices = construction.list_local_realizations(receipt, sort_by=("enzyme_count",))
    assert choices
    assert all(row.geometry.family == "foldback" for row in choices)
    assert all(row.realization_id.startswith("hop:foldback-realization/") for row in choices)
    assert all(row.noncanonical_pairs is None for row in choices)
    assert all(row.cohesive_end is None for row in choices)
    assert len(choices) == receipt.realization_count
    with pytest.raises(ValueError, match="basal"):
        construction.list_local_realizations(receipt, max_noncanonical_pairs=0)
    with pytest.raises(ValueError, match="basal"):
        construction.list_local_realizations(receipt, sort_by=("noncanonical_pairs",))


def test_local_listing_keeps_incomplete_coverage_and_rejects_unverified_input(tmp_path) -> None:
    source = Path(__file__).parents[2] / "examples/basal-junction/request.yaml"
    request = yaml.safe_load(source.read_text())
    request["search"]["max_search_nodes"] = 1
    path = tmp_path / "limited.json"
    path.write_text(json.dumps(request))
    receipt = construction.discover_local_neighborhood(path)
    before = receipt.json_bytes
    assert receipt.completion == "truncated"
    construction.list_local_realizations(receipt, max_noncanonical_pairs=0)
    assert receipt.completion == "truncated"
    assert receipt.json_bytes == before
    with pytest.raises(TypeError, match="verified"):
        construction.list_local_realizations(json.loads(before))
