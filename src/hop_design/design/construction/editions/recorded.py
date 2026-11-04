"""Freeze explicitly bound recorded choices without authorizing their continuation."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypedDict

from hop_design.design import runtime
from hop_design.export.publication import ProtectedRoot, publish_directory_files_create_only
from hop_design.models.construction.editions.source import RecordedDesignSource
from hop_design.models.construction.intents.refinement import DesignRefinementQuery
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.serialization import canonical_json_bytes

from ..intents.base import Source
from ..intents.execute import _admit_resolution, load_design_choices
from ..intents.refinement import load_design_query
from ..intents.results import InsertDesignChoices
from ..public import VerifiedConstructionBundle
from ..surveys.admission import open_survey
from ..surveys.choices import choices_from_admitted_index
from ..surveys.execute import load_request
from ..surveys.retrieve import retrieve_admitted_witness
from .capture import CaptureAuthority, freeze_choices
from .reader import AtlasEdition, load_atlas_edition
from .source_binding import verify_source
from .storage import DirectoryFiles


class _CaptureOptions(TypedDict):
    query: Source | None
    identities: tuple[str, ...] | None
    include_landscape: bool
    compact: bool
    distance_policy: Source | None
    comparison_weights: tuple[float, float, float] | None


def freeze_design_choices(
    directory: str | Path,
    destination: str | Path,
    *,
    query: Source | None = None,
    identities: tuple[str, ...] | None = None,
    include_landscape: bool = False,
    compact: bool = False,
    distance_policy: Source | None = None,
    comparison_weights: tuple[float, float, float] | None = None,
    source_contract: Source | None = None,
) -> AtlasEdition:
    """Capture choices; a source contract explicitly enables read-only recorded import.

    Without a source contract, normal producer admission applies. Recorded import
    supports compact exact-stem released-insert discoveries and returns only an
    immutable atlas edition. It cannot resume or modify the recorded discovery.
    """
    root, output = Path(directory), Path(destination)
    options: _CaptureOptions = {
        "query": query,
        "identities": identities,
        "include_landscape": include_landscape,
        "compact": compact,
        "distance_policy": distance_policy,
        "comparison_weights": comparison_weights,
    }
    if source_contract is None:
        choices = (
            load_atlas_edition(root)
            if (root / "edition.json").exists()
            else load_design_choices(root)
        )
        return choices.freeze(output, **options)
    if compact is not True or isinstance(load_design_query(query), DesignRefinementQuery):
        raise ValueError("Recorded import requires compact capture and ordinary parameter filters.")
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError("Write the edition outside the recorded source.")
    if isinstance(source_contract, (str, Path)):
        from hop_design.design.source_documents import load_source_mapping

        source_contract = load_source_mapping(Path(source_contract))
    source = RecordedDesignSource.model_validate_json(canonical_json_bytes(source_contract))
    return _capture_recorded(root, output, source, options)


def _capture_recorded(
    root: Path, output: Path, source: RecordedDesignSource, options: _CaptureOptions
) -> AtlasEdition:
    verify_source(root, source)
    protected = ProtectedRoot.capture(root)
    bound_roots = tuple(ProtectedRoot.capture(root / name) for name in source.files)
    resolution = _admit_resolution(root)
    if json.loads(resolution)["intent"]["product"] != "released_insert":
        raise ValueError(
            "Recorded import currently supports exact-stem released-insert discoveries."
        )
    request = load_request(root / "intent/request.json")
    exporter = runtime.producer_identity()
    index, limits = open_survey(root / "survey.sqlite", request=request, producer=source.producer)
    with index, TemporaryDirectory(prefix="hop-recorded-capture-") as temporary:
        if (
            SurveyEvaluationLimits.model_validate_json((root / "effort.json").read_bytes())
            != limits
        ):
            raise ValueError("Recorded effort disagrees with checkpoint execution limits.")
        pool = choices_from_admitted_index(
            index, limits, producer=source.producer, roots=bound_roots
        )
        if pool.query()["snapshot_digest"] != source.snapshot_digest:
            raise ValueError("Recorded source snapshot differs from its explicit contract.")
        # This internal adapter never leaves the read-only capture scope.
        choices = object.__new__(InsertDesignChoices)
        object.__setattr__(choices, "_directory", root)
        object.__setattr__(choices, "_resolution", resolution)
        object.__setattr__(choices, "_pool", pool)

        def retrieve(selection: Source, destination: Path) -> VerifiedConstructionBundle:
            return retrieve_admitted_witness(
                index, limits, selection=selection, destination=destination
            )

        origin = canonical_json_bytes(
            {
                "schema": "hop.recorded-capture-origin/v1",
                "source": source.model_dump(mode="json", by_alias=True),
                "exporter": exporter,
                "search_performed": False,
                "verification": (
                    "Read-only checkpoint admission and complete per-member molecular replay; "
                    "aggregate discovery replay remains separate."
                ),
            }
        )
        staging = Path(temporary) / "edition"
        frozen = freeze_choices(
            choices,
            staging,
            **options,
            _authority=CaptureAuthority(source.producer, retrieve, origin),
        )
        verify_source(root, source)
        for bound in bound_roots:
            bound.require_unchanged()
        if runtime.producer_identity() != exporter:
            raise ValueError("Exporter changed during recorded capture.")
        frozen.verify_integrity()
        publish_directory_files_create_only(
            DirectoryFiles(staging),
            output,
            protected_root=protected,
            verifier=lambda path: load_atlas_edition(path).verify_integrity(),
        )
    return load_atlas_edition(output)
