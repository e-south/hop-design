"""Shared navigation operations over live choices and immutable atlas editions."""

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from hop_design.models.construction.variants.landscape import MolecularLandscape
    from hop_design.models.construction.variants.similarity import MolecularDistancePolicy

    from ..editions.reader import AtlasEdition
    from ..intents.base import Source
    from .preview import MolecularPreview


class AtlasNavigation:
    def parameters(self, *, query: "Source | None" = None) -> list[dict[str, Any]]:
        """Explain molecular features, active constraints and supported operations."""
        from .features.vocabulary import parameter_vocabulary
        from .types import ChoiceSource

        return parameter_vocabulary(cast(ChoiceSource, self), query)

    @property
    def has_landscape(self) -> bool:
        """Whether fixed coordinates are available without fitting a layout."""
        from .landscape_source import has_molecular_landscape
        from .types import ChoiceSource

        return has_molecular_landscape(cast(ChoiceSource, self))

    def neighbors(
        self,
        identity: str,
        *,
        query: "Source | None" = None,
        limit: int = 5,
        verify_controls: bool = True,
        timeout_seconds: float = 5.0,
    ) -> dict[str, Any]:
        """Explain eligible neighboring constructions and verify available loop controls."""
        from .neighbor_work import NeighborWork
        from .neighbors import neighboring_preparations
        from .types import ChoiceSource

        return neighboring_preparations(
            cast(ChoiceSource, self),
            identity,
            query=query,
            limit=limit,
            verify_controls=verify_controls,
            work=NeighborWork(timeout_seconds),
        )

    def preview(self, identity: str, *, query: "Source | None" = None) -> "MolecularPreview":
        """Inspect one recorded hairpin and trace without committing a selection."""
        from .preview import preview_preparation
        from .types import ChoiceSource

        return preview_preparation(cast(ChoiceSource, self), identity, query=query)

    def landscape(self) -> "MolecularLandscape":
        """Return fixed molecular coordinates for the complete recorded choice pool."""
        from .landscape_source import molecular_landscape
        from .types import ChoiceSource

        return molecular_landscape(cast(ChoiceSource, self))

    def freeze(
        self,
        destination: str | Path,
        *,
        query: "Source | None" = None,
        identities: tuple[str, ...] | None = None,
        include_landscape: bool = False,
        compact: bool = False,
        distance_policy: "MolecularDistancePolicy | Source | None" = None,
        comparison_weights: tuple[float, float, float] | None = None,
    ) -> "AtlasEdition":
        """Capture molecular evidence and, optionally, fixed similarity coordinates."""
        from ..editions.capture import freeze_choices
        from .types import ChoiceSource

        return freeze_choices(
            cast(ChoiceSource, self),
            destination,
            query=query,
            identities=identities,
            include_landscape=include_landscape,
            compact=compact,
            distance_policy=distance_policy,
            comparison_weights=comparison_weights,
        )
