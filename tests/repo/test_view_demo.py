from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_component_view_example_writes_replayable_didactic_assets(tmp_path: Path) -> None:
    output = tmp_path / "component-views"
    result = subprocess.run(
        [
            sys.executable,
            "examples/render_component_views.py",
            "--out",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(result.stdout)
    assert summary["schema"] == "hop.component-view-demo/v1"
    assert summary["view_kinds"] == ["foldback_junction", "basal_pairing"]
    assert summary["basal_pair_kinds"] == [
        "hard_mismatch",
        "gt_wobble",
        "watson_crick",
        "watson_crick",
    ]
    assert set(summary["artifacts"]) == {
        "basal-junction.json",
        "basal-junction.svg",
        "foldback-junction.json",
        "foldback-junction.svg",
    }
    for relative, expected_digest in summary["artifacts"].items():
        content = (output / relative).read_bytes()
        assert "sha256:" + hashlib.sha256(content).hexdigest() == expected_digest
        if relative.endswith(".svg"):
            assert content == (ROOT / "assets" / "examples" / relative).read_bytes()


def test_component_view_example_is_routed_and_executed() -> None:
    routes = "\n".join(
        (ROOT / relative).read_text(encoding="utf-8")
        for relative in (
            "docs/index.md",
            "docs/guides/quickstart.md",
            "docs/reference/view-contracts.md",
            "scripts/docs-smoke",
        )
    )
    assert "render_component_views.py" in routes
    assert "render-component-views.md" in routes
