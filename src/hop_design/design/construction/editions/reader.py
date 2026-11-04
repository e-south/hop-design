"""Read-only atlas edition lifecycle over captured molecular evidence."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Never, cast

from hop_design.export.publication import publish_directory_files_create_only
from hop_design.models.construction.editions.manifest import EditionSelection
from hop_design.serialization import canonical_json_bytes

from ..intents.base import Source
from ..navigation.facade import AtlasNavigation
from ..packets.atlas import MolecularAtlasPacket
from ..packets.publication import SourceBoundConstructionPacket
from ..surveys.selection import load_query, sample_path
from .descriptors import CapturedDescriptors
from .inspection_context import InspectionContext
from .projection import SelectionIndex
from .refinement import preserved_query, query_edition, selection_query
from .storage import EditionStore


@dataclass(frozen=True)
class CapturedPreparation:
    directory: Path
    materialized_realization_ids: tuple[str, ...]


class CapturedAtlas(MolecularAtlasPacket):
    _packet_schema = "hop.captured-atlas-packet/v1"


class AtlasEdition(AtlasNavigation):
    """Immutable captured choices; execution remains with the original producer."""

    def __init__(self, store: EditionStore):
        self._store = store
        self._directory = store.root.path
        self._index = store.read("choices.json")
        self._resolution = store.read("resolution.json")
        self._regional_options: bytes | None = None
        self._descriptors: CapturedDescriptors | None = None
        self._inspection_context: InspectionContext | None = None
        index = json.loads(self._index)
        identities = {p["materialized_realization_id"] for p in index["paths"]}
        if identities != {m.materialized_realization_id for m in store.manifest.members}:
            raise ValueError("Edition index disagrees with captured member identities.")
        if index["snapshot_digest"] != store.manifest.snapshot_digest:
            raise ValueError("Edition snapshot disagrees with its index.")
        self._selection_index = SelectionIndex.from_choices(index)
        for member in store.manifest.members:
            selection = json.loads(store.read(f"{member.directory}/selection.json"))
            if selection["materialized_realization_id"] != member.materialized_realization_id:
                raise ValueError("Captured selection disagrees with edition membership.")

    @property
    def producer(self) -> dict[str, str]:
        return dict(self._store.manifest.producer)

    @property
    def digest(self) -> str:
        return self._store.digest

    @property
    def integrity(self) -> dict[str, str]:
        return {
            "metadata": "verified",
            "authorities": "verified_on_access" if self._store.compact else "verified_at_open",
            "molecular_replay": "not_performed_by_edition_reader",
        }

    def verify_integrity(self) -> dict[str, object]:
        """Check every captured byte; this does not repeat molecular compilation."""
        for name in self._store.manifest.artifacts:
            self._store.read(name)
        return {
            "edition_digest": self.digest,
            "artifacts_verified": len(self._store.manifest.artifacts),
            "authority_archives_verified": sum(
                name.endswith("/evidence.zip") for name in self._store.manifest.artifacts
            ),
            "molecular_replay": False,
        }

    @property
    def resolution(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self._resolution))

    def query(self, query: Source | None = None) -> dict[str, Any]:
        answer = query_edition(self, query)
        if query is None and self._inspection_context is None:
            # Opening already computes these facts. Retain detached metadata
            # for inspection, never a filtered answer or molecular authority.
            self._inspection_context = InspectionContext.from_choices(answer)
        return answer

    def _inspection_choices(self, identity: str) -> dict[str, Any]:
        if self._inspection_context is None:
            self.query()
        assert self._inspection_context is not None
        return self._inspection_context.member(identity)

    def preserve(
        self, reference: Source, *, stage: str, except_neighborhood: str
    ) -> dict[str, Any]:
        """Keep regional sequence, contacts and chemistry using captured complete routes."""
        return preserved_query(
            self, reference, stage=stage, except_neighborhood=except_neighborhood
        )

    def explain(self, query: Source | None = None) -> dict[str, Any]:
        from ..variants.explanation import explain_choices

        answer = explain_choices(self.resolution, self.query(query), can_continue=False)
        answer["actions"] = [a for a in answer["actions"] if a in {"select", "refine_query"}]
        answer["guidance"] += (
            " This frozen edition supports viewing and retrieval; "
            "new search belongs to the original discovery."
        )
        return answer

    def member(self, name: str) -> Never:
        raise ValueError("An atlas edition contains one experimental stem; open its named edition.")

    def inspection_settings(
        self,
        *,
        presentation: dict[str, Any] | None = None,
        exploration: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Validate presentation without parsing captured molecular records."""
        from ..navigation.views import inspection_settings

        return inspection_settings(presentation=presentation, exploration=exploration, choices=self)

    def families(self, *, query: Source | None = None, stage: str = "endpoint") -> dict[str, Any]:
        from ..navigation.molecular_groups import molecular_families

        return molecular_families(
            self.query(query), stage=stage, endpoint=self.resolution["intent"]["product"]
        )

    def plot_svg_bytes(
        self,
        query: Source | None = None,
        *,
        selected_identity: str | None = None,
        view: str = "parameters",
        stage: str = "endpoint",
        layout: str = "auto",
    ) -> bytes:
        from ..navigation.landscape_figure import choice_plot

        return choice_plot(
            self, query, selected_identity=selected_identity, view=view, stage=stage, layout=layout
        )

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
        from .rendering import edition_figure

        return edition_figure(
            self,
            query=query,
            selection=selection,
            view=view,
            stage=stage,
            layout=layout,
            render_policy=render_policy,
            reference_selection=reference_selection,
            display_axes=display_axes,
        )

    def select(
        self, choice: str | dict[str, Any], *, query: Source | None = None
    ) -> dict[str, Any]:
        identity = choice if isinstance(choice, str) else choice["materialized_realization_id"]
        normalized = selection_query(self, identity, query)
        return EditionSelection.model_validate_json(
            canonical_json_bytes(
                {
                    "edition_digest": self.digest,
                    "materialized_realization_id": identity,
                    "query": normalized,
                }
            )
        ).model_dump(mode="json", by_alias=True)

    def _selected(self, selection: Source) -> EditionSelection:
        from ..navigation.guided_sampling import selection_source

        selected = EditionSelection.model_validate_json(
            canonical_json_bytes(selection_source(self, selection))
        )
        if selected.edition_digest != self.digest:
            raise ValueError("Selected preparation belongs to a different atlas edition.")
        if self.select(
            selected.materialized_realization_id,
            query=selected.query.model_dump(mode="json", by_alias=True),
        ) != selected.model_dump(mode="json", by_alias=True):
            raise ValueError("Selection query disagrees with the edition.")
        return selected

    def _prefix(self, identity: str) -> str:
        for member in self._store.manifest.members:
            if member.materialized_realization_id == identity:
                return member.directory
        raise ValueError("Preparation is not captured in this edition.")

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

    def _sample_preparation(self, *, seed: int, query: Source | None = None) -> dict[str, Any]:
        result = self.query(query)
        path = sample_path([p for p in result["paths"] if p["matches"]], load_query(None), seed)
        return self.select(path, query=query)

    def atlas(
        self,
        selection: Source,
        *,
        reference_selection: Source | None = None,
        render_policy: str | None = None,
        presentation: str | None = None,
        stage: str | None = None,
    ) -> MolecularAtlasPacket:
        return self._inspection_packet(
            selection,
            reference_selection=reference_selection,
            render_policy=render_policy,
            presentation=presentation,
            stage=stage,
            draw_route=True,
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
        from .inspection import inspect_edition_atlas

        return inspect_edition_atlas(
            self,
            selection,
            reference_selection=reference_selection,
            render_policy=render_policy,
            presentation=presentation,
            stage=stage,
            draw_route=draw_route,
        )

    def retrieve(self, selection: Source, destination: str | Path) -> CapturedPreparation:
        from .materials import member_materials

        selected = self._selected(selection)
        files = member_materials(self, selected.materialized_realization_id)
        publish_directory_files_create_only(
            files, Path(destination), protected_root=self._store.root
        )
        return CapturedPreparation(Path(destination), (selected.materialized_realization_id,))

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
        from .inspection import inspection_state_ids

        return inspection_state_ids(self, selection)


def load_atlas_edition(directory: str | Path) -> AtlasEdition:
    """Verify captured bytes without loading a live checkpoint or executing its producer."""
    return AtlasEdition(EditionStore(directory))
