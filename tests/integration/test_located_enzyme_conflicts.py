"""A failed complete continuation identifies the enzyme and its actual molecular site."""

import json
from pathlib import Path

from hop_design import construction


def test_unintended_site_has_molecular_coordinates_and_processing_state(tmp_path):
    value = json.loads(Path("examples/scaffold-comparison/methods.json").read_bytes())
    product = value["discovery"]["product"]
    product["stem_arm"] = "GGTCTC" + product["stem_arm"][6:]
    value["discovery"]["preparation_changes"]["release_enzyme_ids"] = [
        "example:enzyme/bsai-hfv2@1",
        "example:enzyme/bsmbi-v2@1",
    ]
    path = tmp_path / "conflict.json"
    path.write_text(json.dumps(value))
    packet = construction.execute_scaffold_comparison(path)
    summary = json.loads(packet.json_bytes)
    failure = next(
        f
        for f in summary["examined_failures"]
        if "global-actionable-site-conflict" in f["rejection_reasons"]
    )
    sites = failure["actionable_site_conflicts"]
    assert sites
    site = next(s for s in sites if s["enzyme_id"] == "example:enzyme/bsai-hfv2@1")
    assert site["recognition_sequence"] in ("GGTCTC", "GAGACC")
    assert site["stage_id"] and site["state_id"] and site["molecule_id"]
    assert site["recognition_end"] - site["recognition_start"] == 6
    assert site["coordinate_convention"] == "zero_based_half_open_reference_strand"
    assert "GGTCTC" in packet.report_text or "GAGACC" in packet.report_text
    assert "reference positions" in packet.report_text
    assert summary["sets"] == []
    assert any(o["release_method"] == "BsmBI-v2" for o in summary["options"])
