"""Preview, persist and execute explicit context revisions through ordinary discovery."""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.publication import ProtectedRoot, publish_directory_create_only
from hop_design.models.construction.intents.revision import DesignPermissionRevision
from hop_design.models.construction.search import FoldbackGeometryDomain
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..overhead import iter_foldback_geometries
from ..packets.capture import capture_packet
from .base import DesignChoices
from .context import load_intent_context
from .resolve import ResolvedDesignRequest, resolve_design_request
from .revision_changes import revise_context


@dataclass(frozen=True, init=False, repr=False)
class DesignRevisionPreview(ResolvedDesignRequest):
    """A replayable permission diff; execution is a separate explicit operation."""

    _packet_schema: ClassVar[str] = "hop.design-revision-preview-packet/v1"

    def execute(
        self,
        destination: str | Path,
        *,
        max_evaluations: int = 64,
        effort: dict[str, Any] | None = None,
        first_choices: int | None = None,
        objective: dict[str, Any] | None = None,
    ) -> DesignChoices:
        from .execute import discover_designs, load_design_choices

        summary = json.loads(self.json_bytes)
        if summary["status"] != "ready":
            raise ValueError("Resolve the permission revision conflicts before execution.")
        output = Path(destination).absolute()
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing discovery: {output}")
        for root in self._roots:
            root.require_unchanged()
            if output.resolve(strict=False).is_relative_to(root.canonical_path):
                raise ValueError("Write the revised discovery outside protected input roots.")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=f".{output.name}-revision-", dir=output.parent
        ) as temporary:
            staging = Path(temporary)
            staging.rmdir()  # Discovery atomically creates this private, empty staging path.
            discover_designs(
                summary["request"],
                staging,
                max_evaluations=max_evaluations,
                effort=effort,
                first_choices=first_choices,
                objective=objective,
            )
            self.write(staging / "revision")
            for root in self._roots:
                root.require_unchanged()
            publish_directory_create_only(staging, output)
        return load_design_choices(output)


def preview_design_revision(
    request: str | Path | dict[str, Any],
    revision: str | Path | dict[str, Any],
) -> DesignRevisionPreview:
    """Revise context permissions while preserving every authored intent field."""
    intent, context, _, roots = load_intent_context(request)
    mapping = load_source_mapping(revision) if isinstance(revision, (str, Path)) else revision
    if isinstance(revision, (str, Path)):
        roots += (ProtectedRoot.capture(revision),)
    spec = DesignPermissionRevision.model_validate_json(canonical_json_bytes(mapping))
    original = intent.model_dump(mode="json", by_alias=True)
    original["context"] = context.model_dump(mode="json", by_alias=True)
    revised_context, changes, conflicts = revise_context(original["context"], spec)
    revised = {**original, "context": revised_context}
    resolved = None
    if not conflicts:
        try:
            resolved = json.loads(resolve_design_request(revised).json_bytes)
            foldback = resolved["effective_request"]["foldback"]
            maximum = revised_context["foldback"]["max_retained_overhead_nt"]
            geometry = FoldbackGeometryDomain.model_validate_json(
                canonical_json_bytes(foldback["geometry"])
            )
            if next(iter_foldback_geometries(geometry, maximum=maximum), None) is None:
                conflicts.append(
                    {
                        "field": "foldback.max_retained_overhead_nt",
                        "message": (
                            f"No permitted foldback geometry fits the {maximum}-nt "
                            "retained-construction limit. Revise the geometry or "
                            "retained_limits_nt.foldback explicitly."
                        ),
                    }
                )
        except ValueError as error:
            conflicts.append({"field": "effective_request", "message": str(error)})
    summary = {
        "schema": "hop.design-revision-preview/v1",
        "status": "conflicting_requirements" if conflicts else "ready",
        "parent_digest": sha256_digest(canonical_json_bytes(original)),
        "revision_digest": sha256_digest(canonical_json_bytes(spec)),
        "request": revised,
        "changes": changes,
        "conflicts": conflicts,
        "effective_request": None if resolved is None else resolved["effective_request"],
        "preserved": [
            "stem_arm",
            "product",
            "ends",
            "scaffold",
            "loop_words",
            "methods",
            "end_placements",
            "material_policies",
            "whole_route_requirements",
        ],
        "scope": "permission_revision_preview_not_molecular_feasibility",
    }
    report = "# Revised construction permissions\n\n"
    report += "Review the changes, then explicitly evaluate the revised request.\n\n"

    def display(change: dict[str, Any], side: str) -> str:
        value = change[side]
        if change["path"] == "enzyme_catalog.enzymes":
            return ", ".join(e["canonical_name"] for e in value)
        return json.dumps(value)

    report += "\n".join(
        f"- {c['label']}: {display(c, 'before')} → {display(c, 'after')}" for c in changes
    )
    if conflicts:
        report += "\n\nResolve these conflicts:\n\n" + "\n".join(
            f"- {c['field']}: {c['message']}" for c in conflicts
        )
    packet = DesignRevisionPreview._create(
        {
            "parent.json": canonical_json_bytes(original),
            "revision.json": canonical_json_bytes(spec),
            "request.json": canonical_json_bytes(revised),
        },
        summary,
        report + "\n",
    )
    object.__setattr__(packet, "_roots", roots)
    return packet


def load_design_revision(path: str | Path) -> DesignRevisionPreview:
    """Replay a saved diff against captured intent and permissions, after relocation too."""
    root, files = capture_packet(path, schema=DesignRevisionPreview._packet_schema)
    expected = preview_design_revision(
        json.loads(files["parent.json"]), json.loads(files["revision.json"])
    )
    if dict(expected._files) != files:
        raise ValueError("Saved design revision disagrees with its parent and explicit changes.")
    object.__setattr__(expected, "_roots", (root,))
    return expected
