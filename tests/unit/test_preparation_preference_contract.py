"""A preferred preparation is an explicit bounded input, never extra permission."""

import json

import pytest

from hop_design.design.construction.intents.resolve import resolve_design_request
from hop_design.models.construction.intents.request import ConstructionIntent
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.unit.test_interface_survey_request import survey_document


def binding():
    return {
        "result_id": "hop:construction-space/" + "1" * 64 + "@1",
        "materialized_realization_id": "hop:materialized-construction/" + "2" * 64 + "@1",
        "files": [
            {
                "path": "construction-bundle.json",
                "digest": "sha256:" + "3" * 64,
                "size_bytes": 10,
                "media_type": "application/json",
            }
        ],
    }


def test_intent_accepts_preference_without_fixing_materials_or_ends():
    request = ConstructionIntent.model_validate_json(
        json.dumps(
            {
                "stem_arm": "ACGTAC",
                "product": "released_insert",
                "prefer_preparation": {"bundle_path": "known", "selection_path": "selection.json"},
            }
        )
    )
    assert request.prefer_preparation.bundle_path == "known"
    assert request.ends is None and request.scaffold is None


def test_resolution_must_read_the_declared_preparation(tmp_path):
    with pytest.raises((ValueError, FileNotFoundError)):
        resolve_design_request(
            {
                "stem_arm": "ACGTAC",
                "product": "released_insert",
                "prefer_preparation": {
                    "bundle_path": str(tmp_path / "missing"),
                    "selection_path": str(tmp_path / "selection.json"),
                },
            }
        )


def test_other_endpoints_do_not_silently_ignore_unsupported_preference():
    with pytest.raises(ValueError, match=r"preparation.*released"):
        ConstructionIntent.model_validate_json(
            json.dumps(
                {
                    "stem_arm": "ACGTAC",
                    "product": "hairpin",
                    "prefer_preparation": {
                        "bundle_path": "known",
                        "selection_path": "selection.json",
                    },
                }
            )
        )


def test_survey_binding_is_small_explicit_and_preserves_default_bytes():
    data = survey_document()
    ordinary = InterfaceSurveyRequest.model_validate_json(json.dumps(data))
    assert "preferred_preparation" not in ordinary.model_dump(mode="json")
    data.update(
        source_context_objective="paired_scaffold_completions", preferred_preparation=binding()
    )
    parsed = InterfaceSurveyRequest.model_validate_json(json.dumps(data))
    assert parsed.preferred_preparation.files[0].path == "construction-bundle.json"
    assert parsed.targets == ordinary.targets
    assert parsed.foldback == ordinary.foldback and parsed.basal == ordinary.basal


@pytest.mark.parametrize("problem", ["mode", "duplicate", "traversal", "size", "missing_manifest"])
def test_invalid_preference_binding_is_rejected(problem):
    data = survey_document()
    ref = binding()
    data.update(source_context_objective="paired_scaffold_completions", preferred_preparation=ref)
    if problem == "mode":
        data["source_context_objective"] = "all_words"
    elif problem == "duplicate":
        ref["files"] *= 2
    elif problem == "traversal":
        ref["files"][0]["path"] = "../other.json"
    elif problem == "size":
        ref["files"][0]["size_bytes"] = 64 * 1024 * 1024 + 1
    else:
        ref["files"][0]["path"] = "other.json"
    with pytest.raises(ValueError):
        InterfaceSurveyRequest.model_validate_json(json.dumps(data))
