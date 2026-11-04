"""Selection preserves existential membership without constructing facet counts."""

import json
from types import SimpleNamespace

from hop_design.design.construction.editions.projection import SelectionIndex
from hop_design.design.construction.editions.refinement import selection_query


def test_any_matching_record_for_an_identity_remains_selectable():
    edition = SimpleNamespace(
        resolution={"intent": {"product": "hairpin"}, "permissions": {}},
        _index=json.dumps(
            {
                "snapshot_digest": "sha256:" + "0" * 64,
                "paths": [
                    {"materialized_realization_id": "same", "values": {"loop_word": "AAAA"}},
                    {"materialized_realization_id": "same", "values": {"loop_word": "GAAA"}},
                ],
            }
        ).encode(),
    )
    edition._selection_index = SelectionIndex.from_choices(json.loads(edition._index))
    result = selection_query(
        edition, "same", {"parameters": [{"key": "loop_word", "values": ["GAAA"]}]}
    )
    assert result["parameters"][0]["values"] == ["GAAA"]
