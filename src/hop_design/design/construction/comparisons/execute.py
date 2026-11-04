"""Execute a comparison brief using the existing bounded molecular discovery path."""

import tempfile
from pathlib import Path

from hop_design.export.publication import ProtectedRoot
from hop_design.serialization import canonical_json_bytes

from ..discovery.explore import discover_scaffolds
from ..packets.capture import write_snapshot
from .assess import ScaffoldComparison, assess_scaffold_comparison
from .discovery_request import comparison_discovery
from .prepare import load_brief, preview_brief
from .references import capture_references
from .relationships import group_declarations


def execute_scaffold_comparison(path: str | Path) -> ScaffoldComparison:
    protected = ProtectedRoot.capture(path)
    brief = load_brief(path)
    brief, references, reference_files, roots = capture_references(brief, Path(path).parent)
    preview, files = preview_brief(brief, references)
    if preview["conflicts"]:
        summary = {
            "schema": "hop.scaffold-comparison-result/v1",
            "execution": "not_started",
            "status": "conflicting_requirements",
            "request_digest": preview["request_digest"],
            "purpose": brief.purpose,
            **group_declarations(brief),
            "comparison_stage": brief.discovery.comparison_stage,
            "endpoint": brief.discovery.product.endpoint.value,
            "members": [
                {**m.model_dump(mode="json"), "status": "not_evaluated", "option_labels": []}
                for m in brief.required_members
            ],
            "conflicts": preview["conflicts"],
            "sets": [],
            "selected_set": None,
        }
        # Preview artifacts are explicitly separate from an executed discovery.
        files = {f"preview/{name}": content for name, content in files.items()}
        files["request.json"] = canonical_json_bytes(brief)
        files.update(reference_files)
        report = (
            "# Comparison not executed\n\nConflicting declarations require an explicit edit.\n\n"
        )
        report += (
            "\n".join(f"{c['requested_field']}: {c['explicit_edit']}" for c in preview["conflicts"])
            + "\n"
        )
        packet = ScaffoldComparison._create(files, summary, report)
    else:
        with tempfile.TemporaryDirectory(prefix="hop-comparison-execution-") as folder:
            root = Path(folder)
            request = root / "discovery.json"
            request.write_bytes(canonical_json_bytes(comparison_discovery(brief, references)))
            discovery = discover_scaffolds(request).write(root / "discovery")
            # Assess the authored immutable brief captured before execution.
            captured = root / "brief.json"
            write_snapshot(reference_files, root)
            captured.write_bytes(canonical_json_bytes(brief))
            packet = assess_scaffold_comparison(captured, discovery)
    object.__setattr__(packet, "_roots", (protected, *roots))
    return packet
