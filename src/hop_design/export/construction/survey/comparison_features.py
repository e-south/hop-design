"""Compact, lossless display of the molecular descriptors behind saved map coordinates."""

from typing import Any

from hop_design.models.construction.variants.parameters import parameter_definition
from hop_design.models.construction.variants.similarity import (
    MolecularComparisonBasis,
    MolecularDescriptor,
)

from ..presentation.comparison import COMPARISON_GROUPS
from ..presentation.comparison_glyphs import comparison_glyph_presentation

_FEATURE_NAMES = {
    "basal_pairs": "Basal pattern",
    "foldback_pairs": "Loop-side pattern",
    "five_prime_retained_tail": "5\u2032 tail contribution",
    "three_prime_retained_tail": "3\u2032 tail contribution",
    "five_prime_retained_tail_nt": "Retained 5\u2032 tail",
    "three_prime_retained_tail_nt": "Retained 3\u2032 tail",
}
_FEATURE_DEFINITIONS = {
    "open_side_paired_positions": (
        "Folded hairpin: recorded basal contact positions beyond the supplied stem, "
        "including permitted noncanonical contacts. Excludes unpaired terminal tails; it is "
        "not an insert-end spacer."
    ),
    "loop_side_paired_bp": (
        "Folded hairpin: paired extension between the supplied stem and the loop. "
        "On insert release, this region remains internal to the cloning fragment."
    ),
    "loop_nt": (
        "Folded hairpin: number of unpaired bases in the loop. Loop-side pairing measures "
        "the adjoining paired extension separately."
    ),
    "left_gap": (
        "Released insert: paired bases between the left sticky-end boundary and its "
        "supplied-stem-arm boundary. Excludes the sticky-end bases; zero places the end "
        "directly beside the stem."
    ),
    "right_gap": (
        "Released insert: paired bases between the right sticky-end boundary and its "
        "supplied-stem-arm boundary. Excludes the sticky-end bases; zero places the end "
        "directly beside the stem."
    ),
    "basal_pairs": (
        "Folded hairpin: ordered base identities and contact classes in the basal region. "
        "Basal contacts gives the number of these positions."
    ),
    "foldback_pairs": (
        "Folded hairpin: ordered base identities and contact classes in the loop-side "
        "paired extension. Loop-side pairing gives its length."
    ),
    "loop": (
        "Folded hairpin: the loop bases in strand order, read 5\u2032 to 3\u2032. "
        "Loop length gives their count."
    ),
    "left_word": (
        "Released insert: the left sticky-end sequence on its protruding strand, read 5\u2032 to "
        "3\u2032. These bases are separate from the left insert spacer."
    ),
    "right_word": (
        "Released insert: the right sticky-end sequence on its protruding strand, read 5\u2032 "
        "to 3\u2032. These bases are separate from the right insert spacer."
    ),
    "basal_method": ("Preparation: nickase used for basal-side processing."),
    "foldback_method": (
        "Preparation: nickase used for foldback processing at the loop-side region."
    ),
    "release_method": (
        "Preparation: restriction enzyme used to release the duplex cloning insert."
    ),
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


def comparison_field_definition(key: str) -> dict[str, str]:
    """Current reading vocabulary; recorded keys, values and codes stay unchanged."""
    block, name = key.split(".")
    parameter = parameter_definition(_PARAMETERS.get(name, [name])[0])
    return {
        "label": _FEATURE_NAMES.get(name, parameter.label),
        "unit": parameter.unit if block == "shape" else "",
        "definition": _FEATURE_DEFINITIONS.get(name, parameter.measurement),
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
    columns: list[dict[str, Any]] = []
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
            # Stable field codes must not depend on pointer order, filters or
            # the caller's member order. They identify words, not magnitudes.
            dictionary: list[Any] = sorted({row[key] for row in values})
            positions: dict[Any, int] = {value: i for i, value in enumerate(dictionary)}
            indices = []
            for row in values:
                value = row[key]
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
                    **comparison_field_definition(f"{block}.{key}"),
                    "active": key in active,
                    "dictionary": dictionary,
                    "indices": indices,
                    **({"encoding": "contacts"} if paired else {}),
                }
            )
    return {
        "presentation": {
            "groups": {key: dict(value) for key, value in COMPARISON_GROUPS.items()},
            **comparison_glyph_presentation(c["key"] for c in columns if c["active"]),
        },
        "basis": basis.model_dump(mode="json", exclude={"comparison_keys"}),
        "columns": columns,
        "contacts": contacts,
    }


def selected_comparison_features(
    rows: tuple[MolecularDescriptor, ...], basis: MolecularComparisonBasis, identity: str
) -> dict[str, Any]:
    """Decode one browser-equivalent vector; keep omitted constants in its record."""
    members = tuple(row.identity for row in rows)
    return select_projected_features(comparison_features(rows, basis, members), members, identity)


def select_projected_features(
    projected: dict[str, Any], members: tuple[str, ...], identity: str
) -> dict[str, Any]:
    if identity not in members:
        raise ValueError("Selected comparison identity is outside the captured atlas.")
    index = members.index(identity)
    features = []
    for column in projected["columns"]:
        encoded = column["dictionary"][column["indices"][index]]
        features.append(
            {
                **{key: column[key] for key in ("key", "parameters", "label", "unit", "active")},
                **({"definition": column["definition"]} if "definition" in column else {}),
                "encoded": encoded,
                "display_value": encoded
                if column["key"].startswith("shape.")
                else column["indices"][index],
                "value": [projected["contacts"][code] for code in encoded]
                if column.get("encoding") == "contacts"
                else encoded,
                **({"encoding": column["encoding"]} if "encoding" in column else {}),
            }
        )
    indexed = {feature["key"]: feature for feature in features}
    basis = projected["basis"]
    keys = [
        f"{block}.{key}"
        for block, names in (
            ("shape", basis["shape_scales"]),
            ("sequences", basis["sequence_keys"]),
            ("interfaces", basis["interface_keys"]),
            ("processing", basis.get("processing_keys", ())),
        )
        for key in names
    ]
    return {
        "schema": "hop.selected-comparison-features/v1",
        "identity": identity,
        "presentation": projected["presentation"],
        "basis": projected["basis"],
        "contacts": projected["contacts"],
        "features": features,
        "vector": [indexed[key] for key in keys],
    }
