"""Disjoint discovery jobs reunite without changing permissions or molecular evidence."""

import json
from itertools import product

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from tests.integration.test_design_discovery import intent_document


@pytest.fixture(scope="module")
def partitioned_choices(tmp_path_factory):
    root = tmp_path_factory.mktemp("partition-capture")
    parent = {**intent_document(), "ends": {"left": ["AAAA", "AGTC"], "right": ["AAAA", "AGTC"]}}
    parts = []
    for left, right in product(parent["ends"]["left"], parent["ends"]["right"]):
        intent = {**parent, "ends": {"left": left, "right": right}}
        choices = construction.discover_designs(intent, root / (left + right), max_evaluations=2)
        parts.append(choices)
    return parent, parts


def test_partition_capture_preserves_union_and_each_handoff(partitioned_choices, tmp_path):
    parent, parts = partitioned_choices
    edition = construction.combine_design_discoveries(
        parent, [p._directory for p in parts], tmp_path / "combined"
    )
    expected = {p["materialized_realization_id"] for c in parts for p in c.query()["paths"]}
    answer = edition.query()
    assert {p["materialized_realization_id"] for p in answer["paths"]} == expected
    assert answer["coverage"]["target_pairs"] == 4
    assert answer["coverage"]["supported_pairs"] >= 2
    assert answer["coverage"]["target_right_words"] == 2
    assert edition.resolution["intent"]["ends"] == parent["ends"]
    assert not answer["all_preparations_enumerated"]
    for i, source in enumerate(parts):
        if not source.query()["matching_preparations"]:
            continue
        selection = source.sample(seed=1)
        identity = selection["materialized_realization_id"]
        source.retrieve(selection, tmp_path / f"source-{i}")
        edition.retrieve(edition.select(identity), tmp_path / f"combined-{i}")

        def files(directory):
            return {
                p.relative_to(directory): p.read_bytes()
                for p in directory.rglob("*")
                if p.is_file()
            }

        assert files(tmp_path / f"source-{i}") == files(tmp_path / f"combined-{i}")
    restored = construction.load_atlas_edition(tmp_path / "combined")
    assert restored.query() == answer
    origin = json.loads((tmp_path / "combined/capture-origin.json").read_bytes())
    assert len(origin["sources"]) == 4
    assert origin["search_performed"] is False
    assert origin["molecular_replay"] == "captured_preparations_only"
    edition.figure(selection=edition.select(next(iter(expected)))).write(tmp_path / "figure")
    assert (tmp_path / "figure/figure.svg").is_file()


@pytest.mark.parametrize("failure", ["overlap", "missing", "permission"])
def test_partition_capture_rejects_scope_drift_before_output(
    partitioned_choices, tmp_path, failure
):
    parent, parts = partitioned_choices
    directories = [p._directory for p in parts]
    if failure == "overlap":
        directories.append(directories[0])
    elif failure == "missing":
        directories.pop()
    else:
        parent = json.loads(json.dumps(parent))
        parent["context"]["placements"] = [{"left_bp": 0, "right_bp": 0}]
    with pytest.raises(ValueError):
        construction.combine_design_discoveries(parent, directories, tmp_path / "absent")
    assert not (tmp_path / "absent").exists()


def test_partition_cli_uses_same_capture_contract(partitioned_choices, tmp_path):
    parent, parts = partitioned_choices
    request = tmp_path / "intent.json"
    request.write_text(json.dumps(parent))
    result = CliRunner().invoke(
        app,
        [
            "design",
            "combine",
            *[str(p._directory) for p in parts],
            "--request",
            str(request),
            "--out",
            str(tmp_path / "edition"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["preparations"] >= 2


def test_partition_order_does_not_change_edition(partitioned_choices, tmp_path):
    parent, parts = partitioned_choices
    directories = [p._directory for p in parts]
    first = construction.combine_design_discoveries(parent, directories, tmp_path / "first")
    second = construction.combine_design_discoveries(parent, directories[::-1], tmp_path / "second")
    assert first.digest == second.digest
    assert first.query() == second.query()


def test_partition_capture_does_not_replace_or_write_inside_sources(partitioned_choices, tmp_path):
    parent, parts = partitioned_choices
    directories = [p._directory for p in parts]
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        construction.combine_design_discoveries(parent, directories, existing)
    with pytest.raises(ValueError, match="outside"):
        construction.combine_design_discoveries(parent, directories, directories[0] / "nested")
    assert not (directories[0] / "nested").exists()
