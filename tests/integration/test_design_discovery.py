"""One optional-intent lifecycle delegates to existing construction verification."""

import json
import shutil

import pytest

from hop_design import construction
from tests.unit.test_interface_survey_request import survey_document


def intent_document():
    context = survey_document()
    stem = context.pop("stem_arm")
    context.pop("targets")
    context.pop("name", None)
    context.update(
        schema="hop.construction-context/v1",
        context_id="test-permissions/v1",
        description="Public synthetic fixture, with explicit narrow geometry.",
        product="released_insert",
        source_context_objective="all_words",
    )
    context["placements"] = [{"left_bp": 6, "right_bp": 6}]
    context["basal"]["annealing_lengths_nt"] = [17]
    return {"stem_arm": stem, "product": "released_insert", "context": context}


def test_open_intent_reaches_choices_without_authoring_ends(tmp_path):
    directory = tmp_path / "designs"
    choices = construction.discover_designs(intent_document(), directory, max_evaluations=2)
    query = choices.query()
    assert query["coverage"]["target_pairs"] == 65536
    assert query["matching_preparations"] >= 1
    assert choices.resolution["intent"]["ends"] is None
    selected = choices.sample(seed=1)
    assert selected["materialized_realization_id"] in {
        p["materialized_realization_id"] for p in query["paths"]
    }
    assert choices.figure(selection=selected).json_bytes
    atlas = choices.atlas(selected)
    assert (
        json.loads(atlas.json_bytes)["atlas"]["materialized_realization_id"]
        == selected["materialized_realization_id"]
    )
    receipt = choices.retrieve(selected, tmp_path / "preparation")
    assert selected["materialized_realization_id"] in receipt.materialized_realization_ids
    relocated = tmp_path / "relocated"
    shutil.copytree(directory, relocated)
    loaded = construction.load_design_choices(relocated)
    assert loaded.sample(seed=1) == selected
    assert loaded.query() == query
    with pytest.raises(FileExistsError):
        construction.discover_designs(intent_document(), directory, max_evaluations=1)


@pytest.mark.parametrize(
    "ends", [{"left": "AAAA"}, {"right": "AAAA"}, {"left": "AGTC", "right": "AGTC"}]
)
def test_optional_exact_ends_survive_discovery(ends, tmp_path):
    intent = {**intent_document(), "ends": ends}
    choices = construction.discover_designs(intent, tmp_path / "designs", max_evaluations=2)
    matches = choices.query()["paths"]
    assert matches
    for path in matches:
        for side, word in ends.items():
            assert path["values"][side + "_end_word"] == word


def test_continuation_returns_a_new_snapshot_and_rejects_changed_permissions(tmp_path):
    directory = tmp_path / "designs"
    before = construction.discover_designs(intent_document(), directory, max_evaluations=1)
    query = before.query()
    after = before.find_more(max_evaluations=1)
    assert before.query() == query
    assert after.query()["snapshot_digest"] != query["snapshot_digest"]
    assert after.resolution == before.resolution
    request = directory / "intent/request.json"
    content = json.loads(request.read_bytes())
    content["targets"] = {"left_words": ["TTTT"]}
    request.write_text(json.dumps(content))
    with pytest.raises(ValueError, match="digest"):
        construction.load_design_choices(directory)


def test_open_default_discovers_in_a_finite_batch_without_narrowing_permissions(tmp_path):
    intent = {"stem_arm": "ATAACTTCGTATAGCATACATTATACGAAGTTAT", "product": "released_insert"}
    result = construction.discover_designs(intent, tmp_path / "designs", max_evaluations=64)
    assert result.query()["matching_preparations"] >= 1
    assert result.query()["coverage"]["unexamined_pairs"] > 0
    assert result.resolution["intent"]["ends"] is None
    assert len(result.resolution["effective_request"]["placements"]) == 49


def test_choice_labels_have_method_and_material_facts_before_internal_ids(tmp_path):
    pool = construction.discover_designs(intent_document(), tmp_path / "designs", max_evaluations=1)
    path = pool.query()["paths"][0]
    assert path["methods"]
    assert path["material_roles"]
    assert all("name" in m for m in path["methods"])


def test_saved_resolution_cannot_misstate_the_authored_intention(tmp_path):
    from hop_design.serialization import canonical_json_bytes, sha256_digest

    directory = tmp_path / "designs"
    construction.discover_designs(intent_document(), directory, max_evaluations=1)
    root = directory / "intent"
    summary = json.loads((root / "summary.json").read_bytes())
    summary["intent"]["ends"] = {"left": "AAAA", "right": None}
    content = canonical_json_bytes(summary)
    (root / "summary.json").write_bytes(content)
    manifest = json.loads((root / "manifest.json").read_bytes())
    manifest["artifacts"]["summary.json"] = sha256_digest(content)
    (root / "manifest.json").write_bytes(canonical_json_bytes(manifest))
    with pytest.raises(ValueError, match="disagree"):
        construction.load_design_choices(directory)


def test_exact_preparation_identity_can_be_selected_without_record_coordinates(tmp_path):
    choices = construction.discover_designs(
        intent_document(), tmp_path / "designs", max_evaluations=1
    )
    path = choices.query()["paths"][0]
    assert choices.select(path["materialized_realization_id"]) == choices.select(path)
    with pytest.raises(ValueError, match="matching"):
        choices.select(
            path["materialized_realization_id"],
            query={"parameters": [{"key": "left_end_word", "values": ["TTTT"]}]},
        )


@pytest.mark.parametrize("operation", ["figure", "atlas", "retrieve"])
def test_exports_cannot_write_inside_saved_discovery_authority(operation, tmp_path):
    root = tmp_path / "designs"
    choices = construction.discover_designs(intent_document(), root, max_evaluations=1)
    selected = choices.sample(seed=1)
    output = root / "intent" / operation
    with pytest.raises(ValueError, match=r"[Pp]rotected|outside"):
        if operation == "retrieve":
            choices.retrieve(selected, output)
        elif operation == "figure":
            choices.figure(selection=selected).write(output)
        else:
            choices.atlas(selected).write(output)
    assert not output.exists()
    assert construction.load_design_choices(root).sample(seed=1) == selected
