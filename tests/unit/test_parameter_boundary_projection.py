"""Only adjacent recorded ancestry can carry a zero-span boundary to another state."""

from hop_design.design.construction.projections.inspection_lineage import (
    boundary_occurrences,
    span_occurrences,
)
from hop_design.models.construction.variants.inspection import MolecularAddress


def address(state, index):
    return MolecularAddress(state_id=state, strand_id="s", index=index)


def test_boundary_projection_requires_both_neighbors_and_real_adjacency():
    before, after = address("released", 0), address("released", 1)
    edge = {"before": before.model_dump(mode="json"), "after": after.model_dump(mode="json")}
    origins = {
        before: ("source", 7),
        after: ("source", 8),
        address("hairpin", 5): ("source", 8),
        address("hairpin", 6): ("source", 7),
        address("separated", 2): ("source", 7),
        address("separated", 5): ("source", 8),
        address("partial", 0): ("source", 7),
    }
    found = boundary_occurrences([{"start": edge, "end": edge}], origins)
    assert len(found) == 2
    assert {a["start"]["before"]["state_id"] for a in found} == {"released", "hairpin"}
    assert all(a["start"] == a["end"] for a in found)
    assert all(a["start"]["before"]["index"] + 1 == a["start"]["after"]["index"] for a in found)


def test_terminal_boundary_is_not_invented_in_an_earlier_molecule():
    last = address("released", 1)
    edge = {"before": last.model_dump(mode="json"), "after": None}
    assert boundary_occurrences([{"start": edge, "end": edge}], {last: ("source", 8)}) == [
        {"start": edge, "end": edge}
    ]


def test_span_projection_requires_the_complete_ordered_ancestry():
    def edge(state, offset):
        return {
            "before": address(state, offset - 1).model_dump(mode="json"),
            "after": address(state, offset).model_dump(mode="json"),
        }

    anchor = {"start": edge("source", 1), "end": edge("source", 4)}
    origins = {address("source", i): ("source", i) for i in range(5)}
    origins.update({address("hairpin", i + 10): ("source", 3 - i) for i in range(3)})
    origins.update({address("broken", i + 10): ("source", j) for i, j in enumerate([1, 90, 3])})
    found = span_occurrences([anchor], origins)
    projected = [a for a in found if a["start"]["after"]["state_id"] == "hairpin"]
    assert len(projected) == 1
    assert projected[0]["start"]["after"]["index"] == 10
    assert projected[0]["end"]["before"]["index"] == 12
    assert not any(a["start"]["after"]["state_id"] == "broken" for a in found)


def test_recorded_cut_can_locate_a_released_terminal_without_guessing_its_neighbor():
    last, left, right = address("released", 1), address("precursor", 3), address("precursor", 4)
    edge = {"before": last.model_dump(mode="json"), "after": None}
    cut = {"before": left.model_dump(mode="json"), "after": right.model_dump(mode="json")}
    origins = {
        last: ("source", 8),
        left: ("source", 8),
        right: ("source", 9),
        address("hairpin", 10): ("source", 8),
        address("hairpin", 11): ("source", 9),
    }
    found = boundary_occurrences([{"start": edge, "end": edge}], origins, cuts=[cut])
    assert any(a["start"]["after"] and a["start"]["after"]["state_id"] == "hairpin" for a in found)
    # Two incompatible cuts sharing the surviving ancestor do not establish a boundary.
    other = {
        "before": left.model_dump(mode="json"),
        "after": address("other", 0).model_dump(mode="json"),
    }
    origins[address("other", 0)] = ("source", 100)
    assert boundary_occurrences([{"start": edge, "end": edge}], origins, cuts=[cut, other]) == [
        {"start": edge, "end": edge}
    ]
