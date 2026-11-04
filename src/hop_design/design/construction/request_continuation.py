"""Continue an authored request with exact replay-verified local selections."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from hop_design.serialization import canonical_json_bytes

from .execution.context import LocalSelection, describe_request_context, validate_design_id
from .execution.coverage import describe_local_coverage
from .local_choices import list_local_realizations
from .local_public import LocalNeighborhoodDiscovery, load_verified_local_neighborhood
from .product_request import prepare_construction_request
from .request_execution import (
    ConstructionRequestExecution,
    _compile_selected_request,
)


def _load_matching_local(
    path: str | Path, *, family: str, expected_request: dict[str, Any], realization_id: str
) -> LocalNeighborhoodDiscovery:
    local = load_verified_local_neighborhood(path)
    if local.family != family:
        raise ValueError(f"The selected {family} receipt has the wrong local family.")
    result = json.loads(local.json_bytes)
    request = result["neighborhood" if family == "foldback" else "discovery"]["request"]
    if canonical_json_bytes(request) != canonical_json_bytes(expected_request):
        raise ValueError(f"The {family} receipt does not derive from the construction source.")
    if (
        sum(choice.realization_id == realization_id for choice in list_local_realizations(local))
        != 1
    ):
        raise ValueError(f"The selected {family} realization was not found exactly once.")
    return local


def continue_construction_request(
    path: str | Path,
    *,
    design_id: str,
    foldback_path: str | Path,
    foldback_realization_id: str,
    basal_path: str | Path | None = None,
    basal_realization_id: str | None = None,
) -> ConstructionRequestExecution:
    """Compile caller-selected local witnesses under the unchanged authored request.

    Saved local files are replay-verified and must match the request's translated
    local inputs exactly. Payload, endpoint, terminal arms and material policies
    are taken only from that request; no witness or permission is substituted.
    """
    validate_design_id(design_id)
    prepared = prepare_construction_request(path)
    source, component, summary, context = describe_request_context(
        prepared, continuation="explicit-selection"
    )
    if source["basal"] is None:
        if basal_path is not None or basal_realization_id is not None:
            raise ValueError("Direct hairpin continuation must omit basal evidence.")
    elif basal_path is None or basal_realization_id is None:
        raise ValueError("PCR-bearing continuation requires both basal path and realization id.")
    foldback = _load_matching_local(
        foldback_path,
        family="foldback",
        expected_request=source["foldback"],
        realization_id=foldback_realization_id,
    )
    selection: LocalSelection = {
        "foldback": foldback,
        "foldback_realization_id": foldback_realization_id,
    }
    locals_by_family = {"foldback": foldback}
    selected_ids = {"foldback": foldback_realization_id}
    if basal_path is not None and basal_realization_id is not None:
        basal = _load_matching_local(
            basal_path,
            family="basal",
            expected_request=source["basal"],
            realization_id=basal_realization_id,
        )
        selection["basal"] = basal
        selection["basal_realization_id"] = basal_realization_id
        locals_by_family["basal"] = basal
        selected_ids["basal"] = basal_realization_id
    summary["selected_local_realizations"] = selected_ids
    summary["local_coverage"] = {
        family: describe_local_coverage(local, family) for family, local in locals_by_family.items()
    }
    with tempfile.TemporaryDirectory(prefix="hop-continuation-") as temporary:
        directory = Path(temporary)
        prepared.write(directory / "inputs")
        for family, local in locals_by_family.items():
            local.write(directory / family)
        return _compile_selected_request(
            directory,
            design_id=design_id,
            source=source,
            component=component,
            selection=selection,
            summary=summary,
            context=context,
        )
