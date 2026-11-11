"""Shared read-only fixtures and explicit producer context for regression artifacts."""

import pytest

from hop_design.design.runtime import replay_creation

pytest_plugins = ["tests.support.variant_fixtures"]


@pytest.fixture
def frozen_a8_artifact_producer(monkeypatch):
    """Hold provenance constant only for tests asserting recorded a8 artifact bytes.

    Ordinary tests and installed-artifact gates use the real current version.
    Bumping a distribution must not require replacing historical golden hashes.
    """

    with replay_creation("0.1.0a8"):
        yield
