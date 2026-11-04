"""Obtain molecular descriptors through each source's existing authority boundary."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from hop_design.models.construction.variants.landscape import MolecularLandscape
from hop_design.models.construction.variants.similarity import MolecularDescriptor
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .molecular_descriptor import molecular_descriptor
from .types import ChoiceSource, Record

if TYPE_CHECKING:
    from ..editions.reader import AtlasEdition


@dataclass(frozen=True)
class _LandscapeAdmission:
    raw_digest: str
    snapshot: str
    identities: frozenset[str]
    semantic_digest: str


def landscape_digest(choices: ChoiceSource, *, answer: Record) -> str:
    """Validate saved coordinates without rebuilding their model on every view save.

    The receipt belongs to one edition object. Fresh checked bytes and the entire
    recorded membership must agree before reusing it; eligibility is not membership.
    No mutable molecular model or caller-supplied validation evidence is retained.
    """
    from ..editions.reader import AtlasEdition

    if not (
        isinstance(choices, AtlasEdition) and "landscape.json" in choices._store.manifest.artifacts
    ):
        return molecular_landscape(choices, answer=answer).digest
    raw = choices._store.read("landscape.json")
    digest = sha256_digest(raw)
    identities = frozenset(p["materialized_realization_id"] for p in answer["paths"])
    receipt = getattr(choices, "_landscape_admission", None)
    if isinstance(receipt, _LandscapeAdmission) and receipt.raw_digest == digest:
        if receipt.snapshot != answer["snapshot_digest"] or receipt.identities != identities:
            raise ValueError("Saved molecular landscape disagrees with this choice snapshot.")
        return receipt.semantic_digest
    return _admit_captured_landscape(choices, raw, answer)[1]


def inspection_landscape(
    choices: ChoiceSource, *, answer: Record
) -> tuple[MolecularLandscape, str]:
    """Build the map and its immutable admission from the same checked bytes.

    The returned model is disposable. A subsequent view save can reuse the receipt
    without retaining that model or trusting a second, potentially different read.
    """
    from ..editions.reader import AtlasEdition

    if isinstance(choices, AtlasEdition) and "landscape.json" in choices._store.manifest.artifacts:
        return _admit_captured_landscape(choices, choices._store.read("landscape.json"), answer)
    landscape = molecular_landscape(choices, answer=answer)
    return landscape, landscape.digest


def _admit_captured_landscape(
    choices: "AtlasEdition", raw: bytes, answer: Record
) -> tuple[MolecularLandscape, str]:
    landscape = _validated_landscape(raw, answer)
    digest = landscape.digest
    receipt = _LandscapeAdmission(
        sha256_digest(raw),
        landscape.snapshot_digest,
        frozenset(p.identity for p in landscape.preparations),
        digest,
    )
    object.__setattr__(choices, "_landscape_admission", receipt)
    return landscape, digest


def has_molecular_landscape(choices: ChoiceSource) -> bool:
    """Browsing must not implicitly fit coordinates or import the optional fitter."""
    from ..editions.reader import AtlasEdition

    return bool(getattr(choices, "_landscape_bytes", None)) or (
        isinstance(choices, AtlasEdition) and "landscape.json" in choices._store.manifest.artifacts
    )


def molecular_descriptors(choices: ChoiceSource) -> tuple[MolecularDescriptor, ...]:
    from ..editions.comparison import captured_route
    from ..editions.reader import AtlasEdition
    from ..intents.hairpin_choices import HairpinDesignChoices
    from ..intents.inserts.admission import admitted_options
    from ..intents.results import InsertDesignChoices

    identities = {p["materialized_realization_id"] for p in choices.query()["paths"]}
    if isinstance(choices, AtlasEdition):
        if choices._store.compact:
            from ..editions.descriptors import edition_descriptors

            return edition_descriptors(choices)
        return tuple(molecular_descriptor(captured_route(choices, i)) for i in sorted(identities))
    if isinstance(choices, HairpinDesignChoices):
        return tuple(
            molecular_descriptor(route)
            for _, route in choices._pool._routes
            if route.materialized_realization_id in identities
        )
    if isinstance(choices, InsertDesignChoices):
        from .descriptor_index import indexed_descriptors

        recorded = indexed_descriptors(choices._pool)
        if recorded is not None:
            return tuple(p for p in recorded if p.identity in identities)
        return tuple(
            MolecularDescriptor.model_validate_json(canonical_json_bytes(option["descriptor"]))
            for option in admitted_options(choices)
        )
    raise TypeError("This choice source has no admitted molecular descriptor projection.")


def molecular_landscape(
    choices: ChoiceSource, *, answer: Record | None = None
) -> MolecularLandscape:
    from ..editions.reader import AtlasEdition
    from .similarity_layout import build_molecular_landscape

    answer = choices.query() if answer is None else answer
    captured = (
        isinstance(choices, AtlasEdition) and "landscape.json" in choices._store.manifest.artifacts
    )
    raw = (
        choices._store.read("landscape.json")
        if captured and isinstance(choices, AtlasEdition)
        else getattr(choices, "_landscape_bytes", None)
    )
    if raw is None:
        landscape = build_molecular_landscape(
            molecular_descriptors(choices), snapshot_digest=answer["snapshot_digest"]
        )
        raw = canonical_json_bytes(landscape)
        if len(raw) > 32 * 1024 * 1024:
            raise ValueError("Molecular landscape exceeds the 32 MiB retained projection limit.")
        object.__setattr__(choices, "_landscape_bytes", raw)
    return _validated_landscape(cast(bytes, raw), answer)


def _validated_landscape(raw: bytes, answer: Record) -> MolecularLandscape:
    landscape = MolecularLandscape.model_validate_json(raw)
    if landscape.snapshot_digest != answer["snapshot_digest"] or {
        p.identity for p in landscape.preparations
    } != {p["materialized_realization_id"] for p in answer["paths"]}:
        raise ValueError("Saved molecular landscape disagrees with this choice snapshot.")
    return landscape
