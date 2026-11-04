"""The browser receives only the facts it uses, with exact member identities."""

import copy

import pytest

from hop_design.commands.design.inspection_transport import _column, compact_choices


def test_compact_cohort_preserves_values_methods_and_material_differences():
    answer = {
        "query": {"parameters": []},
        "snapshot_digest": "snapshot",
        "axes": [{"key": "loop_word"}],
        "paths": [
            {
                "materialized_realization_id": name,
                "matches": available,
                "values": {"loop_word": loop, "left_gap": 0},
                "methods": [{"name": "Nickase"}],
                "material_roles": {"source": {"material_id": material, "length_nt": 70}},
                "molecular_identity": {"endpoint": name + "-product"},
            }
            for name, available, loop, material in (
                ("one", True, "AAAA", "source-one"),
                ("two", False, "AACA", "source-two"),
                ("three", True, "AAAA", "source-one"),
            )
        ],
    }
    before = copy.deepcopy(answer)
    result = compact_choices(answer)
    assert result["members"] == ["one", "two", "three"]
    assert result["matches"] == [True, False, True]
    assert result["values"]["loop_word"] == {"dictionary": ["AAAA", "AACA"], "indices": [0, 1, 0]}
    assert result["roles"]["source"]["indices"] == [0, 1, 0]
    assert result["roles"]["source"]["dictionary"][1]["material_id"] == "source-two"
    assert result["methods"]["dictionary"] == [[{"name": "Nickase"}]]
    assert result["choices"]["axes"] == answer["axes"]
    assert "paths" not in result["choices"]
    assert answer == before
    answer["paths"][1]["materialized_realization_id"] = "one"
    with pytest.raises(ValueError, match="distinct"):
        compact_choices(answer)


def test_scalar_columns_preserve_json_types_without_reencoding_each_value(monkeypatch):
    import json

    original, encoded = json.dumps, []

    def counted(value, **kwargs):
        encoded.append(value)
        return original(value, **kwargs)

    monkeypatch.setattr("hop_design.commands.design.inspection_transport.json.dumps", counted)
    values = [1, True, "1", None, 1.0, {"a": 1, "b": 2}, {"b": 2, "a": 1}, 1, True, None]
    result = _column(values)
    assert result == {
        "dictionary": [1, True, "1", None, 1.0, {"a": 1, "b": 2}],
        "indices": [0, 1, 2, 3, 4, 5, 5, 0, 1, 3],
    }
    assert encoded == [1.0, {"a": 1, "b": 2}, {"b": 2, "a": 1}]
