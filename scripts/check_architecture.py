#!/usr/bin/env python3
"""Enforce HOP package dependency direction."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "src" / "hop_design"

PUBLIC_FACADE_MODULES = {"api", "discovery", "methods", "views"}
FORBIDDEN_BY_LAYER = {
    "models": PUBLIC_FACADE_MODULES | {"catalog", "cli", "design", "export", "kernel"},
    "kernel": PUBLIC_FACADE_MODULES | {"catalog", "cli", "design", "export"},
    "catalog": PUBLIC_FACADE_MODULES | {"cli", "design", "export"},
    "export": PUBLIC_FACADE_MODULES | {"catalog", "cli", "design"},
    "design": PUBLIC_FACADE_MODULES | {"cli"},
    "api": {"cli"},
    "cli": set(),
}
ROOT_MODULE_LAYERS = {
    "api.py": "api",
    "cli.py": "cli",
    "discovery.py": "api",
    "methods.py": "api",
    "views.py": "api",
}
EXEMPT_ROOT_MODULES = {"__init__.py", "_facade.py", "serialization.py"}
KNOWN_FIRST_PARTY_TARGETS = set(FORBIDDEN_BY_LAYER) | PUBLIC_FACADE_MODULES | {"serialization"}


def _public_facade_manifest(source: str) -> tuple[str, ...]:
    tree = ast.parse(source, filename="_facade.py")
    assignments = (
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "PUBLIC_FACADE_NAMES"
            for target in node.targets
        )
    )
    assignment = next(assignments, None)
    if assignment is None:
        raise ValueError("PUBLIC_FACADE_NAMES assignment is missing")
    value = ast.literal_eval(assignment.value)
    if not isinstance(value, tuple) or not all(isinstance(name, str) for name in value):
        raise ValueError("PUBLIC_FACADE_NAMES must be a literal tuple of strings")
    return value


def public_facade_violations(root_source: str, manifest_source: str) -> list[str]:
    """Return mismatches between explicit root re-exports and the facade manifest."""
    try:
        manifest = _public_facade_manifest(manifest_source)
    except (SyntaxError, ValueError) as exc:
        return [f"invalid public facade manifest: {exc}"]

    errors: list[str] = []
    if len(manifest) != len(set(manifest)):
        errors.append("public facade manifest contains duplicate names")
    tree = ast.parse(root_source, filename="__init__.py")
    imported_names = {
        alias.asname or alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("hop_design")
        for alias in node.names
        if not (alias.asname or alias.name).startswith("_")
    }
    manifest_names = set(manifest)
    for name in sorted(imported_names - manifest_names):
        errors.append(f"root facade imports public name omitted from manifest: {name}")
    missing_imports = manifest_names - imported_names
    if missing_imports:
        errors.append(
            "public facade manifest names missing root import: "
            + ", ".join(sorted(missing_imports))
        )
    return errors


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
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Name):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Name)
                and target.id[:1].isupper()
                and node.value.id[:1].isupper()
                and target.id != node.value.id
            ):
                errors.append(
                    f"{relative}:{node.lineno}: explicit semantic type alias "
                    f"{target.id!r} -> {node.value.id!r} is forbidden"
                )
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
    errors.extend(
        public_facade_violations(
            (PACKAGE_ROOT / "__init__.py").read_text(encoding="utf-8"),
            (PACKAGE_ROOT / "_facade.py").read_text(encoding="utf-8"),
        )
    )

    if errors:
        print("Architecture invariant failures:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Architecture invariants: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
