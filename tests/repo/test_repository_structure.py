"""
--------------------------------------------------------------------------------
HOP Design
tests/repo/test_repository_structure.py

Checks public examples, release documentation, and semantic source organization.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import hop_design as hop

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_public_example_is_a_real_strict_spec() -> None:
    example = REPO_ROOT / "examples" / "generic-symbolic.yaml"

    spec = hop.load_spec(example)
    compilation = hop.compile(spec)

    assert compilation.spec.design_id == "example-symbolic"
    assert compilation.plan.payload_sequence == "NRY"


def test_quickstart_owns_installation_and_compilation_examples() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs" / "guides" / "quickstart.md").read_text(encoding="utf-8")
    release_match = re.search(r"hop_design-([0-9a-z.]+)-py3-none-any\.whl", quickstart)
    assert release_match is not None
    wheel_name = release_match.group(0)

    assert "```" not in readme
    assert "hop-design compile" not in readme
    assert "uv pip install" not in readme
    assert "--spec FILE" in quickstart
    assert "--sequence ATAACTTCGTATAGCATACATTATACGAAGTTAT" in quickstart
    assert 'compilation.write("build/symbolic-python")' in quickstart
    assert wheel_name in quickstart
    checksum_command = f"grep '{wheel_name}$' SHA256SUMS | shasum -a 256 -c -"
    assert checksum_command in quickstart


def test_governance_and_release_routes_exist() -> None:
    expected_paths = (
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        ".github/CODEOWNERS",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/pull_request_template.md",
        "docs/dev/README.md",
        "docs/dev/github-governance.md",
        "docs/dev/releasing.md",
    )

    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_public_documentation_tracks_the_published_source_release() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs" / "guides" / "quickstart.md").read_text(encoding="utf-8")
    roadmap = (REPO_ROOT / "docs" / "dev" / "plans" / "roadmap.md").read_text(encoding="utf-8")

    release_match = re.search(r"hop_design-([0-9a-z.]+)-py3-none-any\.whl", quickstart)
    assert release_match is not None
    release_version = release_match.group(1)
    wheel_name = release_match.group(0)
    assert release_version == version
    assert f"[v{release_version}]" in readme
    assert f"tree/v{release_version}" in readme
    assert f"unreleased v{version} candidate" not in readme
    assert wheel_name in quickstart
    assert f"published `v{release_version}` artifact" in roadmap
    assert f"unreleased `v{version}` candidate" not in roadmap
    assert "Research" + " Studies" not in roadmap
    assert "billing" not in roadmap.lower()


def test_source_layout_has_explicit_sprawl_limits() -> None:
    source_root = REPO_ROOT / "src" / "hop_design"
    package_dirs = [source_root, *sorted(path for path in source_root.rglob("*") if path.is_dir())]

    for directory in package_dirs:
        modules = list(directory.glob("*.py"))
        assert len(modules) <= 25, f"{directory.relative_to(REPO_ROOT)} has too many flat modules"
        for module in modules:
            line_count = len(module.read_text(encoding="utf-8").splitlines())
            assert line_count <= 350, f"{module.relative_to(REPO_ROOT)} is a monolith"


def test_complete_route_evaluation_is_partitioned_by_endpoint_semantics() -> None:
    complete_root = REPO_ROOT / "src/hop_design/models/construction/complete"
    evaluation_root = complete_root / "evaluation"

    assert not (complete_root / "evaluation.py").exists()
    assert not (complete_root / "evaluation_result.py").exists()
    assert {
        "__init__.py",
        "context.py",
        "direct.py",
        "pcr.py",
        "clone.py",
        "result.py",
    }.issubset({path.name for path in evaluation_root.glob("*.py")})
