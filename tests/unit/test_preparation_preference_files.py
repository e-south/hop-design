"""Captured input files remain bound after moving, without trusting local paths."""

import json
from types import SimpleNamespace

import pytest

from hop_design.design.construction.surveys.admission import preference as preference_inputs
from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.evaluate import LocalReceipts
from hop_design.models.bundle import ArtifactManifestEntry
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.preference import SurveyPreparationReference
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.serialization import sha256_digest
from tests.unit.test_interface_survey_request import survey_document
from tests.unit.test_preparation_preference_contract import binding


def test_captured_files_are_content_checked_and_relocatable(tmp_path):
    content = b'{"synthetic": true}'
    root = tmp_path / "preferred-preparation"
    root.mkdir()
    path = root / "construction-bundle.json"
    path.write_bytes(content)
    binding = SurveyPreparationReference(
        result_id="hop:construction-space/" + "1" * 64 + "@1",
        materialized_realization_id="hop:materialized-construction/" + "2" * 64 + "@1",
        files=(
            ArtifactManifestEntry(
                path=path.name,
                digest=sha256_digest(content),
                size_bytes=len(content),
                media_type="application/json",
            ),
        ),
    )
    assert preference_inputs.read_preference_files(root, binding) == {path.name: content}
    moved = tmp_path / "moved"
    root.rename(moved)
    assert preference_inputs.read_preference_files(moved, binding) == {path.name: content}
    (moved / path.name).write_bytes(content.replace(b"true", b"null"))
    with pytest.raises(ValueError, match="digest"):
        preference_inputs.read_preference_files(moved, binding)
    (moved / path.name).write_bytes(content * 10)
    with pytest.raises(ValueError, match="size"):
        preference_inputs.read_preference_files(moved, binding)


def test_reference_file_cannot_follow_a_symlink_outside_capture(tmp_path):
    outer = tmp_path / "outside.json"
    outer.write_bytes(b"{}")
    root = tmp_path / "preferred-preparation"
    root.mkdir()
    (root / "construction-bundle.json").symlink_to(outer)
    binding = SurveyPreparationReference(
        result_id="hop:construction-space/" + "1" * 64 + "@1",
        materialized_realization_id="hop:materialized-construction/" + "2" * 64 + "@1",
        files=(
            ArtifactManifestEntry(
                path="construction-bundle.json",
                digest=sha256_digest(b"{}"),
                size_bytes=2,
                media_type="application/json",
            ),
        ),
    )
    with pytest.raises(ValueError, match="outside"):
        preference_inputs.read_preference_files(root, binding)


def test_reference_must_be_admitted_before_the_first_candidate():
    data = survey_document()
    data.update(
        source_context_objective="paired_scaffold_completions", preferred_preparation=binding()
    )
    request = InterfaceSurveyRequest.model_validate_json(json.dumps(data))
    limits = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=100)

    def missing(digest):
        raise ValueError("Missing preferred authority")

    receipts = LocalReceipts(SimpleNamespace(request=request, get_object=missing), limits)
    with pytest.raises(ValueError, match="Missing preferred authority"):
        receipts.first_address(SurveyBranches(request), limits, 0)
