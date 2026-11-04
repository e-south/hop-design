"""Shared lifecycle; endpoint owners retain their native verification and projections."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast

from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.intents.refinement import DesignRefinementQuery
from hop_design.models.construction.surveys.query import InterfaceSurveyQuery
from hop_design.models.construction.variants.applicability import validate_product_parameters

from ..execution.feedback import ProgressObserver, StopRequest
from ..navigation.facade import AtlasNavigation
from ..packets.atlas import MolecularAtlasPacket
from ..packets.publication import SourceBoundConstructionPacket

Source = str | Path | dict[str, Any]

if TYPE_CHECKING:
    from .revision import DesignRevisionPreview


class PreparationReceipt(Protocol):
    @property
    def materialized_realization_ids(self) -> tuple[str, ...]: ...


@dataclass(frozen=True, init=False, repr=False)
class DesignChoices(AtlasNavigation, ABC):
    """An admitted immutable snapshot. Searching is an explicit separate action."""

    _directory: Path
    _resolution: bytes

    def member(self, name: str) -> DesignChoices:
        """Return ordinary choices for one required experimental member of a family."""
        raise ValueError("This result has one exact stem; it is not a required stem family.")

    def select_members(
        self, members: dict[str, dict[str, Any]], *, baseline: str
    ) -> dict[str, Any]:
        """Select one exact preparation per required experimental stem."""
        raise ValueError("Explicit stem membership requires a construction-family intent.")

    @property
    def resolution(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self._resolution))

    @property
    def inspection_source(self) -> Path:
        """Source location for the existing endpoint-specific inspection adapter."""
        return self._directory

    @abstractmethod
    def query(self, query: Source | None = None) -> dict[str, Any]: ...

    def explain(self, query: Source | None = None) -> dict[str, Any]:
        """Describe available molecules without changing the query or selecting a route."""
        from ..variants.explanation import explain_choices
        from .query import parameters_permitted

        result = self.query(query)
        can_continue = None
        if result.get("execution") is not None:
            can_continue = result["coverage"]["unexamined_pairs"] > 0 and parameters_permitted(
                self._validated_query(query), result["axes"]
            )
        return explain_choices(self.resolution, result, can_continue=can_continue)

    def _validated_query(self, query: Source | None) -> InterfaceSurveyQuery:
        resolved = self._resolved_query(query)
        return (
            resolved
            if isinstance(resolved, InterfaceSurveyQuery)
            else InterfaceSurveyQuery(
                parameters=resolved.parameters, membership=resolved.membership
            )
        )

    def _resolved_query(self, query: Source | None) -> InterfaceSurveyQuery | DesignRefinementQuery:
        from .query import resolve_query
        from .refinement import load_design_query

        predicates = load_design_query(query)
        validate_product_parameters(predicates.parameters, self.resolution["intent"]["product"])
        if isinstance(predicates, DesignRefinementQuery):
            self._validate_refinement(predicates)
        resolved = resolve_query(
            InterfaceSurveyQuery(
                parameters=predicates.parameters, membership=predicates.membership
            ),
            self.resolution["permissions"],
        )
        return predicates.model_copy(update={"parameters": resolved.parameters})

    def _validate_refinement(self, query: DesignRefinementQuery) -> None:
        raise ValueError(
            "Reference-bound preservation is not supported by this endpoint's discovery backend."
        )

    def preserve(
        self, reference: Source, *, stage: str, except_neighborhood: str
    ) -> dict[str, Any]:
        """Create a new refinement from a molecule, independent of its locating filters."""
        raise ValueError(
            "Reference-bound preservation is not supported by this endpoint's discovery backend."
        )

    def _submitted_query(self, query: Source | None) -> dict[str, Any]:
        from .refinement import load_design_query

        return load_design_query(query).model_dump(mode="json", by_alias=True)

    def plot_svg_bytes(
        self,
        query: Source | None = None,
        *,
        selected_identity: str | None = None,
        view: str = "parameters",
        stage: str = "endpoint",
        layout: str = "auto",
    ) -> bytes:
        """Draw admitted eligibility without producing print exports or rerunning search."""
        from ..navigation.landscape_figure import choice_plot

        return choice_plot(
            self, query, selected_identity=selected_identity, view=view, stage=stage, layout=layout
        )

    def compare(self, request: Source, *, query: Source | None = None) -> dict[str, Any]:
        """Assess required members within these choices without searching or selecting."""
        raise ValueError("Required comparisons are not supported by this discovery backend.")

    def inspection_settings(
        self,
        *,
        presentation: dict[str, Any] | None = None,
        exploration: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate the same presentation settings used by saved inspections."""
        from ..navigation.views import inspection_settings

        return inspection_settings(presentation=presentation, exploration=exploration, choices=self)

    def families(self, *, query: Source | None = None, stage: str = "endpoint") -> dict[str, Any]:
        """Group exact products by recorded structure without combining independent parts."""
        from ..navigation.molecular_groups import molecular_families

        return molecular_families(
            self.query(query), stage=stage, endpoint=self.resolution["intent"]["product"]
        )

    def select_set(self, comparison: Source, *, set_label: str, baseline: str) -> dict[str, Any]:
        """Select an assessed comparison with explicit membership and baseline."""
        raise ValueError("Required comparisons are not supported by this discovery backend.")

    @abstractmethod
    def select(
        self, choice: dict[str, Any] | str, *, query: Source | None = None
    ) -> dict[str, Any]: ...

    def sample(
        self,
        *,
        seed: int | None = None,
        query: Source | None = None,
        strategy: str | None = None,
        stage: str | None = None,
        history: tuple[str, ...] = (),
        after: Source | None = None,
    ) -> dict[str, Any]:
        """Sample preparations, or return a replayable family-guided selection receipt."""
        from ..navigation.guided_sampling import sample_choices

        return sample_choices(
            self,
            ordinary=self._sample_preparation,
            seed=seed,
            query=query,
            strategy=strategy,
            stage=stage,
            history=history,
            after=after,
        )

    @abstractmethod
    def _sample_preparation(self, *, seed: int, query: Source | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def figure(
        self,
        *,
        query: Source | None = None,
        selection: Source | None = None,
        view: str | None = None,
        stage: str | None = None,
        layout: str | None = None,
        render_policy: str | None = None,
        reference_selection: Source | None = None,
        display_axes: tuple[str, ...] | None = None,
    ) -> SourceBoundConstructionPacket: ...

    def atlas(
        self,
        selection: Source,
        *,
        reference_selection: Source | None = None,
        render_policy: str | None = None,
        presentation: str | None = None,
        stage: str | None = None,
    ) -> MolecularAtlasPacket:
        """Draw the complete route; interactive inspection may defer this artwork."""
        return self._inspection_packet(
            selection,
            reference_selection=reference_selection,
            render_policy=render_policy,
            presentation=presentation,
            stage=stage,
            draw_route=True,
        )

    @abstractmethod
    def _inspection_packet(
        self,
        selection: Source,
        *,
        reference_selection: Source | None = None,
        render_policy: str | None = None,
        presentation: str | None = None,
        stage: str | None = None,
        draw_route: bool = False,
    ) -> MolecularAtlasPacket: ...

    @abstractmethod
    def retrieve(self, selection: Source, destination: str | Path) -> PreparationReceipt: ...

    def view(
        self,
        selection: Source,
        *,
        stage: str = "all",
        reference_identity: str | None = None,
        camera: tuple[float, float, float, float] | None = None,
        presentation: dict[str, Any] | None = None,
        exploration: dict[str, Any] | None = None,
        render_policy: str = "captured",
    ) -> dict[str, Any]:
        """Capture a replayable inspection position without changing molecular intent."""
        from ..navigation.views import view_receipt

        return view_receipt(
            self,
            selection,
            stage=stage,
            reference_identity=reference_identity,
            camera=camera,
            presentation=presentation,
            exploration=exploration,
            render_policy=render_policy,
        )

    def restore_view(self, receipt: Source) -> dict[str, Any]:
        from ..navigation.views import restore_view

        return restore_view(self, receipt)

    def _view_state_ids(self, selection: Source) -> tuple[str, ...]:
        """Keep native replay authoritative when validating a live inspection."""
        atlas = json.loads(self._inspection_packet(selection).json_bytes)["atlas"]
        return tuple(state["state"]["state_id"] for state in atlas["states"])

    def find_more(
        self,
        *,
        max_evaluations: int = 64,
        first_choices: int | None = None,
        on_progress: ProgressObserver | None = None,
        should_stop: StopRequest | None = None,
    ) -> DesignChoices:
        """Continue explicitly while retaining every previously published snapshot."""
        from .execute import continue_design_discovery

        return continue_design_discovery(
            self._directory,
            max_evaluations=max_evaluations,
            first_choices=first_choices,
            on_progress=on_progress,
            should_stop=should_stop,
        )

    def revise(self, revision: Source) -> DesignRevisionPreview:
        """Preview a new permission context without changing this choice snapshot."""
        from .revision import preview_design_revision

        request = {**self.resolution["intent"], "context": self.resolution["permissions"]}
        preview = preview_design_revision(request, revision)
        object.__setattr__(
            preview, "_roots", (*preview._roots, ProtectedRoot.capture(self._directory))
        )
        return preview

    def _protect[Packet: SourceBoundConstructionPacket](self, packet: Packet) -> Packet:
        object.__setattr__(
            packet, "_roots", (*packet._roots, ProtectedRoot.capture(self._directory))
        )
        return packet

    def _output(self, destination: str | Path) -> Path:
        output = Path(destination)
        if output.resolve(strict=False).is_relative_to(self._directory):
            raise ValueError("Write exports outside the protected discovery directory.")
        return output
