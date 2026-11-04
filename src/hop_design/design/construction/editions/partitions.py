"""Capture one atlas from independent jobs without joining their writable checkpoints."""

from collections.abc import Sequence
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from hop_design.design.runtime import producer_identity
from hop_design.export.publication import ProtectedRoot, publish_directory_files_create_only
from hop_design.models.construction.editions.manifest import AtlasEditionManifest
from hop_design.models.construction.surveys.query import InterfaceSurveyQuery
from hop_design.models.construction.variants.objective import DesignSearchObjective
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..intents.base import Source
from ..intents.execute import load_design_choices
from ..search.diversity import diversity_summary
from ..surveys.choices import _project
from .compact_capture import capture_member
from .partition_scope import admit_partitions, combined_metadata
from .reader import AtlasEdition, load_atlas_edition
from .retrieval import capture_retrieval
from .storage import DirectoryFiles


def combine_design_discoveries(
    request: Source,
    directories: Sequence[str | Path],
    destination: str | Path,
) -> AtlasEdition:
    """Freeze a complete disjoint request-grid partition into one compact edition.

    All jobs must use the same molecular permissions, producer and effort policy.
    Empty-result jobs still contribute coverage. Preparation retrieval replays each
    captured construction; aggregate negative replay remains a separate operation.
    Sources must be stopped while capturing. The result cannot resume discovery;
    continuation belongs to the original independent jobs.
    """
    output = Path(destination)
    if isinstance(directories, (str, bytes)) or not 2 <= len(directories) <= 256:
        raise ValueError("Combine between 2 and 256 discovery directories.")
    roots = tuple(Path(p) for p in directories)
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    if any(output.resolve().is_relative_to(root.resolve()) for root in roots):
        raise ValueError("Write the combined edition outside every discovery source.")
    producer = producer_identity()
    scope = admit_partitions(request, roots)
    origin, paths = combined_metadata(scope)
    identities = {path["materialized_realization_id"] for path in paths}
    if not identities:
        raise ValueError("No complete preparations are available to capture.")
    snapshot = sha256_digest(canonical_json_bytes(origin))
    # Each end pair belongs to exactly one source. Its original address stays in
    # the captured selection; the overview uses the parent grid's canonical address.
    addresses = {
        scope.request.targets.pair_at(i): i for i in range(scope.request.targets.pair_count)
    }
    combined_paths = []
    seen = set()
    for path in paths:
        identity = path["materialized_realization_id"]
        if identity in seen:
            continue
        seen.add(identity)
        pair = tuple(path["values"][f"{side}_end_word"] for side in ("left", "right"))
        combined_paths.append({**path, "address": {**path["address"], "target": addresses[pair]}})
    index = _project(
        scope.request, combined_paths, origin["coverage"], False, InterfaceSurveyQuery()
    )
    index.update(
        snapshot_digest=snapshot,
        query_digest=sha256_digest(canonical_json_bytes(InterfaceSurveyQuery())),
    )
    if objective := scope.effort.get("objective"):
        index["search_objective"] = diversity_summary(
            DesignSearchObjective.model_validate_json(canonical_json_bytes(objective)),
            combined_paths,
        )
    protected = tuple(ProtectedRoot.capture(root) for root in roots)
    with TemporaryDirectory(prefix="hop-partition-capture-") as temporary, ExitStack() as stack:
        staging = Path(temporary)
        members, descriptors = [], []
        captured: set[str] = set()
        for source in scope.sources:
            choices = source.choices
            retrieve = stack.enter_context(capture_retrieval(choices))
            for identity in sorted(
                {p["materialized_realization_id"] for p in source.answer["paths"]}
            ):
                if identity in captured:
                    raise ValueError("A preparation appears in distinct target partitions.")
                captured.add(identity)
                selection = choices.select(identity)
                relative = "members/" + sha256_digest(identity.encode()).removeprefix("sha256:")
                member = staging / relative
                member.mkdir(parents=True)
                (member / "selection.json").write_bytes(canonical_json_bytes(selection))
                descriptor = capture_member(retrieve, selection, member, identity)
                descriptors.append(descriptor.model_dump(mode="json"))
                members.append({"materialized_realization_id": identity, "directory": relative})
        files = {
            "choices.json": index,
            "resolution.json": scope.resolution,
            "capture-origin.json": {**origin, "producer": producer},
            "descriptors.json": {
                "schema": "hop.molecular-descriptor-index/v1",
                "snapshot_digest": snapshot,
                "preparations": descriptors,
            },
        }
        for name, value in files.items():
            (staging / name).write_bytes(canonical_json_bytes(value))
        artifacts = {
            name: {"sha256": sha256_digest(content), "bytes": len(content)}
            for name, content in DirectoryFiles(staging).items()
        }
        manifest = AtlasEditionManifest.model_validate_json(
            canonical_json_bytes(
                {
                    "schema": "hop.atlas-edition/v2",
                    "producer": producer,
                    "snapshot_digest": snapshot,
                    "members": members,
                    "artifacts": artifacts,
                }
            )
        )
        (staging / "edition.json").write_bytes(canonical_json_bytes(manifest))
        for source in scope.sources:
            current = load_design_choices(source.choices._directory).query()
            if current["snapshot_digest"] != source.answer["snapshot_digest"]:
                raise ValueError("A discovery advanced during capture; stop its writer first.")
        if producer_identity() != producer:
            raise ValueError("Producer changed during partition capture.")
        publish_directory_files_create_only(
            DirectoryFiles(staging),
            output,
            protected_root=protected,
            verifier=lambda path: load_atlas_edition(path).verify_integrity(),
        )
    return load_atlas_edition(output)
