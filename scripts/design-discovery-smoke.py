"""Installed/source parity for optional intent, packaged contexts and exact handoff."""

import json
import tempfile
from pathlib import Path

from hop_design import construction
from hop_design.serialization import sha256_digest

stem = "ATAACTTCGTATAGCATACATTATACGAAGTTAT"
contexts = {}
for product in ("released_insert", "hairpin", "adapter_ligated_hairpin"):
    resolved = construction.resolve_design_request({"stem_arm": stem, "product": product})
    contexts[product] = sha256_digest(resolved.json_bytes)
with tempfile.TemporaryDirectory(prefix="hop-design-smoke-") as temporary:
    root = Path(temporary)
    choices = construction.discover_designs(
        {"stem_arm": stem, "product": "released_insert"}, root / "designs"
    )
    selected = choices.sample(seed=1)
    figure = choices.figure(selection=selected)
    atlas = choices.atlas(selected)
    receipt = choices.retrieve(selected, root / "preparation")
    assert receipt.materialized_realization_ids == (selected["materialized_realization_id"],)
    assert construction.load_design_choices(root / "designs").sample(seed=1) == selected
    edition = choices.freeze(
        root / "edition", identities=(selected["materialized_realization_id"],)
    )
    guided = edition.sample(seed=7, strategy="families")
    assert edition.restore_view(edition.view(guided))["selection"] == guided["selection"]
    edition.retrieve(guided, root / "captured-materials")
    assert {
        p.relative_to(root / "preparation"): p.read_bytes()
        for p in (root / "preparation").rglob("*")
        if p.is_file()
    } == {
        p.relative_to(root / "captured-materials"): p.read_bytes()
        for p in (root / "captured-materials").rglob("*")
        if p.is_file()
    }
    families = edition.figure(selection=guided, view="families")
    print(
        json.dumps(
            {
                "contexts": contexts,
                "selection": selected,
                "figure": sha256_digest(figure.json_bytes),
                "atlas": sha256_digest(atlas.json_bytes),
                "edition": edition.digest,
                "guided": guided,
                "families": sha256_digest(families.json_bytes),
            },
            sort_keys=True,
        )
    )
