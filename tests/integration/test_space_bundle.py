"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_space_bundle.py

Validates complete, portable, and semantically verified hairpin design sets.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from hop_design.export.bundle import BundleIntegrityError
from hop_design.spaces import (
    SubstrateSpaceSpec,
    compile_space,
    load_verified_design_set,
)


def _space(
    *,
    name: str = "one-base-context",
    context_question: str = "Which paired context changes activity?",
    variable: str = "N",
    max_members: int = 4,
    segments: list[dict[str, str]] | None = None,
) -> SubstrateSpaceSpec:
    return SubstrateSpaceSpec.model_validate(
        {
            "schema": "hop/substrate-space/v1",
            "name": name,
            "context": {
                "question": context_question,
                "activity": "internal activity",
                "readout": "sequence-indexed assay",
            },
            "payload": {
                "segments": segments
                or [
                    {"fixed": "ACTG"},
                    {"variable": variable, "name": "context"},
                    {"fixed": "GATC", "name": "recognition-site"},
                ]
            },
            "hairpin": {"defaults_ref": "hop:defaults/generic-hairpin-design@2"},
            "enumeration": {"mode": "exhaustive", "max_members": max_members},
        }
    )


def _bundle_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_compile_space_writes_one_verified_complete_design_package(tmp_path: Path) -> None:
    output = tmp_path / "one-base"

    verified = compile_space(_space(), destination=output)

    assert verified.path == output / "bundle"
    assert verified.design_set.coverage == "complete"
    assert verified.design_set.theoretical_cardinality == 4
    assert verified.design_set.enumerated_assignments == 4
    assert verified.design_set.unique_designs == 4
    assert verified.design_set.duplicate_count == 0
    assert tuple(member.exact_payload for member in verified.design_set.members) == (
        "ACTGAGATC",
        "ACTGCGATC",
        "ACTGGGATC",
        "ACTGTGATC",
    )
    assert tuple(member.derived_paired_payload for member in verified.design_set.members) == (
        "GATCTCAGT",
        "GATCGCAGT",
        "GATCCCAGT",
        "GATCACAGT",
    )
    assert all(member.disposition == "canonical" for member in verified.design_set.members)
    assert len(verified.members) == 4
    assert {path.name for path in output.iterdir()} == {
        "bundle",
        "designs.csv",
        "review.html",
        "sequences.fasta",
        "source.yaml",
    }
    assert {path.name for path in (output / "bundle").iterdir()} == {
        "manifest.json",
        "members",
        "spec.json",
    }


def test_compile_space_authority_depends_only_on_normalized_molecular_rules(
    tmp_path: Path,
) -> None:
    first = compile_space(_space(context_question="Question one"), destination=tmp_path / "first")
    second = compile_space(
        _space(
            name="renamed-space",
            context_question="A different explanatory question",
            max_members=20,
            segments=[
                {"fixed": "A", "name": "left-a"},
                {"fixed": "CTG", "name": "left-b"},
                {"variable": "N", "name": "renamed-context"},
                {"fixed": "GA", "name": "right-a"},
                {"fixed": "TC", "name": "right-b"},
            ],
        ),
        destination=tmp_path / "second",
    )

    assert first.design_set == second.design_set
    assert _bundle_bytes(first.path) == _bundle_bytes(second.path)
    assert (tmp_path / "first" / "source.yaml").read_bytes() != (
        tmp_path / "second" / "source.yaml"
    ).read_bytes()

    canonical_spec = (first.path / "spec.json").read_text(encoding="utf-8")
    assert '"payload_domains"' in canonical_spec
    for presentation_field in ('"name"', '"context"', '"segments"', '"max_members"'):
        assert presentation_field not in canonical_spec


def test_compile_space_authority_changes_with_a_molecular_domain(tmp_path: Path) -> None:
    first = compile_space(_space(variable="N"), destination=tmp_path / "first")
    second = compile_space(
        _space(variable="R", max_members=4),
        destination=tmp_path / "second",
    )

    assert first.design_set.spec_digest != second.design_set.spec_digest
    assert first.design_set.design_set_id != second.design_set.design_set_id
    assert _bundle_bytes(first.path) != _bundle_bytes(second.path)


def test_load_verified_design_set_replays_every_member(tmp_path: Path) -> None:
    compiled = compile_space(_space(), destination=tmp_path / "design-set")

    loaded = load_verified_design_set(compiled.path)

    assert loaded.design_set == compiled.design_set
    assert not hasattr(loaded.spec, "context")
    assert tuple(member.bundle for member in loaded.members) == tuple(
        member.bundle for member in compiled.members
    )


def test_design_set_manifest_owns_the_complete_claim_status(tmp_path: Path) -> None:
    compiled = compile_space(_space(), destination=tmp_path / "design-set")

    assert compiled.design_set.claim_status.model_dump(mode="json") == {
        "space_accounting": {
            "status": "complete",
            "basis": "all_declared_assignments_enumerated",
        },
        "digital_design": {
            "status": "verified",
            "basis": "all_unique_member_authorities_replay_verified",
        },
        "named_method": {"status": "not_evaluated"},
        "destination_compatibility": {"status": "not_evaluated"},
        "physical_construction": {"status": "not_recorded"},
        "quality_control": {"status": "not_recorded"},
        "biological_activity": {"status": "not_recorded"},
    }


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda manifest: manifest.pop("claim_status"), "claim_status"),
        (
            lambda manifest: manifest["claim_status"]["physical_construction"].update(
                {"status": "complete"}
            ),
            "physical_construction",
        ),
    ],
)
def test_design_set_verification_rejects_missing_or_corrupt_claim_status(
    tmp_path: Path,
    mutate: Callable[[dict[str, Any]], object],
    expected: str,
) -> None:
    compiled = compile_space(_space(), destination=tmp_path / "design-set")
    manifest_path = compiled.path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutate(manifest)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(BundleIntegrityError, match=expected):
        load_verified_design_set(compiled.path)


def test_projection_changes_do_not_change_design_set_authority(tmp_path: Path) -> None:
    output = tmp_path / "design-set"
    compiled = compile_space(_space(), destination=output)
    (output / "review.html").write_text("presentation-only", encoding="utf-8")

    loaded = load_verified_design_set(output / "bundle")

    assert loaded.design_set == compiled.design_set


def test_design_set_verification_detects_member_mutation(tmp_path: Path) -> None:
    compiled = compile_space(_space(), destination=tmp_path / "design-set")
    member_fasta = next(compiled.path.glob("members/*/hairpin-encoding.fasta"))
    member_fasta.write_text(">changed\nAAAA\n", encoding="utf-8")

    with pytest.raises(BundleIntegrityError, match="digest mismatch"):
        load_verified_design_set(compiled.path)


def test_compile_space_is_create_only_and_blocked_without_partial_output(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError, match="Refusing to replace"):
        compile_space(_space(), destination=existing)

    data = _space().model_dump(mode="json", by_alias=True)
    data["enumeration"]["max_members"] = 3
    blocked = SubstrateSpaceSpec.model_validate(data)
    destination = tmp_path / "blocked"
    with pytest.raises(ValueError, match="above max_members=3"):
        compile_space(blocked, destination=destination)
    assert not destination.exists()
