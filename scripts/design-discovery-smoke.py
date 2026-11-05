"""Installed/source parity for optional intent, packaged contexts and exact handoff."""

import json
import tempfile
from pathlib import Path

from hop_design import construction
from hop_design.serialization import sha256_digest


def require_same_handoff(left: Path, right: Path) -> None:
    def inventory(root):
        return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    expected, actual = inventory(left), inventory(right)
    if not expected or expected != actual:
        raise ValueError("Exact handoff contents or file membership differ")


def run(root: Path, *, max_evaluations: int = 64) -> dict:
    stem = "ATAACTTCGTATAGCATACATTATACGAAGTTAT"
    contexts = {}
    for product in ("released_insert", "hairpin", "adapter_ligated_hairpin"):
        resolved = construction.resolve_design_request({"stem_arm": stem, "product": product})
        contexts[product] = sha256_digest(resolved.json_bytes)
    choices = construction.discover_designs(
        {"stem_arm": stem, "product": "released_insert"},
        root / "designs",
        max_evaluations=max_evaluations,
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
    require_same_handoff(root / "preparation", root / "captured-materials")
    families = edition.figure(selection=guided, view="families")
    return {
        "contexts": contexts,
        "selection": selected,
        "figure": sha256_digest(figure.json_bytes),
        "atlas": sha256_digest(atlas.json_bytes),
        "edition": edition.digest,
        "guided": guided,
        "families": sha256_digest(families.json_bytes),
    }


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="hop-design-smoke-") as temporary:
        print(json.dumps(run(Path(temporary)), sort_keys=True))
