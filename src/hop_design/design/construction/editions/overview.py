"""Admit a captured preparation overview against its actual molecular records."""

from typing import Any, cast

from hop_design.models.construction.variants.overview import PreparationOverview
from hop_design.models.construction.variants.similarity import MolecularDescriptor, ShapeKey
from hop_design.serialization import sha256_digest

from ..navigation.types import ChoiceSource, Record


def validate_overview(
    overview: PreparationOverview, answer: Record, descriptors: dict[str, MolecularDescriptor]
) -> None:
    paths = {p["materialized_realization_id"]: p for p in answer["paths"]}
    if (
        overview.snapshot_digest != answer["snapshot_digest"]
        or set(overview.members) != paths.keys()
    ):
        raise ValueError("Recorded overview snapshot or preparation membership disagrees.")
    labels = {
        axis["key"]: {node["value"]: node["label"] for node in axis.get("nodes", ())}
        for axis in answer["axes"]
    }
    actual = {identity: row.model_dump(mode="json") for identity, row in descriptors.items()}
    for column in overview.columns:
        block, key = column.key.split(".")
        for i, identity in enumerate(overview.members):
            encoded = column.dictionary[column.indices[i]]
            if block in {"sequences", "interfaces"}:
                descriptor = descriptors.get(identity)
                if descriptor is None:
                    raise ValueError("Overview needs the captured molecular descriptor.")
                values: Any = actual[identity][block]
                expected = values[key]
            elif block == "shape":
                descriptor = descriptors.get(identity)
                expected = (
                    actual[identity]["shape"][key]
                    if descriptor is not None
                    else paths[identity]["values"][key]
                )
            else:
                expected = paths[identity]["values"][key]
                if (
                    column.display_dictionary is not None
                    and column.display_dictionary[column.indices[i]] != labels[key][expected]
                ):
                    raise ValueError(
                        "Overview enzyme display name disagrees with the captured identity."
                    )
            if encoded != expected:
                raise ValueError("Overview feature value disagrees with the preparation record.")
        if block == "shape":
            observed = [column.dictionary[i] for i in column.indices]
            if any(type(v) is not int or v < 0 for v in observed):
                raise ValueError("Overview measurements require nonnegative integer values.")
            numbers = [cast(int, value) for value in observed]
            extent = max(numbers) - min(numbers)
            if extent and extent != overview.basis.shape_scales[cast(ShapeKey, key)]:
                raise ValueError("Overview observed-range scale disagrees with its values.")
        if (
            block == "interfaces"
            and key.endswith("_word")
            and len({len(str(column.dictionary[i])) for i in column.indices}) != 1
        ):
            raise ValueError("Overview Hamming comparison requires equal-length ends.")


def recorded_overview(
    choices: ChoiceSource, answer: Record | None = None
) -> PreparationOverview | None:
    from .descriptors import edition_descriptors
    from .reader import AtlasEdition

    if (
        not isinstance(choices, AtlasEdition)
        or "overview.json" not in choices._store.manifest.artifacts
    ):
        return None
    raw = choices._store.read("overview.json")
    overview = PreparationOverview.model_validate_json(raw)
    answer = choices.query() if answer is None else answer
    validate_overview(overview, answer, {p.identity: p for p in edition_descriptors(choices)})
    object.__setattr__(
        choices,
        "_overview_admission",
        (
            sha256_digest(raw),
            overview.digest,
            answer["snapshot_digest"],
            frozenset(overview.members),
        ),
    )
    return overview


def recorded_overview_digest(choices: ChoiceSource, answer: Record) -> str | None:
    from .reader import AtlasEdition

    if (
        not isinstance(choices, AtlasEdition)
        or "overview.json" not in choices._store.manifest.artifacts
    ):
        return None
    raw = choices._store.read("overview.json")
    receipt = getattr(choices, "_overview_admission", None)
    members = frozenset(p["materialized_realization_id"] for p in answer["paths"])
    if (
        receipt is not None
        and receipt[0] == sha256_digest(raw)
        and receipt[2:] == (answer["snapshot_digest"], members)
    ):
        return str(receipt[1])
    # View restoration deliberately supplies only snapshot and membership.
    # Fresh admission still checks against the complete captured metadata.
    admitted = recorded_overview(choices)
    assert admitted is not None
    if admitted.snapshot_digest != answer["snapshot_digest"] or set(admitted.members) != members:
        raise ValueError("Recorded overview disagrees with this view's snapshot or membership.")
    return admitted.digest
