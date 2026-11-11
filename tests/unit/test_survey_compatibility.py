"""Compatibility is declared for exact code and remains bound to runtime inputs."""

import json

import pytest

from hop_design.design import runtime


def test_shipped_current_release_transition_targets_the_installed_sources():
    from hop_design.design.construction.surveys.storage.compatibility import _policy_bytes
    from hop_design.models.construction.surveys.compatibility import SurveyCompatibilityPolicy

    current = runtime.producer_identity()
    policy = SurveyCompatibilityPolicy.model_validate_json(_policy_bytes())
    for entry in policy.declarations:
        if entry.target_version == current["package_version"]:
            assert entry.target_code == current["package_code"], (
                "Qualify and update the exact target code before shipping this transition."
            )


def test_policy_bytes_change_the_producer_without_a_circular_code_digest(tmp_path, monkeypatch):
    package = tmp_path / "package"
    (package / "design").mkdir(parents=True)
    (package / "assets").mkdir()
    (package / "design/runtime.py").write_text("# synthetic implementation\n")
    policy = package / "assets/checkpoint-compatibility.json"
    policy.write_text('{"schema":"hop.survey-compatibility/v1","declarations":[]}\n')
    monkeypatch.setattr(runtime, "__file__", str(package / "design/runtime.py"))
    first = runtime.producer_identity()
    policy.write_text(policy.read_text() + "\n")
    second = runtime.producer_identity()
    assert first["package_code"] == second["package_code"]
    assert first["package_content"] != second["package_content"]
    policy.unlink()
    with pytest.raises(FileNotFoundError):
        runtime.producer_identity()


def test_only_exact_declared_packages_with_unchanged_runtime_are_compatible(monkeypatch):
    from hop_design.design.construction.surveys.storage import compatibility as module
    from hop_design.serialization import canonical_json_bytes, sha256_digest

    source = {
        "package_version": "1",
        "package_content": "sha256:" + "a" * 64,
        "python": "3.12.11",
        "pydantic": "2.13.5",
    }
    target = {
        **source,
        "package_version": "2",
        "package_content": "sha256:" + "b" * 64,
        "package_code": "sha256:" + "c" * 64,
    }
    declaration = {
        "schema": "hop.survey-compatibility/v1",
        "declarations": [
            {
                "source_version": "1",
                "source_content": source["package_content"],
                "target_version": "2",
                "target_code": target["package_code"],
                "computation_contract": "interface-survey/1",
            }
        ],
    }
    raw = json.dumps(declaration).encode()
    monkeypatch.setattr(module, "_policy_bytes", lambda: raw)
    approval = sha256_digest(canonical_json_bytes(declaration["declarations"][0]))
    assert module.authorize_transition(source, target) == approval
    declaration["declarations"].append({**declaration["declarations"][0], "target_version": "3"})
    raw = json.dumps(declaration).encode()
    assert module.authorize_transition(source, target) == approval
    for mapping, field in (
        (source, "package_content"),
        (source, "python"),
        (target, "package_code"),
        (target, "pydantic"),
    ):
        changed = {**mapping, field: "unapproved"}
        with pytest.raises(ValueError, match="compatibility"):
            module.authorize_transition(
                changed if mapping is source else source, changed if mapping is target else target
            )


def test_malformed_or_unknown_policy_is_rejected(monkeypatch):
    from hop_design.design.construction.surveys.storage import compatibility as module

    for raw in (
        b"{}",
        b'{"schema":"unknown","declarations":[]}',
        b'{"schema":"hop.survey-compatibility/v1","declarations":[],"skip":true}',
        b'{"schema":"unknown","schema":"hop.survey-compatibility/v1","declarations":[]}',
        b" " * 1_048_577,
    ):
        monkeypatch.setattr(module, "_policy_bytes", lambda raw=raw: raw)
        with pytest.raises(ValueError, match="compatibility"):
            module.authorize_transition({}, {})


def test_recorded_capture_accepts_legacy_and_policy_bound_producer_shapes():
    from hop_design.models.construction.editions.source import RecordedDesignSource

    current = runtime.producer_identity()
    legacy = {key: value for key, value in current.items() if key != "package_code"}
    assert RecordedDesignSource.complete_producer(legacy) == legacy
    assert RecordedDesignSource.complete_producer(current) == current
    for bad in ({**current, "skip": "true"}, {**current, "package_code": "wrong"}):
        with pytest.raises(ValueError):
            RecordedDesignSource.complete_producer(bad)
