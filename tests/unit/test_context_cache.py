"""Reuse exact context work without conflating a changed molecular declaration."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import hop_design.design.construction.surveys.context_priority as conditioning
import hop_design.design.construction.surveys.partitions as partitioning
from hop_design.design.construction.surveys.completion.population import EndpointPopulation
from hop_design.models.construction.product_request import ProductRequest
from tests.unit.test_source_context_population import inputs


def product_request():
    return ProductRequest.model_validate_json(
        Path("examples/complete-construction/product-request.json").read_text()
    )


@pytest.mark.parametrize("conditioned", [False, True])
def test_same_hint_across_foldback_pages_is_admitted_once_and_changed_hint_is_not(
    monkeypatch, conditioned
):
    policy, enzyme, action = inputs()
    plans = partitioning.PartitionPlans()
    candidates = SimpleNamespace(parts=3)
    plan = partitioning.ProductParts(
        foldback=SimpleNamespace(parts=4),
        basal=SimpleNamespace(parts=9) if conditioned else candidates,
        endpoint=EndpointPopulation(candidates, 9, 1, 0) if conditioned else None,
    )
    monkeypatch.setattr(plans, "get", lambda product: plan)

    def hint(product, population, rank):
        assert population is candidates
        return conditioning.SourceContextHint(
            "TCAAGTCACTG" if rank == 0 else "GCAAGTCACTG", 7, enzyme, action
        )

    monkeypatch.setattr(partitioning, "basal_context_hint", hint)
    admitted = []
    original = conditioning.admit_source_contexts

    def count(**kwargs):
        admitted.append(kwargs["local_source_sequence"])
        return original(**kwargs)

    monkeypatch.setattr(conditioning, "admit_source_contexts", count)
    product = product_request()
    # Local pages 0 and 2 differ in foldback only; page 1 changes basal choice.
    assert plans.context_priority(product, 0, policy).rank_at(0) == 173
    assert plans.context_priority(product, 2, policy).rank_at(0) == 173
    assert plans.context_priority(product, 1, policy).rank_at(0) == 0
    assert admitted == ["TCAAGTCACTG", "GCAAGTCACTG"]


@pytest.mark.parametrize("conditioned", [False, True])
def test_empty_population_does_not_attempt_context_hint(monkeypatch, conditioned):
    policy, _, _ = inputs()
    plans = partitioning.PartitionPlans()
    empty = SimpleNamespace(parts=0)
    monkeypatch.setattr(
        plans,
        "get",
        lambda product: partitioning.ProductParts(
            foldback=SimpleNamespace(parts=4),
            basal=SimpleNamespace(parts=3) if conditioned else empty,
            endpoint=EndpointPopulation(empty, 3, 1, 0) if conditioned else None,
        ),
    )
    monkeypatch.setattr(
        partitioning,
        "basal_context_hint",
        lambda *args: pytest.fail("An empty candidate population has no molecular hint."),
    )
    assert plans.context_priority(product_request(), 0, policy).rank_at(0) == 0


def test_unchanged_product_is_lowered_once_and_changed_requirement_is_lowered(monkeypatch):
    product = product_request()
    calls = []
    original = ProductRequest.construction_source

    def count(self):
        calls.append(self.ends.left.cohesive_end_sequence)
        return original(self)

    monkeypatch.setattr(ProductRequest, "construction_source", count)
    plans = partitioning.PartitionPlans()
    for _ in range(3):
        plans.get(product)
    changed = product.model_dump(mode="json", by_alias=True)
    changed["ends"]["left"]["cohesive_end_sequence"] = "AAAA"
    revised = ProductRequest.model_validate_json(json.dumps(changed))
    plans.get(revised)
    assert calls == [product.ends.left.cohesive_end_sequence, "AAAA"]
