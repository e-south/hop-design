#!/usr/bin/env python3
"""Check documentation frontmatter, links, fences, freshness, and skills."""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

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
}
SKILL_REQUIRED_KEYS = {"name", "description", "metadata"}
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def frontmatter(path: Path) -> tuple[dict[str, str], str]:
    """Read top-level scalar keys from a Markdown YAML frontmatter block."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing opening frontmatter delimiter")
    try:
        closing = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing frontmatter delimiter") from exc
    values: dict[str, str] = {}
    for line in lines[1:closing]:
        match = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip('"')
    return values, text


def check_markdown_links(path: Path, text: str) -> list[str]:
    """Return broken local Markdown links."""
    errors: list[str] = []
    for raw_target in LINK_PATTERN.findall(text):
        target = raw_target.strip().strip("<>").split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            errors.append(f"{path.relative_to(REPO_ROOT)}: broken link {raw_target!r}")
    return errors


def main() -> int:
    """Run knowledge-integrity and skill-legibility checks."""
    errors: list[str] = []
    doc_ids: dict[str, Path] = {}
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
        doc_id = metadata.get("doc_id")
        if doc_id:
            if doc_id in doc_ids:
                errors.append(
                    f"{path.relative_to(REPO_ROOT)}: duplicate doc_id {doc_id!r} also in "
                    f"{doc_ids[doc_id].relative_to(REPO_ROOT)}"
                )
            doc_ids[doc_id] = path
        verified = metadata.get("last_verified")
        if verified:
            try:
                verified_date = date.fromisoformat(verified)
            except ValueError:
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
        for nested_key in ("version", "category", "tags"):
            if not re.search(rf"^  {nested_key}:\s*", text, flags=re.MULTILINE):
                errors.append(
                    f"{skill_path.relative_to(REPO_ROOT)}: metadata.{nested_key} is missing"
                )
        for required_reference in ("external-sources.md", "test-matrix.md"):
            if not (skill_path.parent / "references" / required_reference).is_file():
                errors.append(
                    f"{skill_path.relative_to(REPO_ROOT)}: missing references/{required_reference}"
                )
        if text.count("```") % 2:
            errors.append(f"{skill_path.relative_to(REPO_ROOT)}: unbalanced fenced code blocks")

    for root_markdown in (REPO_ROOT / "README.md", REPO_ROOT / "AGENTS.md"):
        text = root_markdown.read_text(encoding="utf-8")
        errors.extend(check_markdown_links(root_markdown, text))

    if errors:
        print("Documentation integrity failures:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Documentation integrity: ok ({len(docs)} docs, {len(doc_ids)} unique IDs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
