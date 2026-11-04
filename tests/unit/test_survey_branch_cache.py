"""Repeated survey navigation reuses strict products without crossing dependencies."""

import json

import pytest

from hop_design.design.construction.surveys import branches as module
from hop_design.models.construction.product_request import ProductRequest
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.serialization import canonical_json_bytes
from tests.unit.test_interface_survey_request import survey_document

LIMITS = SurveyEvaluationLimits(local_nodes=100, local_realizations=20, release_site_pairs=10)


def branches():
    return module.SurveyBranches(
        InterfaceSurveyRequest.model_validate_json(json.dumps(survey_document()))
    )


def count_parses(monkeypatch):
    original = ProductRequest.model_validate_json
    calls = []

    def counted(cls, *args, **kwargs):
        calls.append(args[0])
        return original(*args, **kwargs)

    monkeypatch.setattr(ProductRequest, "model_validate_json", classmethod(counted))
    return calls


def test_repeated_address_reuses_validation_only_within_its_invocation(monkeypatch):
    first, second = branches(), branches()
    calls = count_parses(monkeypatch)
    original = first.product(0, branch=0, limits=LIMITS)
    for _ in range(5):
        assert first.product(0, branch=0, limits=LIMITS) == original
    assert len(calls) == 1
    assert second.product(0, branch=0, limits=LIMITS) == original
    assert len(calls) == 2


def test_target_branch_and_every_limit_remain_separate_cache_dependencies(monkeypatch):
    scope = branches()
    calls = count_parses(monkeypatch)
    base = scope.product(0, branch=0, limits=LIMITS)
    assert scope.product(1, branch=0, limits=LIMITS).ends.right.cohesive_end_sequence == "AAAC"
    assert scope.product(0, branch=1, limits=LIMITS) != base
    for field in type(LIMITS).model_fields:
        # Default-valued limits may be omitted from canonical serialization;
        # the cache must still distinguish every field of the actual model.
        values = {name: getattr(LIMITS, name) for name in type(LIMITS).model_fields}
        if field == "scheduling":
            values[field] = "discovery"
        elif field == "objective":
            values[field] = {"kind": "diversity", "parameters": ("loop_nt",)}
        else:
            values[field] += -1 if values[field] >= 100_000 else 1
        limits = SurveyEvaluationLimits.model_validate(values)
        scope.product(0, branch=0, limits=limits)
        scope.product(0, branch=0, limits=limits)
    assert len(calls) == 3 + len(type(LIMITS).model_fields)


@pytest.mark.parametrize("invalid", [True, False, 0.0, -1, 10**50])
def test_warm_cache_still_rejects_invalid_target_or_branch_addresses(invalid):
    scope = branches()
    scope.product(0, branch=0, limits=LIMITS)
    scope.product(1, branch=1, limits=LIMITS)
    with pytest.raises(ValueError, match="target"):
        scope.product(invalid, branch=0, limits=LIMITS)
    with pytest.raises(ValueError, match="branch"):
        scope.product(0, branch=invalid, limits=LIMITS)


def test_bounded_product_cache_evicts_old_addresses_without_changing_results(monkeypatch):
    monkeypatch.setattr(module, "_PRODUCT_CACHE_ENTRIES", 2, raising=False)
    scope = branches()
    calls = count_parses(monkeypatch)
    products = [scope.product(i, branch=0, limits=LIMITS) for i in (0, 1, 0, 2, 0)]
    assert len(calls) == 3
    assert products[0] == products[2] == products[4]
    assert scope.product(1, branch=0, limits=LIMITS) == products[1]
    assert len(calls) == 4


def test_oversized_product_is_validated_and_returned_but_not_retained(monkeypatch):
    monkeypatch.setattr(module, "_PRODUCT_CACHE_BYTES", 1, raising=False)
    scope = branches()
    calls = count_parses(monkeypatch)
    first = scope.product(0, branch=0, limits=LIMITS)
    assert scope.product(0, branch=0, limits=LIMITS) == first
    assert len(calls) == 2
    assert not scope._products


def test_combined_product_bytes_enforce_the_memory_budget(monkeypatch):
    uncached = branches()
    size = max(
        len(canonical_json_bytes(uncached.product(i, branch=0, limits=LIMITS))) for i in (0, 1)
    )
    monkeypatch.setattr(module, "_PRODUCT_CACHE_BYTES", size, raising=False)
    scope = branches()
    calls = count_parses(monkeypatch)
    a = scope.product(0, branch=0, limits=LIMITS)
    scope.product(1, branch=0, limits=LIMITS)
    assert scope.product(0, branch=0, limits=LIMITS) == a
    assert len(calls) == 3
    assert len(scope._products) == 1
