"""One saved composition drives inspection and export without pruning authority."""

import json
from xml.etree import ElementTree as ET

import pytest
from typer.testing import CliRunner

from hop_design.cli import app
from hop_design.commands.design.inspection import DesignInspectionSession
from tests.integration.test_atlas_edition import captured_choices, captured_edition  # noqa: F401


def phases(svg):
    return [
        e.get("data-atlas-phase") for e in ET.fromstring(svg).iter() if e.get("data-atlas-state")
    ]


@pytest.mark.parametrize("frozen", [False, True])
def test_saved_assembly_preserves_all_states_and_exact_selection(
    captured_choices,  # noqa: F811
    captured_edition,  # noqa: F811
    frozen,
    tmp_path,
):
    choices = captured_edition if frozen else captured_choices
    selected = choices.sample(seed=0)
    complete = choices.atlas(selected)
    receipt = choices.view(
        selected, render_policy="current", presentation={"molecule": "route", "route": "assembly"}
    )
    packet = choices.atlas(receipt)
    assert len(phases(packet.svg_bytes)) == 9
    assert "denatured_fragments" not in phases(packet.svg_bytes)
    assert "selected_fragments" not in phases(packet.svg_bytes)
    before, after = json.loads(complete.json_bytes), json.loads(packet.json_bytes)
    assert after["atlas"] == before["atlas"]
    assert after["rendering"]["route"]["effective"] == "assembly"
    assert after["rendering"]["route"]["recorded_states"] == 11
    assert receipt["selection"] == selected
    assert choices.restore_view(receipt) == receipt
    hidden = next(
        s["state"]["state_id"]
        for s in after["atlas"]["states"]
        if s["state"]["phase"] == "denatured_fragments"
    )
    focused = choices.atlas({**receipt, "stage": hidden})
    assert "denatured_fragments" in phases(focused.svg_bytes)
    assert json.loads(focused.json_bytes)["rendering"]["route"]["effective"] == "complete"
    assert choices.atlas(receipt).svg_bytes == packet.svg_bytes
    source = tmp_path / "view.json"
    source.write_text(json.dumps(receipt))
    output = tmp_path / "route"
    cli = CliRunner().invoke(
        app,
        [
            "design",
            "atlas",
            str(choices._directory),
            "--selection",
            str(source),
            "--out",
            str(output),
        ],
    )
    assert cli.exit_code == 0, cli.output
    assert (output / "projection.svg").read_bytes() == packet.svg_bytes


def test_captured_artwork_does_not_silently_adopt_requested_composition(
    captured_edition,  # noqa: F811
):
    selected = captured_edition.sample(seed=0)
    original = captured_edition.atlas(selected)
    receipt = captured_edition.view(selected, presentation={"route": "assembly"})
    packet = captured_edition.atlas(receipt)
    assert packet.svg_bytes == original.svg_bytes
    rendered = json.loads(packet.json_bytes)["rendering"]
    assert rendered["route"]["requested"] == "assembly"
    assert rendered["route"]["effective"] == "complete"
    assert "captured" in rendered["notice"].lower()


def test_invalid_route_focus_is_rejected(captured_edition):  # noqa: F811
    selected = captured_edition.sample(seed=0)
    with pytest.raises(ValueError, match="state"):
        captured_edition.atlas(
            selected, render_policy="current", presentation="assembly", stage="missing"
        )


def test_session_recomposes_on_route_change_and_exposes_omitted_state(
    captured_edition,  # noqa: F811
    tmp_path,
):
    session = DesignInspectionSession(captured_edition, tmp_path / "session")
    try:
        state = session.sample({"token": session.state()["token"], "seed": 0})
        selected = state["selection"]
        state = session.view(
            {
                "token": state["token"],
                "stage": "all",
                "camera": None,
                "render_policy": "current",
                "presentation": {"molecule": "route", "route": "assembly"},
            }
        )
        compact = state["preview"]["drawing"]
        assert len(phases((session.root / compact.removeprefix("/files/")).read_bytes())) == 9
        hidden = next(
            s["state"]["state_id"]
            for s in state["preview"]["summary"]["atlas"]["states"]
            if s["state"]["phase"] == "denatured_fragments"
        )
        state = session.view({"token": state["token"], "stage": hidden, "camera": None})
        assert state["preview"]["drawing"] != compact
        assert state["selection"] == selected
        state = session.sample({"token": state["token"], "seed": 1})
        inspected = next(
            s["state"]
            for s in state["preview"]["summary"]["atlas"]["states"]
            if s["state"]["state_id"] == state["stage"]
        )
        assert inspected["phase"] == "denatured_fragments"
        state = session.restore(
            {
                "token": state["token"],
                "receipt": captured_edition.view(
                    selected,
                    render_policy="current",
                    presentation={"molecule": "route", "route": "assembly"},
                ),
            }
        )
        state = session.view({"token": state["token"], "stage": "all", "camera": None})
        assert state["preview"]["drawing"] == compact
        assert state["view_receipt"]["presentation"]["route"] == "assembly"
    finally:
        session.close()
