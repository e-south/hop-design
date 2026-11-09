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
import os
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
    install = (REPO_ROOT / "docs/guides/install.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs/guides/quickstart.md").read_text(encoding="utf-8")
    roadmap = (REPO_ROOT / "docs/dev/plans/roadmap.md").read_text(encoding="utf-8")
    maintainer_index = (REPO_ROOT / "docs/dev/README.md").read_text(encoding="utf-8")
    material_closure_adr = (
        REPO_ROOT / "docs/architecture/decisions/0033-close-linear-source-material-dependencies.md"
    ).read_text(encoding="utf-8")

    assert "docs/guides/install.md" in readme
    assert "https://github.com/e-south/hop-design/tree/v0.1.0a8" in install
    assert "HOP is alpha software" in install
    assert "uv tool install" in install
    assert "hop-design --version" in install
    assert "unreleased v0.1.0a8" not in readme
    assert "install.md" in quickstart
    assert "published `v0.1.0a8`" in roadmap
    assert "Historical construction realignment audit" not in maintainer_index
    assert "Linear-source product closure audit" not in maintainer_index
    assert material_closure_adr.startswith("# ADR 0033")
    assert "Source preparation" in material_closure_adr
    assert "Source partition" in material_closure_adr


def test_construction_guide_starts_with_a_standalone_public_example() -> None:
    guide = (REPO_ROOT / "docs/guides/compile-construction.md").read_text(encoding="utf-8")

    assert guide.index("examples/basal-junction/search.py") < guide.index("## Checkpoint")
    assert "models used by the owning study" not in " ".join(guide.split())
    assert "examples/construction-composed-pcr.yaml" not in guide
    assert "--ordinal ROUTE_NUMBER" in guide


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
    assert summary["substrate_space_designs_verified"] == 256
    assert summary["basal_junction"]["payload_nt"] == 34
    assert summary["basal_junction"]["completion"] == "complete"
    assert summary["payload_record_bundles_verified"] == 3
    assert summary["design_surfaces"] == ["exact", "symbolic", "spec"]
    assert summary["discovery_statuses"] == ["complete", "infeasible", "truncated"]
    assert summary["construction_statuses"] == {
        "composed-pcr": "complete",
        "exact": "complete",
        "infeasible": "infeasible",
        "expanded-domain": "complete",
    }
    assert summary["method_authoring_verified"] is True
    assert summary["method_bundle_verified"] is True
    assert summary["handoff_verified"] is True


def test_verification_endpoints_share_the_docs_smoke_contract() -> None:
    agent_verify = (REPO_ROOT / "scripts" / "agent-verify").read_text(encoding="utf-8")
    wheel_smoke = (REPO_ROOT / "scripts" / "wheel-smoke").read_text(encoding="utf-8")
    assert "examples/basal-junction/search.py --out" in wheel_smoke
    assert '"$smoke_root/source-basal/$relative"' in wheel_smoke
    assert '"$smoke_root/wheel-basal/$relative"' in wheel_smoke

    assert "uv run --locked pytest" in agent_verify
    assert "uv run --locked python scripts/docs-smoke" not in agent_verify
    assert '"$smoke_root/venv/bin/python" scripts/docs-smoke' in wheel_smoke
    assert "scripts/distribution/inventory.py" in wheel_smoke
    inventory = runpy.run_path(str(REPO_ROOT / "scripts/distribution/inventory.py"))
    assert "examples/fixed-site-three-base-context.yaml" in inventory["REQUIRED_SOURCE_PATHS"]
    assert "examples/verify_design_method_handoff.py" in inventory["REQUIRED_SOURCE_PATHS"]
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


@pytest.mark.parametrize("pytest_exit,node_exit", [(0, 0), (17, 0), (0, 19)])
def test_gate_runs_one_source_journey_and_propagates_tool_failure(tmp_path, pytest_exit, node_exit):
    """Exercise the shell gate without rerunning tools whose behavior has separate tests."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "agent-verify").write_bytes((REPO_ROOT / "scripts/agent-verify").read_bytes())
    for name in ("agent-preflight", "precommit-all", "wheel-smoke"):
        (scripts / name).write_text(f'echo "{name}" >> "$GATE_LOG"\n')
    binary = tmp_path / "bin"
    binary.mkdir()
    uv = binary / "uv"
    uv.write_text(
        "#!/usr/bin/env bash\n"
        'echo "uv $*" >> "$GATE_LOG"\n'
        'if [[ "$*" == "run --locked pytest "* ]]; then exit "$PYTEST_EXIT"; fi\n'
    )
    uv.chmod(0o755)
    node = binary / "node"
    node.write_text('#!/usr/bin/env bash\necho "node $*" >> "$GATE_LOG"\nexit "$NODE_EXIT"\n')
    node.chmod(0o755)
    browser = tmp_path / "tests/browser"
    browser.mkdir(parents=True)
    (browser / "seam.test.mjs").touch()
    log = tmp_path / "commands.log"
    result = subprocess.run(
        ["bash", str(scripts / "agent-verify")],
        env={
            **os.environ,
            "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}",
            "GATE_LOG": str(log),
            "PYTEST_EXIT": str(pytest_exit),
            "NODE_EXIT": str(node_exit),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    commands = log.read_text().splitlines()
    assert result.returncode == (node_exit or pytest_exit), result.stderr
    assert sum(command.startswith("uv run --locked pytest ") for command in commands) == (
        0 if node_exit else 1
    )
    assert sum(command.startswith("node --test tests/browser/") for command in commands) == 1
    assert not any("scripts/docs-smoke" in command for command in commands)
    assert commands.count("wheel-smoke") == (1 if pytest_exit == node_exit == 0 else 0)
    assert ("Agent verification: ok" in result.stdout) == (pytest_exit == node_exit == 0)
