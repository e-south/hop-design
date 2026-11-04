"""Rebind a saved choice packet to an independently admitted option pool."""

import json
from pathlib import Path

from ..packets.capture import capture_packet
from .public import ScaffoldExploration, ScaffoldVariantChoices, query_scaffold_variants


def load_scaffold_variant_choices(
    pool: ScaffoldExploration, path: str | Path
) -> ScaffoldVariantChoices:
    protected, files = capture_packet(path, schema=ScaffoldVariantChoices._packet_schema)
    choices = query_scaffold_variants(pool, json.loads(files["query.json"]))
    if choices.json_bytes != files["summary.json"]:
        raise ValueError("Saved choices disagree with the admitted result and query.")
    object.__setattr__(choices, "_roots", (pool._root, protected))
    return choices
