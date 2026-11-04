"""Consolidate exact ordering specifications while retaining every member role."""

import io

from hop_design.export.construction.csv_common import writer
from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.projections.materials import external_material_uses


def render_set_materials(
    members: tuple[tuple[str, MaterializedConstructionRealization], ...],
) -> dict[str, bytes]:
    specifications = io.StringIO(newline="")
    uses = io.StringIO(newline="")
    table = writer(
        specifications,
        ("material_id", "sequence_5prime", "length_nt", "five_prime_end", "three_prime_end"),
    )
    membership = writer(
        uses,
        (
            "member",
            "materialized_realization_id",
            "material_id",
            "role",
            "specification_resolution",
        ),
    )
    seen = set()
    for name, realization in members:
        for material, use in external_material_uses(realization):
            if material.material_id not in seen:
                seen.add(material.material_id)
                table.writerow(
                    {
                        "material_id": material.material_id,
                        "sequence_5prime": material.sequence_5prime,
                        "length_nt": len(material.sequence_5prime),
                        "five_prime_end": material.five_prime_end.value,
                        "three_prime_end": material.three_prime_end.value,
                    }
                )
            membership.writerow(
                {
                    "member": name,
                    "materialized_realization_id": realization.materialized_realization_id,
                    "material_id": material.material_id,
                    "role": use.role.value,
                    "specification_resolution": use.specification_resolution_mode.value,
                }
            )
    return {
        "oligos.csv": specifications.getvalue().encode(),
        "oligo-uses.csv": uses.getvalue().encode(),
    }
