"""Rebuild displayed options from request-bound, replayed complete constructions."""

import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from itertools import islice
from pathlib import Path
from typing import Any

from hop_design.design.source_documents import load_source_mapping
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.variants.objective import DesignSearchObjective
from hop_design.serialization import canonical_json_bytes

from ..execution.context import describe_request_context
from ..execution.coverage import describe_local_coverage
from ..families.member_admission import admit_member
from ..local_choices import list_local_realizations
from ..local_public import load_verified_local_neighborhood
from ..packets.capture import capture_packet, write_snapshot
from ..product_request import prepare_construction_request
from ..public import VerifiedConstructionBundle
from .order import ordered_pairs
from .records import (
    describe_candidate,
    describe_options,
    pair_design_id,
    require_budget,
    summarize_options,
)


def _equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"Options {label} disagrees with the verified request or result.")


def admit_options(root: Path) -> tuple[dict[str, Any], dict[str, VerifiedConstructionBundle]]:
    """Verify coverage, deterministic pair membership and every projected option."""
    recorded = load_source_mapping(root / "summary.json", max_bytes=64 * 1024 * 1024)
    budget = recorded["coverage"]["max_continuations"]
    require_budget(budget)
    start_pair = 0
    if recorded["schema"] == "hop.construction-options/v2":
        start_pair = recorded["pair_window"]["start"]
        if type(start_pair) is not int or start_pair < 1:
            raise ValueError("An options page requires a positive global candidate ordinal.")
    elif recorded["schema"] != "hop.construction-options/v1" or "pair_window" in recorded:
        raise ValueError("Unsupported options summary schema.")
    prepared = prepare_construction_request(root / "inputs/request.json")
    inputs = {
        "request.json": prepared.request_json_bytes,
        "construction.json": prepared.source_json_bytes,
    }
    source, _, context, _ = describe_request_context(prepared, continuation="explicit-selection")
    locals_, choices, coverage = {}, {}, {}
    for family in ("foldback", "basal"):
        if source[family] is None:
            continue
        local = load_verified_local_neighborhood(root / "locals" / family / "result.json")
        document = json.loads(local.json_bytes)
        container = document["neighborhood" if family == "foldback" else "discovery"]
        _equal(container["request"], source[family], f"{family} request")
        locals_[family] = local
        choices[family] = list_local_realizations(local)
        coverage[family] = describe_local_coverage(local, family)
    candidates, options = [], []
    receipts = {}
    objective = (
        DesignSearchObjective.model_validate_json(
            canonical_json_bytes(recorded["search_objective"])
        )
        if recorded.get("search_objective") is not None
        else None
    )
    pairs = ordered_pairs(choices, objective)
    total = len(choices["foldback"]) * len(choices.get("basal", (None,)))
    if start_pair > total:
        raise ValueError("Page start is beyond the recorded local-pair space.")
    with tempfile.TemporaryDirectory(prefix="hop-options-projection-") as temporary:
        for ordinal, (foldback, basal) in enumerate(
            islice(pairs, start_pair, start_pair + budget), start=start_pair
        ):
            prefix = f"candidates/{ordinal:04d}"
            proof = admit_member(
                root / prefix,
                str(ordinal),
                {},
                inputs,
                producer=recorded["producer"],
                continuation="explicit-selection",
                local_receipts=locals_,
            )
            receipt = proof.receipt
            if receipt is None:
                raise ValueError("An examined options candidate requires a complete outcome.")
            expected_pair = {"foldback": foldback.realization_id}
            if basal is not None:
                expected_pair["basal"] = basal.realization_id
            _equal(proof.outcome["selected_local_realizations"], expected_pair, "pair order")
            result = receipt._verified_source().result
            _equal(
                result.request.design.spec.design_id,
                pair_design_id(
                    prepared.request_json_bytes,
                    foldback.realization_id,
                    None if basal is None else basal.realization_id,
                ),
                "design identity",
            )
            for family, local in locals_.items():
                _equal(
                    canonical_json_bytes(getattr(result, f"{family}_authority")),
                    local.json_bytes,
                    "recorded local authority",
                )
            projected = describe_options(
                receipt, Path(temporary) / str(ordinal), prefix=prefix, ordinal=ordinal
            )
            for generated in (Path(temporary) / str(ordinal)).rglob("*"):
                if generated.is_file():
                    relative = generated.relative_to(Path(temporary) / str(ordinal))
                    _equal(
                        (root / prefix / relative).read_bytes(),
                        generated.read_bytes(),
                        "molecular projection",
                    )
            for option in projected:
                receipts[option["label"]] = receipt
            options.extend(projected)
            candidates.append(
                describe_candidate(receipt, proof.outcome, prefix=prefix, ordinal=ordinal)
            )
    summary = summarize_options(
        producer=recorded["producer"],
        request=prepared.request_json_bytes,
        context=context,
        coverage=coverage,
        total=total,
        budget=budget,
        candidates=candidates,
        options=options,
        objective=objective,
        start_pair=start_pair,
    )
    _equal(recorded, summary, "summary")
    return summary, receipts


@contextmanager
def captured_options(
    path: str | Path,
) -> Iterator[tuple[Path, dict[str, Any], dict[str, VerifiedConstructionBundle], ProtectedRoot]]:
    protected, files = capture_packet(path, schema="hop.construction-options-packet/v1")
    with tempfile.TemporaryDirectory(prefix="hop-options-admission-") as temporary:
        root = Path(temporary)
        write_snapshot(files, root)
        try:
            summary, receipts = admit_options(root)
        except (KeyError, TypeError, IndexError, AttributeError) as error:
            raise ValueError("Malformed saved options representation.") from error
        yield root, summary, receipts, protected
