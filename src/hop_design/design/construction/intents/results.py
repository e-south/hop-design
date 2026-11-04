"""One admitted choice object connects discovery, selection, figures and materials."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from hop_design.models.construction.intents.refinement import DesignRefinementQuery
from hop_design.models.construction.surveys.query import InterfaceSurveyQuery
from hop_design.serialization import canonical_json_bytes

from ..packets.atlas import MolecularAtlasPacket
from ..packets.publication import SourceBoundConstructionPacket
from ..public import VerifiedConstructionBundle
from ..surveys.atlas import _inspect_interface_survey_atlas
from ..surveys.choices import InterfaceSurveyChoices
from ..surveys.retrieve import retrieve_interface_survey_witness
from ..surveys.selection import interfaces_excluded, interfaces_pending, sample_path
from ..variants.explanation import explain_choices
from .base import DesignChoices, Source
from .inserts.refinement import refine_result, validate_reference
from .inserts.retrieve import InsertSetHandoff, retrieve_preserved, retrieve_set
from .inserts.selection import native_selection, wrap_selection
from .query import parameters_permitted


class InsertDesignChoices(DesignChoices):
    """Complete insert choices backed by the resumable interface survey."""

    _pool: InterfaceSurveyChoices

    def _validate_refinement(self, query: DesignRefinementQuery) -> None:
        validate_reference(self, query)

    def preserve(
        self, reference: Source, *, stage: str, except_neighborhood: str
    ) -> dict[str, Any]:
        selected = native_selection(self, reference)
        query = DesignRefinementQuery.model_validate_json(
            canonical_json_bytes(
                {
                    "reference": {
                        k: selected[k]
                        for k in (
                            "request_digest",
                            "snapshot_digest",
                            "materialized_realization_id",
                        )
                    },
                    "surroundings": {"stage": stage, "except_neighborhood": except_neighborhood},
                }
            )
        )
        self._validate_refinement(query)
        return query.model_dump(mode="json", by_alias=True)

    def explain(self, query: Source | None = None) -> dict[str, Any]:
        predicates = self._validated_query(query)
        result = self.query(query)
        permitted = parameters_permitted(predicates, result["axes"])
        return explain_choices(
            self.resolution,
            result,
            interface_excluded=interfaces_excluded(
                self._pool._request.targets, self._pool._excluded_pairs, predicates
            ),
            can_continue=permitted
            and interfaces_pending(
                self._pool._request.targets, self._pool._ended_pairs, predicates
            ),
        )

    def query(self, query: Source | None = None) -> dict[str, Any]:
        """Filter recorded choices, without searching or changing molecular intent."""
        predicates = self._resolved_query(query)
        result = self._pool.query(
            InterfaceSurveyQuery(
                parameters=predicates.parameters, membership=predicates.membership
            ).model_dump(mode="json", by_alias=True)
        )
        if isinstance(predicates, DesignRefinementQuery):
            result = refine_result(self, result, predicates)
        result["submitted_query"] = self._submitted_query(query)
        return result

    def select(
        self, choice: dict[str, Any] | str, *, query: Source | None = None
    ) -> dict[str, Any]:
        """Bind a displayed complete choice to its exact verified identity."""
        predicates = self._resolved_query(query)
        resolved = InterfaceSurveyQuery(
            parameters=predicates.parameters, membership=predicates.membership
        ).model_dump(mode="json", by_alias=True)
        if isinstance(choice, str):
            found = next(
                (
                    p
                    for p in self.query(query)["paths"]
                    if p["matches"] and p["materialized_realization_id"] == choice
                ),
                None,
            )
            if found is None:
                raise ValueError("No matching recorded preparation has that identity.")
            choice = cast(dict[str, Any], found)
        if isinstance(predicates, DesignRefinementQuery) and not any(
            p["matches"]
            and p["materialized_realization_id"] == choice["materialized_realization_id"]
            and p["address"] == choice["address"]
            for p in self.query(query)["paths"]
        ):
            raise ValueError("Selected preparation violates the preserved surroundings.")
        selected = self._pool.select(
            **choice["address"],
            materialized_realization_id=choice["materialized_realization_id"],
            query=resolved,
        )
        return (
            wrap_selection(self, selected, predicates)
            if isinstance(predicates, DesignRefinementQuery)
            else selected
        )

    def _sample_preparation(self, *, seed: int, query: Source | None = None) -> dict[str, Any]:
        """Select deterministically from matching recorded preparations."""
        if isinstance(self._resolved_query(query), DesignRefinementQuery):
            paths = [p for p in self.query(query)["paths"] if p["matches"]]
            return self.select(sample_path(paths, InterfaceSurveyQuery(), seed), query=query)
        resolved = self._validated_query(query).model_dump(mode="json", by_alias=True)
        return self._pool.sample(seed=seed, query=resolved)

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
    ) -> SourceBoundConstructionPacket:
        """Draw the landscape and selected path from this same snapshot."""
        from ..navigation.figure_context import figure_context
        from ..navigation.landscape_figure import landscape_figure

        context = figure_context(
            self, selection, view, stage, layout, render_policy, reference_selection, display_axes
        )
        selection, view, stage, layout = (
            context.selection,
            context.view,
            context.stage,
            context.layout,
        )
        atlas = context.atlas(self)
        if view in {"families", "similarity"}:
            return context.attach(
                landscape_figure(
                    self,
                    query=query,
                    selection=selection,
                    stage=stage,
                    layout=layout,
                    atlas=atlas,
                    view=view,
                    display_axes=context.display_axes,
                    color=context.color,
                ),
                atlas,
            )
        if view != "parameters" or stage != "endpoint" or layout != "auto":
            raise ValueError("Choose parameters, or families with its stage and layout.")
        from ..navigation.guided_sampling import selection_source
        from .comparisons import source_value
        from .inserts.figure import refined_figure

        if selection is not None:
            selection = selection_source(self, selection)

        if context.receipt is not None:
            return context.attach(
                refined_figure(
                    self,
                    query or context.receipt["selection"]["query"],
                    selection,
                    atlas=atlas,
                    display_axes=context.display_axes,
                ),
                atlas,
            )

        if (
            selection is not None
            and source_value(selection).get("schema") == "hop.insert-design-selection/v1"
            and query is None
        ):
            query = source_value(selection)["query"]
        if isinstance(self._resolved_query(query), DesignRefinementQuery) or (
            selection is not None
            and source_value(selection).get("schema") == "hop.insert-design-selection/v1"
        ):
            query = query or {}
            return refined_figure(self, query, selection, display_axes=context.display_axes)
        resolved = (
            None
            if query is None
            else self._validated_query(query).model_dump(mode="json", by_alias=True)
        )
        return self._protect(
            self._pool.figure(
                query=resolved, selection=selection, display_axes=context.display_axes
            )
        )

    def _inspection_packet(
        self,
        selection: Source,
        *,
        reference_selection: Source | None = None,
        render_policy: str | None = None,
        presentation: str | None = None,
        stage: str | None = None,
        draw_route: bool = False,
    ) -> MolecularAtlasPacket:
        """Replay and draw every molecular stage of the exact selected preparation."""
        from ..navigation.guided_sampling import selection_source
        from ..navigation.render_policy import render_context
        from .comparisons import source_value

        context = render_context(
            self, selection, reference_selection, render_policy, presentation, stage
        )
        selection, reference_selection = context.selection, context.reference
        selection = selection_source(self, selection)
        if reference_selection is not None:
            reference_selection = selection_source(self, reference_selection)

        if (
            reference_selection is None
            and source_value(selection).get("schema") == "hop.insert-design-selection/v1"
        ):
            reference_selection = source_value(selection)["reference"]
        packet = _inspect_interface_survey_atlas(
            self._directory / "intent/request.json",
            self._directory / "survey.sqlite",
            selection=native_selection(self, selection),
            reference_selection=None
            if reference_selection is None
            else native_selection(self, reference_selection),
            draw_route=draw_route,
        )
        from .inserts.selection import bind_public_selection

        return self._protect(
            context.finish(
                bind_public_selection(packet, selection), "current", draw_route=draw_route
            )
        )

    def retrieve(
        self, selection: Source, destination: str | Path
    ) -> VerifiedConstructionBundle | InsertSetHandoff:
        """Replay and export the selected route and its exact oligos."""
        from ..navigation.guided_sampling import selection_source
        from .comparisons import source_value

        selection = selection_source(self, selection)

        if source_value(selection).get("schema") == "hop.design-set-selection/v2":
            return retrieve_set(self, selection, destination)
        if source_value(selection).get("schema") == "hop.insert-design-selection/v1":
            return retrieve_preserved(self, selection, destination)
        return retrieve_interface_survey_witness(
            self._directory / "intent/request.json",
            self._directory / "survey.sqlite",
            selection=native_selection(self, selection),
            destination=self._output(destination),
        )

    def compare(self, request: Source, *, query: Source | None = None) -> dict[str, Any]:
        from .inserts.comparison import compare

        return compare(self, request, query)

    def select_set(self, comparison: Source, *, set_label: str, baseline: str) -> dict[str, Any]:
        from .inserts.comparison import select_set

        return select_set(self, comparison, set_label=set_label, baseline=baseline)
