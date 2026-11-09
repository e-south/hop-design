#!/usr/bin/env python3
"""Check readable documentation, local links, code fences, and skill metadata."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_ROOTS = [
    REPO_ROOT / "ARCHITECTURE.md",
    REPO_ROOT / "DESIGN.md",
    REPO_ROOT / "RELIABILITY.md",
    REPO_ROOT / "SECURITY.md",
]
SKILL_REQUIRED_KEYS = {"name", "description", "metadata"}
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
INLINE_ROUTE_PATTERN = re.compile(
    r"`((?:(?:docs|\.agents)/[^`\s]+|"
    r"(?:AGENTS|ARCHITECTURE|CONTRIBUTING|DESIGN|README|RELIABILITY|SECURITY)\.md)"
    r"(?:#[^`\s]+)?)`"
)


def frontmatter(path: Path) -> tuple[dict[str, object], str]:
    """Read one complete Markdown YAML frontmatter block."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing opening frontmatter delimiter")
    try:
        closing = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing frontmatter delimiter") from exc
    parsed = yaml.safe_load("\n".join(lines[1:closing]))
    if not isinstance(parsed, dict) or not all(isinstance(key, str) for key in parsed):
        raise ValueError("frontmatter must be a YAML mapping with string keys")
    return parsed, text


def heading_anchors(text: str) -> set[str]:
    """Return the GitHub-style anchors for Markdown ATX headings."""
    text = re.sub(r"^```.*?^```[ \t]*$", "", text, flags=re.MULTILINE | re.DOTALL)
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for raw in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", text, flags=re.MULTILINE):
        plain = re.sub(r"[`*_~]", "", raw).strip().lower()
        anchor = re.sub(r"[^\w\- ]", "", plain, flags=re.UNICODE).replace(" ", "-")
        suffix = counts.get(anchor, 0)
        counts[anchor] = suffix + 1
        anchors.add(anchor if suffix == 0 else f"{anchor}-{suffix}")
    return anchors


def check_markdown_links(path: Path, text: str) -> list[str]:
    """Return broken local Markdown links."""
    errors: list[str] = []
    for raw_target in LINK_PATTERN.findall(text):
        target_with_fragment = raw_target.strip().strip("<>")
        for prefix in (
            "https://github.com/e-south/hop-design/blob/main/",
            "https://raw.githubusercontent.com/e-south/hop-design/main/",
        ):
            if target_with_fragment.startswith(prefix):
                target_with_fragment = target_with_fragment.removeprefix(prefix)
                base = REPO_ROOT
                break
        else:
            if "://" in target_with_fragment or target_with_fragment.startswith("mailto:"):
                continue
            base = path.parent
        target, _, fragment = target_with_fragment.partition("#")
        resolved = path if not target else (base / target).resolve()
        if not resolved.exists():
            errors.append(f"{path.relative_to(REPO_ROOT)}: broken link {raw_target!r}")
        elif (
            fragment
            and resolved.is_file()
            and fragment not in heading_anchors(resolved.read_text(encoding="utf-8"))
        ):
            errors.append(f"{path.relative_to(REPO_ROOT)}: broken heading fragment {raw_target!r}")
    return errors


def check_inline_route_targets(path: Path, text: str) -> list[str]:
    """Return broken repository-relative paths written as inline-code routes."""
    errors: list[str] = []
    for raw_target in INLINE_ROUTE_PATTERN.findall(text):
        target, _, fragment = raw_target.partition("#")
        resolved = (REPO_ROOT / target).resolve()
        if not resolved.exists():
            errors.append(f"{path.relative_to(REPO_ROOT)}: broken inline route {raw_target!r}")
        elif (
            fragment
            and resolved.is_file()
            and fragment not in heading_anchors(resolved.read_text(encoding="utf-8"))
        ):
            errors.append(
                f"{path.relative_to(REPO_ROOT)}: broken inline route fragment {raw_target!r}"
            )
    return errors


def check_skill_metadata(path: Path, metadata: dict[str, object]) -> list[str]:
    """Validate the structured metadata block for one repository skill."""
    errors: list[str] = []
    relative = path.relative_to(REPO_ROOT)
    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{relative}: description must be a non-empty string")
    elif len(description) > 220:
        errors.append(f"{relative}: description exceeds 220 characters")
    block = metadata.get("metadata")
    if not isinstance(block, dict):
        errors.append(f"{relative}: metadata must be a YAML mapping")
        return errors
    for key in ("version", "category"):
        value = block.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{relative}: metadata.{key} must be a nonempty string")
    tags = block.get("tags")
    if (
        not isinstance(tags, list)
        or not tags
        or not all(isinstance(item, str) and item.strip() for item in tags)
    ):
        errors.append(f"{relative}: metadata.tags must be a nonempty string list")
    return errors


def check_document_page(path: Path, text: str) -> list[str]:
    """Keep reader pages title-first and their fenced examples balanced."""
    relative = path.relative_to(REPO_ROOT)
    errors: list[str] = []
    if not re.match(r"^# [^\n]+(?:\n|$)", text):
        errors.append(f"{relative}: begin with a page title, not metadata")
    if text.count("```") % 2:
        errors.append(f"{relative}: unbalanced fenced code blocks")
    return errors


def main() -> int:
    """Run knowledge-integrity and skill-legibility checks."""
    errors: list[str] = []
    docs = DOC_ROOTS + sorted((REPO_ROOT / "docs").rglob("*.md"))
    for path in docs:
        text = path.read_text(encoding="utf-8")
        errors.extend(check_document_page(path, text))
        errors.extend(check_markdown_links(path, text))
        errors.extend(check_inline_route_targets(path, text))

    skill_root = REPO_ROOT / ".agents" / "skills"
    for skill_path in sorted(skill_root.glob("*/SKILL.md")):
        try:
            metadata, text = frontmatter(skill_path)
        except ValueError as exc:
            errors.append(f"{skill_path.relative_to(REPO_ROOT)}: {exc}")
            continue
        missing = sorted(SKILL_REQUIRED_KEYS - metadata.keys())
        if missing:
            errors.append(
                f"{skill_path.relative_to(REPO_ROOT)}: missing skill keys {', '.join(missing)}"
            )
        if metadata.get("name") != skill_path.parent.name:
            errors.append(f"{skill_path.relative_to(REPO_ROOT)}: name must match directory")
        errors.extend(check_skill_metadata(skill_path, metadata))
        for required_reference in ("external-sources.md", "test-matrix.md"):
            if not (skill_path.parent / "references" / required_reference).is_file():
                errors.append(
                    f"{skill_path.relative_to(REPO_ROOT)}: missing references/{required_reference}"
                )
        if text.count("```") % 2:
            errors.append(f"{skill_path.relative_to(REPO_ROOT)}: unbalanced fenced code blocks")
        errors.extend(check_markdown_links(skill_path, text))
        errors.extend(check_inline_route_targets(skill_path, text))

    for reference_path in sorted(skill_root.glob("*/references/*.md")):
        text = reference_path.read_text(encoding="utf-8")
        if text.count("```") % 2:
            errors.append(f"{reference_path.relative_to(REPO_ROOT)}: unbalanced fenced code blocks")
        errors.extend(check_markdown_links(reference_path, text))
        errors.extend(check_inline_route_targets(reference_path, text))

    for root_markdown in (REPO_ROOT / "README.md", REPO_ROOT / "AGENTS.md"):
        text = root_markdown.read_text(encoding="utf-8")
        errors.extend(check_markdown_links(root_markdown, text))
        errors.extend(check_inline_route_targets(root_markdown, text))

    if errors:
        print("Documentation integrity failures:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Documentation integrity: ok ({len(docs)} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
