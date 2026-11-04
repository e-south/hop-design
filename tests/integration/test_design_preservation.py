"""Public refinement preserves molecular surroundings through selection and handoff."""

import json

import pytest

from hop_design import construction
from tests.unit.test_construction_intent import STEM


@pytest.fixture(scope="module")
def loop_designs(tmp_path_factory):
    root = tmp_path_factory.mktemp("design-preservation")
    choices = construction.discover_designs(
        {
            "stem_arm": STEM,
            "product": "hairpin",
            "loop_words": ["GAAA", "TTTC"],
            "scaffold": {"loop_side_paired_bp": {"minimum": 7, "maximum": 8}},
        },
        root / "designs",
        max_evaluations=4,
    )
    return root / "designs", choices


def test_preservation_filters_counts_selection_and_retrieval_together(loop_designs, tmp_path):
    _, choices = loop_designs
    observed = choices.query()
    assert {p["values"]["loop_word"] for p in observed["paths"]} == {"GAAA", "TTTC"}
    reference_path = next(
        p
        for p in observed["paths"]
        if p["values"]["loop_word"] == "GAAA" and p["values"]["foldback_arm_bp"] == 7
    )
    reference = choices.select(reference_path)
    query = choices.preserve(reference, stage="hairpin", except_neighborhood="loop")
    filtered = choices.query(query)
    assert (
        "other neighborhoods remain unchanged at the hairpin" in choices.explain(query)["guidance"]
    )
    matching = [p for p in filtered["paths"] if p["matches"]]
    assert len(matching) == 2
    assert {p["values"]["foldback_arm_bp"] for p in matching} == {7}
    assert {p["values"]["loop_word"] for p in matching} == {"GAAA", "TTTC"}
    arm_axis = next(a for a in filtered["axes"] if a["key"] == "foldback_arm_bp")
    assert next(n for n in arm_axis["nodes"] if n["value"] == 8)["conditional_preparations"] == 0
    excluded = next(p for p in filtered["paths"] if not p["matches"])
    with pytest.raises(ValueError, match="matching"):
        choices.select(excluded, query=query)
    selected = choices.select(
        next(p for p in matching if p["values"]["loop_word"] == "TTTC"), query=query
    )
    change = next(c for c in filtered["changes"] if c["label"] == selected["option_label"])
    assert change["molecular_neighborhoods"] == ["loop"]
    assert "source_ssdna" in change["material_roles"]
    figure = json.loads(choices.figure(selection=selected).json_bytes)
    assert figure["matching_preparations"] == 2
    assert figure["selection"] == selected
    assert choices.atlas(selected).json_bytes
    receipt = choices.retrieve(selected, tmp_path / "preparation")
    assert receipt.materialized_realization_ids == (selected["materialized_realization_id"],)
    assert choices.query()["matching_preparations"] == observed["matching_preparations"]


def test_required_comparison_is_explicit_and_retrieves_named_members(loop_designs, tmp_path):
    _, choices = loop_designs
    reference = choices.sample(
        seed=0,
        query={
            "parameters": [
                {"key": "foldback_arm_bp", "values": [7]},
                {"key": "loop_word", "values": ["GAAA"]},
            ]
        },
    )
    query = choices.preserve(reference, stage="hairpin", except_neighborhood="loop")
    request = {
        "stage": "hairpin",
        "required_members": [
            {"name": "gaaa", "loop_sequence": "GAAA"},
            {"name": "tttc", "loop_sequence": "TTTC"},
        ],
        "max_group_evaluations": 16,
    }
    comparison = choices.compare(request, query=query)
    assert (
        choices.compare(
            {**request, "required_members": list(reversed(request["required_members"]))},
            query=query,
        )
        == comparison
    )
    assert comparison["status"] == "comparison_available"
    assert comparison["selected_set"] is None
    assert len(comparison["sets"]) == 1
    selected = choices.select_set(
        comparison, set_label=comparison["sets"][0]["label"], baseline="gaaa"
    )
    assert set(selected["members"]) == {"gaaa", "tttc"}
    receipt = choices.retrieve(selected, tmp_path / "comparison")
    assert receipt.materialized_realization_ids == tuple(
        selected["members"][name]["materialized_realization_id"] for name in ("gaaa", "tttc")
    )
    for member in selected["members"].values():
        assert member["query"] == query
        assert choices.atlas(member).json_bytes
    handoff = json.loads((tmp_path / "comparison" / "summary.json").read_bytes())
    assert {m["name"] for m in handoff["members"]} == {"gaaa", "tttc"}


def test_required_members_cannot_disappear_into_permissions(loop_designs):
    _, choices = loop_designs
    request = {
        "stage": "hairpin",
        "required_members": [
            {"name": "gaaa", "loop_sequence": "GAAA"},
            {"name": "missing", "loop_sequence": "CCCC"},
        ],
        "max_group_evaluations": 16,
    }
    result = choices.compare(request)
    assert result["sets"] == []
    assert result["missing_members"][0]["reason"] == "not_observed_in_evaluated_pool"
    with pytest.raises(ValueError, match="Unknown comparison set"):
        choices.select_set(result, set_label="set-0001", baseline="gaaa")
    required_present = {
        **request,
        "required_members": [
            {"name": "gaaa", "loop_sequence": "GAAA", "dimensions": {"loop_side_paired_bp": 7}},
            {"name": "tttc", "loop_sequence": "TTTC", "dimensions": {"loop_side_paired_bp": 8}},
        ],
        "stage_controls": [{"stage": "hairpin", "property": "non_loop_sequences", "scope": "set"}],
    }
    incompatible = choices.compare(required_present)
    assert all(m["option_labels"] for m in incompatible["members"])
    assert incompatible["missing_members"] == []
    assert incompatible["sets"] == []
    assert incompatible["status"] == "no_compatible_set_in_evaluated_pool"
    incomplete = choices.compare(
        {
            "stage": "hairpin",
            "required_members": [{"name": n, "dimensions": {"loop_nt": 4}} for n in ("a", "b")],
            "max_group_evaluations": 1,
        }
    )
    assert incomplete["status"] == "group_evaluation_incomplete"
    assert incomplete["group_coverage"]["unexamined_assignments"] > 0


def test_comparison_rejects_inapplicable_release_method_on_hairpins(loop_designs):
    _, choices = loop_designs
    with pytest.raises(ValueError, match=r"release.*hairpin"):
        choices.compare(
            {
                "stage": "hairpin",
                "required_members": [{"name": "release", "release_enzyme_id": "BsaI-HFv2"}],
                "max_group_evaluations": 8,
            }
        )


def test_preservation_uses_the_molecule_not_the_filter_used_to_find_it(loop_designs):
    _, choices = loop_designs
    reference = choices.sample(
        seed=0,
        query={
            "parameters": [
                {"key": "foldback_arm_bp", "values": [7]},
                {"key": "loop_word", "values": ["GAAA"]},
            ]
        },
    )
    query = choices.preserve(reference, stage="hairpin", except_neighborhood="loop")
    assert query["parameters"] == []
    assert choices.query(query)["matching_preparations"] == 2
    assert len(reference["query"]["parameters"]) == 2


def test_refinement_references_and_saved_comparisons_fail_closed(loop_designs, tmp_path):
    from copy import deepcopy

    _, choices = loop_designs
    query = choices.preserve(choices.sample(seed=0), stage="hairpin", except_neighborhood="loop")
    for key in ("request_digest", "snapshot_digest", "materialized_realization_id"):
        broken = deepcopy(query)
        broken["reference"][key] = "sha256:" + "0" * 64
        with pytest.raises(ValueError, match="reference"):
            choices.query(broken)
    with pytest.raises(ValueError, match="stage"):
        choices.compare(
            {
                "stage": "endpoint",
                "required_members": [{"name": "gaaa", "loop_sequence": "GAAA"}],
                "max_group_evaluations": 8,
            },
            query=query,
        )
    with pytest.raises(ValueError, match="comparison"):
        choices.select_set(
            {"schema": "hop.design-comparison/v1"}, set_label="set-0001", baseline="gaaa"
        )
    comparison = choices.compare(
        {
            "stage": "hairpin",
            "required_members": [{"name": "gaaa", "loop_sequence": "GAAA"}],
            "max_group_evaluations": 8,
        }
    )
    altered = deepcopy(comparison)
    altered["group_coverage"]["evaluated_assignments"] += 1
    with pytest.raises(ValueError, match="disagrees"):
        choices.select_set(altered, set_label="set-0001", baseline="gaaa")
    selected = choices.select_set(comparison, set_label="set-0001", baseline="gaaa")
    selected["members"]["gaaa"]["materialized_realization_id"] = "unknown"
    with pytest.raises(ValueError, match="disagrees"):
        choices.retrieve(selected, tmp_path / "rejected")
    assert not (tmp_path / "rejected").exists()


def test_cli_refinement_and_required_set_survive_relocation(loop_designs, tmp_path):
    import shutil

    from typer.testing import CliRunner

    from hop_design.cli import app

    path, choices = loop_designs
    relocated = tmp_path / "relocated designs 'quoted'"
    shutil.copytree(path, relocated)
    reference = choices.select(
        next(p for p in choices.query()["paths"] if p["values"]["foldback_arm_bp"] == 7)
    )
    reference_path = tmp_path / "reference.json"
    reference_path.write_text(json.dumps(reference))
    refinement_path = tmp_path / "refinement.json"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "design",
            "preserve",
            str(relocated),
            "--reference",
            str(reference_path),
            "--stage",
            "hairpin",
            "--except-neighborhood",
            "loop",
            "--out",
            str(refinement_path),
        ],
    )
    assert result.exit_code == 0, result.output
    query = choices.preserve(reference, stage="hairpin", except_neighborhood="loop")
    assert json.loads(refinement_path.read_bytes()) == query
    filtered = runner.invoke(
        app,
        ["design", "query", str(relocated), "--query", str(refinement_path), "--format", "json"],
    )
    assert filtered.exit_code == 0, filtered.output
    assert json.loads(filtered.output) == choices.query(query)
    request = {
        "stage": "hairpin",
        "required_members": [
            {"name": "gaaa", "loop_sequence": "GAAA"},
            {"name": "tttc", "loop_sequence": "TTTC"},
        ],
        "max_group_evaluations": 16,
    }
    request_path = tmp_path / "comparison-request.json"
    request_path.write_text(json.dumps(request))
    comparison_path = tmp_path / "comparison.json"
    compared = runner.invoke(
        app,
        [
            "design",
            "compare",
            str(relocated),
            "--request",
            str(request_path),
            "--query",
            str(refinement_path),
            "--out",
            str(comparison_path),
            "--format",
            "text",
        ],
    )
    assert compared.exit_code == 0, compared.output
    assert "1 compatible set; none selected" in compared.output
    assert "sha256:" not in compared.output
    comparison = choices.compare(request, query=query)
    assert json.loads(comparison_path.read_bytes()) == comparison
    selection_path = tmp_path / "set.json"
    selected = runner.invoke(
        app,
        [
            "design",
            "select-set",
            str(relocated),
            "--comparison",
            str(comparison_path),
            "--set-label",
            "set-0001",
            "--baseline",
            "gaaa",
            "--out",
            str(selection_path),
        ],
    )
    assert selected.exit_code == 0, selected.output
    expected = choices.select_set(comparison, set_label="set-0001", baseline="gaaa")
    assert json.loads(selection_path.read_bytes()) == expected
    retrieved = runner.invoke(
        app,
        [
            "design",
            "retrieve",
            str(relocated),
            "--selection",
            str(selection_path),
            "--out",
            str(tmp_path / "handoff"),
        ],
    )
    assert retrieved.exit_code == 0, retrieved.output
    assert set(json.loads(retrieved.output)["witnesses"]) == {
        member["materialized_realization_id"] for member in expected["members"].values()
    }


def test_comparison_selection_keeps_its_original_snapshot_after_continuation(
    loop_designs, tmp_path
):
    _, complete = loop_designs
    first = construction.discover_designs(
        complete.resolution["intent"], tmp_path / "progressive", max_evaluations=4, first_choices=1
    )
    reference = first.sample(seed=0)
    word = next(p["values"]["loop_word"] for p in first.query()["paths"] if p["matches"])
    query = first.preserve(reference, stage="hairpin", except_neighborhood="loop")
    compared = first.compare(
        {
            "stage": "hairpin",
            "required_members": [{"name": "reference", "loop_sequence": word}],
            "max_group_evaluations": 4,
        },
        query=query,
    )
    selected = first.select_set(compared, set_label="set-0001", baseline="reference")
    latest = first.find_more(max_evaluations=3)
    assert latest.query()["snapshot_digest"] != selected["snapshot_digest"]
    with pytest.raises(ValueError, match="reference"):
        latest.query(query)
    receipt = latest.retrieve(selected, tmp_path / "historical")
    assert receipt.materialized_realization_ids == (reference["materialized_realization_id"],)
    assert (
        json.loads(latest.atlas(selected["members"]["reference"]).json_bytes)["option_label"]
        == reference["option_label"]
    )


def test_adapter_endpoint_uses_the_same_preservation_and_comparison_lifecycle(tmp_path):
    choices = construction.discover_designs(
        {
            "stem_arm": STEM,
            "product": "adapter_ligated_hairpin",
            "loop_words": ["GAAA"],
            "scaffold": {"loop_side_paired_bp": {"minimum": 7, "maximum": 7}},
        },
        tmp_path / "adapter-designs",
        max_evaluations=4,
        first_choices=1,
    )
    reference = choices.sample(seed=0)
    query = choices.preserve(reference, stage="hairpin", except_neighborhood="loop")
    assert choices.query(query)["matching_preparations"] == 1
    comparison = choices.compare(
        {
            "stage": "hairpin",
            "required_members": [{"name": "gaaa", "loop_sequence": "GAAA"}],
            "max_group_evaluations": 4,
        },
        query=query,
    )
    selected = choices.select_set(comparison, set_label="set-0001", baseline="gaaa")
    receipt = choices.retrieve(selected, tmp_path / "adapter-preparation")
    assert receipt.materialized_realization_ids == (reference["materialized_realization_id"],)
