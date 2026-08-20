#!/usr/bin/env python3
"""Enforce HOP package dependency direction."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "src" / "hop_design"

FORBIDDEN_BY_LAYER = {
    "models": {"api", "catalog", "cli", "design", "export", "kernel"},
    "kernel": {"api", "catalog", "cli", "design", "export"},
    "catalog": {"api", "cli", "design", "export"},
    "export": {"api", "catalog", "cli", "design"},
    "design": {"api", "cli"},
    "api": {"cli"},
    "cli": set(),
}
ROOT_MODULE_LAYERS = {"api.py": "api", "cli.py": "cli"}
EXEMPT_ROOT_MODULES = {"__init__.py", "serialization.py"}
KNOWN_FIRST_PARTY_TARGETS = set(FORBIDDEN_BY_LAYER) | {"serialization"}


def _source_layer(relative_path: Path) -> tuple[str | None, str | None]:
    if len(relative_path.parts) == 1:
        if relative_path.name in EXEMPT_ROOT_MODULES:
            return None, None
        layer = ROOT_MODULE_LAYERS.get(relative_path.name)
        if layer is None:
            return None, f"unknown first-party root module {relative_path.name!r}"
        return layer, None
    layer = relative_path.parts[0]
    if layer not in FORBIDDEN_BY_LAYER:
        return None, f"unknown first-party layer {layer!r}"
    return layer, None


def _absolute_from_module(relative_path: Path, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    package_parts = ["hop_design", *relative_path.parent.parts]
    ascend = node.level - 1
    if ascend >= len(package_parts):
        return ""
    prefix = package_parts[: len(package_parts) - ascend]
    if node.module:
        prefix.extend(node.module.split("."))
    return ".".join(prefix)


def imported_hop_layer(
    relative_path: Path,
    node: ast.Import | ast.ImportFrom,
) -> set[str]:
    """Return first-party top-level layers imported by one AST node."""
    modules: list[str] = []
    if isinstance(node, ast.Import):
        modules.extend(alias.name for alias in node.names)
    else:
        base_module = _absolute_from_module(relative_path, node)
        modules.append(base_module)
        if base_module == "hop_design":
            modules.extend(f"hop_design.{alias.name}" for alias in node.names)

    layers: set[str] = set()
    for module in modules:
        parts = module.split(".")
        if len(parts) >= 2 and parts[0] == "hop_design":
            layers.add(parts[1])
    return layers


def violations_for_source(relative_path: str | Path, source: str) -> list[str]:
    """Return all dependency violations for one first-party source module."""
    relative = Path(relative_path)
    layer, path_error = _source_layer(relative)
    if path_error is not None:
        return [f"{relative.as_posix()}: {path_error}"]
    if layer is None:
        return []

    tree = ast.parse(source, filename=str(relative))
    errors: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import | ast.ImportFrom):
            continue
        imported = imported_hop_layer(relative, node)
        unknown = imported - KNOWN_FIRST_PARTY_TARGETS
        for target in sorted(unknown):
            errors.append(f"{relative}:{node.lineno}: import targets unknown layer {target!r}")
        forbidden = imported & FORBIDDEN_BY_LAYER[layer]
        for target in sorted(forbidden):
            errors.append(f"{relative}:{node.lineno}: layer {layer!r} must not import {target!r}")
    return errors


def main() -> int:
    """Check every layered package module and report all inversions."""
    errors: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        relative = path.relative_to(PACKAGE_ROOT)
        errors.extend(violations_for_source(relative, path.read_text(encoding="utf-8")))

    if errors:
        print("Architecture invariant failures:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Architecture invariants: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
