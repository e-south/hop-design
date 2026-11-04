"""Conditional choices retain complete-route support and explicit molecular controls."""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hop_design import construction
from hop_design.cli import app
from hop_design.serialization import canonical_json_bytes, sha256_digest


def test_query_exposes_complete_loop_variants_without_selecting_a_product(loop_options):
    path, original = loop_options
    pool = construction.load_scaffold_exploration(path)
    request = {
        "schema": "hop.scaffold-variant-query/v1",
        "result_digest": pool.result_digest,
        "stage": "hairpin",
        "focus": "loop",
        "reference": original["options"][0]["label"],
        "controls": [{"stage": "hairpin", "property": "non_loop_sequences"}],
    }
    result = construction.query_scaffold_variants(pool, request)
    summary = json.loads(result.json_bytes)
    assert summary["status"] == "options_available"
    assert summary["selected_product"] is None
    assert len(summary["products"]) == 2
    assert len(summary["variants"]) == 2
    assert {v["sequences"][0]["sequence"] for v in summary["variants"]} == {"GAAA", "TTTC"}
    assert summary["coverage"] == original["coverage"]
    assert summary["query"]["reference"] == request["reference"]
    supported = {label for v in summary["variants"] for label in v["option_labels"]}
    assert supported == {o["label"] for o in original["options"]}


def test_replacement_query_retains_other_pins_and_does_not_replay(loop_options, monkeypatch):
    path, original = loop_options
    pool = construction.load_scaffold_exploration(path)
    request = {
        "schema": "hop.scaffold-variant-query/v1",
        "result_digest": pool.result_digest,
        "stage": "hairpin",
        "focus": "loop",
        "reference": original["options"][0]["label"],
        "controls": [{"stage": "hairpin", "property": "non_loop_sequences"}],
    }
    initial = json.loads(construction.query_scaffold_variants(pool, request).json_bytes)
    ga = next(v for v in initial["variants"] if v["sequences"][0]["sequence"] == "GAAA")
    request["pins"] = [{"neighborhood": "loop", "variant_ids": [ga["variant_id"]]}]

    def forbidden(*args, **kwargs):
        raise AssertionError("Warm choices must not search or replay molecular authorities")

    monkeypatch.setattr(construction, "discover_scaffolds", forbidden)
    monkeypatch.setattr(construction, "execute_molecular_edit", forbidden)
    monkeypatch.setattr(construction, "load_verified_construction_bundle", forbidden)
    monkeypatch.setattr(
        "hop_design.design.construction.variants.public.captured_variant_source", forbidden
    )
    monkeypatch.setattr(
        "hop_design.design.construction.packets.publication.ConstructionPacket._create", forbidden
    )
    for _ in range(3):
        result = json.loads(construction.query_scaffold_variants(pool, request).json_bytes)
        assert result["compatible_options"] == ga["option_labels"]
        assert len(result["variants"]) == 2  # Replacement omits only the focus pin.
        assert result["query"]["reference"] == request["reference"]
        assert result["selected_product"] is None


def test_selection_rechecks_pins_and_preserves_controlled_portable_set(loop_options, tmp_path):
    path, original = loop_options
    pool = construction.load_scaffold_exploration(path)
    request = {
        "schema": "hop.scaffold-variant-query/v1",
        "result_digest": pool.result_digest,
        "stage": "hairpin",
        "focus": "loop",
        "reference": original["options"][0]["label"],
        "controls": [{"stage": "hairpin", "property": "non_loop_sequences"}],
    }
    choices = construction.query_scaffold_variants(pool, request)
    observed = json.loads(choices.json_bytes)
    names = {
        v["sequences"][0]["sequence"].lower(): v["option_labels"][0] for v in observed["variants"]
    }
    ga = next(v for v in observed["variants"] if v["sequences"][0]["sequence"] == "GAAA")
    pinned = construction.query_scaffold_variants(
        pool, {**request, "pins": [{"neighborhood": "loop", "variant_ids": [ga["variant_id"]]}]}
    )
    with pytest.raises(ValueError, match=r"outside.*active"):
        construction.select_scaffold_variants(path, pinned, members=names, baseline="gaaa")
    saved = choices.write(tmp_path / "choices")
    selected = construction.select_scaffold_variants(path, saved, members=names, baseline="gaaa")
    out = selected.write(tmp_path / "selected")
    decision = json.loads((out / "exploration-selection.json").read_bytes())
    assert decision["result_digest"] == pool.result_digest
    assert decision["query_digest"] == observed["query_digest"]
    assert decision["members"] == names
    assert (
        json.loads((out / "exploration-query.json").read_bytes())["reference"]
        == request["reference"]
    )
    set_request = json.loads((out / "set.json").read_bytes())
    assert set_request["stage_controls"][0]["property"] == "non_loop_sequences"
    replay = construction.select_construction_set(out / "set.json")
    assert json.loads(replay.json_bytes)["set_id"] == json.loads(selected.json_bytes)["set_id"]


def test_cli_queries_and_retrieves_the_same_explicit_choices(loop_options, tmp_path):
    path, original = loop_options
    output = tmp_path / "choices"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "construction",
            "variants",
            str(path),
            "--stage",
            "hairpin",
            "--focus",
            "loop",
            "--reference",
            original["options"][0]["label"],
            "--preserve",
            "hairpin:non_loop_sequences",
            "--out",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    pool = construction.load_scaffold_exploration(path)
    api = construction.query_scaffold_variants(pool, output / "query.json")
    assert api.json_bytes == (output / "summary.json").read_bytes()
    summary = json.loads(api.json_bytes)
    members = [v["option_labels"][0] for v in summary["variants"]]
    result = runner.invoke(
        app,
        [
            "construction",
            "select-variants",
            str(path),
            str(output),
            "--member",
            f"a={members[0]}",
            "--member",
            f"b={members[1]}",
            "--baseline",
            "a",
            "--out",
            str(tmp_path / "selected"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "selected/exploration-query.json").read_bytes() == (
        output / "query.json"
    ).read_bytes()


def test_projection_uses_fixed_reference_and_never_commits_a_preview(loop_options):
    path, original = loop_options
    pool = construction.load_scaffold_exploration(path)
    reference, alternative = [o["label"] for o in original["options"]]
    choices = construction.query_scaffold_variants(
        pool,
        {
            "result_digest": pool.result_digest,
            "stage": "hairpin",
            "focus": "loop",
            "reference": reference,
            "controls": [{"stage": "hairpin", "property": "non_loop_sequences"}],
        },
    )
    view = construction.project_scaffold_variant(pool, choices, option_label=alternative)
    facts = json.loads(view.json_bytes)
    assert facts["reference"] == reference
    assert facts["option_label"] == alternative
    assert facts["selected_product"] is None
    assert facts["view"]["reference_label"] == reference
    changed = [
        r for r in facts["view"]["regions"] if r["reference_sequence"] != r["observed_sequence"]
    ]
    assert [r["region"] for r in changed] == ["loop"]
    assert b'data-region="loop"' in view.svg_bytes
    with pytest.raises(ValueError, match="compatible"):
        construction.project_scaffold_variant(pool, choices, option_label="not-supported")


def test_saved_choices_are_rederived_even_after_manifest_resealing(loop_options, tmp_path):
    path, original = loop_options
    pool = construction.load_scaffold_exploration(path)
    choices = construction.query_scaffold_variants(
        pool,
        {
            "result_digest": pool.result_digest,
            "stage": "hairpin",
            "focus": "loop",
        },
    ).write(tmp_path / "choices")
    value = json.loads((choices / "summary.json").read_bytes())
    value["coverage"]["exploration_complete"] = True
    data = canonical_json_bytes(value)
    (choices / "summary.json").write_bytes(data)
    manifest = json.loads((choices / "manifest.json").read_bytes())
    manifest["artifacts"]["summary.json"] = sha256_digest(data)
    (choices / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(ValueError, match="disagree"):
        construction.select_scaffold_variants(
            path, choices, members={"only": original["options"][0]["label"]}, baseline="only"
        )


def test_relocated_source_keeps_query_identity(loop_options, tmp_path):
    path, _ = loop_options
    pool = construction.load_scaffold_exploration(path)
    moved = tmp_path / "moved"
    shutil.copytree(path, moved)
    other = construction.load_scaffold_exploration(moved)
    request = {"result_digest": pool.result_digest, "stage": "endpoint", "focus": "interfaces"}
    assert (
        construction.query_scaffold_variants(pool, request).json_bytes
        == construction.query_scaffold_variants(other, request).json_bytes
    )


def test_variant_identifiers_are_bound_to_their_molecular_stage(loop_options):
    path, _ = loop_options
    pool = construction.load_scaffold_exploration(path)
    request = {"result_digest": pool.result_digest, "stage": "hairpin", "focus": "loop"}
    summary = json.loads(construction.query_scaffold_variants(pool, request).json_bytes)
    pin = {"neighborhood": "loop", "variant_ids": [summary["variants"][0]["variant_id"]]}
    with pytest.raises(ValueError, match="wrong-stage"):
        construction.query_scaffold_variants(pool, {**request, "stage": "endpoint", "pins": [pin]})


def test_exhausted_local_request_keeps_an_empty_complete_pool(tmp_path):
    intent = construction.author_molecular_edit(
        Path("examples/molecular-editing/request.json"), end_placements=((0, 0),)
    ).write(tmp_path / "intent")
    result = construction.execute_molecular_edit(intent / "edit.json").write(tmp_path / "result")
    pool = construction.load_scaffold_exploration(result)
    choices = construction.query_scaffold_variants(
        pool,
        {
            "result_digest": pool.result_digest,
            "stage": "hairpin",
            "focus": "loop",
        },
    )
    summary = json.loads(choices.json_bytes)
    assert summary["compatible_options"] == []
    assert summary["products"] == summary["variants"] == []
    assert summary["local_coverage"]
    assert summary["status"] == "no_compatible_options_in_evaluated_pool"
