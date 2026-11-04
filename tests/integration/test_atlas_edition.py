"""A frozen selection travels with its molecular drawings and exact materials."""

import json
import shutil

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from tests.integration.test_design_discovery import intent_document


@pytest.fixture(scope="module")
def captured_choices(tmp_path_factory):
    root = tmp_path_factory.mktemp("edition-source")
    return construction.discover_designs(intent_document(), root / "designs", max_evaluations=1)


def test_frozen_edition_reopens_after_relocation_without_live_producer_admission(
    captured_choices, tmp_path, monkeypatch
):
    choices = captured_choices
    selected = choices.sample(seed=1)
    identity = selected["materialized_realization_id"]
    expected = choices.atlas(selected)
    choices.retrieve(selected, tmp_path / "expected-materials")
    edition = choices.freeze(tmp_path / "edition", identities=(identity,))
    original_producer = edition.producer
    original_view = edition.view(edition.select(identity), stage="all")
    shutil.copytree(tmp_path / "edition", tmp_path / "moved")

    def forbidden(*args, **kwargs):
        pytest.fail("Frozen viewing must not execute or admit live discovery")

    monkeypatch.setattr(construction, "discover_designs", forbidden)
    monkeypatch.setattr(construction, "load_design_choices", forbidden)
    monkeypatch.setattr("hop_design.design.runtime.producer_identity", forbidden)
    loaded = construction.load_atlas_edition(tmp_path / "moved")
    assert loaded.producer == original_producer
    assert loaded.restore_view(original_view) == original_view
    exact = loaded.select(identity)
    assert exact["materialized_realization_id"] == identity
    assert loaded.atlas(exact).svg_bytes == expected.svg_bytes
    assert (
        json.loads(loaded.atlas(exact).json_bytes)["atlas"]
        == json.loads(expected.json_bytes)["atlas"]
    )
    handoff = loaded.retrieve(exact, tmp_path / "retrieved")
    assert handoff.materialized_realization_ids == (identity,)
    expected_files = {
        p.relative_to(tmp_path / "expected-materials"): p.read_bytes()
        for p in (tmp_path / "expected-materials").rglob("*")
        if p.is_file()
    }
    actual_files = {
        p.relative_to(tmp_path / "retrieved"): p.read_bytes()
        for p in (tmp_path / "retrieved").rglob("*")
        if p.is_file()
    }
    assert actual_files == expected_files


@pytest.fixture(scope="module")
def captured_edition(captured_choices, tmp_path_factory):
    directory = tmp_path_factory.mktemp("atlas-edition") / "edition"
    return captured_choices.freeze(directory)


def test_existing_cli_verbs_work_on_a_frozen_edition(captured_edition, tmp_path):
    runner = CliRunner()
    directory = str(captured_edition._directory)
    selected = captured_edition.sample(seed=3)
    result = runner.invoke(app, ["design", "sample", directory, "--seed", "3"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == selected
    output = tmp_path / "figure"
    figure = captured_edition.figure(selection=selected)
    assert json.loads(figure.json_bytes)["selection"] == selected
    figure.write(output)
    assert (output / "figure.svg").is_file()
    assert selected["materialized_realization_id"].encode() in (output / "figure.svg").read_bytes()
    assert json.loads(figure.json_bytes)["renderer"]["content"] != "sha256:" + "0" * 64
    selection_file = tmp_path / "selection.json"
    selection_file.write_text(json.dumps(selected))
    route = runner.invoke(
        app,
        [
            "design",
            "atlas",
            directory,
            "--selection",
            str(selection_file),
            "--out",
            str(tmp_path / "route"),
        ],
    )
    assert route.exit_code == 0, route.output
    family = runner.invoke(
        app,
        [
            "design",
            "figure",
            directory,
            "--selection",
            str(selection_file),
            "--view",
            "families",
            "--layout",
            "mosaic",
            "--out",
            str(tmp_path / "family"),
        ],
    )
    assert family.exit_code == 0, family.output


def test_freeze_cli_keeps_the_same_selection_lifecycle(captured_choices, tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "design",
            "freeze",
            str(captured_choices._directory),
            "--out",
            str(tmp_path / "edition"),
        ],
    )
    assert result.exit_code == 0, result.output
    loaded = construction.load_atlas_edition(tmp_path / "edition")
    assert json.loads(result.stdout)["edition_digest"] == loaded.digest


def test_explicit_distance_policy_round_trips_api_cli_and_keeps_materials(
    captured_choices, tmp_path
):
    from hop_design.models.construction.variants.similarity import MolecularDistancePolicy

    policy = MolecularDistancePolicy(regional_metric="normalized_edit", end_word_metric="hamming")
    with pytest.raises(ValueError, match="include_landscape"):
        captured_choices.freeze(tmp_path / "invalid", distance_policy=policy)
    assert not (tmp_path / "invalid").exists()
    api = captured_choices.freeze(
        tmp_path / "api",
        include_landscape=True,
        distance_policy=policy,
        comparison_weights=(2, 1, 3),
    )
    spec = tmp_path / "distance.json"
    spec.write_text(policy.model_dump_json(by_alias=True))
    result = CliRunner().invoke(
        app,
        [
            "design",
            "freeze",
            str(captured_choices._directory),
            "--out",
            str(tmp_path / "cli"),
            "--include-landscape",
            "--distance-policy",
            str(spec),
            "--comparison-weights",
            "2",
            "1",
            "3",
        ],
    )
    assert result.exit_code == 0, result.output
    cli = construction.load_atlas_edition(tmp_path / "cli")
    assert api.landscape() == cli.landscape()
    assert api.landscape().basis.distance_policy == policy
    assert api.landscape().basis.weights == (2, 1, 3)
    compact = api.freeze(tmp_path / "compact", compact=True, include_landscape=True)
    assert compact.landscape().basis.distance_policy == policy
    assert compact.landscape().basis.weights == (2, 1, 3)
    repeated = compact.freeze(tmp_path / "recaptured", compact=True, include_landscape=True)
    assert repeated.landscape() == compact.landscape()
    identity = captured_choices.sample(seed=1)["materialized_realization_id"]
    for label, choices in (("original", captured_choices), ("api", api), ("cli", cli)):
        choices.retrieve(choices.select(identity), tmp_path / (label + "-materials"))

    def files(label):
        root = tmp_path / (label + "-materials")
        return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    assert files("original") == files("api") == files("cli")


def test_recapture_keeps_historical_descriptor_scope(captured_choices, tmp_path, monkeypatch):
    from hop_design.design.construction.editions import compact_capture
    from hop_design.models.construction.variants.similarity import MolecularDistancePolicy

    current = compact_capture.molecular_descriptor
    with monkeypatch.context() as legacy_producer:
        # Emulate the recorded full-tail projection emitted before retained-tail v2.
        legacy_producer.setattr(
            compact_capture,
            "molecular_descriptor",
            lambda route: current(route).model_copy(update={"retained_terminal_bases": None}),
        )
        legacy = captured_choices.freeze(tmp_path / "legacy", compact=True, include_landscape=True)
    assert legacy.landscape().basis.schema_id == "hop.molecular-comparison/v1"
    recaptured = legacy.freeze(tmp_path / "recaptured", compact=True, include_landscape=True)
    assert recaptured.landscape() == legacy.landscape()
    policy = MolecularDistancePolicy(regional_metric="normalized_edit")
    candidate = legacy.freeze(
        tmp_path / "candidate", compact=True, include_landscape=True, distance_policy=policy
    )
    assert candidate.landscape().preparations == legacy.landscape().preparations
    assert candidate.landscape().basis.schema_id == "hop.molecular-comparison/v1"
    assert candidate.landscape().basis.distance_policy == policy


@pytest.mark.parametrize("product", ["hairpin", "adapter_ligated_hairpin"])
@pytest.mark.parametrize("compact", [False, True])
def test_hairpin_endpoints_use_the_same_frozen_lifecycle(product, compact, tmp_path):
    from tests.unit.test_construction_intent import STEM

    choices = construction.discover_designs(
        {"stem_arm": STEM, "product": product},
        tmp_path / "designs",
        max_evaluations=4,
        first_choices=1,
    )
    edition = choices.freeze(tmp_path / "edition", compact=compact)
    selected = edition.sample(seed=1)
    assert edition.resolution["intent"]["product"] == product
    assert edition.query()["matching_preparations"] == choices.query()["matching_preparations"]
    facts = json.loads(edition.atlas(selected).json_bytes)
    assert not any(s["state"]["phase"] == "released_insert" for s in facts["atlas"]["states"])
    if compact:
        from hop_design.api import _InspectionProjection
        from hop_design.export.construction.molecular.teaching_overview import (
            render_teaching_overview,
        )
        from hop_design.export.construction.presentation.figure_profile import INSPECTOR_FIGURE

        overview, _ = _InspectionProjection.preview(
            edition, selected["materialized_realization_id"], edition.query()
        )
        assert overview == render_teaching_overview(facts, profile=INSPECTOR_FIGURE)
    figure = edition.figure(selection=selected)
    assert json.loads(figure.json_bytes)["selection"] == selected
    from hop_design.commands.design.inspection import DesignInspectionSession

    session = DesignInspectionSession(choices, tmp_path / "inspection")
    try:
        state = session.sample(
            {"token": session.state()["token"], "seed": 3, "strategy": "families"}
        )
        assert state["selection"] == choices.sample(seed=3, strategy="families")["selection"]
        again = session.sample({"token": state["token"], "seed": 4, "strategy": "families"})
        if again["selection"] != state["selection"]:
            assert again["preview"]["summary"]["comparison"]
        else:
            assert again["cache"]["retained_bytes"] == state["cache"]["retained_bytes"]
    finally:
        session.close()


@pytest.mark.parametrize("damage", ["changed", "missing", "extra", "symlink", "schema", "escape"])
def test_editions_reject_corruption_before_viewing(captured_edition, tmp_path, damage):
    root = tmp_path / "damaged"
    shutil.copytree(captured_edition._directory, root)
    if damage == "changed":
        (root / "choices.json").write_text("{}")
    elif damage == "missing":
        (root / "resolution.json").unlink()
    elif damage == "extra":
        (root / "extra.txt").write_text("unrecorded")
    elif damage == "symlink":
        (root / "choices.json").unlink()
        (root / "choices.json").symlink_to(captured_edition._directory / "choices.json")
    else:
        manifest = json.loads((root / "edition.json").read_bytes())
        if damage == "schema":
            manifest["schema"] = "hop.atlas-edition/unknown"
        else:
            manifest["artifacts"]["../outside"] = manifest["artifacts"]["choices.json"]
        (root / "edition.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        construction.load_atlas_edition(root)


def test_view_and_selection_fail_closed(captured_edition):
    selected = captured_edition.sample(seed=1)
    with pytest.raises(ValueError, match="different atlas"):
        captured_edition.atlas({**selected, "edition_digest": "sha256:" + "0" * 64})
    with pytest.raises(ValueError, match="stage"):
        captured_edition.view(selected, stage="imaginary-intermediate")
    identity = selected["materialized_realization_id"]
    with pytest.raises(ValueError, match="No matching"):
        captured_edition.select(
            identity, query={"parameters": [{"key": "loop_nt", "values": [100]}]}
        )
    view = captured_edition.view(selected, camera=(0.0, 1.0, 120.0, 80.0))
    assert captured_edition.restore_view(view) == view


def test_guided_receipt_round_trips_through_existing_api_and_cli(
    captured_edition, captured_choices
):
    for choices in (captured_choices, captured_edition):
        guided = choices.sample(seed=7, strategy="families", stage="hairpin")
        selected = guided["selection"]
        assert choices.atlas(guided).svg_bytes == choices.atlas(selected).svg_bytes
        assert json.loads(choices.figure(selection=guided).json_bytes)["selection"] == selected
        with pytest.raises(ValueError, match="receipt"):
            choices.atlas({**guided, "eligible_digest": "sha256:" + "0" * 64})
    result = CliRunner().invoke(
        app,
        [
            "design",
            "sample",
            str(captured_edition._directory),
            "--seed",
            "7",
            "--strategy",
            "families",
            "--stage",
            "hairpin",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == captured_edition.sample(
        seed=7, strategy="families", stage="hairpin"
    )


def test_edition_rechecks_lazy_files_and_preserves_existing_destinations(
    captured_edition, tmp_path
):
    root = tmp_path / "copy"
    shutil.copytree(captured_edition._directory, root)
    loaded = construction.load_atlas_edition(root)
    selected = loaded.sample(seed=1)
    target = next(root.glob("members/*/atlas/projection.svg"))
    target.write_text("changed after admission")
    with pytest.raises(ValueError, match="digest"):
        loaded.atlas(selected)
    with pytest.raises((FileExistsError, ValueError)):
        captured_edition.retrieve(captured_edition.sample(seed=1), captured_edition._directory)


def test_family_figure_uses_the_same_selected_molecule(captured_edition, captured_choices):
    for choices in (captured_choices, captured_edition):
        selected = choices.sample(seed=1)
        packet = choices.figure(selection=selected, view="families", layout="mosaic")
        summary = json.loads(packet.json_bytes)
        assert summary["selection"] == selected
        assert summary["families"] == choices.families()
        assert selected["materialized_realization_id"].encode() in dict(packet._files)["figure.svg"]


def test_one_inspection_session_for_live_and_frozen_choices(
    captured_choices, captured_edition, tmp_path
):
    from hop_design.api import _InspectionProjection
    from hop_design.commands.design.inspection import DesignInspectionSession

    for label, choices in (("live", captured_choices), ("edition", captured_edition)):
        session = DesignInspectionSession(choices, tmp_path / label)
        try:
            state = session.state()
            assert state["choices"] == _InspectionProjection.display(choices.query())
            state = session.sample({"token": state["token"], "seed": 7, "strategy": "families"})
            expected = choices.sample(seed=7, strategy="families")
            assert state["sample_receipt"] == expected
            assert state["selection"] == expected["selection"]
            assert (
                state["preview"]["summary"]["atlas"]["materialized_realization_id"]
                == state["selection"]["materialized_realization_id"]
            )
            stage = state["preview"]["summary"]["atlas"]["states"][1]["state"]["state_id"]
            state = session.view(
                {"token": state["token"], "stage": stage, "camera": [1, 2, 100, 80]}
            )
            receipt = state["view_receipt"]
            assert choices.restore_view(receipt) == receipt
            state = session.sample({"token": state["token"], "seed": 8, "strategy": "families"})
            assert state["stage"] == stage
            state = session.back({"token": state["token"]})
            assert state["view_receipt"] == receipt
            state = session.retrieve({"token": state["token"], "selection": state["selection"]})
            assert (session.root / state["handoff"]["archive"].removeprefix("/files/")).is_file()
            cache = session.cache_root
            assert cache.is_dir()
            with pytest.raises(ValueError, match="Stale"):
                session.sample({"token": "old", "seed": 8})
        finally:
            session.close()
        assert not cache.exists()


def test_view_receipts_reject_nonfinite_camera_and_wrong_snapshot(captured_edition):
    selected = captured_edition.sample(seed=0)
    with pytest.raises(ValueError):
        captured_edition.view(selected, camera=(0, 0, float("nan"), 10))
    receipt = captured_edition.view(selected)
    with pytest.raises(ValueError, match="snapshot"):
        captured_edition.restore_view({**receipt, "pool_digest": "sha256:" + "0" * 64})


def test_applicable_parameter_vocabulary_is_shared_by_api_and_cli(
    captured_edition, captured_choices, tmp_path, monkeypatch
):
    vocabulary = captured_edition.parameters()
    loop = next(p for p in vocabulary if p["key"] == "loop_nt")
    assert loop["stage"] == "hairpin" and loop["unit"] == "nt"
    assert loop["operations"]["filter"]["available"]
    assert not loop["operations"]["revise"]["available"]
    assert "frozen" in loop["operations"]["revise"]["reason"].lower()
    assert loop["operations"]["preserve"]["arguments"] == {
        "stage": "hairpin",
        "except_neighborhood": "loop",
    }
    assert loop["operations"]["preserve"]["requires_reference"]
    assert not loop["operations"]["prefer"]["available"]
    live = {p["key"]: p for p in captured_choices.parameters()}
    assert live["loop_nt"]["operations"]["revise"]["available"]
    assert "loop_side_paired_bp" in live["foldback_arm_bp"]["equivalent_measurements"]
    assert live["self_paired_arm_bp"]["operations"]["filter"]["available"]
    assert not live["self_paired_arm_bp"]["operations"]["revise"]["available"]
    assert live["left_gap"]["operations"]["revise"]["field"] == "end_placements"
    assert "joint" in live["left_gap"]["operations"]["revise"]["reason"].lower()
    assert not live["left_end_word"]["operations"]["revise"]["available"]
    result = CliRunner().invoke(app, ["design", "parameters", str(captured_edition._directory)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == vocabulary
    query = {"parameters": [{"key": "left_gap", "values": [999]}]}
    query_file = tmp_path / "query.json"
    query_file.write_text(json.dumps(query))
    filtered = captured_edition.parameters(query=query)
    assert next(p for p in filtered if p["key"] == "left_gap")["operations"]["filter"]["available"]
    result = CliRunner().invoke(
        app, ["design", "parameters", str(captured_edition._directory), "--query", str(query_file)]
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == filtered
    assert captured_edition.parameters() == vocabulary
    alias = captured_edition.parameters(
        query={"parameters": [{"key": "loop_side_paired_bp", "values": [3]}]}
    )
    assert next(p for p in alias if p["key"] == "foldback_arm_bp")["constraints"][0]["values"] == [
        3
    ]
    reference = captured_edition.sample(seed=0)
    preserved = captured_edition.preserve(reference, stage="hairpin", except_neighborhood="loop")

    def no_scan(*args, **kwargs):
        raise AssertionError("Parameter explanations must not load molecular routes.")

    monkeypatch.setattr(
        "hop_design.design.construction.editions.refinement.captured_options", no_scan
    )
    assert captured_edition.parameters(query=preserved) == vocabulary
