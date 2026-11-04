"""Selecting one recorded member does not need whole-cohort facet statistics."""

import json

import pytest

from tests.integration.test_design_preservation import loop_designs as loop_designs


def test_repeated_selection_does_not_decode_unrelated_preparations(
    loop_designs, tmp_path, monkeypatch
):
    edition = loop_designs[1].freeze(tmp_path / "edition", compact=True)
    first = edition.query()["paths"][0]
    query = {"parameters": [{"key": "loop_word", "values": [first["values"]["loop_word"]]}]}
    loads = json.loads

    def selected_coordinates_only(value, *args, **kwargs):
        if value == edition._index:
            pytest.fail("Selecting one preparation must not decode the complete cohort")
        return loads(value, *args, **kwargs)

    monkeypatch.setattr(json, "loads", selected_coordinates_only)
    for _ in range(3):
        selected = edition.select(first["materialized_realization_id"], query=query)
        assert selected["materialized_realization_id"] == first["materialized_realization_id"]
        assert selected["query"]["parameters"][0]["values"] == query["parameters"][0]["values"]
        assert edition._selected(selected).model_dump(mode="json", by_alias=True) == selected


@pytest.mark.parametrize("with_reference", [False, True])
def test_filtered_inspection_preserves_existing_selection_contract(
    loop_designs, tmp_path, monkeypatch, with_reference
):
    edition = loop_designs[1].freeze(tmp_path / "edition", compact=True)
    path = edition.query()["paths"][0]
    default = edition.select(path)
    filtered = edition.select(
        path, query={"parameters": [{"key": "loop_word", "values": [path["values"]["loop_word"]]}]}
    )
    assert filtered["query"] != default["query"]

    def forbidden(*args, **kwargs):
        pytest.fail("Inspection must reuse the unfiltered cohort already returned to its caller")

    monkeypatch.setattr(edition, "query", forbidden)
    baseline = json.loads(edition._inspection_packet(default).json_bytes)
    packet = edition._inspection_packet(
        filtered, reference_selection=default if with_reference else None
    )
    summary = json.loads(packet.json_bytes)
    assert summary["selection"] == (filtered if with_reference else default)
    assert bool(summary["comparison"]) == with_reference
    assert summary["projection"] == path
    assert summary["teaching"] == baseline["teaching"]
    assert summary["parameter_locations"] == baseline["parameter_locations"]
    other = next(
        p
        for p in json.loads(edition._index)["paths"]
        if p["materialized_realization_id"] != path["materialized_realization_id"]
    )
    other_summary = json.loads(edition._inspection_packet(edition.select(other)).json_bytes)
    assert (
        other_summary["projection"]["materialized_realization_id"]
        == other["materialized_realization_id"]
    )

    # Cached teaching context cannot authorize changed molecular bytes.
    archive = (
        edition._directory / edition._prefix(path["materialized_realization_id"]) / "evidence.zip"
    )
    raw = archive.read_bytes()
    archive.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    with pytest.raises(ValueError, match="digest"):
        edition._inspection_packet(filtered)


def test_selection_preserves_query_semantics_without_projecting_every_facet(
    loop_designs, tmp_path, monkeypatch
):
    from hop_design.design.construction.editions import refinement

    edition = loop_designs[1].freeze(tmp_path / "edition", compact=True)
    answer = edition.query()
    first = answer["paths"][0]
    queries = [
        None,
        {"parameters": [{"key": "loop_word", "values": [first["values"]["loop_word"]]}]},
        {"parameters": [{"key": "loop_side_paired_bp", "minimum": 0, "maximum": 100}]},
        {
            "membership": {
                "snapshot_digest": answer["snapshot_digest"],
                "preparations": [first["materialized_realization_id"]],
            }
        },
        {"parameters": [{"key": "loop_word", "values": ["CCCCCCCCCCCC"]}]},
    ]
    expected = []
    for query in queries:
        result = edition.query(query)
        expected.append(
            (
                query,
                {
                    p["materialized_realization_id"]: edition.select(p, query=query)
                    if p["matches"]
                    else None
                    for p in result["paths"]
                },
            )
        )

    def forbidden(*args, **kwargs):
        pytest.fail("Selecting one preparation must not rebuild all cohort facet statistics")

    monkeypatch.setattr(refinement, "project_choices", forbidden)
    for query, members in expected:
        for identity, wanted in members.items():
            if wanted is None:
                with pytest.raises(ValueError, match="No matching captured preparation"):
                    edition.select(identity, query=query)
            else:
                selected = edition.select(identity, query=query)
                assert selected == wanted
                assert edition._selected(selected).model_dump(mode="json", by_alias=True) == wanted
    with pytest.raises(ValueError, match="snapshot"):
        edition.select(
            first,
            query={
                "membership": {
                    "snapshot_digest": "sha256:" + "0" * 64,
                    "preparations": [first["materialized_realization_id"]],
                }
            },
        )
    with pytest.raises(ValueError, match="conflict"):
        edition.select(
            first,
            query={
                "parameters": [
                    {"key": "foldback_arm_bp", "values": [1]},
                    {"key": "loop_side_paired_bp", "values": [2]},
                ]
            },
        )
