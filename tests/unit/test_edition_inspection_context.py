"""An inspection context keeps first-row semantics and isolates mutable callers."""

import copy

import pytest

from hop_design.design.construction.editions import reader
from hop_design.design.construction.editions.inspection_context import InspectionContext


def test_context_preserves_first_row_and_returns_detached_teaching_metadata():
    first = {"materialized_realization_id": "one", "values": {"loop_word": "AAAA"}}
    second = {"materialized_realization_id": "two", "values": {"loop_word": "TTTT"}}
    answer = {
        "snapshot_digest": "snapshot",
        "axes": [{"key": "loop_word", "nodes": [{"value": "AAAA"}]}],
        "context": {"permission": "fixed"},
        "coverage": {"unresolved": 3},
        "paths": [first, {**first, "values": {"loop_word": "CCCC"}}, second],
    }
    expected = copy.deepcopy({**answer, "paths": [first]})
    context = InspectionContext.from_choices(answer)
    answer["axes"].clear()
    first["values"].clear()
    detached = context.member("one")
    assert detached == expected
    detached["paths"].clear()
    detached["coverage"].clear()
    assert context.member("one") == expected
    assert context.member("two")["paths"] == [second]
    assert context.bytes == len(context.shared) + sum(len(row) for row in context.rows.values())
    with pytest.raises(KeyError):
        context.member("absent")
    with pytest.raises(TypeError):
        context.rows["one"] = b"{}"


def test_query_reuses_only_unfiltered_detached_teaching_context(monkeypatch):
    edition = object.__new__(reader.AtlasEdition)
    edition._inspection_context = None
    answer = {
        "axes": [{"key": "loop_word"}],
        "coverage": {"unresolved": 3},
        "paths": [{"materialized_realization_id": "one", "values": {"loop_word": "AAAA"}}],
    }

    def project(_edition, query):
        return copy.deepcopy({**answer, "paths": []} if query is not None else answer)

    monkeypatch.setattr(reader, "query_edition", project)
    assert edition.query({"parameters": []})["paths"] == []
    assert edition._inspection_context is None
    returned = edition.query()
    returned["axes"].clear()
    returned["paths"][0]["values"].clear()

    def forbidden(*args):
        pytest.fail("Already returned unfiltered choices must not be projected again")

    monkeypatch.setattr(reader, "query_edition", forbidden)
    assert edition._inspection_choices("one") == answer
