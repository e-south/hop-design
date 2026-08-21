from __future__ import annotations

import re

import pytest

import hop_design as hop


def test_compile_exact_sequence_through_resolved_plan() -> None:
    compilation = hop.compile(sequence="ACGT", design_id="demo-exact")

    assert compilation.plan.payload_sequence == "ACGT"
    assert compilation.plan.paired_payload_sequence == "ACGT"
    assert compilation.plan.hairpin_encoding_insert.sequence == "GACGTGTTTCACGTC"
    assert (
        compilation.plan.source_oligo.sequence == compilation.plan.hairpin_encoding_insert.sequence
    )
    assert [feature.role for feature in compilation.plan.hairpin_encoding_insert.features] == [
        "basal_left_arm",
        "payload",
        "foldback_junction",
        "paired_payload",
        "basal_right_arm",
    ]
    assert re.fullmatch(r"hop:plan/demo-exact/[0-9a-f]{16}", compilation.plan.plan_id)
    assert compilation.report.status == "valid"


def test_compile_degenerate_sequence_without_implicit_expansion() -> None:
    compilation = hop.compile(sequence="NRY", design_id="demo-symbolic")

    assert compilation.spec.payload.kind == "degenerate"
    assert compilation.plan.payload_sequence == "NRY"
    assert compilation.plan.paired_payload_sequence == "RYN"
    assert compilation.plan.hairpin_encoding_insert.sequence == "GNRYGTTTCRYNC"
    assert compilation.plan.hairpin_encoding_insert.is_symbolic


def test_explicit_spec_and_sequence_convenience_are_observationally_equivalent() -> None:
    spec = hop.create_spec(sequence="ACGT", design_id="demo-equivalent")

    from_spec = hop.compile(spec)
    from_sequence = hop.compile(sequence="ACGT", design_id="demo-equivalent")

    assert from_spec.spec == from_sequence.spec
    assert from_spec.plan == from_sequence.plan
    assert from_spec.bundle == from_sequence.bundle
    assert from_spec.artifacts == from_sequence.artifacts


def test_compile_rejects_ambiguous_call_shape() -> None:
    spec = hop.create_spec(sequence="ACGT", design_id="demo")

    with pytest.raises(TypeError, match="exactly one"):
        hop.compile(spec, sequence="ACGT")

    with pytest.raises(TypeError, match="exactly one"):
        hop.compile()

    with pytest.raises(TypeError, match="only valid with"):
        hop.compile(spec, design_id="replacement")


def test_public_check_uses_the_same_locked_catalog_resolution() -> None:
    spec = hop.create_spec(sequence="ACGT", design_id="demo")

    assert hop.check(spec).status == "valid"
