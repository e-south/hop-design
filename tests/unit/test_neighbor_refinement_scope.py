"""A local contrast verifies only its explicit comparison membership."""

from types import SimpleNamespace

import pytest

from hop_design.design.construction.editions.refinement import captured_options
from hop_design.design.construction.navigation.local_contrast import loop_alternatives
from hop_design.design.construction.navigation.neighbor_work import NeighborWork


def test_loop_neighbors_intersect_candidate_membership_before_verification():
    requests = []
    paths = [
        {
            "materialized_realization_id": key,
            "matches": key != "excluded",
            "values": {"loop_word": word},
        }
        for key, word in (
            ("reference", "AAAA"),
            ("candidate", "AAAC"),
            ("other", "AACA"),
            ("excluded", "ACAA"),
        )
    ]
    choices = SimpleNamespace(
        select=lambda identity: identity,
        preserve=lambda *args, **kwargs: {},
        query=lambda query: (
            requests.append(query)
            or {
                "paths": [
                    dict(p)
                    for p in paths
                    if p["materialized_realization_id"] in query["membership"]["preparations"]
                ]
            }
        ),
    )
    answer = loop_alternatives(
        choices,
        {"paths": paths, "query": {"parameters": []}, "snapshot_digest": "snapshot"},
        ("reference",),
        candidates=("candidate", "excluded"),
    )
    assert requests[0]["membership"]["preparations"] == ["candidate"]
    assert [p["materialized_realization_id"] for p in answer["paths"] if p["matches"]] == [
        "candidate"
    ]


def test_captured_options_reads_only_members_and_reference(monkeypatch):
    import json

    import hop_design.design.construction.editions.refinement as owner

    edition = SimpleNamespace(
        _regional_options=None,
        _index=json.dumps(
            {
                "paths": [
                    {"materialized_realization_id": key}
                    for key in ("reference", "candidate", "other")
                ]
            }
        ).encode(),
    )
    loaded = []
    monkeypatch.setattr(owner, "captured_route", lambda _, key: loaded.append(key) or key)
    monkeypatch.setattr(owner, "regional_variants", lambda route: {"route": route})
    monkeypatch.setattr(owner, "route_materials", lambda route: {"route": route})
    options = captured_options(edition, identities={"reference", "candidate"})
    assert loaded == ["reference", "candidate"]
    assert {o["label"] for o in options} == {"reference", "candidate"}
    assert edition._regional_options is None


def test_scoped_absence_does_not_exclude_untested_preparations():
    choices = SimpleNamespace(
        select=lambda identity: identity,
        preserve=lambda *args, **kwargs: {},
        query=lambda query: {"paths": [{"matches": False, "values": {"loop_word": "AAAC"}}]},
    )
    current = {
        "paths": [
            {"materialized_realization_id": key, "matches": True, "values": {"loop_word": word}}
            for key, word in (("reference", "AAAA"), ("candidate", "AAAC"), ("untested", "AACA"))
        ],
        "query": {"parameters": []},
        "snapshot_digest": "snapshot",
    }
    with pytest.raises(ValueError, match=r"among these candidates.*not tested"):
        loop_alternatives(choices, current, ("reference",), candidates=("candidate",))


def test_cached_control_facts_recheck_requested_authority_bytes(monkeypatch):
    import json

    import hop_design.design.construction.editions.refinement as owner

    rows = [
        {"materialized_realization_id": key, "label": key}
        for key in ("reference", "candidate", "other")
    ]
    edition = SimpleNamespace(
        _index=json.dumps({"paths": rows}).encode(), _regional_options=json.dumps(rows).encode()
    )
    checked = []

    def authority(_, key):
        checked.append(key)
        if key == "candidate":
            raise ValueError("Edition artifact digest disagrees")

    monkeypatch.setattr(owner, "member_materials", authority)
    with pytest.raises(ValueError, match="digest disagrees"):
        captured_options(edition, identities={"reference", "candidate"})
    assert checked == ["reference", "candidate"]


def test_cancel_stops_between_route_proofs_without_installing_a_partial_cache(monkeypatch):
    import json

    import hop_design.design.construction.editions.refinement as owner

    work = NeighborWork()
    edition = SimpleNamespace(
        _regional_options=None,
        _index=json.dumps(
            {"paths": [{"materialized_realization_id": key} for key in ("reference", "candidate")]}
        ).encode(),
    )
    loaded = []

    def route(_, key):
        loaded.append(key)
        work.cancelled.set()
        return key

    monkeypatch.setattr(owner, "captured_route", route)
    monkeypatch.setattr(owner, "regional_variants", lambda _: {})
    monkeypatch.setattr(owner, "route_materials", lambda _: {})
    with pytest.raises(ValueError, match="cancelled"), work.activate():
        captured_options(edition)
    assert loaded == ["reference"]
    assert edition._regional_options is None
