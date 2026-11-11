"""Bound admitted local reuse by bytes and entries, with independent cold admission."""

from collections import Counter
from types import SimpleNamespace

import pytest

from hop_design.design.construction.surveys.admission import locals as module
from hop_design.design.construction.surveys.execute import load_request
from hop_design.design.runtime import producer_identity
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.serialization import canonical_json_bytes, sha256_digest
from tests.support.context_completion import LIMITS, request
from tests.unit.test_survey_completion_binding import product


@pytest.fixture
def local_cache(monkeypatch, tmp_path):
    saved, reads, admissions = {}, Counter(), []
    survey = load_request(request(tmp_path, "local-cache", completion=True))

    def cached(key):
        reads[key] += 1
        return saved.get(key)

    def store(key, content):
        saved[key] = content

    def packet(local):
        return SimpleNamespace(
            family="basal",
            json_bytes=canonical_json_bytes(
                {
                    "discovery": {"request": local.model_dump(mode="json", by_alias=True)},
                }
            ),
        )

    def admit(data):
        admissions.append(data)
        return SimpleNamespace(family="basal", json_bytes=canonical_json_bytes(data))

    monkeypatch.setattr(module, "_discover_request", packet)
    monkeypatch.setattr(module, "_verify_result_mapping", admit)
    index = SimpleNamespace(
        request=survey, cached=cached, cache=store, creator_producer=producer_identity()
    )

    def owner():
        return module.LocalReceipts(index, SurveyEvaluationLimits(**LIMITS))

    base = product().construction_source().basal
    requests = [base.model_copy(update={"name": f"local-{i:02d}"}) for i in range(20)]

    def key(local):
        return sha256_digest(canonical_json_bytes(local))

    return owner, requests, saved, reads, admissions, packet, key


def test_small_repeated_roster_is_admitted_once_per_invocation(local_cache):
    owner, requests, _, reads, admissions, _, key = local_cache
    current = owner()
    for local in (*requests, *requests):
        assert current.get(local).family == "basal"
    assert all(reads[key(local)] == 1 for local in requests)
    assert not admissions
    reopened = owner()
    reopened.get(requests[0])
    assert len(admissions) == 1 and reads[key(requests[0])] == 2


def test_byte_pressure_evicts_then_independently_admits_saved_bytes(monkeypatch, local_cache):
    owner, requests, _, reads, admissions, packet, key = local_cache
    limit = len(packet(requests[0]).json_bytes) + 10
    monkeypatch.setattr(module, "_LOCAL_CACHE_BYTES", limit, raising=False)
    current = owner()
    for local in (requests[0], requests[1], requests[0]):
        current.get(local)
    assert reads[key(requests[0])] == 2 and len(admissions) == 1


def test_entry_pressure_recomputes_without_changing_the_receipt(monkeypatch, local_cache):
    owner, requests, _, reads, admissions, _, key = local_cache
    monkeypatch.setattr(module, "_LOCAL_CACHE_ENTRIES", 2, raising=False)
    current = owner()
    original = current.get(requests[0])
    current.get(requests[1])
    current.get(requests[2])
    assert current.get(requests[0]).json_bytes == original.json_bytes
    assert reads[key(requests[0])] == 2 and len(admissions) == 1


def test_oversized_receipt_is_returned_but_not_retained(monkeypatch, local_cache):
    owner, requests, _, reads, admissions, _, key = local_cache
    monkeypatch.setattr(module, "_LOCAL_CACHE_BYTES", 1, raising=False)
    current = owner()
    original = current.get(requests[0])
    assert current.get(requests[0]).json_bytes == original.json_bytes
    assert reads[key(requests[0])] == 2 and len(admissions) == 1


def test_wrong_embedded_request_never_enters_the_warm_cache(local_cache):
    owner, requests, saved, _, admissions, packet, key = local_cache
    saved[key(requests[0])] = packet(requests[1]).json_bytes
    current = owner()
    for _ in range(2):
        with pytest.raises(ValueError, match="complete dependency key"):
            current.get(requests[0])
    assert len(admissions) == 2
    saved[key(requests[0])] = packet(requests[0]).json_bytes
    assert current.get(requests[0]).json_bytes == saved[key(requests[0])]
