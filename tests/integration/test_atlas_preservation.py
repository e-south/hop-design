"""Captured routes support the same regional controls without reopening discovery."""

import json
from copy import deepcopy

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.commands.design.inspection import DesignInspectionSession
from tests.integration.test_design_preservation import loop_designs  # noqa: F401


@pytest.fixture(scope="module")
def preserved_edition(loop_designs, tmp_path_factory):  # noqa: F811
    return loop_designs[1].freeze(tmp_path_factory.mktemp("preserved-edition") / "edition")


def test_molecular_neighbors_distinguish_verified_loop_control_from_arm_change(preserved_edition):
    pytest.importorskip("umap")
    rows = preserved_edition.query()["paths"]
    reference = next(
        p
        for p in rows
        if p["values"]["loop_word"] == "GAAA" and p["values"]["foldback_arm_bp"] == 7
    )
    answer = preserved_edition.neighbors(reference["materialized_realization_id"])
    by_id = {p["materialized_realization_id"]: p for p in rows}
    controlled = [
        n for n in answer["neighbors"] if n["preservation"] == "non_loop_hairpin_verified"
    ]
    assert len(controlled) == 1
    assert controlled[0]["description"] == "Loop GAAA → TTTC; surroundings preserved"
    target = by_id[controlled[0]["materialized_realization_id"]]
    assert target["values"]["loop_word"] == "TTTC"
    assert target["values"]["foldback_arm_bp"] == 7
    assert all(
        n["preservation"] == "not_established"
        for n in answer["neighbors"]
        if by_id[n["materialized_realization_id"]]["values"]["foldback_arm_bp"] == 8
    )
    assert all("sha256" not in n["description"] for n in answer["neighbors"])


def test_captured_preservation_uses_exact_regions_and_existing_cli(
    preserved_edition, tmp_path, monkeypatch
):
    edition = preserved_edition
    path = next(
        p
        for p in edition.query()["paths"]
        if p["values"]["loop_word"] == "GAAA" and p["values"]["foldback_arm_bp"] == 7
    )
    reference = edition.select(path)

    def forbidden(*args, **kwargs):
        pytest.fail("Captured preservation must not admit or search a live producer")

    monkeypatch.setattr(construction, "load_design_choices", forbidden)
    monkeypatch.setattr(construction, "discover_designs", forbidden)
    query = edition.preserve(reference, stage="hairpin", except_neighborhood="loop")
    result = edition.query(query)
    matching = [p for p in result["paths"] if p["matches"]]
    assert len(matching) == 2
    assert {p["values"]["loop_word"] for p in matching} == {"GAAA", "TTTC"}
    assert {p["values"]["foldback_arm_bp"] for p in matching} == {7}
    assert result["validation"] == "captured_complete_routes; no_current_producer_replay"
    target = next(p for p in matching if p["values"]["loop_word"] == "TTTC")
    selected = edition.select(target, query=query)
    loose = edition.select(target)
    loose_summary = edition.atlas(loose, reference_selection=reference).inspection_summary(loose)
    assert loose_summary["comparison"]["description"] == "Loop GAAA → TTTC."
    change = next(
        c for c in result["changes"] if c["label"] == selected["materialized_realization_id"]
    )
    assert change["molecular_neighborhoods"] == ["loop"]
    assert "source_ssdna" in change["material_roles"]
    receipt = edition.view(selected, reference_identity=reference["materialized_realization_id"])
    assert edition.restore_view(receipt) == receipt
    assert edition.atlas(receipt).json_bytes
    assert edition.retrieve(receipt, tmp_path / "orders").materialized_realization_ids == (
        selected["materialized_realization_id"],
    )
    source = tmp_path / "reference.json"
    source.write_text(json.dumps(reference))
    cli = CliRunner().invoke(
        app,
        [
            "design",
            "preserve",
            str(edition._directory),
            "--reference",
            str(source),
            "--stage",
            "hairpin",
            "--except-neighborhood",
            "loop",
        ],
    )
    assert cli.exit_code == 0, cli.output
    assert json.loads(cli.stdout) == query


def test_captured_preservation_rejects_stale_references_and_intersects_membership(
    preserved_edition,
):
    edition = preserved_edition
    query = edition.preserve(edition.sample(seed=0), stage="hairpin", except_neighborhood="loop")
    for field in ("request_digest", "snapshot_digest", "materialized_realization_id"):
        broken = deepcopy(query)
        broken["reference"][field] = "sha256:" + "0" * 64
        with pytest.raises(ValueError, match="reference"):
            edition.query(broken)
    query["membership"] = {
        "snapshot_digest": edition.query()["snapshot_digest"],
        "preparations": [],
    }
    result = edition.query(query)
    assert result["matching_preparations"] == 0
    assert all(n["conditional_preparations"] == 0 for a in result["axes"] for n in a["nodes"])


@pytest.mark.parametrize("frozen", [False, True])
def test_another_loop_is_replayable_and_keeps_active_requirements(
    frozen,
    loop_designs,  # noqa: F811
    preserved_edition,
    tmp_path,
):
    choices = preserved_edition if frozen else loop_designs[1]
    path = next(
        p
        for p in choices.query()["paths"]
        if p["values"]["loop_word"] == "GAAA" and p["values"]["foldback_arm_bp"] == 7
    )
    reference = choices.select(path)
    view = choices.view(
        reference, exploration={"seed": 5, "history": [path["materialized_realization_id"]]}
    )
    sampled = choices.sample(after=view, strategy="loop")
    assert sampled["strategy"] == "loop/v1"
    assert sampled["status"] == "loop_alternative"
    selected = sampled["selection"]
    result = choices.query(selected["query"])
    target = next(
        p
        for p in result["paths"]
        if p["materialized_realization_id"] == selected["materialized_realization_id"]
    )
    assert target["values"]["loop_word"] == "TTTC"
    assert target["values"]["foldback_arm_bp"] == 7
    assert len([p for p in result["paths"] if p["matches"]]) == 2
    assert choices.atlas(sampled).json_bytes
    next_view = choices.view(
        sampled,
        exploration={
            "seed": 6,
            "strategy": "loop",
            "history": [
                path["materialized_realization_id"],
                selected["materialized_realization_id"],
            ],
        },
    )
    following = choices.sample(after=next_view)
    assert (
        following["selection"]["materialized_realization_id"]
        == reference["materialized_realization_id"]
    )
    saved = tmp_path / "view.json"
    saved.write_text(json.dumps(next_view))
    cli = CliRunner().invoke(
        app, ["design", "sample", str(choices._directory), "--after", str(saved)]
    )
    assert cli.exit_code == 0, cli.output
    assert json.loads(cli.stdout) == following
    strict = {"parameters": [{"key": "loop_word", "values": ["GAAA"]}]}
    with pytest.raises(ValueError, match="No different loop"):
        choices.sample(
            seed=5,
            query=strict,
            strategy="loop",
            history=(reference["materialized_realization_id"],),
        )
    assert choices.query()["query"]["parameters"] == []


@pytest.mark.parametrize("assembly", [False, True])
def test_local_loop_action_keeps_inspection_and_query_coherent(
    preserved_edition, tmp_path, assembly
):
    edition = preserved_edition
    path = next(p for p in edition.query()["paths"] if p["values"]["loop_word"] == "GAAA")
    selected = edition.select(path)
    record = json.loads(edition.atlas(selected).json_bytes)
    hidden = next(
        s["state"]["state_id"]
        for s in record["atlas"]["states"]
        if s["state"]["phase"] == "denatured_fragments"
    )
    view = edition.view(
        selected,
        camera=(0, 0, 500, 400),
        stage=hidden if assembly else "all",
        presentation={"route": "assembly" if assembly else "complete"},
        render_policy="current" if assembly else "captured",
    )
    session = DesignInspectionSession(edition, tmp_path / "local-view")
    try:
        initial = session.restore({"token": session.state()["token"], "receipt": view})
        changed = session.sample({"token": initial["token"], "strategy": "loop"})
        assert changed["sample_receipt"]["status"] == "loop_alternative"
        assert changed["choices"]["query"] == changed["selection"]["query"]
        assert changed["view_receipt"]["camera"] == [0, 0, 500, 400]
        if assembly:
            assert (
                changed["selection"]["materialized_realization_id"]
                != selected["materialized_realization_id"]
            )
            assert (
                next(
                    s["state"]["phase"]
                    for s in changed["preview"]["summary"]["atlas"]["states"]
                    if s["state"]["state_id"] == changed["stage"]
                )
                == "denatured_fragments"
            )
            assert changed["preview"]["drawing"] is None
            assert changed["preview"]["summary"]["rendering"]["route"] is None
            opened = session.view(
                {
                    "token": changed["token"],
                    "stage": changed["stage"],
                    "camera": changed["view_receipt"]["camera"],
                    "presentation": {**changed["presentation"], "molecule": "route"},
                }
            )
            assert opened["selection"] == changed["selection"]
            assert opened["stage"] == changed["stage"]
            assert opened["preview"]["drawing"] is not None
            assert opened["preview"]["summary"]["rendering"]["route"]["effective"] == "complete"
            changed = opened
        assert (
            changed["view_receipt"]["reference_identity"] == selected["materialized_realization_id"]
        )
        expected = edition.sample(after=changed["view_receipt"])
        restored = session.restore({"token": changed["token"], "receipt": changed["view_receipt"]})
        assert restored["preview"]["summary"]["comparison"]["description"] == (
            "Loop GAAA → TTTC; other hairpin regions held."
        )
        following = session.sample({"token": restored["token"]})
        assert following["sample_receipt"] == expected
    finally:
        session.close()


def test_missing_captured_route_reports_unsupported_preservation(preserved_edition, monkeypatch):
    edition = construction.load_atlas_edition(preserved_edition._directory)
    selected = edition.sample(seed=0)
    query = edition.preserve(selected, stage="hairpin", except_neighborhood="loop")

    def unavailable(*args):
        raise ValueError("The captured route uses an unsupported schema")

    monkeypatch.setattr(
        "hop_design.design.construction.editions.refinement.captured_route", unavailable
    )
    with pytest.raises(ValueError, match="cannot verify preserved surroundings"):
        edition.query(query)
    assert edition.atlas(selected).json_bytes


def test_compact_inspection_and_settings_use_public_objects(preserved_edition):
    edition = preserved_edition
    selected = edition.sample(seed=0)
    packet = edition.atlas(selected)
    summary = packet.inspection_summary(selected)
    assert summary["selection"] == selected
    assert "molecules" not in summary["atlas"]["states"][0]["state"]
    with pytest.raises(ValueError, match="disagrees"):
        packet.inspection_summary({"materialized_realization_id": "other"})
    assert edition.inspection_settings()["presentation"]["molecule"] == "molecule"
    with pytest.raises(ValueError):
        edition.inspection_settings(presentation={"molecule": "unknown"})
    assert b"<svg" in edition.plot_svg_bytes(view="distributions", stage="hairpin")
