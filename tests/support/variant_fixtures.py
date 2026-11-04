"""
--------------------------------------------------------------------------------
HOP Design
tests/support/variant_fixtures.py

Provide one read-only molecular option packet and admitted pool for variant tests.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

import json
from pathlib import Path

import pytest

from hop_design import construction


@pytest.fixture(scope="session")
def _loop_option_path(tmp_path_factory):
    root = tmp_path_factory.mktemp("conditional-variants")
    intent = construction.author_molecular_edit(
        Path("examples/molecular-editing/request.json"), loop_sequences=("GAAA", "TTTC")
    ).write(root / "intent")
    return construction.execute_molecular_edit(intent / "edit.json").write(root / "options")


@pytest.fixture
def loop_options(_loop_option_path):
    """Give each test its own summary; mutations must copy the shared file packet."""
    return _loop_option_path, json.loads((_loop_option_path / "summary.json").read_bytes())


@pytest.fixture(scope="session")
def loop_pool(_loop_option_path):
    """Share immutable admission only for query and projection tests."""
    return construction.load_scaffold_exploration(_loop_option_path)
