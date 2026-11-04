"""Evaluate explicit molecular edits through ordinary bounded discovery and preparation."""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from hop_design.export.construction.molecular.plate import sequence_plates
from hop_design.export.construction.scaffold.report_pdf import render_report_pdf

from ..discovery.explore import discover_scaffolds
from ..options.limits import require_inventory_size
from ..packets.publication import SourceBoundConstructionPacket
from .drawings import sequence_drawings
from .prepare import prepare_molecular_edit
from .results import edit_result_summary


@dataclass(frozen=True, init=False, repr=False)
class MolecularEditEvaluation(SourceBoundConstructionPacket):
    """Complete alternatives, exact sequence views and original edited intention."""

    _packet_schema: ClassVar[str] = "hop.molecular-edit-result-packet/v1"


def execute_molecular_edit(path: str | Path) -> MolecularEditEvaluation:
    prepared = prepare_molecular_edit(path)
    preview = json.loads(prepared.json_bytes)
    if preview["status"] != "ready":
        raise ValueError(prepared.report_text)
    with tempfile.TemporaryDirectory(prefix="hop-molecular-edit-") as temporary:
        root = Path(temporary)
        prepared.write(root / "intent")
        discovery = discover_scaffolds(root / "intent/compiled-request.json")
        discovery.write(root / "options")
        native = json.loads(discovery.json_bytes)
        summary = edit_result_summary(preview, native)
        files = {
            p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()
        }
        drawings, pages = sequence_drawings(root / "options", native)
        files.update(drawings)
        plates = sequence_plates(pages)
        files.update({f"plates/sequence-{i + 1}.svg": page for i, page in enumerate(plates)})
        files["report.pdf"] = render_report_pdf(plates) if plates else files["options/report.pdf"]
    report = (
        "# Edited molecular alternatives\n\n"
        "Whole molecules and exact sequence differences: report.pdf. "
        "The display reference is not a selection or rank.\n\n"
        f"Edit: {preview['edit_digest']}\n\n"
        f"Complete preparations: {len(native['options'])}. "
        "Detailed failures, branches and unexamined coverage: options/report.md.\n\n"
        "Select named options explicitly to retrieve exact preparations "
        "and checked shared controls.\n"
    )
    report += (
        "\n"
        + "\n".join(
            f"- Design {i}: `{o['label']}`; loop {o.get('target_facts', {}).get('loop_sequence')}."
            for i, o in enumerate(native["options"], 1)
        )
        + "\n"
    )
    require_inventory_size(len(files), sum(map(len, files.values())))
    packet = MolecularEditEvaluation._create(files, summary, report)
    object.__setattr__(packet, "_roots", prepared._roots)
    return packet
