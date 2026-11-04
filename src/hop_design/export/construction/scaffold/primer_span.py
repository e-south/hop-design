"""Locate a verified source-primer span failure without inventing a failed product."""

from html import escape

from hop_design.models.construction.complete.preparation_diagnostics import (
    PreparationConstraintDiagnostic,
)

from .report_primitives import text


def primer_span_drawing(diagnostic: PreparationConstraintDiagnostic, y: int) -> str:
    d = diagnostic
    if d.code != "primer-annealing-span-exceeded" or not (
        isinstance(d.available, int) and isinstance(d.requested, int)
    ):
        raise ValueError("Primer span drawing requires a numeric source-primer span diagnostic.")
    reverse = ".reverse_primer." in d.field
    start, stop = 200.0, 650.0
    available_width = (stop - start) * d.available / d.requested
    boundary = stop - available_width if reverse else start + available_width
    a, b = (boundary, stop) if reverse else (start, boundary)
    stem_a, stem_b = (100, boundary) if reverse else (boundary, 750)
    rows = [
        f'<g id="primer-span-boundary" data-available-nt="{d.available}" '
        f'data-required-nt="{d.requested}" data-field="{escape(d.field)}">',
        text(25, y, "Requested source span · preparation rejected", 16),
        text(25, y + 35, "5\u2032", 15),
        text(790, y + 35, "3\u2032", 15),
        f'<path d="M {stem_a} {y + 30} H {stem_b}" stroke="#8A949C" stroke-width="5"/>',
        f'<path d="M {a} {y + 30} H {b}" stroke="#177CB0" stroke-width="5"/>',
        f'<path d="M {boundary} {y + 15} V {y + 75}" stroke="#23313B" stroke-dasharray="4 3"/>',
        text(25, y + 85, f"Source flank: {d.available} nt available", 14),
        text(
            425,
            y + 85,
            f"{'Reverse' if reverse else 'Forward'} primer: {d.requested} nt required",
            14,
        ),
        f'<path d="M {start} {y + 58} H {stop}" stroke="#B66A25" stroke-width="5"/>',
        text(
            25,
            y + 111,
            "Gray: supplied stem · blue: permitted flank · orange: primer footprint",
            13,
        ),
        "</g>",
    ]
    # Countable requested positions, bounded for long primers.
    if d.requested <= 30:
        for i in range(d.requested + 1):
            x = start + (stop - start) * i / d.requested
            rows.insert(-1, f'<path d="M {x} {y + 52} v 12" stroke="#B66A25"/>')
    return "\n".join(rows)
