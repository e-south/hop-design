"""
--------------------------------------------------------------------------------
HOP Design
tests/repo/test_docs_smoke.py

Tests installed-package documentation journeys and construction examples.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
import runpy
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_release_routing_names_published_and_current_contracts() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs/guides/quickstart.md").read_text(encoding="utf-8")
    roadmap = (REPO_ROOT / "docs/dev/plans/roadmap.md").read_text(encoding="utf-8")
    maintainer_index = (REPO_ROOT / "docs/dev/README.md").read_text(encoding="utf-8")
    material_closure_adr = (
        REPO_ROOT / "docs/architecture/decisions/0033-close-linear-source-material-dependencies.md"
    ).read_text(encoding="utf-8")

    assert "Published release | [v0.1.0a8]" in readme
    assert "unreleased v0.1.0a8" not in readme
    assert "hop_design-0.1.0a8-py3-none-any.whl" in quickstart
    assert "published `v0.1.0a8`" in roadmap
    assert "Historical construction realignment audit" not in maintainer_index
    assert "Linear-source product closure audit" not in maintainer_index
    assert "status: accepted" in material_closure_adr
    assert "Source preparation" in material_closure_adr
    assert "Source partition" in material_closure_adr


def test_docs_smoke_exercises_the_public_documentation_journey() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/docs-smoke"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(result.stdout)
    assert summary["schema"] == "hop.docs-smoke/v1"
    assert summary["status"] == "ok"
    assert summary["substrate_space_designs_verified"] == 64
    assert summary["payload_record_bundles_verified"] == 3
    assert summary["design_surfaces"] == ["exact", "symbolic", "spec"]
    assert summary["discovery_statuses"] == ["complete", "infeasible", "truncated"]
    assert summary["construction_statuses"] == {
        "composed-pcr": "complete",
        "exact": "complete",
        "infeasible": "infeasible",
        "relaxed": "complete",
    }
    assert summary["method_authoring_verified"] is True
    assert summary["method_bundle_verified"] is True
    assert summary["handoff_verified"] is True


def test_verification_endpoints_share_the_docs_smoke_contract() -> None:
    agent_verify = (REPO_ROOT / "scripts" / "agent-verify").read_text(encoding="utf-8")
    wheel_smoke = (REPO_ROOT / "scripts" / "wheel-smoke").read_text(encoding="utf-8")

    assert "uv run --locked python scripts/docs-smoke" in agent_verify
    assert '"$smoke_root/venv/bin/python" scripts/docs-smoke' in wheel_smoke
    assert "'examples/fixed-site-three-base-context.yaml'" in wheel_smoke
    assert "'examples/foldback-local-partition.yaml'" in wheel_smoke
    assert "'examples/compile_payload_records.py'" in wheel_smoke
    assert "'examples/compile_construction.py'" in wheel_smoke
    assert "'examples/construction-exact-design.yaml'" in wheel_smoke
    assert "'examples/construction-composed-pcr.yaml'" in wheel_smoke
    assert "'examples/construction-exact.yaml'" in wheel_smoke
    assert "'examples/construction-infeasible.yaml'" in wheel_smoke
    assert "'examples/construction-relaxed.yaml'" in wheel_smoke
    assert "'examples/linear-source-matched-design.yaml'" in wheel_smoke
    assert "'examples/author_linear_source_method.py'" in wheel_smoke
    assert "'examples/verify_design_method_handoff.py'" in wheel_smoke
    assert 'tar -xzf "$sdist_path" -C "$sdist_extract_root"' in wheel_smoke
    assert '--content-root "$sdist_root"' in wheel_smoke
    assert wheel_smoke.count("import hop_design.spaces as spaces") == 2
    assert wheel_smoke.count('"spaces": spaces.__all__') == 2


def test_docs_smoke_bounds_child_execution_time() -> None:
    namespace = runpy.run_path(str(REPO_ROOT / "scripts" / "docs-smoke"))
    run = cast(Callable[..., str], namespace["_run"])
    error_type = cast(type[Exception], namespace["DocsSmokeError"])

    with pytest.raises(error_type, match="sleeping child timed out"):
        run(
            "sleeping child",
            ["-c", "import time; time.sleep(0.2)"],
            content_root=REPO_ROOT,
            timeout_seconds=0.01,
        )
