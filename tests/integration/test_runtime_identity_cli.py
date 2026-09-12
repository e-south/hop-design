from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design.cli import app
from hop_design.design import runtime


def test_runtime_identity_is_machine_readable_and_does_not_contain_local_paths() -> None:
    result = CliRunner().invoke(app, ["identity"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema"] == "hop/runtime-identity/v1"
    assert payload["distribution"] == "hop-design"
    assert payload["version"] == version("hop-design")
    assert payload["package_content"].startswith("sha256:")
    assert "hop/design-report/v1" in payload["report_schemas"]
    assert "file:" not in result.output
    assert str(Path.home()) not in result.output


@pytest.mark.parametrize(
    "metadata, expected",
    [
        (None, {"kind": "unrecorded"}),
        ({"url": "file:///example/source", "dir_info": {"editable": True}}, {"kind": "local"}),
        (
            {
                "url": "https://example.org/tool.git?temporary=value#fragment",
                "vcs_info": {"vcs": "git", "commit_id": "a" * 40},
            },
            {"kind": "git", "url": "https://example.org/tool.git", "commit": "a" * 40},
        ),
        (
            {
                "url": "https://example.org/tool.whl",
                "archive_info": {"hashes": {"sha256": "b" * 64}},
            },
            {
                "kind": "archive",
                "url": "https://example.org/tool.whl",
                "hashes": {"sha256": "b" * 64},
            },
        ),
        (
            {
                "url": "https://reader@example.org/tool.git",
                "vcs_info": {"vcs": "git", "commit_id": "a" * 40},
            },
            {"kind": "unrecorded"},
        ),
    ],
)
def test_runtime_identity_separates_installation_metadata_from_actual_content(
    monkeypatch: pytest.MonkeyPatch, metadata: dict | None, expected: dict
) -> None:
    class Metadata:
        def read_text(self, name: str) -> str | None:
            assert name == "direct_url.json"
            return json.dumps(metadata) if metadata is not None else None

    actual = runtime.producer_identity()["package_content"]
    monkeypatch.setattr(runtime, "distribution", lambda name: Metadata())
    report = runtime.runtime_identity()
    assert report["source"] == expected
    assert report["package_content"] == actual
    assert "hop/linear-source-method-report/v1" in report["report_schemas"]
