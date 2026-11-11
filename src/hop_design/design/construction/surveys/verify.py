"""Replay every committed continuation before treating indexed coverage as evidence."""

import tempfile
from pathlib import Path
from typing import Any

from hop_design.design.runtime import producer_identity

from .admission import open_survey
from .execute import load_request
from .index import SurveyIndex
from .replay import replay_evaluations


def verify_interface_survey(request_path: str | Path, index_path: str | Path) -> dict[str, Any]:
    """Recompute recorded positives, negatives, cursors and coverage; never extend the input."""
    request, producer = load_request(request_path), producer_identity()
    saved, limits = open_survey(Path(index_path), request=request, producer=producer)
    with (
        saved,
        tempfile.TemporaryDirectory(prefix="hop-survey-replay-") as directory,
        SurveyIndex.create(
            Path(directory) / "replay.sqlite",
            request=request,
            producer=saved.creator_producer if len(saved.creators) > 1 else producer,
            limits=limits.model_dump(mode="json"),
            format_version=2 if len(saved.creators) > 1 else 1,
        ) as replay,
    ):
        if len(saved.creators) > 1:
            replay.origins.import_history(saved.origins)
        return {
            "schema": "hop.interface-survey-verification/v1",
            **replay_evaluations(saved, replay, limits, producer=producer),
        }
