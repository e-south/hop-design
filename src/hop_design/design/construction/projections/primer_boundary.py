"""Locate a recorded primer rejection on its examined source, not a failed product."""

import json
from typing import Any

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.complete.evaluation.context import (
    build_combination_context,
    prepare_context,
)
from hop_design.models.construction.complete.evaluation.result import CombinationEvaluation
from hop_design.models.construction.complete.evaluation_inputs import (
    derive_complete_payload_source_span,
    derive_linear_source_embedding,
)
from hop_design.models.construction.complete.request import ConstructionDiscoveryRequest
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.enzymes import EnzymeProvisioningPolicy


def primer_boundaries(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Project source geometry from an admitted result and replay its source-only gate.

    The caller owns complete-result admission. This projection does not establish a
    molecule identity, a complete route, or a universal bound on other preparations.
    """
    rows = [
        d
        for d in record["combination_dispositions"]
        if (d.get("preparation_constraint") or {}).get("code") == "primer-annealing-span-exceeded"
    ]
    if not rows:
        return []
    request = ConstructionDiscoveryRequest.model_validate_json(json.dumps(record["request"]))
    foldbacks = {
        f["foldback_realization_id"]: f for f in record["foldback_authority"]["realizations"]
    }
    basal_authority = record["basal_authority"]
    basals = (
        {b["basal_realization_id"]: b for b in basal_authority["realizations"]}
        if basal_authority
        else {}
    )
    foldback_policy = EnzymeProvisioningPolicy.model_validate_json(
        json.dumps(record["foldback_authority"]["neighborhood"]["request"]["enzyme_provisioning"])
    )
    basal_policy = (
        EnzymeProvisioningPolicy.model_validate_json(
            json.dumps(basal_authority["discovery"]["request"]["enzyme_provisioning"])
        )
        if basal_authority
        else None
    )
    projected = []
    for row in rows:
        foldback = FoldbackLocalRealization.model_validate_json(
            json.dumps(foldbacks[row["foldback_realization_id"]])
        )
        basal = (
            BasalRealizationRecord.model_validate_json(
                json.dumps(basals[row["basal_realization_id"]])
            )
            if row["basal_realization_id"]
            else None
        )
        evaluated = prepare_context(
            build_combination_context(
                request,
                foldback=foldback,
                basal=basal,
                foldback_policy=foldback_policy,
                basal_policy=basal_policy,
                source_context_sequence=row.get("source_context_sequence"),
                source_partition_plan=None,
            )
        )
        if (
            not isinstance(evaluated, CombinationEvaluation)
            or evaluated.preparation_constraint is None
            or evaluated.preparation_constraint.model_dump(mode="json")
            != row["preparation_constraint"]
            or evaluated.prefix is None
            or evaluated.source_return_arm is None
        ):
            raise ValueError(
                "Primer boundary must agree with the examined source-preparation gate."
            )
        embedding = derive_linear_source_embedding(
            foldback=foldback,
            prefix=evaluated.prefix,
            source_return_arm=evaluated.source_return_arm,
        )
        span = derive_complete_payload_source_span(foldback=foldback, embedding=embedding)
        diagnostic = row["preparation_constraint"]
        forward = ".forward_primer." in diagnostic["field"]
        length = len(embedding.source_sequence)
        required = diagnostic["requested"]
        available_span = [0, span.start.offset] if forward else [span.end.offset, length]
        if available_span[1] - available_span[0] != diagnostic["available"]:
            raise ValueError("Primer availability must equal the source flank length.")
        projected.append(
            {
                "status": "rejected_continuation",
                "scope": "examined_source_geometry_only",
                "result_id": record["result_id"],
                "ordinal": row["ordinal"],
                "foldback_realization_id": row["foldback_realization_id"],
                "basal_realization_id": row["basal_realization_id"],
                "primer": "forward" if forward else "reverse",
                "required_nt": required,
                "available_nt": diagnostic["available"],
                "source_sequence": embedding.source_sequence,
                "stem_span": [span.start.offset, span.end.offset],
                "available_span": available_span,
                "required_span": [0, required] if forward else [length - required, length],
                "diagnostic": diagnostic,
            }
        )
    return projected
