"""Evaluate every required exact stem under an explicit aggregate work bound."""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from hop_design.design.runtime import producer_identity
from hop_design.export.construction.molecular.plate import sequence_plates
from hop_design.export.construction.scaffold.report_pdf import render_report_pdf

from ..discovery.explore import discover_scaffolds
from ..discovery.prepare import prepare_scaffold_discovery
from ..edits.drawings import sequence_drawings
from ..options.limits import check_generated_inventory, require_inventory_size
from ..packets.publication import SourceBoundConstructionPacket
from .prepare import prepare_sequence_family
from .records import family_summary


@dataclass(frozen=True, init=False, repr=False)
class SequenceFamilyEvaluation(SourceBoundConstructionPacket):
    _packet_schema: ClassVar[str] = "hop.sequence-family-result-packet/v1"


def execute_sequence_family(path: str | Path) -> SequenceFamilyEvaluation:
    producer = producer_identity()
    prepared = prepare_sequence_family(path)
    preview = json.loads(prepared.json_bytes)
    records = {}
    with tempfile.TemporaryDirectory(prefix="hop-sequence-family-") as temporary:
        root = Path(temporary)
        prepared.write(root / "intent")
        for member in preview["members"]:
            request = root / "intent" / member["request"]
            local = prepare_scaffold_discovery(request)
            outcome = (
                local
                if json.loads(local.json_bytes)["status"] != "ready"
                else discover_scaffolds(request)
            )
            outcome.write(root / "members" / member["name"])
            records[member["name"]] = json.loads(outcome.json_bytes)
            check_generated_inventory(root)
        summary = family_summary(preview, records, producer)
        views, pages = sequence_drawings(root, summary)
        files = {
            p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()
        }
        files.update(views)
        if pages:
            plates = sequence_plates(pages)
            files.update({f"plates/sequence-{i + 1}.svg": page for i, page in enumerate(plates)})
            files["report.pdf"] = render_report_pdf(plates)
    if producer_identity() != producer:
        raise ValueError("HOP producer changed during sequence-family discovery.")
    require_inventory_size(len(files), sum(map(len, files.values())))
    report = (
        "# Exact sequence family outcomes\n\n"
        + "\n".join(
            f"- {m['name']}: {len(m['option_labels'])} complete options; {m['report']}"
            for m in summary["members"]
        )
        + "\n\nSelect one complete option for every required member to verify shared flanks "
        "and material roles. Missing members do not establish global impossibility. "
        "No pooled-library guarantee.\n"
    )
    packet = SequenceFamilyEvaluation._create(files, summary, report)
    object.__setattr__(packet, "_roots", prepared._roots)
    return packet
