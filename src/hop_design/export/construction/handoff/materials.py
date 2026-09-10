"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/export/construction/handoff/materials.py

Exports externally required oligos with contextual roles and terminal chemistry.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import io

from hop_design.export.construction.csv_common import writer
from hop_design.export.fasta import render_fasta_records
from hop_design.models.construction.complete import MaterializedConstructionRealization
from hop_design.models.construction.complete.material import (
    ExactConstructionMaterial,
    MaterialRouteEntry,
    MaterialUse,
)
from hop_design.models.plan import SequenceRecord


def external_oligos(
    realization: MaterializedConstructionRealization,
) -> tuple[tuple[ExactConstructionMaterial, tuple[MaterialUse, ...]], ...]:
    """Group external uses by molecular identity, preserving first-use order."""
    preparation = realization.source_preparation
    entries = (
        (preparation.source_ssdna, preparation.source_ssdna_use),
        (preparation.forward_primer.oligo, preparation.forward_primer_use),
        (preparation.reverse_primer.oligo, preparation.reverse_primer_use),
        *zip(realization.materials, realization.material_uses, strict=True),
    )
    materials: dict[str, ExactConstructionMaterial] = {}
    uses: dict[str, list[MaterialUse]] = {}
    for material, use in entries:
        if use.route_entry is MaterialRouteEntry.REQUIRED_EXTERNAL:
            materials[material.material_id] = material
            uses.setdefault(material.material_id, []).append(use)
    return tuple((material, tuple(uses[key])) for key, material in materials.items())


def render_oligos_csv(realization: MaterializedConstructionRealization) -> bytes:
    """Render one order row per distinct sequence-and-chemistry specification."""
    buffer = io.StringIO(newline="")
    table = writer(
        buffer,
        (
            "name",
            "roles",
            "sequence_5prime",
            "length_nt",
            "five_prime_end",
            "three_prime_end",
            "specification_resolution",
            "material_id",
        ),
    )
    for material, uses in external_oligos(realization):
        table.writerow(
            {
                "name": uses[0].role.value,
                "roles": ";".join(use.role.value for use in uses),
                "sequence_5prime": material.sequence_5prime,
                "length_nt": len(material.sequence_5prime),
                "five_prime_end": material.five_prime_end.value,
                "three_prime_end": material.three_prime_end.value,
                "specification_resolution": ";".join(
                    f"{use.role.value}={use.specification_resolution_mode.value}" for use in uses
                ),
                "material_id": material.material_id,
            }
        )
    return buffer.getvalue().encode("utf-8")


def render_oligos_fasta(realization: MaterializedConstructionRealization) -> bytes:
    """Export external sequences; their required end chemistry remains in the CSV."""
    return render_fasta_records(
        tuple(
            SequenceRecord(record_id=uses[0].role.value, sequence=material.sequence_5prime)
            for material, uses in external_oligos(realization)
        )
    )
