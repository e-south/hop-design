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
        "362dc73bc427c0a6045686ea90eba46fabffd0191e97333cb8c38394e269c1a7@1"
    ),
    "exact": (
        "hop:materialized-construction/"
        "af61b54ab34978e6c2ee044216cc132fbe8177765f11ff07639a116efe1c08b2@1"
    ),
    "relaxed": (
        "hop:materialized-construction/"
        "4ce8ee05f2a7dc4ba0ef78aa287dd76b5c7d8973aa7470408c2022f2bd91d65c@1"
    ),
}


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
