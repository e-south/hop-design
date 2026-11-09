"""Pinning a molecule keeps its facts; the route is drawn only when requested."""

import json
from xml.etree import ElementTree as ET

import pytest

from hop_design import construction
from hop_design.commands.design.inspection import DesignInspectionSession
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.integration.test_atlas_edition import captured_choices as captured_choices
from tests.integration.test_design_preservation import loop_designs as loop_designs


def forbid_route(*args, **kwargs):
    pytest.fail("Molecule inspection must not render the full processing route")


@pytest.mark.parametrize("source", ["compact", "captured"])
def test_preview_can_include_visible_scenes_without_committing(source, captured_choices, tmp_path):
    choices = captured_choices.freeze(tmp_path / "edition", compact=source == "compact")
    session = DesignInspectionSession(choices, tmp_path / "session")
    try:
        state = session.state()
        identity = state["choices"]["paths"][0]["materialized_realization_id"]
        payload = {"token": state["token"], "materialized_realization_id": identity}
        original = session.preview(payload)
        expected = session.scenes({**payload, "phases": ["duplex", "cleaved_duplex"]})
        result = session.preview({**payload, "phases": ["duplex", "cleaved_duplex"]})
        scene_result = result.pop("route_scenes")
        assert scene_result["token"] == state["token"]
        assert scene_result["materialized_realization_id"] == identity
        for actual, prior in zip(scene_result["scenes"], expected["scenes"], strict=True):
            a = session.root / actual["drawing"].removeprefix("/files/")
            b = session.root / prior["drawing"].removeprefix("/files/")
            assert a.read_bytes() == b.read_bytes()
            assert {k: v for k, v in actual.items() if k != "drawing"} == {
                k: v for k, v in prior.items() if k != "drawing"
            }
        result.pop("molecule")
        original.pop("molecule")
        assert result == original
        assert session.state()["selection"] is None
        assert session.state()["token"] == state["token"]
        for invalid in ([], ["duplex", "duplex"], "duplex", ["invented"]):
            with pytest.raises(ValueError, match="distinct recorded"):
                session.preview({**payload, "phases": invalid})
    finally:
        session.close()
    assert not session._hover.root.exists()


@pytest.mark.parametrize("source", ["live", "compact", "captured"])
def test_inspector_pin_and_hover_share_readable_profile_without_changing_public_artwork(
    source, captured_choices, tmp_path, monkeypatch
):
    from hop_design.export.construction.molecular.teaching_overview import render_teaching_overview
    from hop_design.export.construction.presentation.figure_profile import (
        INSPECTOR_FIGURE,
        PUBLICATION_FIGURE,
    )

    choices = (
        captured_choices
        if source == "live"
        else captured_choices.freeze(tmp_path / "edition", compact=source == "compact")
    )
    selected = choices.sample(seed=0)
    public = choices.atlas(selected)
    public_overview = dict(public._files)["overview.svg"]
    profiles = []

    def measured_overview(*args, **kwargs):
        profiles.append(kwargs.get("profile", PUBLICATION_FIGURE).key)
        return render_teaching_overview(*args, **kwargs)

    for module in ("packets.inspection", "navigation.inspection_projection"):
        monkeypatch.setattr(
            f"hop_design.design.construction.{module}.render_teaching_overview",
            measured_overview,
        )
    session = DesignInspectionSession(choices, tmp_path / "session")
    try:
        state = session.select(
            {
                "token": session.state()["token"],
                "materialized_realization_id": selected["materialized_realization_id"],
            }
        )
        if source == "captured":
            state = session.view(
                {
                    "token": state["token"],
                    "stage": "all",
                    "camera": None,
                    "render_policy": "current",
                }
            )
        # Live saved-view validation separately replays its preparation. Each
        # packet should draw the requested composition once; that replay is not
        # changed by the inspector's presentation-only optimization.
        packet_count = 2 if source == "live" else 1
        assert profiles == [INSPECTOR_FIGURE.key] * packet_count
        pin_bytes = (
            session.root / state["preview"]["teaching"].removeprefix("/files/")
        ).read_bytes()
        pin = ET.fromstring(pin_bytes)
        assert float(pin.get("font-size")) >= 30
        hovered = session.preview(
            {
                "token": state["token"],
                "materialized_realization_id": selected["materialized_realization_id"],
            }
        )
        hover_bytes = (session.root / hovered["molecule"].removeprefix("/files/")).read_bytes()
        assert hover_bytes == pin_bytes
        axes = ET.fromstring(
            (session.root / state["plots"]["inspection"].removeprefix("/files/")).read_bytes()
        )
        assert float(axes.get("viewBox").split()[2]) == 600
        assert state["trace_projection"]["frame"] == axes.get("data-landscape-frame")
        assert hovered["figure_layout"]["frame"] == state["figure_layout"]["frame"]
        assert dict(choices.atlas(selected)._files)["overview.svg"] == public_overview
        record = json.loads(
            (session.root / state["preview"]["record"].removeprefix("/files/")).read_bytes()
        )
        assert record["atlas"] == json.loads(public.json_bytes)["atlas"]
    finally:
        session.close()


@pytest.mark.parametrize("source", ["live", "compact", "captured"])
def test_pin_restore_and_route_transition_share_identity_and_facts(
    source, captured_choices, tmp_path, monkeypatch
):
    choices = captured_choices
    if source != "live":
        choices = choices.freeze(tmp_path / "edition", compact=source == "compact")
    selected = choices.sample(seed=0)
    expected = json.loads(choices.atlas(selected).json_bytes)["atlas"]
    session = DesignInspectionSession(choices, tmp_path / "session")
    try:
        with monkeypatch.context() as scoped:
            for module in (
                "surveys.atlas",
                "editions.compact_projection",
                "editions.redraw",
                "navigation.route_presentation",
                "navigation.route_comparison",
            ):
                scoped.setattr(
                    f"hop_design.design.construction.{module}.render_molecular_atlas", forbid_route
                )
            state = session.select(
                {
                    "token": session.state()["token"],
                    "materialized_realization_id": selected["materialized_realization_id"],
                }
            )
            preview = state["preview"]
            assert preview.get("drawing") is None
            assert preview["summary"]["atlas"]["construction_cost"] == expected["construction_cost"]
            assert len(preview["summary"]["atlas"]["states"]) == len(expected["states"])
            record = session.root / preview["record"].removeprefix("/files/")
            assert json.loads(record.read_text())["atlas"] == expected
            assert not list(session.cache_root.rglob("projection.svg"))
            state = session.restore({"token": state["token"], "receipt": state["view_receipt"]})
        before = state["view_receipt"]
        state = session.view(
            {
                "token": state["token"],
                "stage": before["stage"],
                "camera": before["camera"],
                "presentation": {**before["presentation"], "molecule": "route"},
            }
        )
        assert state["preview"]["drawing"]
        assert state["selection"] == selected
        for field in ("selection", "stage", "camera", "reference_identity", "exploration"):
            assert state["view_receipt"][field] == before[field]
        path = session.root / state["preview"]["record"].removeprefix("/files/")
        assert json.loads(path.read_text())["atlas"] == expected
        assert session.state()["preview"] == state["preview"]
    finally:
        session.close()


@pytest.mark.parametrize("compact", [False, True])
def test_molecule_comparison_keeps_exact_changes_without_route_artwork(
    compact, loop_designs, tmp_path, monkeypatch
):
    choices = loop_designs[1]
    if compact:
        choices = choices.freeze(tmp_path / "edition", compact=True)
    paths = choices.query()["paths"]
    old, new = (choices.select(p) for p in paths[:2])
    expected = json.loads(choices.atlas(new, reference_selection=old).json_bytes)
    session = DesignInspectionSession(choices, tmp_path / "session")
    try:
        for module in (
            "variants.atlas",
            "editions.compact_projection",
            "navigation.route_comparison",
        ):
            monkeypatch.setattr(
                f"hop_design.design.construction.{module}.render_molecular_atlas", forbid_route
            )
        state = session.state()
        for selected in (old, new):
            state = session.select(
                {
                    "token": state["token"],
                    "materialized_realization_id": selected["materialized_realization_id"],
                }
            )
        path = session.root / state["preview"]["record"].removeprefix("/files/")
        actual = json.loads(path.read_text())
        assert actual["comparison"] == expected["comparison"]
        assert actual["atlas"] == expected["atlas"]
        assert state["preview"]["summary"]["comparison"] is not None
        assert not list(session.cache_root.rglob("projection.svg"))
        assert not list(session.cache_root.rglob("comparison.svg"))
    finally:
        session.close()


def test_captured_molecule_current_fallback_keeps_original_overview(
    captured_choices, tmp_path, monkeypatch
):
    root = tmp_path / "edition"
    edition = captured_choices.freeze(root)
    selected = edition.sample(seed=0)
    original = dict(edition.atlas(selected)._files)["overview.svg"]
    manifest = json.loads((root / "edition.json").read_bytes())
    member = manifest["members"][0]
    path = member["directory"] + "/atlas/summary.json"
    summary = json.loads((root / path).read_bytes())
    summary["atlas"]["future_presentation_feature"] = True
    content = canonical_json_bytes(summary)
    (root / path).write_bytes(content)
    manifest["artifacts"][path] = {"sha256": sha256_digest(content), "bytes": len(content)}
    (root / "edition.json").write_bytes(canonical_json_bytes(manifest))
    edition = construction.load_atlas_edition(root)
    selected = edition.sample(seed=0)
    monkeypatch.setattr(
        "hop_design.design.construction.editions.redraw.render_molecular_atlas", forbid_route
    )
    for policy in ("captured", "current"):
        packet = edition._inspection_packet(
            selected, reference_selection=selected, render_policy=policy
        )
        result = json.loads(packet.json_bytes)
        assert result["comparison"] is not None
        assert result["rendering"]["effective"] == "captured"
        assert dict(packet._files)["overview.svg"] == original
        assert "projection.svg" not in dict(packet._files)
        if policy == "current":
            assert "not supported" in result["rendering"]["notice"]
        from hop_design.api import _InspectionProjection

        overview, facts = _InspectionProjection.preview(
            edition, selected["materialized_realization_id"], edition.query(), render_policy=policy
        )
        assert overview == original
        assert facts["rendering"] == "captured"


def test_failed_route_upgrade_keeps_pinned_molecule_and_cache(
    captured_choices, tmp_path, monkeypatch
):
    edition = captured_choices.freeze(tmp_path / "edition", compact=True)
    session = DesignInspectionSession(edition, tmp_path / "session")
    try:
        before = session.sample({"token": session.state()["token"], "seed": 0})
        cached = set(session.cache_root.iterdir())

        def fail(*args, **kwargs):
            raise ValueError("route drawing failed")

        monkeypatch.setattr(
            "hop_design.design.construction.editions.compact_projection.render_molecular_atlas",
            fail,
        )
        with pytest.raises(ValueError, match="route drawing failed"):
            session.view(
                {
                    "token": before["token"],
                    "stage": "all",
                    "camera": None,
                    "presentation": {**before["presentation"], "molecule": "route"},
                }
            )
        assert session.state() == before
        assert set(session.cache_root.iterdir()) == cached
    finally:
        session.close()


def test_compact_pin_compares_before_drawing_and_reads_each_route_once(
    loop_designs, tmp_path, monkeypatch
):
    from hop_design.design.construction.editions import authority, compact_projection, comparison
    from hop_design.design.construction.packets import inspection

    edition = loop_designs[1].freeze(tmp_path / "edition", compact=True)
    old, new = (edition.select(p) for p in edition.query()["paths"][:2])
    # Preserve the previous two-pass composition, including SVG metadata order.
    expected = comparison.compare_captured(
        edition,
        compact_projection.compact_atlas(edition, edition._selected(new), draw_route=False),
        new,
        old,
        redraw=True,
        draw_route=False,
    )
    reads, drawings = [], []
    read, draw = comparison.captured_route, inspection.render_teaching_overview

    def counted_read(edition, identity):
        reads.append(identity)
        return read(edition, identity)

    def counted_draw(summary, **kwargs):
        drawings.append(summary.get("comparison"))
        return draw(summary, **kwargs)

    monkeypatch.setattr(authority, "captured_route", counted_read)
    monkeypatch.setattr(comparison, "captured_route", counted_read)
    monkeypatch.setattr(compact_projection, "captured_route", counted_read)
    monkeypatch.setattr(inspection, "render_teaching_overview", counted_draw)
    actual = compact_projection.compact_atlas(
        edition, edition._selected(new), reference_selection=old, draw_route=False
    )
    assert actual.json_bytes == expected.json_bytes
    assert dict(actual._files)["overview.svg"] == dict(expected._files)["overview.svg"]
    assert len(drawings) == 1, "Draw once, after the exact comparison is known"
    assert drawings[0] is not None
    assert sorted(reads) == sorted(
        [old["materialized_realization_id"], new["materialized_realization_id"]]
    )


@pytest.mark.parametrize(
    "source,policy",
    [
        ("live", "current"),
        ("compact", "captured"),
        ("captured", "captured"),
        ("captured", "current"),
    ],
)
def test_visible_scene_preview_keeps_authority_and_renders_only_requested_states(
    source, policy, captured_choices, tmp_path, monkeypatch
):
    from hop_design.api import _InspectionProjection
    from hop_design.export.construction.molecular import atlas_layout

    choices = (
        captured_choices
        if source == "live"
        else captured_choices.freeze(tmp_path / "edition", compact=source == "compact")
    )
    answer = choices.query()
    identity = answer["paths"][0]["materialized_realization_id"]
    selection = choices.select(identity)
    expected = json.loads(choices.atlas(selection).json_bytes)["atlas"]
    phases = ("foldback_closed_hairpin", "hairpin_pcr_duplex")
    calls = []
    original = atlas_layout.molecular_inspection_element

    def counted(state, **kwargs):
        calls.append(state.state.state_id)
        return original(state, **kwargs)

    monkeypatch.setattr(atlas_layout, "molecular_inspection_element", counted)
    monkeypatch.setattr(
        "hop_design.design.construction.navigation.route_presentation.render_molecular_atlas",
        forbid_route,
    )
    if source == "compact":
        # The compact source has already projected a strict, typed atlas from
        # its checked authority. Drawing two scenes must not round-trip it.
        def forbid_atlas_reconstruction(*args, **kwargs):
            pytest.fail("Scene inspection must reuse the typed molecular projection")

        monkeypatch.setattr(
            "hop_design.models.construction.projections.atlas.MolecularAtlas.model_validate_json",
            forbid_atlas_reconstruction,
        )
    drawings, result = _InspectionProjection.scenes(
        choices, identity, answer, phases=phases, presentation="assembly", render_policy=policy
    )
    assert result["materialized_realization_id"] == identity
    assert result["snapshot_digest"] == answer["snapshot_digest"]
    assert not result["unavailable"]
    assert len(result["scenes"]) == 2
    assert len(calls) == (0 if source == "captured" and policy == "captured" else 2)
    assert result["presentation"]["effective"] == (
        "complete" if source == "captured" and policy == "captured" else "assembly"
    )
    for scene in result["scenes"]:
        state = next(s for s in expected["states"] if s["state"]["state_id"] == scene["state_id"])
        root = ET.fromstring(drawings[scene["state_id"]])
        assert root.get("data-preparation-id") == identity
        bases = [e for e in root.iter() if e.get("data-base-index") is not None]
        assert len(bases) == len(state["bases"])
        assert {e.get("data-state-id") for e in bases} == {scene["state_id"]}
        assert all(e.get("data-preparation-id") == identity for e in bases)
    assert choices.select(identity) == selection


def test_visible_scene_request_is_bounded_and_hidden_state_falls_back(captured_choices):
    from hop_design.api import _InspectionProjection

    answer = captured_choices.query()
    identity = answer["paths"][0]["materialized_realization_id"]
    for phases in (
        (),
        ("duplex",) * 2,
        ("invented",),
    ):
        with pytest.raises(ValueError, match="scene"):
            _InspectionProjection.scenes(captured_choices, identity, answer, phases=phases)
    drawings, result = _InspectionProjection.scenes(
        captured_choices, identity, answer, phases=("denatured_fragments",), presentation="assembly"
    )
    assert len(drawings) == 1
    assert result["presentation"] == {"requested": "assembly", "effective": "complete"}


def test_visible_scene_batch_reuses_one_projection_without_changing_drawings(
    captured_choices, tmp_path, monkeypatch
):
    from hop_design.api import _InspectionProjection
    from hop_design.design.construction.editions import authority

    edition = captured_choices.freeze(tmp_path / "edition", compact=True)
    answer = edition.query()
    identity = answer["paths"][0]["materialized_realization_id"]
    phases = (
        "source_ssdna",
        "duplex",
        "selected_fragments",
        "annealed_complex",
        "foldback_closed_hairpin",
        "adapter_annealed",
        "hairpin_pcr_duplex",
    )
    expected = {}
    expected_scenes = []
    for start in range(0, len(phases), 2):
        drawings, result = _InspectionProjection.scenes(
            edition, identity, answer, phases=phases[start : start + 2], presentation="assembly"
        )
        expected.update(drawings)
        expected_scenes.extend(result["scenes"])
    reads = []
    original = authority.captured_route

    def counted(edition, identity):
        reads.append(identity)
        return original(edition, identity)

    monkeypatch.setattr(authority, "captured_route", counted)
    drawings, result = _InspectionProjection.scenes(
        edition, identity, answer, phases=phases, presentation="assembly"
    )
    assert drawings == expected
    assert result["scenes"] == expected_scenes
    assert not result["unavailable"]
    assert reads == [identity], "Admit once for the requested visible scenes, not once per pair"


def test_scene_session_is_read_only_bounded_and_cleans_its_files(captured_choices, tmp_path):
    edition = captured_choices.freeze(tmp_path / "edition", compact=True)
    session = DesignInspectionSession(edition, tmp_path / "session")
    try:
        before = session.sample({"token": session.state()["token"], "seed": 0})
        identity = before["selection"]["materialized_realization_id"]
        request = {
            "token": before["token"],
            "materialized_realization_id": identity,
            "phases": ["duplex"],
        }
        first = session.scenes(request)
        scene = first["scenes"][0]
        path = session.root / scene["drawing"].removeprefix("/files/")
        assert path.exists()
        assert first["token"] == before["token"]
        assert first["materialized_realization_id"] == identity
        assert session.scenes(request) == first
        assert {k: v for k, v in session.state().items() if k != "cache"} == {
            k: v for k, v in before.items() if k != "cache"
        }
        with pytest.raises(ValueError, match="Stale"):
            session.scenes({**request, "token": "stale"})
        for phase in ("source_ssdna", "cleaved_duplex", "adapter_annealed"):
            session._hover.entries = 2
            session.scenes({**request, "phases": [phase]})
        assert not path.exists()
        assert session._hover.bytes <= session._hover.byte_limit
        root = session._hover.root
    finally:
        session.close()
    assert not root.exists()


def test_captured_scene_keeps_inherited_ink_font_and_definitions(captured_choices, tmp_path):
    from hop_design.api import _InspectionProjection

    root = tmp_path / "edition"
    edition = captured_choices.freeze(root)
    identity = edition.sample(seed=0)["materialized_realization_id"]
    path = edition._prefix(identity) + "/atlas/projection.svg"
    drawing = ET.fromstring((root / path).read_bytes())
    ns = "http://www.w3.org/2000/svg"
    drawing.set("style", "font-family:serif")
    group = next(e for e in drawing if e.tag.endswith("}g"))
    group.set("fill", "#123456")
    group.set("font-family", "Georgia")
    defs = ET.SubElement(drawing, f"{{{ns}}}defs")
    ET.SubElement(defs, f"{{{ns}}}linearGradient", {"id": "historic-ink"})
    content = ET.tostring(drawing)
    (root / path).write_bytes(content)
    manifest = json.loads((root / "edition.json").read_bytes())
    manifest["artifacts"][path] = {"sha256": sha256_digest(content), "bytes": len(content)}
    (root / "edition.json").write_bytes(canonical_json_bytes(manifest))
    edition = construction.load_atlas_edition(root)
    drawings, result = _InspectionProjection.scenes(
        edition, identity, edition.query(), phases=("duplex",)
    )
    excerpt = ET.fromstring(next(iter(drawings.values())))
    assert excerpt.get("style") == drawing.get("style")
    assert any(e.get("id") == "historic-ink" for e in excerpt.iter())
    parents = {child: parent for parent in excerpt.iter() for child in parent}
    row = next(e for e in excerpt.iter() if e.get("data-atlas-state"))
    assert parents[row].get("fill") == "#123456"
    assert parents[row].get("font-family") == "Georgia"
    assert result["rendering"] == "captured"


def test_broken_current_scene_projection_is_not_relabelled_captured(captured_choices, monkeypatch):
    from pydantic import ValidationError

    from hop_design.api import _InspectionProjection
    from hop_design.design.construction.navigation import route_presentation

    answer = captured_choices.query()
    identity = answer["paths"][0]["materialized_realization_id"]
    monkeypatch.setattr(route_presentation, "preview_record", lambda *a: ({"atlas": {}}, False))
    with pytest.raises(ValidationError):
        _InspectionProjection.scenes(captured_choices, identity, answer, phases=("duplex",))


@pytest.mark.parametrize("compact", [False, True])
def test_absent_scene_is_explicit_and_never_substituted(compact, captured_choices, tmp_path):
    from hop_design.api import _InspectionProjection

    choices = (
        captured_choices.freeze(tmp_path / "edition", compact=True) if compact else captured_choices
    )
    answer = choices.query()
    identity = answer["paths"][0]["materialized_realization_id"]
    drawings, result = _InspectionProjection.scenes(
        choices, identity, answer, phases=("ligated_product",)
    )
    assert not drawings and not result["scenes"]
    assert result["unavailable"] == ["ligated_product"]
    with pytest.raises(ValueError, match="recorded pool"):
        _InspectionProjection.scenes(choices, "missing", answer, phases=("duplex",))


@pytest.mark.parametrize("placement", ["ancestor", "row", "stylesheet"])
def test_captured_nonstandard_scene_coordinates_are_explicitly_unavailable(
    placement, captured_choices, tmp_path
):
    from hop_design.api import _InspectionProjection

    root = tmp_path / "edition"
    edition = captured_choices.freeze(root)
    identity = edition.sample(seed=0)["materialized_realization_id"]
    path = edition._prefix(identity) + "/atlas/projection.svg"
    drawing = ET.fromstring((root / path).read_bytes())
    row = next(e for e in drawing.iter() if e.get("data-atlas-phase") == "duplex")
    if placement == "ancestor":
        parent = next(e for e in drawing.iter() if row in list(e))
        parent.set("transform", "scale(0.5)")
    elif placement == "row":
        row.set("transform", "rotate(20)")
    else:
        ET.SubElement(
            drawing, "{http://www.w3.org/2000/svg}style"
        ).text = "g { transform: scale(.5); }"
    content = ET.tostring(drawing)
    (root / path).write_bytes(content)
    manifest = json.loads((root / "edition.json").read_bytes())
    manifest["artifacts"][path] = {"sha256": sha256_digest(content), "bytes": len(content)}
    (root / "edition.json").write_bytes(canonical_json_bytes(manifest))
    edition = construction.load_atlas_edition(root)
    drawings, result = _InspectionProjection.scenes(
        edition, identity, edition.query(), phases=("duplex",)
    )
    assert not drawings and not result["scenes"]
    assert result["unavailable"] == ["duplex"]
    assert "layout" in result["notice"]
