#!/usr/bin/env python3
"""Check documentation frontmatter, links, fences, freshness, and skills."""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_ROOTS = [
    REPO_ROOT / "ARCHITECTURE.md",
    REPO_ROOT / "DESIGN.md",
    REPO_ROOT / "RELIABILITY.md",
    REPO_ROOT / "SECURITY.md",
]
DOC_REQUIRED_KEYS = {
    "doc_id",
    "title",
    "intent",
    "audience",
    "owner",
    "status",
    "last_verified",
    "doc_type",
}
DOC_TYPES = {"tutorial", "how-to", "reference", "explanation", "decision", "index"}
DOC_STATUSES = {"active", "accepted"}
JOURNEYS = {"install", "compile", "discover", "method", "verify", "integrate", "maintain"}
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
        if "://" in target_with_fragment or target_with_fragment.startswith("mailto:"):
            continue
        target, _, fragment = target_with_fragment.partition("#")
        resolved = path if not target else (path.parent / target).resolve()
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
    block = metadata.get("metadata")
    relative = path.relative_to(REPO_ROOT)
    if not isinstance(block, dict):
        return [f"{relative}: metadata must be a YAML mapping"]
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


def main() -> int:
    """Run knowledge-integrity and skill-legibility checks."""
    errors: list[str] = []
    doc_ids: dict[str, Path] = {}
    amendment_refs: list[tuple[Path, str]] = []
    docs = DOC_ROOTS + sorted((REPO_ROOT / "docs").rglob("*.md"))
    oldest_allowed = date.today() - timedelta(days=180)

    for path in docs:
        try:
            metadata, text = frontmatter(path)
        except ValueError as exc:
            errors.append(f"{path.relative_to(REPO_ROOT)}: {exc}")
            continue
        missing = sorted(DOC_REQUIRED_KEYS - metadata.keys())
        if missing:
            errors.append(
                f"{path.relative_to(REPO_ROOT)}: missing frontmatter keys {', '.join(missing)}"
            )
        for scalar_key in ("doc_id", "title", "intent", "owner"):
            value = metadata.get(scalar_key)
            if not isinstance(value, str) or not value.strip():
                errors.append(
                    f"{path.relative_to(REPO_ROOT)}: {scalar_key} must be a nonempty string"
                )
        audience = metadata.get("audience")
        if (
            not isinstance(audience, list)
            or not audience
            or not all(isinstance(item, str) and item.strip() for item in audience)
        ):
            errors.append(f"{path.relative_to(REPO_ROOT)}: audience must be a nonempty string list")
        status = metadata.get("status")
        if status not in DOC_STATUSES:
            errors.append(f"{path.relative_to(REPO_ROOT)}: invalid status {status!r}")
        doc_type = metadata.get("doc_type")
        if doc_type not in DOC_TYPES:
            errors.append(f"{path.relative_to(REPO_ROOT)}: invalid doc_type {doc_type!r}")
        journey = metadata.get("journey")
        if journey is not None and (
            not isinstance(journey, list)
            or not journey
            or not all(isinstance(item, str) and item in JOURNEYS for item in journey)
        ):
            errors.append(f"{path.relative_to(REPO_ROOT)}: invalid journey list")
        doc_id = metadata.get("doc_id")
        if isinstance(doc_id, str) and doc_id:
            if doc_id in doc_ids:
                errors.append(
                    f"{path.relative_to(REPO_ROOT)}: duplicate doc_id {doc_id!r} also in "
                    f"{doc_ids[doc_id].relative_to(REPO_ROOT)}"
                )
            doc_ids[doc_id] = path
        amended_by = metadata.get("amended_by")
        if amended_by is not None:
            if not isinstance(amended_by, str) or not amended_by.strip():
                errors.append(
                    f"{path.relative_to(REPO_ROOT)}: amended_by must be one nonempty doc_id"
                )
            else:
                amendment_refs.append((path, amended_by))
        verified = metadata.get("last_verified")
        if isinstance(verified, date):
            verified_date = verified
        elif isinstance(verified, str):
            try:
                verified_date = date.fromisoformat(verified)
            except ValueError:
                verified_date = None
        else:
            verified_date = None
        if verified_date is None:
            errors.append(f"{path.relative_to(REPO_ROOT)}: invalid last_verified date")
        else:
            if verified_date > date.today():
                errors.append(f"{path.relative_to(REPO_ROOT)}: last_verified is in the future")
            if verified_date < oldest_allowed:
                errors.append(
                    f"{path.relative_to(REPO_ROOT)}: last_verified is older than 180 days"
                )
        if text.count("```") % 2:
            errors.append(f"{path.relative_to(REPO_ROOT)}: unbalanced fenced code blocks")
        errors.extend(check_markdown_links(path, text))

    for path, amended_by in amendment_refs:
        if amended_by not in doc_ids:
            errors.append(
                f"{path.relative_to(REPO_ROOT)}: amended_by target {amended_by!r} does not exist"
            )

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

    for root_markdown in (REPO_ROOT / "README.md", REPO_ROOT / "AGENTS.md"):
        text = root_markdown.read_text(encoding="utf-8")
        errors.extend(check_markdown_links(root_markdown, text))
        errors.extend(check_inline_route_targets(root_markdown, text))

    if errors:
        print("Documentation integrity failures:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Documentation integrity: ok ({len(docs)} docs, {len(doc_ids)} unique IDs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
