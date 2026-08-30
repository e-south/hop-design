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


def _space_data(*, variable: str = "NNN") -> dict[str, object]:
    return {
        "schema": "hop/substrate-space/v1",
        "name": "fixed-site-three-base-context",
        "question": "How does activity vary across paired context positions?",
        "payload": [
            {"fixed": "ACTG"},
            {"variable": variable, "label": "context"},
            {"fixed": "GATC", "label": "recognition-site"},
        ],
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
    assert preview.compilation_limit == 256
    assert preview.message is None
    assert not hasattr(preview, "members")


def test_preview_blocks_a_valid_space_above_the_supported_release_envelope() -> None:
    spec = spaces.SubstrateSpaceSpec.model_validate(_space_data(variable="NNNNN"))

    preview = spaces.preview_space(spec)

    assert preview.state == "blocked"
    assert preview.theoretical_cardinality == 1024
    assert preview.compilation_limit == 256
    assert preview.message == (
        "This valid specification defines 1024 exact assignments. "
        "Compilation supports up to 256 designs in this release."
    )


def test_scientist_spec_rejects_hairpin_and_enumeration_policy() -> None:
    for field, value in (
        ("hairpin", {"defaults_ref": "hop:defaults/generic-hairpin-design@2"}),
        ("enumeration", {"mode": "exhaustive", "max_members": 64}),
    ):
        data = _space_data()
        data[field] = value
        with pytest.raises(ValidationError, match=field):
            spaces.SubstrateSpaceSpec.model_validate(data)


def test_spec_rejects_a_second_authored_arm_and_noncanonical_fixed_bases() -> None:
    second_arm = _space_data()
    second_arm["paired_payload"] = [
        {"fixed": "GATC"},
        {"variable": "NNN"},
        {"fixed": "CAGT"},
    ]
    with pytest.raises(ValidationError, match="paired_payload"):
        spaces.SubstrateSpaceSpec.model_validate(second_arm)

    noncanonical = _space_data()
    noncanonical["payload"] = [{"fixed": "ACNG"}]
    with pytest.raises(ValidationError, match="exact DNA"):
        spaces.SubstrateSpaceSpec.model_validate(noncanonical)


def test_segment_names_are_optional_but_unique() -> None:
    data = _space_data()
    data["payload"] = [
        {"fixed": "ACTG", "label": "context"},
        {"variable": "NNN", "label": "context"},
    ]

    with pytest.raises(ValidationError, match="Segment labels must be unique"):
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
    spec = spaces.SubstrateSpaceSpec.model_validate(_space_data(variable="RYN"))
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
