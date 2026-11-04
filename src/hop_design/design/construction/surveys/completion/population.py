"""Keep local admission and endpoint-conditioned candidates as separate claims."""

from dataclasses import dataclass

from hop_design.kernel.construction.basal.conditioned_population import ConditionedBasalPopulation
from hop_design.kernel.construction.basal.sequence_population import BasalSequencePopulation
from hop_design.kernel.construction.release_population import admit_release_population
from hop_design.models.construction.complete.source_preparation.policy import SourceSsdnaPolicy
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.sequence_sets import SequenceSpaceLimits

from ..basal_population import BasalPopulation


@dataclass(frozen=True)
class EndpointPopulation:
    population: BasalPopulation
    local_configurations: int
    translated_programs: int
    untranslated_programs: int

    def facts(self) -> dict[str, object]:
        return {
            "scope": "necessary_endpoint_admission",
            "local_configurations": self.local_configurations,
            "candidate_configurations": self.population.parts,
            "translated_programs": self.translated_programs,
            "untranslated_programs": self.untranslated_programs,
        }


def condition_population(
    product: ProductRequest,
    local: BasalPopulation,
    source: SourceSsdnaPolicy,
    limits: SequenceSpaceLimits,
) -> EndpointPopulation:
    supports: list[BasalSequencePopulation | ConditionedBasalPopulation] = []
    translated = untranslated = 0
    for support in local.supports:
        if not isinstance(support, BasalSequencePopulation):
            raise ValueError("Endpoint conditioning requires the original local population.")
        permitted = admit_release_population(product, support, source, limits)
        if permitted is None:
            untranslated += 1
            supports.append(support)
        else:
            translated += 1
            subset = ConditionedBasalPopulation(support, permitted, limits)
            if subset.cardinality:
                supports.append(subset)
    population = BasalPopulation(tuple(supports), local.candidate_count, local.program_count)
    return EndpointPopulation(population, local.parts, translated, untranslated)
