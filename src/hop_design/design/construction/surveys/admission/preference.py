"""Store a bounded reference once; replay and continuation use captured objects."""

import os
import tempfile
from pathlib import Path
from typing import Any

from hop_design.design.runtime import replay_creation
from hop_design.models.construction.surveys.preference import SurveyPreparationReference
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest
from hop_design.serialization import sha256_digest

from ...complete.bundle import VerifiedConstructionBundle, load_verified_construction_bundle
from ..index import SurveyIndex


def create_survey_index(
    path: Path,
    *,
    request: InterfaceSurveyRequest,
    producer: dict[str, str],
    limits: dict[str, Any],
    maximum_bytes: int,
    files: dict[str, bytes],
) -> SurveyIndex:
    """Publish a new reference-bearing index only after every input is stored."""
    if request.preferred_preparation is None:
        if files:
            raise ValueError("Unrequested preparation inputs cannot enter a survey.")
        return SurveyIndex.create(path, request=request, producer=producer, limits=limits)
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    with tempfile.TemporaryDirectory(prefix=".hop-survey-input-", dir=path.parent) as directory:
        staged = Path(directory) / "survey.sqlite"
        with SurveyIndex.create(staged, request=request, producer=producer, limits=limits) as index:
            index.set_storage_limit(maximum_bytes)
            store_preference_files(index, files)
        # SQLite is closed before publication. A crash or failed import cannot
        # expose partial reference objects as an apparently resumable index.
        os.link(staged, path, follow_symlinks=False)
    return SurveyIndex.open(path, request=request, producer=producer, limits=limits)


def read_preference_files(root: Path, reference: SurveyPreparationReference) -> dict[str, bytes]:
    root = root.resolve(strict=True)
    files = {}
    for entry in reference.files:
        path = (root / entry.path).resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError("Preferred preparation file resolves outside its captured input.")
        if not path.is_file() or path.stat().st_size != entry.size_bytes:
            raise ValueError("Preferred preparation file size disagrees with its binding.")
        with path.open("rb") as stream:
            data = stream.read(entry.size_bytes + 1)
        if len(data) != entry.size_bytes:
            raise ValueError("Preferred preparation file size changed while reading.")
        if sha256_digest(data) != entry.digest:
            raise ValueError("Preferred preparation file digest disagrees with its binding.")
        files[entry.path] = data
    return files


def store_preference_files(index: SurveyIndex, files: dict[str, bytes]) -> None:
    reference = index.request.preferred_preparation
    if reference is None:
        if files:
            raise ValueError("Unrequested preparation inputs cannot enter a survey.")
        return
    if set(files) != {entry.path for entry in reference.files}:
        raise ValueError("Preferred preparation artifact set differs from its binding.")
    for entry in reference.files:
        data = files[entry.path]
        if len(data) != entry.size_bytes or sha256_digest(data) != entry.digest:
            raise ValueError("Preferred preparation artifact bytes differ from their binding.")
        index.put_object(data)


def load_preferred_preparation(index: SurveyIndex) -> VerifiedConstructionBundle:
    reference = index.request.preferred_preparation
    if reference is None:
        raise ValueError("This survey has no preferred preparation.")
    with tempfile.TemporaryDirectory(prefix="hop-preparation-preference-") as directory:
        root = Path(directory)
        for entry in reference.files:
            data = index.get_object(entry.digest)
            if len(data) != entry.size_bytes:
                raise ValueError("Preferred preparation object size disagrees with its binding.")
            path = root / entry.path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        with replay_creation(index.creator_producer["package_version"]):
            receipt = load_verified_construction_bundle(root)
    if (
        receipt.result_id != reference.result_id
        or reference.materialized_realization_id not in receipt.materialized_realization_ids
    ):
        raise ValueError("Preferred preparation identity disagrees with its replayed authority.")
    return receipt
