"""Only complete local molecular evidence can exclude a basal plane."""

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from hop_design.design.construction.surveys.basal_population import admit_population
from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.coordinates import coordinate_rank
from hop_design.design.construction.surveys.navigation.proofs import (
    certify_empty_basal,
    verify_empty_basal,
)
from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.serialization import canonical_json_bytes
from tests.unit.test_interface_survey_request import survey_document

PRODUCER = {"implementation": "test-producer"}
LIMITS = SurveyEvaluationLimits(local_nodes=100, local_realizations=100, release_site_pairs=10)


def case():
    document = survey_document()
    document["foldback"]["geometry"]["loop_lengths_nt"] = [4, 5]
    document["foldback"]["max_retained_overhead_nt"] = 17
    document["materialization"]["source_preparation"]["source_ssdna"]["upstream_sequence_spec"] = (
        "ACGTACAGTCGTAN"
    )
    branches = SurveyBranches(InterfaceSurveyRequest.model_validate_json(json.dumps(document)))
    local = branches.product(0, branch=0, limits=LIMITS).construction_source().basal
    population = admit_population(local, LIMITS.sequence_space_limits)
    assert population.parts == 0
    proof = certify_empty_basal(
        branches, LIMITS, target=0, branch=0, population=population, producer=PRODUCER
    )
    return branches, local, population, proof


def test_free_foldback_and_context_axes_really_preserve_the_entire_basal_request():
    branches, local, _, proof = case()
    assert proof is not None
    expected = canonical_json_bytes(local)
    for context in range(branches.context_count):
        for foldback in range(branches.geometry_sizes[4]):
            geometry = coordinate_rank(branches.geometry_sizes, (0, 0, 0, 0, foldback, 0))
            branch = context * branches.geometry_count + geometry
            observed = branches.product(0, branch=branch, limits=LIMITS).construction_source().basal
            assert canonical_json_bytes(observed) == expected
    assert verify_empty_basal(proof, branches, LIMITS, producer=PRODUCER) == (0, 0, 0, 0, 0)


def test_nonempty_local_population_cannot_be_certified_from_zero_candidate_count():
    branches, _, empty, _ = case()
    nonempty = replace(empty, supports=(SimpleNamespace(cardinality=1),))
    assert (
        certify_empty_basal(
            branches, LIMITS, target=0, branch=0, population=nonempty, producer=PRODUCER
        )
        is None
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("target", 1),
        ("branch", 10**30),
        ("coordinates", (0, 1, 0, 0, 0)),
        ("survey_digest", "0" * 64),
        ("producer_digest", "0" * 64),
    ],
)
def test_rehashed_proof_claims_still_require_rederived_scope(field, value):
    branches, _, _, proof = case()
    changed = proof.model_copy(update={field: value})
    with pytest.raises(ValueError):
        verify_empty_basal(changed, branches, LIMITS, producer=PRODUCER)


def test_rehashed_admission_facts_require_molecular_replay():
    branches, _, _, proof = case()
    facts = proof.facts.model_copy(update={"program_count": proof.facts.program_count + 1})
    changed = proof.model_copy(update={"facts": facts})
    with pytest.raises(ValueError, match="replay"):
        verify_empty_basal(changed, branches, LIMITS, producer=PRODUCER)


def test_changed_limits_or_producer_do_not_reuse_a_certificate():
    branches, _, _, proof = case()
    with pytest.raises(ValueError):
        verify_empty_basal(
            proof, branches, LIMITS.model_copy(update={"local_nodes": 101}), producer=PRODUCER
        )
    with pytest.raises(ValueError):
        verify_empty_basal(proof, branches, LIMITS, producer={"implementation": "another"})


def test_budget_exhaustion_remains_unresolved_during_proof_admission(monkeypatch):
    from hop_design.design.construction.surveys.navigation import proofs

    branches, _, _, proof = case()

    def stop(*args, **kwargs):
        raise SequenceSetLimitError("budget exhausted")

    monkeypatch.setattr(proofs, "admit_population", stop)
    with pytest.raises(SequenceSetLimitError):
        verify_empty_basal(proof, branches, LIMITS, producer=PRODUCER)


def test_a_selected_partition_does_not_become_a_full_plane_proof():
    branches, local, _, proof = case()
    data = local.model_dump(mode="json", by_alias=True)
    data["search"]["sequence_partition"] = {"part_count": 2, "part_index": 0}
    changed = proof.model_copy(
        update={"basal_request": type(local).model_validate_json(json.dumps(data))}
    )
    with pytest.raises(ValueError):
        verify_empty_basal(changed, branches, LIMITS, producer=PRODUCER)
