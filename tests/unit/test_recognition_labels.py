"""Every physical enzyme footprint has its own nearby, addressed name."""

import json
from types import SimpleNamespace as NS
from xml.etree import ElementTree as ET

from hop_design.export.construction.molecular.recognition_sites import recognition_site_overlays


def test_repeated_sites_keep_both_addressed_footprints_and_names():
    sites = []
    points = {("strand", i): (100 + i * 16, 160) for i in range(20)}
    for index, start in enumerate((0, 12)):
        addresses = [NS(strand_id="strand", index=i) for i in range(start, start + 5)]
        sites.append(
            NS(
                site_id=f"site-{index}",
                role="basal_nick",
                enzyme_name="Nickase",
                orientation="forward",
                presence="complete",
                substrate_eligibility="eligible",
                orientation_path=addresses,
                recognition=addresses,
            )
        )
    projection = NS(operations=(), recognition_sites=sites, state=NS(state_id="state"))
    root = ET.fromstring("<svg>" + recognition_site_overlays(projection, points) + "</svg>")
    assert len([e for e in root.iter() if e.get("data-site-id")]) == 2
    assert len([e for e in root.iter() if e.get("data-members")]) == 2
    assert len([e for e in root.iter() if e.get("data-label-kind") == "recognition"]) == 2
    assert {e.get("data-label-for-site") for e in root.iter() if e.get("data-label-for-site")} == {
        "site-0",
        "site-1",
    }


def test_strand_aware_names_preserve_every_site_status_and_side():
    points = {
        (strand, i): (100 + i * 16, y)
        for strand, y in (("top", 100), ("bottom", 160))
        for i in range(20)
    }
    sites = []
    for index, (strand, start, presence) in enumerate(
        (
            ("top", 0, "partial"),
            ("top", 12, "partial"),
            ("bottom", 0, "partial"),
            ("bottom", 12, "complete"),
        )
    ):
        addresses = [NS(strand_id=strand, index=i) for i in range(start, start + 5)]
        sites.append(
            NS(
                site_id=f"site-{index}",
                role="basal_nick",
                enzyme_name="Nickase",
                orientation="forward",
                presence=presence,
                substrate_eligibility="eligible",
                orientation_path=addresses,
                recognition=addresses,
            )
        )
    projection = NS(operations=(), recognition_sites=sites, state=NS(state_id="state"))
    root = ET.fromstring(
        "<svg>" + recognition_site_overlays(projection, points, strand_labels=True) + "</svg>"
    )
    groups = {
        tuple(json.loads(e.get("data-site-labels")))
        for e in root.iter()
        if e.get("data-site-labels")
    }
    assert groups == {("site-0",), ("site-1",), ("site-2",), ("site-3",)}
    assert len([e for e in root.iter() if e.get("data-recognition-footprint")]) == 4
    assert sorted(e.text for e in root.iter() if e.get("data-label-kind") == "recognition") == [
        "Nickase",
        "Nickase *",
        "Nickase *",
        "Nickase *",
    ]
