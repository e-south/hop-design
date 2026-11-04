"""Capture admitted choices through their existing selection and handoff operations."""

from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from hop_design.design import runtime
from hop_design.export.publication import ProtectedRoot, publish_directory_files_create_only
from hop_design.models.construction.editions.manifest import AtlasEditionManifest
from hop_design.models.construction.variants.similarity import MolecularDistancePolicy
from hop_design.serialization import canonical_json_bytes, sha256_digest

from .retrieval import RetrievePreparation, capture_retrieval
from .storage import DirectoryFiles

if TYPE_CHECKING:
    from ..intents.base import Source
    from ..navigation.types import ChoiceSource
    from .reader import AtlasEdition


@dataclass(frozen=True)
class CaptureAuthority:
    """Internal authority supplied only after an explicit recorded-source admission."""

    producer: dict[str, str]
    retrieve: RetrievePreparation
    origin: bytes


def freeze_choices(
    choices: "ChoiceSource",
    destination: str | Path,
    *,
    query: "Source | None" = None,
    identities: tuple[str, ...] | None = None,
    include_landscape: bool = False,
    compact: bool = False,
    distance_policy: "MolecularDistancePolicy | Source | None" = None,
    comparison_weights: tuple[float, float, float] | None = None,
    _authority: CaptureAuthority | None = None,
) -> "AtlasEdition":
    from .reader import AtlasEdition, load_atlas_edition

    if distance_policy is not None and not isinstance(distance_policy, MolecularDistancePolicy):
        from hop_design.design.source_documents import load_source_mapping

        mapping = (
            load_source_mapping(Path(distance_policy))
            if isinstance(distance_policy, (str, Path))
            else distance_policy
        )
        distance_policy = MolecularDistancePolicy.model_validate_json(canonical_json_bytes(mapping))

    output = Path(destination)
    if output.resolve().is_relative_to(choices._directory.resolve()):
        raise ValueError("Write exports outside the protected choice directory.")
    if type(include_landscape) is not bool:
        raise ValueError("include_landscape must be a Boolean.")
    if type(compact) is not bool:
        raise ValueError("compact must be a Boolean.")
    new_comparison = distance_policy is not None or comparison_weights is not None
    if new_comparison and not include_landscape:
        raise ValueError("An explicit comparison requires include_landscape=True.")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to replace atlas edition: {output}")
    source = choices.query(query)
    available = {p["materialized_realization_id"]: p for p in source["paths"] if p["matches"]}
    wanted = tuple(sorted(available)) if identities is None else identities
    if not wanted or len(set(wanted)) != len(wanted) or not set(wanted) <= available.keys():
        raise ValueError("Choose distinct, matching complete preparations to freeze.")
    executing_producer = runtime.producer_identity()
    original_producer = (
        _authority.producer
        if _authority is not None
        else choices.producer
        if isinstance(choices, AtlasEdition)
        else executing_producer
    )
    saved = (
        choices.landscape()
        if isinstance(choices, AtlasEdition)
        and "landscape.json" in choices._store.manifest.artifacts
        and (compact or include_landscape)
        else None
    )
    recorded_descriptors = {}
    if saved is not None:
        recorded_descriptors = {row.identity: row for row in saved.preparations}
    elif compact and isinstance(choices, AtlasEdition) and choices._store.compact:
        from .descriptors import edition_descriptors

        recorded_descriptors = {row.identity: row for row in edition_descriptors(choices)}
    protected = ProtectedRoot.capture(choices._directory)
    with (
        TemporaryDirectory(prefix="hop-atlas-capture-") as temporary,
        (
            nullcontext(_authority.retrieve)
            if _authority is not None
            else capture_retrieval(choices)
        ) as retrieve,
    ):
        root = Path(temporary)
        index = {
            **source,
            "paths": [available[identity] for identity in sorted(wanted)],
            "edition_scope": {
                "captured_preparations": len(wanted),
                "source_matching_preparations": source["matching_preparations"],
                "source_snapshot_digest": source["snapshot_digest"],
            },
        }
        (root / "choices.json").write_bytes(canonical_json_bytes(index))
        (root / "resolution.json").write_bytes(canonical_json_bytes(choices.resolution))
        if _authority is not None:
            (root / "capture-origin.json").write_bytes(_authority.origin)
        elif (
            isinstance(choices, AtlasEdition)
            and "capture-origin.json" in choices._store.manifest.artifacts
        ):
            (root / "capture-origin.json").write_bytes(choices._store.read("capture-origin.json"))
        members = []
        descriptors = []
        for identity in sorted(wanted):
            selected = choices.select(available[identity], query=query)
            key = sha256_digest(identity.encode()).removeprefix("sha256:")
            relative = f"members/{key}"
            member = root / relative
            member.mkdir(parents=True)
            (member / "selection.json").write_bytes(canonical_json_bytes(selected))
            if compact:
                from .compact_capture import capture_member

                descriptors.append(
                    capture_member(
                        retrieve,
                        selected,
                        member,
                        identity,
                        recorded_descriptor=recorded_descriptors.get(identity),
                    )
                )
            else:
                choices.atlas(selected).write(member / "atlas", print_pages=False)
                receipt = retrieve(selected, member / "materials")
                if receipt.materialized_realization_ids != (identity,):
                    raise ValueError(
                        "Captured material handoff disagrees with the selected preparation."
                    )
            members.append({"materialized_realization_id": identity, "directory": relative})
        if compact:
            (root / "descriptors.json").write_bytes(
                canonical_json_bytes(
                    {
                        "schema": "hop.molecular-descriptor-index/v1",
                        "snapshot_digest": source["snapshot_digest"],
                        "preparations": [item.model_dump(mode="json") for item in descriptors],
                    }
                )
            )
        if include_landscape:
            from ..navigation.landscape_source import molecular_descriptors
            from ..navigation.similarity_layout import build_molecular_landscape

            complete = {p["materialized_realization_id"] for p in choices.query()["paths"]}
            rows = (
                tuple(descriptors)
                if compact
                else tuple(
                    p
                    for p in (
                        saved.preparations if saved is not None else molecular_descriptors(choices)
                    )
                    if p.identity in wanted
                )
            )
            same_descriptors = saved is not None and {p.identity: p for p in rows} == {
                p.identity: p for p in saved.preparations
            }
            if saved is not None and same_descriptors and not new_comparison:
                landscape = saved
            elif not compact and complete == set(wanted) and not new_comparison:
                landscape = choices.landscape()
            else:
                landscape = build_molecular_landscape(
                    rows,
                    snapshot_digest=source["snapshot_digest"],
                    distance_policy=distance_policy
                    if distance_policy is not None
                    else (saved.basis.distance_policy if saved is not None else None),
                    weights=comparison_weights
                    if comparison_weights is not None
                    else (saved.basis.weights if saved is not None else (1, 1, 1)),
                )
            (root / "landscape.json").write_bytes(canonical_json_bytes(landscape))
        artifacts = {}
        for name, content in DirectoryFiles(root).items():
            artifacts[name] = {"sha256": sha256_digest(content), "bytes": len(content)}
        manifest = AtlasEditionManifest.model_validate_json(
            canonical_json_bytes(
                {
                    "schema": "hop.atlas-edition/v2" if compact else "hop.atlas-edition/v1",
                    "producer": original_producer,
                    "snapshot_digest": source["snapshot_digest"],
                    "members": members,
                    "artifacts": artifacts,
                }
            )
        )
        (root / "edition.json").write_bytes(canonical_json_bytes(manifest))
        if runtime.producer_identity() != executing_producer:
            raise ValueError("Producer changed while capturing the atlas edition.")

        def verify_capture(directory: Path) -> None:
            captured = load_atlas_edition(directory)
            if compact:
                captured.verify_integrity()

        # Mapping reads each file on demand; complete route packets are not retained together.
        publish_directory_files_create_only(
            DirectoryFiles(root),
            output,
            protected_root=protected,
            verifier=verify_capture,
        )
    return load_atlas_edition(output)
