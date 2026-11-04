"""Compact, lossless display of the molecular descriptors behind saved map coordinates."""

from typing import Any

from hop_design.models.construction.variants.parameters import parameter_definition
from hop_design.models.construction.variants.similarity import (
    MolecularComparisonBasis,
    MolecularDescriptor,
)

_FEATURE_NAMES = {
    "basal_pairs": "Basal contacts",
    "foldback_pairs": "Foldback contacts",
    "loop": "Loop",
    "five_prime_retained_tail": "5\u2032 tail contribution",
    "three_prime_retained_tail": "3\u2032 tail contribution",
    "five_prime_retained_tail_nt": "Retained 5\u2032 tail",
    "three_prime_retained_tail_nt": "Retained 3\u2032 tail",
}

# These are links to the existing molecular spans, not additional design controls.
_PARAMETERS = {
    "loop_side_paired_bp": ["foldback_arm_bp"],
    "loop": ["loop_word", "loop_nt"],
    "basal_pairs": ["open_side_paired_positions", "noncanonical_pairs"],
    "foldback_pairs": ["foldback_arm_bp"],
    "left_word": ["left_end_word"],
    "right_word": ["right_end_word"],
    "left_polarity": ["left_end_polarity"],
    "right_polarity": ["right_end_polarity"],
    "five_prime_retained_tail_nt": ["five_prime_unpaired_nt"],
    "three_prime_retained_tail_nt": ["three_prime_unpaired_nt"],
    "five_prime_retained_tail": ["five_prime_unpaired_nt"],
    "three_prime_retained_tail": ["three_prime_unpaired_nt"],
}


def comparison_features(
    rows: tuple[MolecularDescriptor, ...],
    basis: MolecularComparisonBasis,
    members: tuple[str, ...],
) -> dict[str, Any]:
    """Dictionary columns follow map membership; fixed values stay explicit.

    Project once with the admitted map. Pointer movement only decodes one member,
    so it neither parses the full landscape again nor adds another network request.
    """
    indexed = {row.identity: row for row in rows}
    if len(indexed) != len(members) or set(indexed) != set(members):
        raise ValueError("Comparison features disagree with map membership.")
    ordered = [indexed[identity] for identity in members]
    columns = []
    # Codes label contacts, so an API query order must not change the displayed x.
    # Both browser and publication projections use this cohort-wide dictionary.
    contacts = sorted(
        {
            contact
            for row in ordered
            for key in ("basal_pairs", "foldback_pairs")
            for contact in row.compared_sequences[key]
        }
    )
    contact_index = {contact: index for index, contact in enumerate(contacts)}
    for block, active in (
        ("shape", basis.shape_scales),
        ("sequences", basis.sequence_keys),
        ("interfaces", basis.interface_keys),
    ):
        values = [
            getattr(
                row,
                {"shape": "compared_shape", "sequences": "compared_sequences"}.get(block, block),
            )
            for row in ordered
        ]
        for key in values[0] or {}:
            dictionary: list[Any] = []
            positions: dict[Any, int] = {}
            indices = []
            for row in values:
                value = row[key]
                if value not in positions:
                    positions[value] = len(dictionary)
                    dictionary.append(value)
                indices.append(positions[value])
            paired = block == "sequences" and key in {"basal_pairs", "foldback_pairs"}
            if paired:
                encoded = []
                for value in dictionary:
                    tokens = []
                    for contact in value:
                        tokens.append(contact_index[contact])
                    encoded.append(tokens)
                dictionary = encoded
            columns.append(
                {
                    "key": f"{block}.{key}",
                    "parameters": _PARAMETERS.get(key, [key]),
                    "label": _FEATURE_NAMES.get(key)
                    or parameter_definition(_PARAMETERS.get(key, [key])[0]).label,
                    "unit": parameter_definition(_PARAMETERS.get(key, [key])[0]).unit
                    if block == "shape"
                    else "",
                    "active": key in active,
                    "dictionary": dictionary,
                    "indices": indices,
                    **({"encoding": "contacts"} if paired else {}),
                }
            )
    return {
        "basis": basis.model_dump(mode="json", exclude={"comparison_keys"}),
        "columns": columns,
        "contacts": contacts,
    }


def selected_comparison_features(
    rows: tuple[MolecularDescriptor, ...], basis: MolecularComparisonBasis, identity: str
) -> dict[str, Any]:
    """Decode one browser-equivalent vector; keep omitted constants in its record."""
    members = tuple(row.identity for row in rows)
    if identity not in members:
        raise ValueError("Selected comparison identity is outside the captured atlas.")
    projected = comparison_features(rows, basis, members)
    index = members.index(identity)
    features = []
    for column in projected["columns"]:
        encoded = column["dictionary"][column["indices"][index]]
        features.append(
            {
                **{key: column[key] for key in ("key", "parameters", "label", "unit", "active")},
                "encoded": encoded,
                "value": [projected["contacts"][code] for code in encoded]
                if column.get("encoding") == "contacts"
                else encoded,
                **({"encoding": column["encoding"]} if "encoding" in column else {}),
            }
        )
    indexed = {feature["key"]: feature for feature in features}
    keys = [
        *[f"shape.{key}" for key in basis.shape_scales],
        *[f"sequences.{key}" for key in basis.sequence_keys],
        *[f"interfaces.{key}" for key in basis.interface_keys],
    ]
    return {
        "schema": "hop.selected-comparison-features/v1",
        "identity": identity,
        "basis": projected["basis"],
        "contacts": projected["contacts"],
        "features": features,
        "vector": [indexed[key] for key in keys],
    }
