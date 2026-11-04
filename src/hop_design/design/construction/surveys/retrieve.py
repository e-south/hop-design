"""Rehydrate and replay one indexed witness; generate handoff only after selection."""

import shutil
import tempfile
from pathlib import Path
from typing import Any

from hop_design.design.runtime import producer_identity
from hop_design.export.publication import publish_directory_create_only
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.serialization import canonical_json_bytes

from ..public import (
    VerifiedConstructionBundle,
    project_construction_trajectory,
)
from .admission import open_survey
from .execute import load_request
from .index import SurveyIndex
from .selection import admit_selection
from .witness import recover_witness


def retrieve_interface_survey_witness(
    request_path: str | Path,
    index_path: str | Path,
    *,
    selection: str | Path | dict[str, Any],
    destination: str | Path,
) -> VerifiedConstructionBundle:
    """Recover one exact complete route under the unchanged survey request and producer."""
    request = load_request(request_path)
    path = Path(index_path)
    output = Path(destination)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to replace survey preparation: {output}")
    index, limits = open_survey(path, request=request, producer=producer_identity())
    with index:
        return retrieve_admitted_witness(index, limits, selection=selection, destination=output)


def retrieve_admitted_witness(
    index: SurveyIndex,
    limits: SurveyEvaluationLimits,
    *,
    selection: str | Path | dict[str, Any],
    destination: Path,
) -> VerifiedConstructionBundle:
    """Export one member of an admitted snapshot; its caller owns the reader lifetime."""
    output = destination
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Refusing to replace survey preparation: {output}")
    selected = admit_selection(selection, index.request, index)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        root = staging / "construction"
        root.mkdir()
        receipt, product, record = recover_witness(
            index,
            index.request,
            limits,
            target=selected.address.target,
            step=selected.address.step,
            root=root,
        )
        (staging / "selection.json").write_bytes(canonical_json_bytes(selected))
        (staging / "product-request.json").write_bytes(canonical_json_bytes(product))
        project_construction_trajectory(
            receipt, materialized_realization_id=record["witnesses"][0]
        ).write(staging / "preparation")
        publish_directory_create_only(staging, output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return receipt
