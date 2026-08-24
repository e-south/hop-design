from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.check_architecture import public_facade_violations, violations_for_source

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("path", "source"),
    [
        ("models/bad.py", "from hop_design.design import compile_spec"),
        ("models/bad.py", "from ..design import compile_spec"),
        ("models/bad.py", "from hop_design import design"),
        ("models/bad.py", "from .. import design"),
        ("models/bad.py", "from hop_design.discovery import search_basal_candidates"),
        ("design/bad.py", "from hop_design.methods import MethodBundle"),
        ("api.py", "from hop_design.cli import app"),
        ("cli.py", "from hop_design.design import compile_spec"),
        ("cli.py", "from hop_design.models import HopSpec"),
        ("serialization.py", "from hop_design.cli import app"),
        ("serialization.py", "from hop_design.models import HopSpec"),
    ],
)
def test_forbidden_absolute_relative_and_root_imports_fail(path: str, source: str) -> None:
    assert violations_for_source(path, source)


@pytest.mark.parametrize(
    ("path", "source"),
    [
        ("design/good.py", "from hop_design.kernel import bundle_identity"),
        ("cli.py", "from hop_design.api import compile"),
        ("discovery.py", "from hop_design.design.discovery import search_nicking_placements"),
    ],
)
def test_allowed_edges_pass(path: str, source: str) -> None:
    assert violations_for_source(path, source) == []


def test_unknown_top_level_package_fails_closed() -> None:
    assert violations_for_source("new_layer/module.py", "") == [
        "new_layer/module.py: unknown first-party layer 'new_layer'"
    ]


def test_explicit_semantic_type_alias_fails_closed() -> None:
    assert violations_for_source(
        "models/bad.py",
        "BasalPairKind = JunctionPairKind\n",
    ) == [
        "models/bad.py:1: explicit semantic type alias 'BasalPairKind' -> "
        "'JunctionPairKind' is forbidden"
    ]


def test_public_facade_manifest_must_match_root_reexports() -> None:
    root_source = """\
from hop_design._facade import PUBLIC_FACADE_NAMES as _PUBLIC_FACADE_NAMES
from hop_design.api import exported_operation, omitted_operation

__all__ = list(_PUBLIC_FACADE_NAMES)
"""
    manifest_source = """\
PUBLIC_FACADE_NAMES = (
    "exported_operation",
    "missing_operation",
)
"""

    assert public_facade_violations(root_source, manifest_source) == [
        "root facade imports public name omitted from manifest: omitted_operation",
        "public facade manifest names missing root import: missing_operation",
    ]


def test_temporal_method_replay_has_truthful_ownership_and_bounded_modules() -> None:
    architecture = (REPO_ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "Model-adjacent semantic replay" in architecture

    expected_modules = (
        "src/hop_design/models/linear_source_method/__init__.py",
        "src/hop_design/models/linear_source_method/replay.py",
        "src/hop_design/design/linear_source_states/material.py",
        "src/hop_design/design/linear_source_states/product.py",
    )
    assert not (REPO_ROOT / "src/hop_design/design/linear_source_states.py").exists()
    for relative_path in expected_modules:
        path = REPO_ROOT / relative_path
        assert path.is_file(), relative_path
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 300, relative_path
