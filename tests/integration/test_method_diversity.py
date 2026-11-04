"""Method allocation feeds back only complete witnesses and survives cold resume."""

import json

from hop_design import construction
from hop_design.design.construction.search.diversity import allocation_classes
from hop_design.design.construction.surveys.branches import SurveyBranches
from hop_design.design.construction.surveys.navigation.diversity import (
    local_page_values,
)
from hop_design.design.construction.surveys.partitions import PartitionPlans
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from tests.integration.test_design_discovery import intent_document
from tests.support.context_completion import records


def test_method_feedback_matches_compiled_roles_and_retains_exact_resume(tmp_path):
    intent = intent_document()
    intent["context"]["source_context_objective"] = "paired_scaffold_completions"
    intent["ends"] = {"left": "AGTC", "right": "AGTC"}
    objective = {"kind": "diversity", "parameters": ["basal_method", "foldback_method"]}
    first = construction.discover_designs(
        intent, tmp_path / "split", max_evaluations=2, objective=objective
    )
    continued = construction.load_design_choices(tmp_path / "split").find_more(max_evaluations=2)
    whole = construction.discover_designs(
        intent, tmp_path / "whole", max_evaluations=4, objective=objective
    )
    assert continued.query() == whole.query()
    assert continued.query()["paths"]
    assert records(tmp_path / "split/survey.sqlite") == records(tmp_path / "whole/survey.sqlite")
    request = InterfaceSurveyRequest.model_validate_json(
        json.dumps(first.resolution["effective_request"])
    )
    limits = SurveyEvaluationLimits.model_validate_json(
        (tmp_path / "split/effort.json").read_bytes()
    )
    branches = SurveyBranches(request)
    plans = PartitionPlans(request=request, limits=limits.sequence_space_limits)
    observed = set()
    checked = 0
    for record in records(tmp_path / "split/survey.sqlite"):
        if record["projections"]:
            address = record["completion"]
            product = branches.product(
                record["target"], branch=address["geometry_rank"], limits=limits
            )
            facts = local_page_values(
                plans.get(product), address["page"], limits.objective.parameters
            )
            for projection in record["projections"]:
                assert facts == {
                    key: projection["values"][key] for key in limits.objective.parameters
                }
                observed.update(allocation_classes(limits.objective, projection["values"]))
                checked += 1
        following = record.get("next") or {}
        cursor = following.get("completion_seek", following.get("completion", {}).get("after"))
        if cursor is not None:
            assert set(cursor.get("observed_classes", ())) == observed
    assert checked > 0
    selected = continued.sample(seed=0)
    receipt = continued.retrieve(selected, tmp_path / "preparation")
    route = next(
        item
        for item in receipt._verified_source().result.realizations
        if item.materialized_realization_id == selected["materialized_realization_id"]
    )
    path = next(
        item
        for item in continued.query()["paths"]
        if item["materialized_realization_id"] == route.materialized_realization_id
    )
    assert path["values"]["basal_method"] == route.basal_authority.basal_nick.enzyme_id
    assert path["values"]["foldback_method"] == route.foldback_authority.foldback_nick.enzyme_id
