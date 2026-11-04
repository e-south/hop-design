"""Live feedback stays on stderr and never corrupts the machine-readable answer."""

import importlib
import json
import signal

from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app


def test_cli_progress_preserves_json_and_installs_cooperative_interrupt(monkeypatch, tmp_path):
    module = importlib.import_module("hop_design.commands.design")
    original = signal.getsignal(signal.SIGINT)

    def discover(*args, **kwargs):
        assert kwargs["should_stop"]() is False
        kwargs["on_progress"](
            construction.DiscoveryProgress(
                product="released_insert",
                phase="searching",
                evaluations=0,
                new_evaluations=0,
                evaluation_budget=2,
            )
        )
        signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
        assert kwargs["should_stop"]() is True
        return object()

    monkeypatch.setattr(construction, "discover_designs", discover)
    monkeypatch.setattr(module, "emit_choices", lambda *args: print('{"saved":true}'))
    result = CliRunner().invoke(
        app,
        [
            "design",
            "discover",
            "--stem",
            "ACGT",
            "--product",
            "released_insert",
            "--out",
            str(tmp_path / "result"),
            "--evaluations",
            "2",
            "--progress",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"saved": True}
    event = json.loads(result.stderr.splitlines()[0])
    assert event["schema"] == "hop.discovery-progress/v1"
    assert event["evaluations"] == 0
    assert "Stopping after the current" in result.stderr
    assert signal.getsignal(signal.SIGINT) == original


def test_cli_empty_cancel_is_explicit_without_traceback(monkeypatch, tmp_path):
    def cancelled(*args, **kwargs):
        raise construction.DiscoveryCancelled("Saved intent remains available to continue.")

    monkeypatch.setattr(construction, "discover_designs", cancelled)
    result = CliRunner().invoke(
        app,
        [
            "design",
            "discover",
            "--stem",
            "ACGT",
            "--product",
            "hairpin",
            "--out",
            str(tmp_path / "cancelled"),
            "--progress",
        ],
    )
    assert result.exit_code == 130
    assert "Saved intent remains available" in result.stderr
    assert "Traceback" not in result.output
