"""The common choice lifecycle over existing verified hairpin discovery objects."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from hop_design.models.construction.intents.comparison import DesignSetSelection
from hop_design.models.construction.intents.refinement import DesignRefinementQuery
from hop_design.models.construction.intents.selection import HairpinDesignSelection
from hop_design.models.construction.variants.objective import DesignSearchObjective
from hop_design.models.construction.variants.query import MolecularStage
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..navigation.guided_sampling import selection_source
from ..packets.atlas import MolecularAtlasPacket
from ..packets.publication import SourceBoundConstructionPacket
from ..search.diversity import diversity_summary
from ..surveys.selection import sample_path
from ..variants.public import ScaffoldExploration, ScaffoldVariantChoices, query_scaffold_variants
from ..variants.selection import select_scaffold_variants
from .base import DesignChoices, Source
from .hairpin_projection import project_hairpin_choices
from .refinement import reference_label


@dataclass(frozen=True)
class HairpinHandoff:
    """A replay-verified exported preparation set with its exact member identities."""

    directory: Path
    materialized_realization_ids: tuple[str, ...]


class HairpinDesignChoices(DesignChoices):
    _pool: ScaffoldExploration
    _execution: bytes
    _objective: DesignSearchObjective | None

    @property
    def inspection_source(self) -> Path:
        return self._pool.source_path

    def _native(
        self, query: Source | None = None, *, stage: MolecularStage | None = None
    ) -> ScaffoldVariantChoices:
        predicates = self._resolved_query(query)
        preserved: dict[str, Any] = {}
        if isinstance(predicates, DesignRefinementQuery):
            if stage is not None and stage != predicates.surroundings.stage:
                raise ValueError(
                    "Comparison stage conflicts with the preserved surroundings stage."
                )
            preserved = {
                "stage": predicates.surroundings.stage,
                "focus": predicates.surroundings.except_neighborhood,
                "reference": self._reference_label(predicates),
                "surroundings": [predicates.surroundings.model_dump(mode="json")],
            }
        return query_scaffold_variants(
            self._pool,
            {
                "schema": "hop.scaffold-variant-query/v2",
                "result_digest": self._pool.result_digest,
                "stage": stage or "hairpin",
                "focus": "loop",
                "parameters": predicates.model_dump(mode="json")["parameters"],
                **(
                    {"membership": predicates.membership.model_dump(mode="json")}
                    if predicates.membership is not None
                    else {}
                ),
                **preserved,
            },
        )

    def _reference_label(self, query: DesignRefinementQuery) -> str:
        return reference_label(
            query,
            effective_request=self.resolution["effective_request"],
            snapshot_digest=self._pool.result_digest,
            options=self._pool._options,
        )

    def _validate_refinement(self, query: DesignRefinementQuery) -> None:
        self._reference_label(query)

    def preserve(
        self, reference: Source, *, stage: str, except_neighborhood: str
    ) -> dict[str, Any]:
        selected = self._selected(reference)
        surroundings = {"stage": stage, "except_neighborhood": except_neighborhood}
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
                    "surroundings": surroundings,
                    "parameters": [],
                }
            )
        )
        self._validate_refinement(query)
        return query.model_dump(mode="json", by_alias=True)

    def query(self, query: Source | None = None) -> dict[str, Any]:
        predicates = self._resolved_query(query)
        native = json.loads(self._native(query).json_bytes)
        projection = project_hairpin_choices(native, self._pool._options)
        return {
            "schema": "hop.hairpin-design-choices/v1",
            "submitted_query": self._submitted_query(query),
            "query": predicates.model_dump(mode="json", by_alias=True),
            "query_digest": sha256_digest(canonical_json_bytes(predicates)),
            "request_digest": sha256_digest(
                canonical_json_bytes(self.resolution["effective_request"])
            ),
            "snapshot_digest": self._pool.result_digest,
            **projection,
            "coverage": native["coverage"],
            "execution": json.loads(self._execution),
            "validation": "replayed_scaffold_discovery",
            "fully_enumerated": False,
            **(
                {"search_objective": diversity_summary(self._objective, projection["paths"])}
                if self._objective
                else {}
            ),
            **(
                {"changes": native["changes"], "excluded_options": native["excluded_options"]}
                if isinstance(predicates, DesignRefinementQuery)
                else {}
            ),
        }

    def select(
        self, choice: dict[str, Any] | str, *, query: Source | None = None
    ) -> dict[str, Any]:
        result = self.query(query)
        if isinstance(choice, str):
            found = next(
                (
                    p
                    for p in result["paths"]
                    if p["matches"] and p["materialized_realization_id"] == choice
                ),
                None,
            )
            if found is None:
                raise ValueError("No matching recorded preparation has that identity.")
            choice = cast(dict[str, Any], found)
        option = next(
            (
                p
                for p in result["paths"]
                if p["option_label"] == choice["option_label"]
                and p["materialized_realization_id"] == choice["materialized_realization_id"]
                and p["matches"]
            ),
            None,
        )
        if option is None:
            raise ValueError("No matching complete hairpin preparation has that identity.")
        selected = {
            k: result[k] for k in ("request_digest", "snapshot_digest", "query_digest", "query")
        }
        selected.update(
            option_label=option["option_label"],
            materialized_realization_id=option["materialized_realization_id"],
        )
        if result["query"]["schema"] == "hop.design-refinement/v1":
            selected["schema"] = "hop.hairpin-design-selection/v2"
        return HairpinDesignSelection.model_validate_json(
            canonical_json_bytes(selected)
        ).model_dump(mode="json", by_alias=True)

    def _selected(self, selection: Source) -> dict[str, Any]:
        raw = selection_source(self, selection)
        selected = HairpinDesignSelection.model_validate_json(canonical_json_bytes(raw)).model_dump(
            mode="json", by_alias=True
        )
        if self.select(selected, query=selected["query"]) != selected:
            raise ValueError(
                "Selected hairpin identity, snapshot or query disagrees with this discovery."
            )
        return selected

    def _for_selection(self, selection: Source) -> "HairpinDesignChoices":
        raw = selection_source(self, selection)
        model = (
            DesignSetSelection
            if raw.get("schema") == "hop.design-set-selection/v1"
            else HairpinDesignSelection
        )
        selected = model.model_validate_json(canonical_json_bytes(raw))
        if selected.snapshot_digest == self._pool.result_digest:
            return self
        from .hairpins import load_hairpin_choices

        return load_hairpin_choices(
            self._directory, self._resolution, snapshot_digest=selected.snapshot_digest
        )

    def _sample_preparation(self, *, seed: int, query: Source | None = None) -> dict[str, Any]:
        paths = [p for p in self.query(query)["paths"] if p["matches"]]
        from hop_design.models.construction.surveys.query import InterfaceSurveyQuery

        path = sample_path(paths, InterfaceSurveyQuery(), seed)
        return self.select(path, query=query)

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
        from ..navigation.render_policy import render_context

        context = render_context(
            self, selection, reference_selection, render_policy, presentation, stage
        )
        selection, reference_selection, policy = (
            context.selection,
            context.reference,
            context.policy,
        )
        owner = self._for_selection(selection)
        if owner is not self:
            return owner._inspection_packet(
                selection,
                reference_selection=reference_selection,
                render_policy=policy,
                presentation=context.presentation,
                stage=context.stage,
                draw_route=draw_route,
            )
        from .hairpin_atlas import inspect_hairpin

        return context.finish(
            inspect_hairpin(self, selection, reference_selection, draw_route=draw_route),
            "current",
            draw_route=draw_route,
        )

    def retrieve(self, selection: Source, destination: str | Path) -> HairpinHandoff:
        owner = self._for_selection(selection)
        if owner is not self:
            return owner.retrieve(selection, destination)
        from .comparisons import retrieve_comparison, source_value

        if source_value(selection).get("schema") == "hop.design-set-selection/v1":
            identities = retrieve_comparison(self, selection, destination)
            return HairpinHandoff(Path(destination), identities)
        selected = self._selected(selection)
        packet = select_scaffold_variants(
            self._pool.source_path,
            self._native(selected["query"]),
            members={"selected": selected["option_label"]},
            baseline="selected",
        )
        packet.write(self._output(destination))
        return HairpinHandoff(Path(destination), (selected["materialized_realization_id"],))

    def compare(self, request: Source, *, query: Source | None = None) -> dict[str, Any]:
        from .comparisons import compare_choices

        return compare_choices(self, request, query)

    def select_set(self, comparison: Source, *, set_label: str, baseline: str) -> dict[str, Any]:
        from .comparisons import select_comparison

        return select_comparison(self, comparison, set_label=set_label, baseline=baseline)

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
        if selection is not None:
            owner = self._for_selection(selection)
            if owner is not self:
                return owner.figure(
                    query=query,
                    selection=selection,
                    view=view,
                    stage=stage,
                    layout=layout,
                    render_policy=render_policy,
                    reference_selection=reference_selection,
                    display_axes=display_axes,
                )
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
        from .hairpin_figure import hairpin_figure

        return hairpin_figure(self, query, selection, context, atlas)
