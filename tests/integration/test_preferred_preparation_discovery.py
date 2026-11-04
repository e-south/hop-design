"""A supplied preparation is recompiled inside one broader, portable choice owner."""

import json
from pathlib import Path

import pytest

from hop_design import construction
from hop_design.design.construction.selection_reference import select_construction_realization
from hop_design.design.construction.surveys.index import SurveyIndex
from hop_design.design.construction.surveys.preference_addressing import material_signature
from tests.support.context_completion import LIMITS, records
from tests.unit.test_interface_survey_request import survey_document


@pytest.mark.parametrize("interrupt_initialization", [False, True])
def test_preferred_preparation_replays_and_resumes_without_importing_a_witness(
    tmp_path, monkeypatch, interrupt_initialization
):
    packet = construction.execute_construction_request(
        Path("examples/complete-construction/product-request.json"),
        design_id="preferred-preparation-example",
        continuation="sole-witness",
    )
    receipt = packet._compilation
    assert receipt is not None and len(receipt.materialized_realization_ids) == 1
    prior = tmp_path / "prior"
    packet.write(prior)
    select_construction_realization(
        receipt, materialized_realization_id=receipt.materialized_realization_ids[0]
    ).write(prior / "selected.json")
    native = survey_document()
    native["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "N" * 14
    )
    context = {
        key: value
        for key, value in native.items()
        if key not in {"schema", "stem_arm", "targets", "name"}
    }
    context.update(
        schema="hop.construction-context/v1",
        context_id="preferred-example/v1",
        description="Broad synthetic preparation permissions.",
        product="released_insert",
        source_context_objective="paired_scaffold_completions",
    )
    intent = {
        "stem_arm": native["stem_arm"],
        "product": "released_insert",
        "context": context,
        "prefer_preparation": {
            "bundle_path": str(prior / "construction"),
            "selection_path": str(prior / "selected.json"),
        },
    }
    baseline = json.loads(
        construction.resolve_design_request(
            {key: value for key, value in intent.items() if key != "prefer_preparation"}
        ).json_bytes
    )["effective_request"]
    if interrupt_initialization:
        original = SurveyIndex.put_object
        calls = 0

        def interrupted(self, content):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("interrupted reference import")
            return original(self, content)

        with monkeypatch.context() as patch:
            patch.setattr(SurveyIndex, "put_object", interrupted)
            with pytest.raises(OSError, match="interrupted reference"):
                construction.discover_designs(
                    intent, tmp_path / "split", effort=LIMITS, max_evaluations=1
                )
        assert not (tmp_path / "split/survey.sqlite").exists()
        first = construction.continue_design_discovery(tmp_path / "split", max_evaluations=1)
    else:
        first = construction.discover_designs(
            intent, tmp_path / "split", effort=LIMITS, max_evaluations=1
        )
    assert first.query()["matching_preparations"] == 0  # Prefix navigation is not a witness.
    whole = construction.discover_designs(
        intent, tmp_path / "whole", effort=LIMITS, max_evaluations=2
    )
    prior.rename(tmp_path / "original-moved")
    moved = tmp_path / "relocated"
    (tmp_path / "split").rename(moved)
    resumed = construction.continue_design_discovery(moved, max_evaluations=1)
    assert records(moved / "survey.sqlite") == records(tmp_path / "whole/survey.sqlite")
    assert resumed.query() == whole.query()
    assert resumed.query()["matching_preparations"] >= 1
    selected = resumed.sample(seed=0)
    retrieved = resumed.retrieve(selected, tmp_path / "retrieved")
    expected = receipt._verified_source().result.realizations[0]
    actual = next(
        r
        for r in retrieved._verified_source().result.realizations
        if r.materialized_realization_id == selected["materialized_realization_id"]
    )
    assert material_signature(actual) == material_signature(expected)
    effective = json.loads((moved / "intent/request.json").read_bytes())
    assert {
        key: value for key, value in effective.items() if key != "preferred_preparation"
    } == baseline
    assert (
        construction.verify_interface_survey(
            moved / "intent/request.json", moved / "survey.sqlite"
        )["replayed_evaluations"]
        == 2
    )
