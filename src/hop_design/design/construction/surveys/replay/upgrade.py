"""Replay into a new producer-bound checkpoint while preserving the original."""

import hashlib
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from hop_design.design.runtime import producer_identity
from hop_design.design.source_documents import load_source_mapping
from hop_design.export.publication import publish_directory_create_only
from hop_design.serialization import canonical_json_bytes

from ..admission import open_survey
from ..execute import load_request
from ..index import SurveyIndex
from . import replay_evaluations
from .comparison import ProducerTransition


def _file_digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Survey checkpoint must be an existing regular file.")
    with path.open("rb") as handle:
        return "sha256:" + hashlib.file_digest(handle, "sha256").hexdigest()


def upgrade_interface_survey(
    request_path: str | Path,
    index_path: str | Path,
    *,
    source_producer: dict[str, str] | str | Path,
    destination: str | Path,
    max_checkpoint_bytes: int = 1_073_741_824,
    on_replayed: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Recompute a stopped checkpoint under this producer, refusing scientific drift.

    Callers must stop writers first and retain the original checkpoint/runtime.
    The destination is create-only. No caller may skip records or suppress a
    mismatch. A successful receipt establishes equivalence of the saved prefix,
    not equivalence of all future computations or versions.
    """
    path, output = Path(index_path), Path(destination)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to replace survey upgrade: {output}")
    if isinstance(source_producer, (str, Path)):
        source_producer = load_source_mapping(source_producer)
    if (
        not isinstance(source_producer, dict)
        or not source_producer
        or any(type(k) is not str or type(v) is not str for k, v in source_producer.items())
    ):
        raise ValueError("Provide the exact source producer mapping.")
    if type(max_checkpoint_bytes) is not int or max_checkpoint_bytes < 1_048_576:
        raise ValueError("Survey checkpoint storage limit must be at least 1048576 bytes.")
    source_producer = dict(source_producer)
    request, producer = load_request(request_path), producer_identity()
    before = _file_digest(path)
    saved, limits = open_survey(path, request=request, producer=source_producer)
    with saved:
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            checkpoint = staging / "survey.sqlite"
            with SurveyIndex.create(
                checkpoint,
                request=request,
                producer=producer,
                limits=limits.model_dump(mode="json"),
            ) as replay:
                replay.set_storage_limit(max_checkpoint_bytes)
                comparison = ProducerTransition(saved, replay, source_producer, producer)
                report = replay_evaluations(
                    saved,
                    replay,
                    limits,
                    producer=producer,
                    transition=comparison,
                    on_replayed=on_replayed,
                )
                if report["coverage"] != saved.coverage():
                    raise ValueError("Survey coverage changed during producer replay.")
            if before != _file_digest(path):
                raise ValueError(
                    "Source checkpoint changed during producer replay; stop its writers."
                )
            receipt = {
                "schema": "hop.interface-survey-upgrade/v1",
                "source_producer": source_producer,
                "producer": producer,
                "source_checkpoint_digest": before,
                "checkpoint_digest": _file_digest(checkpoint),
                "rebound_proof_references": comparison.rebound_proof_references,
                **report,
            }
            (staging / "request.json").write_bytes(canonical_json_bytes(request))
            (staging / "transition.json").write_bytes(canonical_json_bytes(receipt))
            publish_directory_create_only(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
    return receipt
