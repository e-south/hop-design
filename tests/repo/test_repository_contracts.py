from __future__ import annotations

import re
import tomllib
from pathlib import Path

import yaml

import hop_design as hop

REPO_ROOT = Path(__file__).resolve().parents[2]
FULL_SHA_ACTION = re.compile(r"^\s*uses:\s*[^\s@]+@[0-9a-f]{40}(?:\s+#.*)?$", re.MULTILINE)
ANY_ACTION = re.compile(r"^\s*uses:\s*[^\s]+(?:\s+#.*)?$", re.MULTILINE)
FULL_SHA_PRECOMMIT = re.compile(r"^\s*rev:\s*[0-9a-f]{40}(?:\s+#.*)?$", re.MULTILINE)
ANY_PRECOMMIT_REV = re.compile(r"^\s*rev:\s*[^\s]+(?:\s+#.*)?$", re.MULTILINE)


def _workflow(name: str) -> tuple[dict[str, object], str]:
    path = REPO_ROOT / ".github" / "workflows" / name
    text = path.read_text(encoding="utf-8")
    parsed = yaml.load(text, Loader=yaml.BaseLoader)
    assert isinstance(parsed, dict)
    return parsed, text


def test_public_landing_page_routes_without_becoming_a_manual() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert readme.startswith("# ![HOP Design")
    assert "assets/hop-design-banner.svg" in readme
    assert "CONTRIBUTING.md" in readme
    assert "SECURITY.md" in readme
    assert "docs/README.md" in readme
    assert len(readme.splitlines()) <= 140


def test_distribution_metadata_keeps_pypi_brake_but_names_public_home() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)

    project = config["project"]
    assert "Private :: Do Not Upload" in project["classifiers"]
    assert project["urls"] == {
        "Documentation": "https://github.com/e-south/hop-design/tree/main/docs",
        "Issues": "https://github.com/e-south/hop-design/issues",
        "Repository": "https://github.com/e-south/hop-design",
    }
    assert config["tool"]["uv"]["required-version"] == ">=0.12.3,<0.13"
    assert config["tool"]["coverage"]["report"] == {
        "fail_under": 90,
        "precision": 2,
        "show_missing": True,
        "skip_covered": True,
    }
    dev_dependencies = "\n".join(config["dependency-groups"]["dev"])
    for dependency in ("pip-audit", "pre-commit", "twine"):
        assert dependency in dev_dependencies


def test_ci_has_one_stable_required_context_and_supported_python_probe() -> None:
    workflow, text = _workflow("ci.yaml")
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)

    assert set(jobs) == {"verify", "python-compatibility", "checks"}
    assert jobs["checks"]["name"] == "Checks"
    assert set(jobs["checks"]["needs"]) == {"verify", "python-compatibility"}
    assert jobs["python-compatibility"]["strategy"]["matrix"]["python-version"] == [
        "3.12",
        "3.13",
        "3.14",
    ]
    assert workflow["permissions"] == {"contents": "read"}
    assert "pull_request_target" not in text


def test_workflows_use_immutable_actions_and_bounded_permissions() -> None:
    for path in sorted((REPO_ROOT / ".github" / "workflows").glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        action_lines = ANY_ACTION.findall(text)
        assert action_lines, f"{path.name} must use at least one action"
        assert len(FULL_SHA_ACTION.findall(text)) == len(action_lines), (
            f"{path.name} contains an action that is not pinned to a full commit SHA"
        )
        assert "permissions:" in text
        assert "pull_request_target" not in text


def test_dependency_review_is_a_separate_required_signal() -> None:
    workflow, text = _workflow("dependency-review.yaml")

    assert workflow["on"] == {"pull_request": ""}
    assert workflow["permissions"] == {"contents": "read"}
    assert "name: Dependency review" in text
    assert "fail-on-severity: moderate" in text


def test_release_workflow_verifies_before_publishing_and_cannot_publish_to_pypi() -> None:
    workflow, text = _workflow("release.yaml")

    assert workflow["on"] == {"push": {"tags": ["v*"]}}
    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    assert set(jobs) == {"build", "publish"}
    assert jobs["publish"]["needs"] == "build"
    assert jobs["publish"]["permissions"] == {
        "actions": "read",
        "contents": "write",
    }
    assert jobs["publish"]["env"] == {"GH_REPO": "${{ github.repository }}"}
    assert "id-token: write" not in text
    assert "gh-action-pypi-publish" not in text
    assert "release:" not in text
    assert "git merge-base --is-ancestor" in text
    assert "uv build --no-sources" in text
    assert "scripts/wheel-smoke dist" in text
    assert "sha256sum *.whl *.tar.gz > SHA256SUMS" in text
    assert "actions/upload-artifact" in text
    assert "retention-days: 1" in text
    assert "gh release create" in text
    assert '"${GITHUB_REF_NAME}" dist/*' in text
    assert "--verify-tag" in text
    assert "--generate-notes" in text
    assert "gh release upload" not in text
    assert "--clobber" not in text


def test_source_distribution_includes_readme_routed_public_content() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        config = tomllib.load(handle)

    includes = set(config["tool"]["hatch"]["build"]["targets"]["sdist"]["include"])
    assert {
        "/ARCHITECTURE.md",
        "/CONTRIBUTING.md",
        "/DESIGN.md",
        "/RELIABILITY.md",
        "/SECURITY.md",
        "/assets",
        "/docs",
        "/examples",
    } <= includes


def test_dependabot_and_precommit_cover_declared_supply_chain() -> None:
    dependabot = yaml.safe_load(
        (REPO_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    )
    ecosystems = {entry["package-ecosystem"] for entry in dependabot["updates"]}
    assert ecosystems == {"uv", "github-actions", "pre-commit"}

    precommit = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert len(FULL_SHA_PRECOMMIT.findall(precommit)) == len(ANY_PRECOMMIT_REV.findall(precommit))
    for hook in (
        "check-github-workflows",
        "detect-private-key",
        "detect-secrets",
        "ruff-check",
        "ruff-format",
        "uv-lock",
    ):
        assert f"id: {hook}" in precommit


def test_public_example_is_a_real_strict_spec() -> None:
    example = REPO_ROOT / "examples" / "generic-symbolic.yaml"

    spec = hop.load_spec(example)
    compilation = hop.compile(spec)

    assert compilation.spec.design_id == "example-symbolic"
    assert compilation.plan.payload_sequence == "NRY"


def test_readme_and_quickstart_use_real_inputs_and_distinct_outputs() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    quickstart = (REPO_ROOT / "docs" / "guides" / "quickstart.md").read_text(encoding="utf-8")

    assert 'compilation.write("build/demo-python")' in readme
    assert "--spec examples/generic-symbolic.yaml" in quickstart
    assert 'compilation.write("build/symbolic-python")' in quickstart


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


def test_source_layout_has_explicit_sprawl_limits() -> None:
    source_root = REPO_ROOT / "src" / "hop_design"
    package_dirs = [source_root, *sorted(path for path in source_root.rglob("*") if path.is_dir())]

    for directory in package_dirs:
        modules = list(directory.glob("*.py"))
        assert len(modules) <= 25, f"{directory.relative_to(REPO_ROOT)} has too many flat modules"
        for module in modules:
            line_count = len(module.read_text(encoding="utf-8").splitlines())
            assert line_count <= 350, f"{module.relative_to(REPO_ROOT)} is a monolith"
