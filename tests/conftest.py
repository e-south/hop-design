"""Shared read-only fixtures and explicit producer context for regression artifacts."""

from importlib import import_module
from importlib.metadata import version

import pytest

pytest_plugins = ["tests.support.variant_fixtures"]


@pytest.fixture
def frozen_a8_artifact_producer(monkeypatch):
    """Hold provenance constant only for tests asserting recorded a8 artifact bytes.

    Ordinary tests and installed-artifact gates use the real current version.
    Bumping a distribution must not require replacing historical golden hashes.
    """

    def frozen_version(name):
        return "0.1.0a8" if name == "hop-design" else version(name)

    for module in (
        "hop_design.design.assembly",
        "hop_design.design.construction.foldback.discovery",
        "hop_design.design.construction.basal.discovery",
        "hop_design.design.construction.complete.results",
    ):
        monkeypatch.setattr(import_module(module), "version", frozen_version)
