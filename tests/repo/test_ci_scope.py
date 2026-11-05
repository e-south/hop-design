"""Only known README artwork may avoid molecular replay in routine CI."""

import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci_scope.py"


def select(paths):
    return runpy.run_path(str(SCRIPT))["classify_paths"](paths)


def test_only_explicit_readme_artwork_uses_the_fast_path():
    assert select(["README.md", "assets/hop-design-banner.svg"]) == "artwork"
    assert (
        select(["assets/hop-design-banner.png", "assets/fonts/OFL-IBM-Plex-Sans.txt"]) == "artwork"
    )


@pytest.mark.parametrize(
    "path",
    [
        "src/hop_design/__init__.py",
        "src/hop_design/assets/variant_explorer/atlas_view.js",
        "assets/examples/basal-junction.svg",
        ".github/workflows/ci.yaml",
        "scripts/ci_scope.py",
        "tests/repo/test_ci_scope.py",
        "pyproject.toml",
        "uv.lock",
        "docs/guides/discover-designs.md",
        "AGENTS.md",
        "unknown-file",
        "README.md\nnew-code.py",
    ],
)
def test_mixed_or_unrecognized_changes_require_the_full_gate(path):
    assert select(["README.md", path]) == "full"


def test_empty_changes_do_not_establish_an_artwork_only_change():
    assert select([]) == "full"


@pytest.mark.parametrize(
    "paths,expected",
    [
        (["src/hop_design/kernel/base.py", "tests/unit/test_base.py"], "routine"),
        (["docs/guides/quickstart.md"], "routine"),
        (["src/hop_design/cli.py"], "extended"),
        (["src/hop_design/cli/commands.py"], "extended"),
        (["src/hop_design/assets/editor.js"], "extended"),
        (["pyproject.toml"], "extended"),
        (["uv.lock"], "extended"),
        (["scripts/distribution/smoke.py"], "extended"),
        ([".github/workflows/ci.yaml"], "extended"),
        (["src/hop_design/kernel/base.py", "unknown"], "extended"),
        ([], "extended"),
    ],
)
def test_distribution_mode_keeps_sensitive_and_unknown_changes_extended(paths, expected):
    assert runpy.run_path(str(SCRIPT))["distribution_mode"](paths) == expected


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    git(tmp_path, "config", "user.name", "CI contract test")
    (tmp_path / "source.py").write_text("print('source')\n")
    git(tmp_path, "add", "source.py")
    git(tmp_path, "commit", "-qm", "baseline")
    return tmp_path, git(tmp_path, "rev-parse", "HEAD")


def execute(repo, event, base, tmp_path):
    output = tmp_path / "scope-output"
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        env={**os.environ, "CI_EVENT": event, "CI_BASE_SHA": base, "GITHUB_OUTPUT": str(output)},
        capture_output=True,
        text=True,
        check=False,
    )
    return result, output.read_text() if output.exists() else ""


def test_real_readme_diff_is_classified_and_reported(repo, tmp_path):
    path, base = repo
    (path / "README.md").write_text("Read the guide.\n")
    git(path, "add", "README.md")
    git(path, "commit", "-qm", "readme")
    result, output = execute(path, "pull_request", base, tmp_path)
    assert result.returncode == 0, result.stderr
    assert output == "scope=artwork\ndistribution=routine\n"


def test_real_source_diff_preserves_full_suite_with_routine_installation(repo, tmp_path):
    path, base = repo
    source = path / "src/hop_design/kernel/base.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n")
    git(path, "add", ".")
    git(path, "commit", "-qm", "ordinary source")
    result, output = execute(path, "pull_request", base, tmp_path)
    assert result.returncode == 0, result.stderr
    assert output == "scope=full\ndistribution=routine\n"


def test_code_renamed_to_readme_cannot_hide_a_source_deletion(repo, tmp_path):
    path, base = repo
    git(path, "mv", "source.py", "README.md")
    git(path, "commit", "-qm", "rename")
    result, output = execute(path, "push", base, tmp_path)
    assert result.returncode == 0
    assert output == "scope=full\ndistribution=extended\n"


@pytest.mark.parametrize(
    "event,base", [("workflow_dispatch", ""), ("push", "0" * 40), ("push", "f" * 40)]
)
def test_manual_and_missing_base_use_full_verification(repo, tmp_path, event, base):
    result, output = execute(repo[0], event, base, tmp_path)
    assert result.returncode == 0
    assert output == "scope=full\ndistribution=extended\n"


def test_invalid_revision_fails_before_emitting_a_successful_scope(repo, tmp_path):
    result, output = execute(repo[0], "push", "--help", tmp_path)
    assert result.returncode != 0
    assert "CI base must be a complete commit SHA" in result.stderr
    assert not output


def test_symlink_in_artwork_path_requires_full_verification(repo, tmp_path):
    path, base = repo
    (path / "README.md").symlink_to("source.py")
    git(path, "add", "README.md")
    git(path, "commit", "-qm", "symlink")
    result, output = execute(path, "pull_request", base, tmp_path)
    assert result.returncode == 0
    assert output == "scope=full\ndistribution=extended\n"
