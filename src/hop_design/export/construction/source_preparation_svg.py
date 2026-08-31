"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/source_preparation_svg.py

Renders exact source-ssDNA preparation facts for construction trajectories.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from hop_design.models.construction.complete import (
    ExactConstructionMaterial,
    SourceDuplexPreparationAuthority,
)

from .svg_common import escape, short_id

_SEQUENCE_CHUNK_SIZE = 48


def _material_rows(
    *,
    role: str,
    label: str,
    material: ExactConstructionMaterial,
    y_start: int,
) -> tuple[str, int]:
    sequence_chunks = tuple(
        material.sequence_5prime[start : start + _SEQUENCE_CHUNK_SIZE]
        for start in range(0, len(material.sequence_5prime), _SEQUENCE_CHUNK_SIZE)
    )
    rows = [
        f'<g data-source-preparation-material-role="{escape(role)}" '
        f'data-material-id="{escape(material.material_id)}" '
        f'data-material-sequence="{escape(material.sequence_5prime)}" '
        f'data-material-five-prime-end="{escape(material.five_prime_end.value)}" '
        f'data-material-three-prime-end="{escape(material.three_prime_end.value)}">'
        f'<text x="122" y="{y_start}" class="body">{escape(label)}</text>'
        f'<text x="390" y="{y_start}" class="small">ends '
        f"{escape(material.five_prime_end.value)}/"
        f"{escape(material.three_prime_end.value)}</text>"
    ]
    for chunk_index, chunk in enumerate(sequence_chunks):
        boundary_prefix = "5-prime " if chunk_index == 0 else ""
        boundary_suffix = " 3-prime" if chunk_index == len(sequence_chunks) - 1 else ""
        rows.append(
            f'<text x="390" y="{y_start + 18 + chunk_index * 18}" class="small" '
            f'style="font-family:monospace" data-layout-row="bounded" '
            f'data-source-material-sequence-chunk-index="{chunk_index}" '
            f'data-source-material-sequence-chunk="{escape(chunk)}">'
            f"{boundary_prefix}{escape(chunk)}{boundary_suffix}</text>"
        )
    rows.append("</g>")
    return "".join(rows), len(sequence_chunks) + 1


def render_source_preparation_rows(
    preparation: SourceDuplexPreparationAuthority,
    *,
    y_start: int,
) -> tuple[str, int]:
    """Render source materials and their exact template-copy relation."""
    rows = [
        f'<g data-source-preparation-id="{escape(preparation.authority_id)}" '
        f'data-source-preparation-pre-state="{escape(preparation.pre_state_id)}" '
        f'data-source-preparation-post-state="{escape(preparation.post_state_id)}">'
        f'<text x="72" y="{y_start}" class="label">Source preparation</text>'
    ]
    cursor = y_start + 30
    materials = (
        ("source_ssdna", "Source ssDNA", preparation.source_ssdna),
        (
            "source_forward_primer",
            "Source-preparation forward primer",
            preparation.forward_primer.oligo,
        ),
        (
            "source_reverse_primer",
            "Source-preparation reverse primer",
            preparation.reverse_primer.oligo,
        ),
    )
    for role, label, material in materials:
        material_rows, row_count = _material_rows(
            role=role,
            label=label,
            material=material,
            y_start=cursor,
        )
        rows.append(material_rows)
        cursor += row_count * 18 + 18
    for binding in preparation.bindings:
        rows.append(
            f'<text x="390" y="{cursor}" class="small" '
            f'style="font-family:monospace" data-layout-row="bounded" '
            f'data-source-preparation-binding-id="{escape(binding.binding_id)}" '
            f'data-primer-id="{escape(binding.primer_id)}" '
            f'data-template-strand-id="{escape(binding.template_strand_id)}" '
            f'data-template-start="{binding.template_span.start.offset}" '
            f'data-template-end="{binding.template_span.end.offset}" '
            f'data-binding-orientation="{escape(binding.orientation.value)}">'
            f"primer {escape(short_id(binding.primer_id))} binds "
            f"{escape(short_id(binding.template_strand_id))} · span "
            f"{binding.template_span.start.offset}-{binding.template_span.end.offset} · "
            f"{escape(binding.orientation.value)}</text>"
        )
        cursor += 18
    rows.append(
        f'<line x1="92" y1="{cursor + 2}" x2="92" y2="{cursor + 42}" class="rule"/>'
        f'<text x="122" y="{cursor + 28}" class="body">'
        "Template copy produces the exact source duplex.</text></g>"
    )
    return "".join(rows), cursor + 62 - y_start


__all__ = ["render_source_preparation_rows"]
