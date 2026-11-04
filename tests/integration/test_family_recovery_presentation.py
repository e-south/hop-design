"""An explicit preference is recorded and checked, never inferred from enumeration order."""

import json
from xml.etree import ElementTree as ET

import pytest

from hop_design import construction
from tests.integration.test_family_reconciliation import continued_family as continued_family


def test_recovery_shows_local_choices_preference_and_complete_product(continued_family, tmp_path):
    revised = construction.reconcile_construction_family(
        continued_family / "saved",
        source_member="choices",
        outcome_path=continued_family / "continued",
        preferred_loop_nt=4,
    ).write(tmp_path / "revised")
    report = construction.project_construction_family_report(revised)
    summary = json.loads(report.json_bytes)
    assert summary["recovery"]["preferred_loop_nt"] == 4
    assert {c["loop_nt"] for c in summary["recovery"]["foldback_choices"]} == {3, 4}
    assert sum(c["selected"] for c in summary["recovery"]["foldback_choices"]) == 1
    out = report.write(tmp_path / "report")
    root = ET.parse(out / "report.svg").getroot()
    text = " ".join(root.itertext())
    assert "Local choices" in text and "Declared preference: 4-nt loop" in text
    assert "selection-required" in text and "Complete preparation" in text
    assert "not complete preparations" in text
    assert "No baseline comparison" not in text
    assert float(root.attrib["viewBox"].split()[3]) <= 760


def test_reconciliation_rejects_preference_that_does_not_match_selected_molecule(
    continued_family, tmp_path
):
    with pytest.raises(ValueError, match="preference"):
        construction.reconcile_construction_family(
            continued_family / "saved",
            source_member="choices",
            outcome_path=continued_family / "continued",
            preferred_loop_nt=5,
        ).write(tmp_path / "wrong")
    assert not (tmp_path / "wrong").exists()


def test_report_rejects_rehashed_but_false_recovery_preference(continued_family, tmp_path):
    from hop_design.serialization import canonical_json_bytes, sha256_digest

    revised = construction.reconcile_construction_family(
        continued_family / "saved",
        source_member="choices",
        outcome_path=continued_family / "continued",
        preferred_loop_nt=4,
    ).write(tmp_path / "revised")
    summary = revised / "summary.json"
    data = json.loads(summary.read_text())
    data["revision"]["preferred_loop_nt"] = 5
    summary.write_bytes(canonical_json_bytes(data))
    manifest = revised / "manifest.json"
    inventory = json.loads(manifest.read_text())
    inventory["artifacts"]["summary.json"] = sha256_digest(summary.read_bytes())
    manifest.write_bytes(canonical_json_bytes(inventory))
    with pytest.raises(ValueError, match="preference"):
        construction.project_construction_family_report(revised).write(tmp_path / "report")
    assert not (tmp_path / "report").exists()
