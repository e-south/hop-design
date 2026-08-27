"""
--------------------------------------------------------------------------------
HOP Design
tests/integration/test_space_review.py

Validates the offline scientific review and its claim-bounded responsive surface.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
from pathlib import Path

from hop_design.spaces import SubstrateSpaceSpec, compile_space


def _review_spec() -> SubstrateSpaceSpec:
    return SubstrateSpaceSpec.model_validate(
        {
            "schema": "hop/substrate-space/v1",
            "name": "review-tracer",
            "context": {
                "question": "How does activity vary across one paired context position?",
                "activity": "internal DNA-binding or processing activity",
                "readout": "sequence-indexed downstream assay",
            },
            "payload": {
                "segments": [
                    {"fixed": "ACTG", "name": "left-context"},
                    {"variable": "N", "name": "context"},
                    {"fixed": "GATC", "name": "recognition-site"},
                ]
            },
            "hairpin": {"defaults_ref": "hop:defaults/generic-hairpin-design@2"},
            "enumeration": {"mode": "exhaustive", "max_members": 4},
        }
    )


def test_review_is_one_self_contained_claim_bounded_scientific_story(tmp_path: Path) -> None:
    output = tmp_path / "review"
    compile_space(_review_spec(), destination=output)
    review = (output / "review.html").read_text(encoding="utf-8")

    headings = (
        "Summary",
        "Substrate definition",
        "Designs",
        "Evidence and handoff",
    )
    assert tuple(review.index(heading) for heading in headings) == tuple(
        sorted(review.index(heading) for heading in headings)
    )
    assert "4 exact hairpin designs" in review
    assert "Complete: 4/4 · 4 unique · 0 duplicates" in review
    assert "How does activity vary across one paired context position?" in review
    assert "Digital design was verified." in review
    assert "Named-method and destination compatibility were not evaluated" in review
    assert "physical construction, QC, and biological activity were not recorded" in review
    assert "Named construction method</td><td>Not evaluated" in review
    assert "Physical construction</td><td>Not recorded" in review
    assert "Quality control</td><td>Not recorded" in review
    assert "Biological activity</td><td>Not recorded" in review

    assert "https://" not in review
    assert "http://" not in review
    assert "<script src=" not in review
    assert '<link rel="icon" href="data:,">' in review
    assert "min-width:960" not in review.replace(" ", "")
    assert "overflow-x:auto" in review.replace(" ", "")
    assert "#design-table { min-width:56rem; }" in review
    assert "@media (max-width: 768px)" in review

    manifest = json.loads((output / "bundle" / "manifest.json").read_text(encoding="utf-8"))
    for dimension, claim in manifest["claim_status"].items():
        assert f'data-claim="{dimension}"' in review
        assert f'data-status="{claim["status"]}"' in review
        if "basis" in claim:
            assert f'data-basis="{claim["basis"]}"' in review


def test_review_anatomy_labels_fixed_variable_and_physical_pairing_without_color_alone(
    tmp_path: Path,
) -> None:
    output = tmp_path / "anatomy"
    compile_space(_review_spec(), destination=output)
    review = (output / "review.html").read_text(encoding="utf-8")

    assert "left-context · fixed" in review
    assert "context · variable A/C/G/T" in review
    assert "recognition-site · fixed" in review
    assert 'class="base fixed"' in review
    assert 'class="base variable"' in review
    assert 'class="pair-line"' in review
    assert '<div class="duplex-stack">' in review
    assert "The paired arm is displayed 3&prime;&rarr;5&prime; beneath the authored arm" in review
    assert "stored 5&prime;&rarr;3&prime; sequence is its reverse complement" in review
    assert (
        "Paired payload:</strong> derived from the authored payload by reverse complement" in review
    )
    assert "Hairpin context:</strong> supplied by the selected" in review
    assert "GTTTC foldback junction (TTT turn)" in review
    assert "one-base-pair G:C basal junction" in review
    assert "Pairing is derived automatically using" not in review


def test_review_table_is_searchable_and_technical_identity_is_collapsed(tmp_path: Path) -> None:
    output = tmp_path / "table"
    compile_space(_review_spec(), destination=output)
    review = (output / "review.html").read_text(encoding="utf-8")

    assert '<label for="design-search">Filter exact designs</label>' in review
    assert 'id="design-search"' in review
    assert 'data-design-row="true"' in review
    assert 'data-sort-column="0"' in review
    assert 'data-sort-column="5"' in review
    assert "addEventListener(&quot;input&quot;" not in review
    assert 'addEventListener("input"' in review
    assert 'addEventListener("click"' in review
    assert "Designs are listed in deterministic 5&prime;&rarr;3&prime; assignment order" in review
    assert "Ordinal is not rank." in review
    assert "<details><summary>Technical details</summary>" in review
    assert "HOP version:" in review
    assert "Schema IDs:" in review
    assert "Resolved anatomy:" in review
    assert "Canonical space digest:" in review
    assert "Verification:" in review
    assert "Member authority root:" in review
    assert "normalized authored specification" in review
    assert "member_bundle_id" not in review
    for prohibited in (
        "assay-ready",
        "buildable",
        "fold correctly",
        "functional designs",
        "HOP optimizes",
        "physical library",
    ):
        assert prohibited not in review
