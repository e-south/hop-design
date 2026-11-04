"""Hover inspection is a read-only molecular projection, independent of selection."""

import json

import pytest

from hop_design.commands.design.inspection import DesignInspectionSession
from tests.integration.test_atlas_edition import captured_choices, captured_edition  # noqa: F401


def test_preview_projects_exact_molecule_without_full_route_or_selection(
    captured_choices,  # noqa: F811
    captured_edition,  # noqa: F811
    monkeypatch,
):
    identity = captured_edition.query()["paths"][0]["materialized_realization_id"]
    captured = dict(captured_edition.atlas(captured_edition.select(identity))._files)[
        "overview.svg"
    ]

    def forbidden(*args, **kwargs):
        pytest.fail("Hover must not render the complete route or call the atlas operation")

    for source in (captured_choices, captured_edition):
        monkeypatch.setattr(source, "atlas", forbidden)
    monkeypatch.setattr(
        "hop_design.export.construction.molecular.atlas.render_molecular_atlas", forbidden
    )
    for source in (captured_choices, captured_edition):
        before = source.query()
        packet = source.preview(identity)
        summary = json.loads(packet.json_bytes)
        assert summary["materialized_realization_id"] == identity
        assert summary["eligible"]
        assert summary["path"]["values"] == before["paths"][0]["values"]
        files = dict(packet._files)
        assert {name for name in files if name.endswith(".svg")} == {"overview.svg", "trace.svg"}
        assert identity.encode() in files["overview.svg"]
        if source is captured_edition:
            assert files["overview.svg"] == captured
        excluded = source.preview(
            identity, query={"parameters": [{"key": "loop_nt", "values": [100]}]}
        )
        assert not json.loads(excluded.json_bytes)["eligible"]
        assert source.query() == before
        with pytest.raises(ValueError, match="recorded"):
            source.preview("missing")


def test_session_hover_keeps_query_history_reference_camera_and_retrieval(
    captured_edition,  # noqa: F811
    tmp_path,
):
    session = DesignInspectionSession(captured_edition, tmp_path / "inspection")
    try:
        pinned = session.sample({"token": session.state()["token"], "seed": 0})
        identity = pinned["selection"]["materialized_realization_id"]
        result = session.preview(
            {"token": pinned["token"], "materialized_realization_id": identity}
        )
        assert result["materialized_realization_id"] == identity
        assert result["token"] == pinned["token"]
        after = session.state()
        assert {k: v for k, v in after.items() if k != "cache"} == {
            k: v for k, v in pinned.items() if k != "cache"
        }
        assert after["cache"]["retained_bytes"] <= after["cache"]["byte_limit"]
        assert (session.root / result["molecule"].removeprefix("/files/")).is_file()
        assert result["trace"]["materialized_realization_id"] == identity
        assert result["trace"]["projection"] == after["trace_projection"]["projection"]
        root = session._hover.root
        with pytest.raises(ValueError, match="Stale"):
            session.preview({"token": "stale", "materialized_realization_id": identity})
    finally:
        session.close()
    assert not root.exists()


def test_private_preview_never_renders_the_cohort_and_matches_public_overview(
    captured_edition,  # noqa: F811
    tmp_path,
    monkeypatch,
):
    session = DesignInspectionSession(captured_edition, tmp_path / "inspection")
    try:
        before = session.state()
        identity = before["choices"]["paths"][0]["materialized_realization_id"]
        public = dict(captured_edition.preview(identity)._files)["overview.svg"]

        def forbidden(*args, **kwargs):
            pytest.fail("Pointer inspection must not generate the whole-cohort trace")

        monkeypatch.setattr(
            "hop_design.design.construction.navigation.preview.render_survey_plot", forbidden
        )
        result = session.preview(
            {"token": before["token"], "materialized_realization_id": identity}
        )
        assert (session.root / result["molecule"].removeprefix("/files/")).read_bytes() == public
        assert result["trace"]["materialized_realization_id"] == identity
        assert result["trace"]["projection"] == before["trace_projection"]["projection"]
        assert session._state["selection"] is None
        assert not list(session._hover.root.rglob("trace.svg"))
    finally:
        session.close()


def test_neighbors_explain_features_and_verify_controls_without_selecting(
    captured_edition,  # noqa: F811
    monkeypatch,
):
    identity = captured_edition.query()["paths"][0]["materialized_realization_id"]
    calls = []
    original = captured_edition.preserve

    def preserved(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(captured_edition, "preserve", preserved)
    before = captured_edition.query()
    result = captured_edition.neighbors(identity, limit=5)
    assert result["reference_identity"] == identity
    assert result["landscape_digest"] == captured_edition.landscape().digest
    assert all(n["materialized_realization_id"] != identity for n in result["neighbors"])
    assert all(0 <= n["dissimilarity"]["total"] <= 1 for n in result["neighbors"])
    assert captured_edition.query() == before
    for row in result["neighbors"]:
        if row["preservation"] == "non_loop_hairpin_verified":
            assert calls
            assert row["description"].startswith("Loop ")
            assert row["description"].endswith("; surroundings preserved")
            assert " → " in row["description"]
    assert not captured_edition.neighbors(
        identity, query={"parameters": [{"key": "loop_nt", "values": [100]}]}
    )["neighbors"]


def test_inspector_neighbor_context_reuses_its_answer_but_checks_landscape(
    captured_edition,  # noqa: F811
    monkeypatch,
):
    from hop_design.design.construction.navigation.neighbors import neighboring_preparations

    answer = captured_edition.query()
    identity = answer["paths"][0]["materialized_realization_id"]
    landscape = captured_edition.landscape()

    def forbidden(*args, **kwargs):
        pytest.fail("The admitted inspector answer must not be projected again")

    monkeypatch.setattr(captured_edition, "query", forbidden)
    result = neighboring_preparations(
        captured_edition, identity, query=answer["query"], answer=answer, verify_controls=False
    )
    assert result["landscape_digest"] == landscape.digest
    with pytest.raises(ValueError, match="context disagrees"):
        neighboring_preparations(captured_edition, identity, query={}, answer=answer)


def test_preview_cli_and_bounded_eviction_preserve_public_identity(captured_edition, tmp_path):  # noqa: F811
    from typer.testing import CliRunner

    from hop_design.cli import app
    from hop_design.commands.design.inspection_hover import HoverCache

    identity = captured_edition.sample(seed=0)["materialized_realization_id"]
    runner = CliRunner()
    target = tmp_path / "preview"
    result = runner.invoke(
        app,
        [
            "design",
            "preview",
            str(captured_edition._directory),
            "--preparation",
            identity,
            "--out",
            str(target),
        ],
    )
    assert result.exit_code == 0, result.output
    expected = dict(captured_edition.preview(identity)._files)
    assert (target / "overview.svg").read_bytes() == expected["overview.svg"]
    assert (target / "trace.svg").read_bytes() == expected["trace.svg"]
    result = runner.invoke(
        app, ["design", "neighbors", str(captured_edition._directory), "--preparation", identity]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == captured_edition.neighbors(identity)
    cache = HoverCache(tmp_path, entries=2)
    try:
        first = cache.get(captured_edition, identity, {})
        old = tmp_path / first["molecule"].removeprefix("/files/")
        for count in (100, 101):
            cache.get(
                captured_edition, identity, {"parameters": [{"key": "loop_nt", "values": [count]}]}
            )
        assert not old.exists()
        assert len(list(cache.root.iterdir())) == 2
        assert cache.bytes <= cache.byte_limit
        root = cache.root
    finally:
        cache.close()
    assert not root.exists() and cache.bytes == 0
