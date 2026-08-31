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
    "relaxed": REPO_ROOT / "examples" / "construction-relaxed.yaml",
}
TRAJECTORY_REALIZATION_IDS = {
    "composed-pcr": (
        "hop:materialized-construction/"
        "ed200f1b66a4b76cd9f6f33ba214798833fe5ec515474d6eed4ef8e9233de283@1"
    ),
    "exact": (
        "hop:materialized-construction/"
        "63982f1d523dac0ad6f4034ce4ff83259fc05353392e783e96831a9096fb2109@1"
    ),
    "relaxed": (
        "hop:materialized-construction/"
        "05558439e5be5e026a4b14ff39bdd1907e45bf588e138bb9ef9a4e1922f1f48a@1"
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
        ("relaxed", "complete", True, False),
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
    assert first["schema"] == "hop.construction-dogfood/v1"
    assert first["case"] == case
    assert first["status"] == status
    assert first["bundle_verified"] is True
    projection_hashes = first["projection_sha256"]
    assert isinstance(projection_hashes, dict)
    assert set(projection_hashes) >= {"foldback_feasibility", "foldback_relaxation", "summary"}
    for formats in projection_hashes.values():
        assert isinstance(formats, dict)
        assert set(formats) >= {"json", "svg"}
        assert all(len(value) == 64 for value in formats.values())
    assert "csv" not in projection_hashes.get("trajectory", {})
    basal_projection_names = {"basal_feasibility", "basal_relaxation"}
    if basal_expected:
        assert basal_projection_names <= set(projection_hashes)
    else:
        assert basal_projection_names.isdisjoint(projection_hashes)
    shells = first["foldback_shells"]
    if case == "relaxed":
        assert shells == [
            {"radius": 0, "realization_count": 0},
            {"radius": 1, "realization_count": 2},
        ]
    elif case in {"composed-pcr", "exact"}:
        assert shells == [{"radius": 0, "realization_count": 2}]
    else:
        assert shells == [{"radius": 0, "realization_count": 0}]
    selected = first["selected_trajectory_realization_id"]
    if trajectory_expected:
        assert isinstance(selected, str)
        assert selected in first["materialized_realization_ids"]
        assert "trajectory" in projection_hashes
    else:
        assert selected is None
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
    assert '"construction": construction.__all__' in wheel_smoke
    for path in (EXAMPLE, DESIGN, *SOURCES.values()):
        assert f"'{path.relative_to(REPO_ROOT)}'" in wheel_smoke
    assert "source_construction" in wheel_smoke
    assert "wheel_construction" in wheel_smoke


def test_local_foldback_partition_defaults_to_both_strands_and_replays(tmp_path: Path) -> None:
    authored = yaml.safe_load(LOCAL_FOLDBACK_PARTITION.read_text(encoding="utf-8"))

    assert "nick_strand" not in authored["target"]
    assert authored["enumeration"]["sequence_partition"] == {
        "part_count": 2,
        "part_index": 0,
    }

    receipt = construction.discover_local_neighborhood(LOCAL_FOLDBACK_PARTITION)
    result = json.loads(receipt.json_bytes)
    strands = {realization["foldback_nick"]["strand"] for realization in result["realizations"]}

    assert receipt.family == "foldback"
    assert receipt.status == "complete"
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
