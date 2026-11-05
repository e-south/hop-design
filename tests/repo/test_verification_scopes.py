"""Verification scope is explicit; no narrow selection can become an empty full run."""

import os
import runpy
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_presentation_map_names_real_tests_and_rejects_stale_patterns(tmp_path):
    select = runpy.run_path(str(ROOT / "scripts/verification_tests.py"))["presentation_tests"]
    paths = select(ROOT)
    assert "tests/integration/test_molecular_atlas.py" in paths
    assert "tests/integration/test_design_progressive.py" not in paths
    assert "tests/integration/test_atlas_edition.py" not in paths
    assert "tests/integration/test_design_inspection_http.py" in paths
    assert "tests/integration/test_compact_preview_context.py" in paths
    assert "tests/unit/test_parameter_display_labels.py" in paths
    assert "tests/unit/test_choice_presentation.py" in paths
    assert "tests/integration/test_figure_display_projection.py" in paths
    assert len(paths) == len(set(paths))
    with pytest.raises(ValueError, match="matched no tests"):
        select(tmp_path)


def run_gate(tmp_path, *args, pytest_exit=0, installation_exit=0, audit_exit=0, selection=True):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "agent-verify").write_bytes((ROOT / "scripts/agent-verify").read_bytes())
    for name in ("agent-preflight", "precommit-all", "wheel-smoke"):
        (scripts / name).write_text(f'echo {name} >> "$GATE_LOG"\n')
    binary = tmp_path / "bin"
    binary.mkdir()
    uv = binary / "uv"
    uv.write_text(
        '#!/usr/bin/env bash\necho "uv $*" >> "$GATE_LOG"\n'
        'if [[ "$*" == *"verification_tests.py"* ]]; then\n'
        + ("echo tests/unit/test_recognition_ribbon.py\n" if selection else ":\n")
        + 'elif [[ "$*" == "run --locked pytest "* ]]; then exit "$PYTEST_EXIT";\n'
        + 'elif [[ "$*" == "run --locked pip-audit "* ]]; then exit "$AUDIT_EXIT";\n'
        + 'elif [[ "$*" == *"distribution/smoke.py"* ]]; then exit "$INSTALLATION_EXIT"; fi\n'
    )
    uv.chmod(0o755)
    node = binary / "node"
    node.write_text('#!/usr/bin/env bash\necho "node $*" >> "$GATE_LOG"\n')
    node.chmod(0o755)
    log = tmp_path / "gate.log"
    result = subprocess.run(
        ["bash", str(scripts / "agent-verify"), *args],
        env={
            **os.environ,
            "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}",
            "GATE_LOG": str(log),
            "PYTEST_EXIT": str(pytest_exit),
            "INSTALLATION_EXIT": str(installation_exit),
            "AUDIT_EXIT": str(audit_exit),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    return result, log.read_text() if log.exists() else ""


def test_presentation_scope_runs_views_and_browser_without_distribution(tmp_path):
    result, log = run_gate(tmp_path, "--scope", "presentation")
    assert result.returncode == 0, result.stderr
    assert "test_recognition_ribbon.py" in log
    assert "node --test" in log
    assert "wheel-smoke" not in log and "pip-audit" not in log
    assert "--cov=hop_design" not in log


def test_source_scope_keeps_all_source_tests_and_coverage(tmp_path):
    result, log = run_gate(tmp_path, "--scope", "source", "--workers", "2")
    assert result.returncode == 0, result.stderr
    assert "--cov=hop_design" in log and "--cov-report=xml:.artifacts/coverage.xml" in log
    assert "-n 2 --dist loadscope" in log
    assert "wheel-smoke" not in log


def test_verification_labels_stages_without_repeating_lint(tmp_path):
    result, log = run_gate(tmp_path, "--scope", "source")
    assert result.returncode == 0, result.stderr
    assert log.count("precommit-all") == 1
    assert "ruff check" not in log and "ruff format" not in log
    assert "START verification: source-tests" in result.stdout
    assert "PASSED verification: source-tests" in result.stdout
    timings = (tmp_path / ".artifacts/verification/stages.tsv").read_text().splitlines()
    assert timings[0] == "stage\tseconds\texit_code"
    assert [line.split("\t")[0] for line in timings[1:]] == [
        "preflight",
        "repository-hooks",
        "types",
        "compilation",
        "browser-tests",
        "source-tests",
    ]
    assert all(line.split("\t")[2] == "0" for line in timings[1:])


def test_failed_stage_retains_timing_and_exit_code(tmp_path):
    result, log = run_gate(tmp_path, "--scope", "source", pytest_exit=17)
    assert result.returncode == 17, result.stderr
    assert "FAILED verification: source-tests" in result.stdout
    timings = (tmp_path / ".artifacts/verification/stages.tsv").read_text().splitlines()
    assert timings[-1].split("\t")[::2] == ["source-tests", "17"]
    assert "wheel-smoke" not in log


def test_four_workers_use_the_same_tests_coverage_and_fixture_grouping(tmp_path):
    result, log = run_gate(tmp_path, "--scope", "source", "--workers", "4")
    assert result.returncode == 0, result.stderr
    assert "-n 4 --dist loadscope" in log
    assert "--cov=hop_design" in log and "--cov-report=xml:.artifacts/coverage.xml" in log
    assert "--junitxml=.artifacts/verification/source.xml" in log


def test_default_remains_the_complete_release_gate(tmp_path):
    result, log = run_gate(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "wheel-smoke" in log and "pip-audit" in log


def test_dependency_failure_stops_before_expensive_source_suite(tmp_path):
    result, log = run_gate(tmp_path, audit_exit=19)
    assert result.returncode == 19, result.stderr
    assert "pip-audit" in log
    assert "uv run --locked pytest" not in log and "wheel-smoke" not in log
    assert "--no-dev" not in log
    assert "--all-extras" in log and "--require-hashes" in log
    assert "FAILED verification: dependency-audit" in result.stdout


@pytest.mark.parametrize("exit_code", [0, 23])
def test_routine_installation_runs_once_and_propagates_failure(tmp_path, exit_code):
    result, log = run_gate(tmp_path, "--distribution", "routine", installation_exit=exit_code)
    assert result.returncode == exit_code, result.stderr
    assert "--cov=hop_design" in log and "pip-audit" in log
    assert log.count("scripts/distribution/smoke.py") == 1
    assert "wheel-smoke" not in log
    assert ("Agent verification: ok" in result.stdout) == (exit_code == 0)


@pytest.mark.parametrize(
    "args",
    [
        ("--scope", "typo"),
        ("--workers", "0"),
        ("--workers", "8"),
        ("--workers", "auto"),
        ("--distribution", "typo"),
        ("--scope", "source", "--distribution", "routine"),
        ("--unknown",),
    ],
)
def test_invalid_scope_or_unbounded_workers_fail_before_execution(tmp_path, args):
    result, log = run_gate(tmp_path, *args)
    assert result.returncode != 0
    assert not log


def test_empty_presentation_selection_cannot_run_the_entire_suite(tmp_path):
    result, log = run_gate(tmp_path, "--scope", "presentation", selection=False)
    assert result.returncode != 0
    assert "uv run --locked pytest" not in log


def test_scoped_test_failure_propagates(tmp_path):
    result, log = run_gate(tmp_path, "--scope", "presentation", pytest_exit=17)
    assert result.returncode == 17
    assert "wheel-smoke" not in log
