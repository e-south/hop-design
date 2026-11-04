"""Evaluate one survey continuation through the existing local and complete compilers."""

import tempfile
from pathlib import Path
from typing import Any

from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction.surveys.execution import SurveyEvaluationLimits
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ..design_authority import compile_design_from_local_realizations
from ..execution.cleanup import compile_request_candidate
from ..execution.context import LocalSelection
from ..execution.coverage import describe_local_coverage
from ..execution.outcome import describe_complete_outcome
from ..local_choices import list_local_realizations
from ..options.records import pair_design_id
from .admission.locals import LocalReceipts as LocalReceipts
from .branches import SurveyBranches
from .index import SurveyIndex
from .navigation.advance import advance, cursor_after, navigation_record
from .projection import witness_projection


def compile_continuation(
    index: SurveyIndex,
    locals_: LocalReceipts,
    branches: SurveyBranches,
    limits: SurveyEvaluationLimits,
    *,
    target: int,
    address: dict[str, Any],
) -> tuple[dict[str, Any], bytes, bool]:
    """Advance one recorded local pair, or one branch with no local witness.

    Declared local parts seek directly to candidate addresses. Expected branch
    contradictions are recorded; malformed inputs and unexpected errors raise.
    """
    branch, pair, page = address["branch"], address["pair"], address["page"]
    product = branches.product(target, branch=branch, limits=limits)
    plan = locals_.partitions.get(product)
    product = plan.product(product, page)
    coverage: dict[str, Any] = {}
    total, complete = 0, True
    if plan.foldback is not None:
        coverage["foldback_population"] = plan.foldback.facts()
    if plan.basal is not None:
        coverage["basal_population"] = plan.basal.facts()
    if plan.endpoint is not None:
        coverage["endpoint_population"] = plan.endpoint.facts()
    if plan.conflict is None and not plan.empty_candidates:
        source = product.construction_source()
        assert source.basal is not None
        foldback, basal = locals_.get(source.foldback), locals_.get(source.basal)
        fchoices, bchoices = list_local_realizations(foldback), list_local_realizations(basal)
        total = len(fchoices) * len(bchoices)
        coverage.update(
            {
                family: describe_local_coverage(receipt, family)
                for family, receipt in (("foldback", foldback), ("basal", basal))
            }
        )
        complete = all(
            receipt.termination_reason == "exhausted_domain" for receipt in (foldback, basal)
        )
    request_bytes = canonical_json_bytes(product)
    result = {
        "schema": "hop.interface-survey-evaluation/v2",
        "target": target,
        "branch": branch,
        "pair": pair,
        "page": page,
        "recorded_pairs": total,
        "local_coverage": coverage,
        "witnesses": [],
        "empty_basal_planes": [],
        "bundle": None,
        "projections": [],
        "product_request": sha256_digest(request_bytes),
        "limits": limits.model_dump(mode="json"),
        "rejection": None if plan.conflict is None else plan.conflict.diagnostic(),
    }
    if plan.basal is not None and plan.basal.parts == 0:
        certificate = locals_.proofs.record(target, branch, plan.basal)
        if certificate is not None:
            result["empty_basal_planes"].append(certificate)
    if total:
        if not 0 <= pair < total:
            raise ValueError("Survey continuation cursor lies outside the recorded local pairs.")
        fi, bi = divmod(pair, len(bchoices))
        selection: LocalSelection = {
            "foldback": foldback,
            "foldback_realization_id": fchoices[fi].realization_id,
            "basal": basal,
            "basal_realization_id": bchoices[bi].realization_id,
        }
        with tempfile.TemporaryDirectory(prefix="hop-survey-candidate-") as temporary:
            root = Path(temporary)
            design = compile_design_from_local_realizations(
                design_id=pair_design_id(
                    canonical_json_bytes(product),
                    fchoices[fi].realization_id,
                    bchoices[bi].realization_id,
                ),
                payload_sequence=product.stem_arm,
                endpoint=product.endpoint.value,
                **selection,
            )
            design.write(root / "design")
            (root / "source.json").write_bytes(canonical_json_bytes(source))
            construction = compile_request_candidate(
                root / "source.json",
                design_bundle_path=root / "design",
                selection=selection,
                cleanup=product.source_cleanup,
            )
        complete = complete and construction.status != "truncated"
        result["outcome"] = describe_complete_outcome(construction)
        if (
            branches.request.source_context_objective == "paired_scaffold_completions"
            and product.source_cleanup is None
        ):
            from .completion.source_sites import context_site_exclusions

            result["context_site_exclusions"] = context_site_exclusions(construction)
        result["witnesses"] = list(construction.materialized_realization_ids)
        result["projections"] = [
            witness_projection(
                construction, product.model_dump(mode="json", by_alias=True), identity
            )
            for identity in construction.materialized_realization_ids
        ]
        # Authority bytes only. No portrait, atlas, PDF or preparation export.
        files = {
            "construction-bundle.json": canonical_json_bytes(construction._bundle),
            **construction._artifacts,
        }
        result["bundle"] = {name: index.put_object(content) for name, content in files.items()}
    exhausted = address["exhaustion_proven"] and complete
    result["exhaustion_proven"] = exhausted
    return result, request_bytes, plan.conflict is not None or plan.empty_candidates


def _evaluate_one(
    index: SurveyIndex,
    locals_: LocalReceipts,
    branches: SurveyBranches,
    limits: SurveyEvaluationLimits,
    *,
    target: int,
    address: dict[str, Any],
) -> tuple[dict[str, Any], bytes, bool]:
    result, request_bytes, empty = compile_continuation(
        index, locals_, branches, limits, target=target, address=address
    )
    branch, pair, page = address["branch"], address["pair"], address["page"]
    total, exhausted = result["recorded_pairs"], result["exhaustion_proven"]
    if pair + 1 < total:
        result["next"] = {
            "branch": branch,
            "page": page,
            "pair": pair + 1,
            "exhaustion_proven": exhausted,
        }
    else:
        cursor = cursor_after(
            locals_.partitions, branches, limits, target, branch=branch, page=page
        )
        try:
            result["next"], result["navigation_nodes"] = advance(
                locals_.partitions,
                branches,
                limits,
                target,
                cursor,
                planes=locals_.proofs.planes(target),
                exhaustion_proven=exhausted,
            )
        except SequenceSetLimitError:
            # Preserve the completed molecular attempt. Admission of the next
            # geometry belongs to a resumable seek, not this evidence's validity.
            result["next"] = {
                "seek": cursor.model_dump(mode="json", by_alias=True),
                "exhaustion_proven": exhausted,
            }
            result["navigation_stop"] = "sequence_space_budget"
            result["navigation_nodes_complete"] = False
    return result, request_bytes, empty


def evaluate_step(
    index: SurveyIndex,
    locals_: LocalReceipts,
    branches: SurveyBranches,
    limits: SurveyEvaluationLimits,
    *,
    target: int,
    address: dict[str, Any],
) -> dict[str, Any]:
    """Batch certified empty admissions, stopping before a second compile attempt.

    The cap counts the terminal attempt too. Unresolved zero-result local searches
    and failed whole constructions remain individual recorded evaluations. Every
    skipped empty address retains its proof facts and is recomputed by replay.
    """
    if branches.request.source_context_objective == "paired_scaffold_completions":
        from .completion.batching import evaluate_completion_batch

        return evaluate_completion_batch(
            index, locals_, branches, limits, target=target, address=address
        )
    if "seek" in address:
        return navigation_record(
            locals_.partitions,
            branches,
            limits,
            target,
            address,
            planes=locals_.proofs.planes(target),
        )
    skipped: list[dict[str, Any]] = []
    for attempt in range(limits.continuation_batch_size):
        result, request_bytes, certified_empty = _evaluate_one(
            index, locals_, branches, limits, target=target, address=address
        )
        if (
            not certified_empty
            or result["next"] is None
            or "seek" in result["next"]
            or attempt + 1 == limits.continuation_batch_size
        ):
            index.put_object(request_bytes)
            result["continuations_examined"] = attempt + 1
            result["navigation_nodes"] = result.get("navigation_nodes", 0) + sum(
                preceding["navigation_nodes"] for preceding in skipped
            )
            result["navigation_nodes_complete"] = result.get(
                "navigation_nodes_complete", True
            ) and all(preceding["navigation_nodes_complete"] for preceding in skipped)
            if skipped:
                result["skipped_empty"] = skipped
            return result
        skipped.append(
            {
                key: result[key]
                for key in (
                    "branch",
                    "page",
                    "pair",
                    "local_coverage",
                    "rejection",
                    "next",
                    "exhaustion_proven",
                )
            }
            | {
                "empty_basal_planes": result.get("empty_basal_planes", []),
                "navigation_nodes": result.get("navigation_nodes", 0),
                "navigation_nodes_complete": result.get("navigation_nodes_complete", True),
            }
        )
        address = result["next"]
    raise AssertionError("A positive continuation cap always returns a terminal attempt.")
