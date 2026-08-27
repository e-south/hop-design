"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_space_figures.py

Validates publication-oriented SVG projections of a verified substrate space.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

from hop_design.spaces import SubstrateSpaceSpec, compile_space


def _figure_spec() -> SubstrateSpaceSpec:
    return SubstrateSpaceSpec.model_validate(
        {
            "schema": "hop/substrate-space/v1",
            "name": "figure-tracer",
            "question": "How does activity vary across two paired context positions?",
            "payload": [
                {"fixed": "ACTG", "label": "left-context"},
                {"variable": "RY", "label": "paired-context"},
                {"fixed": "GATC", "label": "recognition-site"},
            ],
        }
    )


def _svg(path: Path) -> ElementTree.Element:
    return ElementTree.fromstring(path.read_bytes())


def _text(root: ElementTree.Element) -> str:
    return " ".join(text.strip() for text in root.itertext() if text.strip())


def test_compile_space_writes_three_scientific_svg_projections(tmp_path: Path) -> None:
    output = tmp_path / "figures"

    compile_space(_figure_spec(), destination=output)

    expected = {
        output / "figures" / "01-substrate-space.svg",
        output / "figures" / "02-design-set.svg",
        output / "handoff" / "scientific-receipt.svg",
    }
    assert all(path.is_file() for path in expected)
    assert all(_svg(path).tag == "{http://www.w3.org/2000/svg}svg" for path in expected)


def test_substrate_space_figure_states_the_rule_and_complete_encoding(tmp_path: Path) -> None:
    output = tmp_path / "substrate-space"
    compiled = compile_space(_figure_spec(), destination=output)
    root = _svg(output / "figures" / "01-substrate-space.svg")
    text = _text(root)

    assert "One authored arm defines a complete paired substrate space." in text
    assert "R=A/G" in text
    assert "Y=C/T" in text
    assert "4 exact designs" in text
    assert "paired arm is derived by reverse complement" in text.lower()
    assert compiled.design_set.members[0].exact_payload in text
    assert compiled.design_set.members[0].derived_paired_payload in text


def test_design_set_figure_contains_every_member_without_ranking(tmp_path: Path) -> None:
    output = tmp_path / "design-set"
    compiled = compile_space(_figure_spec(), destination=output)
    root = _svg(output / "figures" / "02-design-set.svg")
    text = _text(root)
    members = [element for element in root.iter() if element.get("data-design-member") == "true"]

    assert "Exhaustive compilation preserves every valid member and its molecular identity." in text
    assert len(members) == compiled.design_set.enumerated_assignments
    assert {element.get("data-ordinal") for element in members} == {"1", "2", "3", "4"}
    assert {element.get("data-payload") for element in members} == {
        member.exact_payload for member in compiled.design_set.members
    }
    assert "Ordinal is deterministic replay order, not rank." in text
    assert "score" not in text.lower()
    assert "best" not in text.lower()


def test_scientific_receipt_renders_manifest_claim_status(tmp_path: Path) -> None:
    output = tmp_path / "receipt"
    compiled = compile_space(_figure_spec(), destination=output)
    root = _svg(output / "handoff" / "scientific-receipt.svg")
    text = _text(root)
    statuses = {
        element.get("data-evidence-dimension"): element.get("data-status")
        for element in root.iter()
        if element.get("data-evidence-dimension") is not None
    }

    assert (
        "The handoff distinguishes verified digital derivation from untested experimental claims."
        in text
    )
    assert compiled.design_set.design_set_id in text
    assert statuses == {
        dimension: claim.model_dump(mode="json")["status"]
        for dimension, claim in compiled.design_set.claim_status
    }
    assert "No physical construction, QC, or activity record is attached." in text
    assert "assay-ready" not in text.lower()
    assert "qc-passed" not in text.lower()
