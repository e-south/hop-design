"""Executable contract for the readable method-authoring example."""

from __future__ import annotations

import json
import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_method_authoring_example_sets_defaultable_contract_fields_explicitly() -> None:
    namespace = runpy.run_path(str(ROOT / "examples" / "author_linear_source_method.py"))
    request = namespace["build_request"]()

    assert {
        "method_kind",
        "hairpin_encoding_projection_orientation",
    } <= request.model_fields_set


def test_method_authoring_example_writes_and_verifies_bundle(tmp_path: Path) -> None:
    output_path = tmp_path / "authored-method"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples" / "author_linear_source_method.py"),
            "--out",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)
    assert result["method_bundle_verified"] is True
    assert result["method_kind"] == ("linear-source-multinick-size-selection-hairpin-pcr@1")
    assert result["material_count"] == 6
    assert result["nicking_agent_count"] == 2
    assert result["selected_fragment_count"] == 2
    assert result["cohesive_end_count"] == 2
    assert result["destination_readiness"] == "not_evaluated"
    assert (output_path / "method-bundle.json").is_file()
