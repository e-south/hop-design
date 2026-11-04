"""Read execution limits, then admit the full request/producer-bound checkpoint."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.models.construction.surveys.request import InterfaceSurveyRequest

from ..index import MAX_RECORD_BYTES, SurveyIndex


def open_survey(
    path: Path, *, request: InterfaceSurveyRequest, producer: dict[str, str], read_only: bool = True
) -> tuple[SurveyIndex, SurveyEvaluationLimits]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Survey index must be an existing regular file.")
    try:
        with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as db:
            db.execute("PRAGMA trusted_schema = OFF")
            rows = db.execute("SELECT content FROM metadata").fetchall()
        if len(rows) != 1 or len(rows[0][0]) > MAX_RECORD_BYTES:
            raise ValueError("Invalid survey metadata.")
        limits = SurveyEvaluationLimits.model_validate_json(
            json.dumps(json.loads(rows[0][0])["evaluation_limits"])
        )
    except (sqlite3.Error, KeyError, TypeError, ValueError) as error:
        raise ValueError("Invalid survey checkpoint metadata.") from error
    return SurveyIndex.open(
        path,
        request=request,
        producer=producer,
        limits=limits.model_dump(mode="json"),
        read_only=read_only,
    ), limits
