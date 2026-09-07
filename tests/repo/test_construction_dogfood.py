"""
--------------------------------------------------------------------------------
HOP Design
tests/repo/test_construction_dogfood.py

Tests installed-artifact construction examples and source-wheel parity wiring.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import hop_design.construction as construction

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = REPO_ROOT / "examples" / "compile_construction.py"
DESIGN = REPO_ROOT / "examples" / "construction-exact-design.yaml"
SOURCES = {
    "composed-pcr": REPO_ROOT / "examples" / "construction-composed-pcr.yaml",
    "exact": REPO_ROOT / "examples" / "construction-exact.yaml",
    "infeasible": REPO_ROOT / "examples" / "construction-infeasible.yaml",
    "expanded-domain": REPO_ROOT / "examples" / "construction-expanded-domain.yaml",
}
TRAJECTORY_REALIZATION_IDS = {
    "composed-pcr": (
        "hop:materialized-construction/"
        "81ceb0c0f5aae50200e22a51f394487710580419e0fd02010fe48812976a8904@1"
    ),
    "exact": (
        "hop:materialized-construction/"
        "18b865aacc420439aa8fefe839ee1f4d6743b5d5588142adee713cebcfe55877@1"
    ),
    "expanded-domain": (
        "hop:materialized-construction/"
        "18b865aacc420439aa8fefe839ee1f4d6743b5d5588142adee713cebcfe55877@1"
    ),
}
LOCAL_FOLDBACK_PARTITION = REPO_ROOT / "examples" / "foldback-local-partition.yaml"


def _run_example(tmp_path: Path, case: str, suffix: str) -> dict[str, object]:
    arguments = [
        sys.executable,
        str(EXAMPLE),
        "--design",
        str(DESIGN),
        "--source",
        str(SOURCES[case]),
        "--out",
        str(tmp_path / f"{case}-{suffix}"),
    ]
    if case in TRAJECTORY_REALIZATION_IDS:
        arguments.extend(["--trajectory-realization-id", TRAJECTORY_REALIZATION_IDS[case]])
    result = subprocess.run(
        arguments,
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_construction_example_uses_only_public_hop_facades() -> None:
    tree = ast.parse(EXAMPLE.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}

    assert {name for name in imported if name.startswith("hop_design")} == {
        "hop_design",
        "hop_design.construction",
    }
    assert not {
        name for name in imported_from if name is not None and name.startswith("hop_design")
    }
    assert "os.replace" not in EXAMPLE.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("case", "status", "trajectory_expected", "basal_expected"),
    [
        ("composed-pcr", "complete", True, True),
        ("exact", "complete", True, False),
        ("infeasible", "infeasible", False, False),
        ("expanded-domain", "complete", True, False),
    ],
)
def test_construction_example_is_deterministic_and_preserves_search_status(
    tmp_path: Path,
    case: str,
    status: str,
    trajectory_expected: bool,
    basal_expected: bool,
) -> None:
    first = _run_example(tmp_path, case, "first")
    second = _run_example(tmp_path, case, "second")

    assert first == second
    assert first["schema"] == "hop.construction-dogfood/v2"
    assert first["case"] == case
    assert first["status"] == status
    assert first["bundle_verified"] is True
    projection_hashes = first["projection_sha256"]
    assert isinstance(projection_hashes, dict)
    assert set(projection_hashes) >= {
        "foldback_feasibility",
        "foldback_retained_overhead",
        "navigation",
        "summary",
    }
    for formats in projection_hashes.values():
        assert isinstance(formats, dict)
        assert set(formats) >= {"json", "svg"}
        assert all(len(value) == 64 for value in formats.values())
    assert "csv" not in projection_hashes.get("trajectory", {})
    basal_projection_names = {"basal_feasibility", "basal_retained_overhead"}
    if basal_expected:
        assert basal_projection_names <= set(projection_hashes)
    else:
        assert basal_projection_names.isdisjoint(projection_hashes)
    levels = first["foldback_overhead_levels"]
    maximum_overhead = 9 if case == "infeasible" else 11
    assert [level["retained_overhead_nt"] for level in levels] == list(range(maximum_overhead + 1))
    realized_levels = [level for level in levels if level["realization_count"]]
    if case == "infeasible":
        assert realized_levels == []
    else:
        assert realized_levels == [{"retained_overhead_nt": 11, "realization_count": 2}]
    selected = first["selected_trajectory_realization_id"]
    if trajectory_expected:
        assert isinstance(selected, str)
        assert selected in first["materialized_realization_ids"]
        assert "trajectory" in projection_hashes
        assert len(first["selection_sha256"]) == 64
    else:
        assert selected is None
        assert first["selection_sha256"] is None
        assert first["materialized_realization_ids"] == []
        assert "trajectory" not in projection_hashes


def test_construction_example_rejects_an_unaccepted_trajectory_selection(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(EXAMPLE),
            "--design",
            str(DESIGN),
            "--source",
            str(SOURCES["exact"]),
            "--out",
            str(tmp_path / "invalid-selection"),
            "--trajectory-realization-id",
            "hop:materialized-construction/not-accepted@1",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "is not an accepted construction realization" in result.stderr
    assert not (tmp_path / "invalid-selection").exists()


def test_docs_and_wheel_smoke_share_the_construction_example() -> None:
    docs_smoke = (REPO_ROOT / "scripts" / "docs-smoke").read_text(encoding="utf-8")
    wheel_smoke = (REPO_ROOT / "scripts" / "wheel-smoke").read_text(encoding="utf-8")

    assert '"examples/compile_construction.py"' in docs_smoke
    assert '"construction_statuses": construction_statuses' in docs_smoke
    assert '"--trajectory-realization-id"' in docs_smoke
    assert '"navigation"' in docs_smoke
    assert 'summary.get("selection_sha256")' in docs_smoke
    assert '"construction": construction.__all__' in wheel_smoke
    for path in (EXAMPLE, DESIGN, *SOURCES.values()):
        assert f"'{path.relative_to(REPO_ROOT)}'" in wheel_smoke
    assert "source_construction" in wheel_smoke
    assert "wheel_construction" in wheel_smoke
    for command in (
        "construction summary",
        "construction list",
        "construction select",
        "construction inspect",
    ):
        assert command in wheel_smoke


def test_local_foldback_partition_defaults_to_both_strands_and_replays(tmp_path: Path) -> None:
    authored = yaml.safe_load(LOCAL_FOLDBACK_PARTITION.read_text(encoding="utf-8"))

    assert "nick_strand" not in authored["geometry_domain"]
    assert authored["search"]["sequence_partition"] == {
        "part_count": 2,
        "part_index": 0,
    }

    receipt = construction.discover_local_neighborhood(LOCAL_FOLDBACK_PARTITION)
    result = json.loads(receipt.json_bytes)
    strands = {realization["foldback_nick"]["strand"] for realization in result["realizations"]}

    assert receipt.family == "foldback"
    assert receipt.completion == "complete"
    assert strands == {"top", "bottom"}
    output = receipt.write(tmp_path / "foldback-partition")
    loaded = construction.load_verified_local_neighborhood(output / "result.json")
    assert loaded.result_id == receipt.result_id
    assert loaded.json_bytes == receipt.json_bytes


def test_wheel_smoke_exercises_local_foldback_partition_source_parity() -> None:
    wheel_smoke = (REPO_ROOT / "scripts" / "wheel-smoke").read_text(encoding="utf-8")

    assert "'examples/foldback-local-partition.yaml'" in wheel_smoke
    assert "discover_local_neighborhood" in wheel_smoke
    assert "load_verified_local_neighborhood" in wheel_smoke
    assert 'strands != {"top", "bottom"}' in wheel_smoke
    assert "source_local_result" in wheel_smoke
    assert "wheel_local_result" in wheel_smoke
    assert 'cmp -s "$source_local_result" "$wheel_local_result"' in wheel_smoke
