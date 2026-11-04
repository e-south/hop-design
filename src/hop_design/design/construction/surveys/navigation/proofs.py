"""Create and replay certificates for full basal populations with no members."""

from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.proofs import EmptyBasalFacts, EmptyBasalPlane
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..basal_population import BasalPopulation, admit_population
from ..branches import SurveyBranches
from ..coordinates import coordinate_at


def _plane(branches: SurveyBranches, branch: int) -> tuple[int, int, int, int, int]:
    if type(branch) is not int or not 0 <= branch < branches.count:
        raise ValueError("Plane representative lies outside the survey domain.")
    geometry = coordinate_at(branches.geometry_sizes, branch % branches.geometry_count)
    return geometry[0], geometry[1], geometry[2], geometry[3], geometry[5]


def certify_empty_basal(
    branches: SurveyBranches,
    limits: SurveyEvaluationLimits,
    *,
    target: int,
    branch: int,
    population: BasalPopulation,
    producer: dict[str, str],
) -> EmptyBasalPlane | None:
    """Record an ordinary completed admission; no new search or reordered check."""
    if population.parts != 0:
        return None
    local = branches.product(target, branch=branch, limits=limits).construction_source().basal
    assert local is not None
    if local.search.sequence_partition is not None:
        return None
    return EmptyBasalPlane(
        survey_digest=sha256_digest(canonical_json_bytes(branches.request)),
        producer_digest=sha256_digest(canonical_json_bytes(producer)),
        target=target,
        branch=branch,
        coordinates=_plane(branches, branch),
        basal_request=local,
        evaluation_limits=limits,
        facts=EmptyBasalFacts.model_validate(population.facts()),
    )


def verify_empty_basal(
    proof: EmptyBasalPlane,
    branches: SurveyBranches,
    limits: SurveyEvaluationLimits,
    *,
    producer: dict[str, str],
) -> tuple[int, int, int, int, int]:
    """Recompute scope and local admission; hashing alone does not prove exclusion."""
    if (
        proof.survey_digest != sha256_digest(canonical_json_bytes(branches.request))
        or proof.producer_digest != sha256_digest(canonical_json_bytes(producer))
        or proof.evaluation_limits != limits
        or proof.coordinates != _plane(branches, proof.branch)
    ):
        raise ValueError("Empty-plane proof scope disagrees with the bound survey.")
    local = (
        branches.product(proof.target, branch=proof.branch, limits=limits)
        .construction_source()
        .basal
    )
    if (
        local is None
        or local.search.sequence_partition is not None
        or canonical_json_bytes(local) != canonical_json_bytes(proof.basal_request)
    ):
        raise ValueError("Empty-plane proof does not match its entire basal request.")
    # A SequenceSetLimitError propagates: an unresolved population is not empty.
    actual = admit_population(local, limits.sequence_space_limits)
    if actual.parts != 0 or actual.facts() != proof.facts.model_dump(mode="json"):
        raise ValueError(
            "Empty-plane molecular replay disagrees with its complete admission facts."
        )
    return proof.coordinates
