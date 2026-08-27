"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_substrate_spaces.py

Validates the scientist-facing substrate-space specification and symbolic preview.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import hop_design as hop
import hop_design.spaces as spaces
from hop_design.design.space.authority import assignment_text
from hop_design.design.spaces import SubstrateMemberCompilationError
from hop_design.models.design_space import HairpinDesignMember, VariableAssignment


def _space_data(*, variable: str = "NNN", max_members: int = 64) -> dict[str, object]:
    return {
        "schema": "hop/substrate-space/v1",
        "name": "fixed-site-three-base-context",
        "context": {
            "question": "How does activity vary across paired context positions?",
            "activity": "internal DNA-binding or processing activity",
            "readout": "sequence-indexed downstream assay",
        },
        "payload": {
            "segments": [
                {"fixed": "ACTG"},
                {"variable": variable, "name": "context"},
                {"fixed": "GATC", "name": "recognition-site"},
            ]
        },
        "hairpin": {"defaults_ref": "hop:defaults/generic-hairpin-design@2"},
        "enumeration": {"mode": "exhaustive", "max_members": max_members},
    }


def test_spaces_facade_is_an_exact_allowlist() -> None:
    assert spaces.__all__ == [
        "HairpinDesignSet",
        "SubstrateSpacePreview",
        "SubstrateSpaceSpec",
        "VerifiedHairpinDesignSet",
        "compile_space",
        "load_verified_design_set",
        "preview_space",
    ]
    for name in spaces.__all__:
        assert not hasattr(hop, name)


def test_preview_reports_one_complete_bounded_space_without_enumerating_members() -> None:
    spec = spaces.SubstrateSpaceSpec.model_validate(_space_data())

    preview = spaces.preview_space(spec)

    assert preview.state == "ready"
    assert preview.authored_payload == "ACTGNNNGATC"
    assert preview.derived_paired_payload == "GATCNNNCAGT"
    assert preview.variable_positions == (5, 6, 7)
    assert preview.variable_domains == (
        ("A", "C", "G", "T"),
        ("A", "C", "G", "T"),
        ("A", "C", "G", "T"),
    )
    assert preview.theoretical_cardinality == 64
    assert preview.max_members == 64
    assert preview.message is None
    assert not hasattr(preview, "members")


def test_preview_blocks_a_valid_space_above_its_explicit_bound() -> None:
    spec = spaces.SubstrateSpaceSpec.model_validate(_space_data(variable="NNNNNN", max_members=256))

    preview = spaces.preview_space(spec)

    assert preview.state == "blocked"
    assert preview.theoretical_cardinality == 4096
    assert preview.max_members == 256
    assert preview.message == (
        "This valid specification defines 4096 exact assignments. "
        "Compilation is blocked by max_members=256."
    )


def test_preview_marks_an_unresolved_defaults_reference_invalid() -> None:
    data = _space_data()
    data["hairpin"] = {"defaults_ref": "hop:defaults/unknown@1"}
    spec = spaces.SubstrateSpaceSpec.model_validate(data)

    preview = spaces.preview_space(spec)

    assert preview.state == "invalid"
    assert preview.message == (
        "Unknown defaults reference 'hop:defaults/unknown@1'; "
        "locked catalog supports 'hop:defaults/generic-hairpin-design@2'."
    )


def test_spec_reports_the_member_bound_as_an_implementation_ceiling() -> None:
    with pytest.raises(
        ValidationError,
        match="max_members cannot exceed the current implementation ceiling of 100,000",
    ):
        spaces.SubstrateSpaceSpec.model_validate(_space_data(max_members=100_001))


def test_spec_rejects_a_second_authored_arm_and_noncanonical_fixed_bases() -> None:
    second_arm = _space_data()
    second_arm["payload"] = {
        "segments": [{"fixed": "ACTG"}, {"variable": "NNN"}, {"fixed": "GATC"}],
        "paired_segments": [{"fixed": "GATC"}, {"variable": "NNN"}, {"fixed": "CAGT"}],
    }
    with pytest.raises(ValidationError, match="paired_segments"):
        spaces.SubstrateSpaceSpec.model_validate(second_arm)

    noncanonical = _space_data()
    noncanonical["payload"] = {"segments": [{"fixed": "ACNG"}]}
    with pytest.raises(ValidationError, match="exact DNA"):
        spaces.SubstrateSpaceSpec.model_validate(noncanonical)


def test_segment_names_are_optional_but_unique() -> None:
    data = _space_data()
    data["payload"] = {
        "segments": [
            {"fixed": "ACTG", "name": "context"},
            {"variable": "NNN", "name": "context"},
        ]
    }

    with pytest.raises(ValidationError, match="Segment names must be unique"):
        spaces.SubstrateSpaceSpec.model_validate(data)


def test_member_bundle_paths_are_confined_to_the_collection_member_root() -> None:
    member = {
        "canonical_ordinal": 1,
        "variable_assignment": ({"position": 1, "base": "A"},),
        "exact_payload": "A",
        "derived_paired_payload": "T",
        "exact_hairpin_length": 19,
        "exact_encoding_digest": f"sha256:{'0' * 64}",
        "member_bundle_id": "hop:bundle/member/example",
        "member_bundle_path": "../outside",
        "disposition": "canonical",
    }

    with pytest.raises(ValidationError, match="members/<member-id>"):
        HairpinDesignMember.model_validate(member)


def test_member_compilation_error_identifies_the_authored_assignment() -> None:
    spec = spaces.SubstrateSpaceSpec.model_validate(_space_data(variable="RYN", max_members=16))
    assignments = (
        VariableAssignment(position=5, base="A"),
        VariableAssignment(position=6, base="G"),
        VariableAssignment(position=7, base="T"),
    )

    assert assignment_text(spec, assignments) == "context=AGT"
    error = SubstrateMemberCompilationError(
        ordinal=7,
        total=16,
        assignment=assignment_text(spec, assignments),
        reason="HOP design is infeasible: HOP-EXAMPLE-001",
    )

    assert str(error) == (
        "Compilation stopped at assignment 7 of 16.\n"
        "Assignment: context=AGT\n"
        "Reason: HOP design is infeasible: HOP-EXAMPLE-001\n"
        "No output package was committed."
    )
