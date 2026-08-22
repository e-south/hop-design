"""FASTA export."""

from __future__ import annotations

from collections.abc import Sequence

from hop_design.models.plan import HairpinEncodingInsert, SequenceRecord


def render_fasta(record: SequenceRecord | HairpinEncodingInsert, *, line_width: int = 80) -> bytes:
    """Render one sequence record as deterministic UTF-8 FASTA."""
    if line_width < 1:
        raise ValueError("FASTA line width must be positive.")
    symbolic = "true" if record.is_symbolic else "false"
    lines = [f">{record.record_id} symbolic={symbolic}"]
    lines.extend(
        record.sequence[index : index + line_width]
        for index in range(0, len(record.sequence), line_width)
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def render_fasta_records(
    records: Sequence[SequenceRecord | HairpinEncodingInsert], *, line_width: int = 80
) -> bytes:
    """Render a nonempty ordered record set without changing record identity."""
    if not records:
        raise ValueError("Multi-record FASTA requires at least one record.")
    return b"".join(render_fasta(record, line_width=line_width) for record in records)


__all__ = ["render_fasta", "render_fasta_records"]
