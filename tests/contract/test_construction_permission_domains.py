"""Inclusive association ranges are shared permissions, not sparse sampling hints."""

import json

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.design.construction.navigation.features.operations import parameter_operations
from hop_design.models.construction.variants.parameters import parameter_definition
from tests.unit.test_design_revision import intent


@pytest.mark.parametrize(
    ("selection", "expected"),
    (
        ({"minimum": 14, "maximum": 24}, list(range(14, 25))),
        ({"values": [14, 17, 20, 24]}, [14, 17, 20, 24]),
    ),
)
def test_association_permission_preserves_ranges_and_deliberate_subsets(selection, expected):
    original = intent()
    preview = construction.preview_design_revision(
        original,
        {
            "parameters": [{"key": "adapter_annealing_min_nt", **selection}],
        },
    )
    result = json.loads(preview.json_bytes)
    assert result["status"] == "ready"
    assert result["effective_request"]["basal"]["annealing_lengths_nt"] == expected
    assert original == intent()
    assert all(c["path"] == "basal.annealing_lengths_nt" for c in result["changes"])


def test_browser_exposes_same_association_permission():
    operation = parameter_operations(
        parameter_definition("adapter_annealing_min_nt"),
        product="released_insert",
        permissions={"basal": {}},
        live=True,
    )["revise"]
    assert operation["available"]
    assert operation["parameter"] == "adapter_annealing_min_nt"


def test_cli_and_api_preview_the_identical_integer_domain(tmp_path):
    changes = {"parameters": [{"key": "adapter_annealing_min_nt", "minimum": 14, "maximum": 24}]}
    request = tmp_path / "intent.json"
    request.write_text(json.dumps(intent()))
    revision = tmp_path / "revision.json"
    revision.write_text(json.dumps(changes))
    output = tmp_path / "preview"
    result = CliRunner().invoke(
        app,
        [
            "design",
            "revise",
            "--request",
            str(request),
            "--changes",
            str(revision),
            "--out",
            str(output),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    expected = construction.preview_design_revision(intent(), changes)
    assert construction.load_design_revision(output).json_bytes == expected.json_bytes


@pytest.mark.parametrize(
    "selection",
    (
        {"minimum": 24, "maximum": 14},
        {"minimum": 14, "maximum": 24, "values": [14, 24]},
        {"minimum": True, "maximum": 24},
    ),
)
def test_conflicting_or_invalid_bounds_fail_before_search(selection):
    with pytest.raises(ValueError):
        construction.preview_design_revision(
            intent(),
            {
                "parameters": [{"key": "adapter_annealing_min_nt", **selection}],
            },
        )


def test_default_context_includes_adjacent_lengths_without_reinterpreting_v1():
    current = json.loads(construction.resolve_design_request(intent()).json_bytes)
    assert current["context"]["id"] == "linear-source/v2"
    effective = current["effective_request"]
    assert effective["basal"]["annealing_lengths_nt"] == list(range(14, 25))
    assert {(p["left_bp"], p["right_bp"]) for p in effective["placements"]} == {
        (left, right) for left in range(7) for right in range(7)
    }
    legacy = json.loads(
        construction.resolve_design_request(
            {
                **intent(),
                "context": "linear-source/v1",
            }
        ).json_bytes
    )
    assert legacy["context"]["id"] == "linear-source/v1"
    assert legacy["effective_request"]["basal"]["annealing_lengths_nt"] == [14, 17, 20, 24]
    assert len(legacy["effective_request"]["placements"]) == 9
