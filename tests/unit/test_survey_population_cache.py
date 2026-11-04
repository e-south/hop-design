"""Broad local geometry can reuse admitted populations within bounded memory."""

import json

from hop_design.design.construction.surveys import partitions
from hop_design.models.construction.request import LocalNeighborhoodRequest
from tests.unit.test_interface_survey_compact_foldback import _two_method_product


def _requests(count=12):
    data = (
        _two_method_product().construction_source().foldback.model_dump(mode="json", by_alias=True)
    )
    data["search"]["max_retained_overhead_nt"] = 44
    requests = []
    for length in range(5, 5 + count):
        data["geometry_domain"]["annealing_arm_lengths_bp"] = [length]
        requests.append(LocalNeighborhoodRequest.model_validate_json(json.dumps(data)))
    return requests


def _count_admissions(monkeypatch):
    original = partitions.admit_population
    calls = []

    def counted(request, index):
        calls.append(request)
        return original(request, index)

    monkeypatch.setattr(partitions, "admit_population", counted)
    return calls


def test_geometry_sweep_reuses_populations_only_within_the_admitting_invocation(monkeypatch):
    requests = _requests()
    calls = _count_admissions(monkeypatch)
    plans = partitions.PartitionPlans()
    first = [plans._population(r) for r in requests]
    second = [plans._population(r) for r in requests]
    assert second == first
    assert len(calls) == 12
    another = partitions.PartitionPlans()
    assert [another._population(r) for r in requests] == first
    assert len(calls) == 24


def test_population_count_bound_evicts_least_recently_used_not_recent_hit(monkeypatch):
    monkeypatch.setattr(partitions, "_POPULATION_CACHE_ENTRIES", 2, raising=False)
    requests = _requests(3)
    calls = _count_admissions(monkeypatch)
    plans = partitions.PartitionPlans()
    for i in (0, 1, 0, 2, 0):
        plans._population(requests[i])
    assert len(plans._populations) == 2
    assert len(calls) == 3
    plans._population(requests[1])
    assert len(calls) == 4


def test_oversized_population_is_returned_but_not_retained(monkeypatch):
    monkeypatch.setattr(partitions, "_POPULATION_CACHE_BYTES", 1, raising=False)
    request = _requests(1)[0]
    calls = _count_admissions(monkeypatch)
    plans = partitions.PartitionPlans()
    first = plans._population(request)
    assert not plans._populations
    assert plans._population(request) == first
    assert len(calls) == 2


def test_combined_population_bytes_trigger_eviction(monkeypatch):
    from hop_design.serialization import canonical_json_bytes

    requests = _requests(2)
    uncached = partitions.PartitionPlans()
    sizes = [len(canonical_json_bytes(uncached._population(r).result)) for r in requests]
    monkeypatch.setattr(partitions, "_POPULATION_CACHE_BYTES", max(sizes), raising=False)
    calls = _count_admissions(monkeypatch)
    plans = partitions.PartitionPlans()
    for request in requests:
        plans._population(request)
    assert len(plans._populations) == 1
    plans._population(requests[0])
    assert len(calls) == 3
