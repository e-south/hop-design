"""The landscape reads recorded descriptors; selected preparations still replay."""

import json
import shutil

import pytest

from hop_design import construction
from tests.integration.test_design_discovery import intent_document


@pytest.fixture(scope="module")
def choices(tmp_path_factory):
    return construction.discover_designs(
        intent_document(),
        tmp_path_factory.mktemp("descriptor-index") / "choices",
        max_evaluations=1,
    )


def test_reopened_landscape_does_not_recover_every_complete_route(choices, monkeypatch):
    from hop_design.design.construction.intents.inserts import admission

    loaded = construction.load_design_choices(choices._directory)
    expected = loaded.query()["paths"][0]

    def forbidden(*args, **kwargs):
        pytest.fail("Landscape fitting must use the recorded descriptor index")

    monkeypatch.setattr(admission, "admitted_options", forbidden)
    landscape = loaded.landscape()
    assert len(landscape.preparations) == 1
    descriptor = landscape.preparations[0]
    assert descriptor.identity == expected["materialized_realization_id"]
    assert descriptor.stem == intent_document()["stem_arm"]
    assert descriptor.shape["loop_nt"] == expected["values"]["loop_nt"]


def test_indexed_descriptor_agrees_with_selected_authority(choices, tmp_path):
    from hop_design.design.construction.navigation.molecular_descriptor import molecular_descriptor
    from hop_design.models.construction.complete.realization import (
        MaterializedConstructionRealization,
    )

    selected = choices.sample(seed=1)
    choices.retrieve(selected, tmp_path / "materials")
    raw = json.loads((tmp_path / "materials/construction/construction-result.json").read_bytes())
    route = MaterializedConstructionRealization.model_validate_json(
        json.dumps(raw["realizations"][0])
    )
    assert choices.landscape().preparations == (molecular_descriptor(route),)


def test_resealed_descriptor_cannot_change_retrieved_molecule(choices, tmp_path):
    from tests.integration.test_interface_survey_integrity import mutate

    root = tmp_path / "altered"
    shutil.copytree(choices._directory, root)

    def change(record):
        descriptor = record["projections"][0]["molecular_descriptor"]
        descriptor["sequences"]["loop"][0] = "C"

    mutate(root / "intent/request.json", root / "survey.sqlite", change)
    loaded = construction.load_design_choices(root)
    # This is an index-integrity view, not a complete molecular replay.
    assert loaded.landscape().preparations[0].sequences["loop"][0] == "C"
    with pytest.raises(ValueError, match="plotting facts"):
        loaded.retrieve(loaded.sample(seed=1), tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()


def test_descriptor_scope_rejects_a_resealed_different_stem(choices, tmp_path):
    from tests.integration.test_interface_survey_integrity import mutate

    root = tmp_path / "altered"
    shutil.copytree(choices._directory, root)

    def change(record):
        record["projections"][0]["molecular_descriptor"]["stem"] = "AAAA"

    mutate(root / "intent/request.json", root / "survey.sqlite", change)
    with pytest.raises(ValueError, match="scope"):
        construction.load_design_choices(root).landscape()
