"""Readers reach products and preparations before the technical evidence ledger."""

import json
from xml.etree import ElementTree as ET

from hop_design import construction
from tests.integration.test_construction_family_report import family_capture as family_capture


def test_retrieval_and_comparison_control_precede_execution_details(family_capture):
    packet = construction.project_construction_family_report(
        family_capture / "executed", selection=family_capture / "set.json", baseline="loop3"
    )
    text = packet.report_text
    assert text.index("## Retrieve") < text.index("Effective geometry domains")
    assert text.index("loop4/choices/0/preparation/report.md") < text.index("Local coverage")
    assert text.index("## Comparison controls") < text.index("Search bounds")
    assert "Observed agreement" in text
    assert "Required and verified" in text
    assert "Not assessed" in text
    assert "selected/oligo-uses.csv" in text
    assert "Intended comparison: Loop nucleotide count" in text
    assert "Intended variation; observed difference" in text
    assert json.loads(packet.json_bytes)["compared_properties"] == ["loop_nt"]


def test_single_selected_report_names_the_family_member_and_selection_alias(
    family_capture, tmp_path
):
    request = json.loads((family_capture / "set.json").read_text())
    request["members"] = request["members"][:1]
    member = request["members"][0]
    member["name"] = "reference-design"
    for key in ("bundle_path", "selection_path"):
        member[key] = str(family_capture / member[key])
    request["baseline"] = member["name"]
    request["compared_properties"] = []
    path = tmp_path / "single.json"
    path.write_text(json.dumps(request))
    packet = construction.project_construction_family_report(
        family_capture / "executed", selection=path
    )
    text = packet.report_text
    assert "Single selected molecule; between-member agreement is not assessed" in text
    assert "Selected as reference-design" in text
    assert "Observed agreement" not in text
    assert "Required and verified" not in text


def test_failed_request_and_explicit_alternative_share_one_compact_page(family_capture, tmp_path):
    packet = construction.project_construction_family_report(
        family_capture / "executed",
        selection=family_capture / "set.json",
        baseline="loop3",
        edits=(("short-primer", "loop3"),),
    )
    out = packet.write(tmp_path / "report")
    pages = sorted((out / "pages").glob("*.svg"))
    assert len(pages) == 2
    first = ET.parse(pages[0]).getroot()
    assert "Reference scaffold" in " ".join(first.itertext())
    second = ET.parse(pages[1]).getroot()
    text = " ".join(second.itertext())
    assert "13" in text and "14" in text and "7 bp" in text
    assert float(second.attrib["viewBox"].split()[3]) <= 650
    assert sum(e.get("id") == "hairpin-shape" for e in second.iter()) == 1
    span = next(e for e in second.iter() if e.get("id") == "primer-span-boundary")
    assert span.get("data-available-nt") == "13"
    assert span.get("data-required-nt") == "14"
    assert (
        span.get("data-field")
        == "materialization.source_preparation.reverse_primer.annealing_length_nt"
    )
    assert "Requested source span" in text
    assert json.loads(packet.json_bytes)["members"][-1]["choices"] == []
