"""Bounded complete-route evaluation without a preselected reference or product."""

import json
import tempfile
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import ClassVar

from hop_design.design.runtime import producer_identity
from hop_design.export.construction.scaffold.options_report import options_report
from hop_design.export.construction.scaffold.options_text import render_options_text
from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.variants.objective import DesignSearchObjective

from ..execution.candidate import evaluate_candidate
from ..execution.context import describe_request_context
from ..execution.coverage import describe_local_coverage
from ..execution.feedback import DiscoveryCancelled, DiscoveryFeedback
from ..local_choices import LocalRealizationChoice, list_local_realizations
from ..local_public import discover_local_neighborhood, load_verified_local_neighborhood
from ..packets.publication import SourceBoundConstructionPacket
from ..product_request import prepare_construction_request
from ..public import VerifiedConstructionBundle
from ..verification import local_replay_scope
from .limits import check_generated_inventory, require_inventory_size
from .order import ordered_pairs
from .records import (
    describe_candidate,
    describe_options,
    pair_design_id,
    require_budget,
    summarize_options,
)
from .resume import resume_options


@dataclass(frozen=True, init=False, repr=False)
class ConstructionOptions(SourceBoundConstructionPacket):
    """A bounded inventory of complete molecular options; selection remains explicit."""

    _packet_schema: ClassVar[str] = "hop.construction-options-packet/v1"


def explore_construction_options(
    path: str | Path, *, max_continuations: int
) -> ConstructionOptions:
    """Evaluate a bounded prefix of recorded pairs, retaining all tested outcomes."""
    packet, _ = _explore_with_receipts(path, max_continuations=max_continuations)
    return packet


def _explore_with_receipts(
    path: str | Path,
    *,
    max_continuations: int,
    previous: str | Path | None = None,
    first_choices: int | None = None,
    objective: DesignSearchObjective | None = None,
    start_pair: int = 0,
    local_source: Path | None = None,
    feedback: DiscoveryFeedback | None = None,
) -> tuple[ConstructionOptions, dict[str, VerifiedConstructionBundle]]:
    """Keep admitted candidates available to this invocation's branch projection."""
    require_budget(max_continuations)
    if type(start_pair) is not int or start_pair < 0:
        raise ValueError("Page start must be a nonnegative candidate ordinal.")
    if previous is not None and (start_pair or local_source is not None):
        raise ValueError("Choose prefix continuation or a new page, not both.")
    if first_choices is not None and (type(first_choices) is not int or first_choices < 1):
        raise ValueError("first_choices must be a positive integer or None.")
    protected = ProtectedRoot.capture(path)
    producer = producer_identity()
    prepared = prepare_construction_request(path)
    source, _, context, _ = describe_request_context(prepared, continuation="explicit-selection")
    # Every candidate still verifies its own route and files. Shared local
    # proofs live only for this bounded evaluation, including interrupted runs.
    with (
        local_replay_scope(),
        tempfile.TemporaryDirectory(prefix="hop-options-") as temporary,
    ):
        root = Path(temporary)
        inputs = prepared.write(root / "inputs")
        candidates, options = [], []
        receipts: dict[str, VerifiedConstructionBundle] = {}
        roots: tuple[ProtectedRoot, ...] = (protected,)
        if local_source is not None:
            roots = (*roots, ProtectedRoot.capture(local_source))
            if (local_source / "inputs/request.json").read_bytes() != prepared.request_json_bytes:
                raise ValueError("Paged local source disagrees with the molecular request.")
        if previous is not None:
            prior, receipts, prior_root = resume_options(
                previous,
                root,
                request=prepared.request_json_bytes,
                producer=producer,
                budget=max_continuations,
                objective=objective,
            )
            candidates, options = prior["candidates"], prior["options"]
            roots = (*roots, prior_root)
        starting_choices = len(options)
        locations = {}
        choices: dict[str, tuple[LocalRealizationChoice, ...]] = {}
        coverage = {}
        for local in ("foldback", "basal"):
            if source[local] is None:
                continue
            if local_source is not None:
                receipt = load_verified_local_neighborhood(
                    local_source / "locals" / local / "result.json"
                )
                locations[local] = receipt.write(root / "locals" / local) / "result.json"
            elif previous is None:
                receipt = discover_local_neighborhood(inputs / f"{local}.json")
                locations[local] = receipt.write(root / "locals" / local) / "result.json"
            else:
                locations[local] = root / "locals" / local / "result.json"
                receipt = load_verified_local_neighborhood(locations[local])
            choices[local] = list_local_realizations(receipt)
            coverage[local] = describe_local_coverage(receipt, local)
            check_generated_inventory(root)
        total = len(choices["foldback"]) * len(choices.get("basal", (None,)))
        if start_pair > total:
            raise ValueError("Page start is beyond the recorded local-pair space.")
        cancelled = False
        for ordinal, (foldback, basal) in enumerate(
            islice(
                ordered_pairs(choices, objective),
                start_pair + len(candidates),
                start_pair + max_continuations,
            ),
            start=start_pair + len(candidates),
        ):
            if feedback is not None and feedback.stop_requested():
                if not candidates:
                    raise DiscoveryCancelled(
                        "Discovery cancelled before a new molecular snapshot. "
                        "Saved intent remains available to continue."
                    )
                cancelled = True
                break
            prefix = f"candidates/{ordinal:04d}"
            folder = root / prefix
            folder.mkdir(parents=True)
            # These exact inputs also support existing request-bound admission.
            for name in ("request.json", "construction.json"):
                (folder / name).write_bytes((inputs / name).read_bytes())
            continuation, verified = evaluate_candidate(
                inputs / "request.json",
                design_id=pair_design_id(
                    prepared.request_json_bytes,
                    foldback.realization_id,
                    None if basal is None else basal.realization_id,
                ),
                locations=locations,
                foldback=foldback,
                basal=basal,
                output=folder / "outcome",
            )
            result = json.loads(continuation.json_bytes)
            complete = describe_options(verified, folder, prefix=prefix, ordinal=ordinal)
            options.extend(complete)
            receipts.update({option["label"]: verified for option in complete})
            candidates.append(describe_candidate(verified, result, prefix=prefix, ordinal=ordinal))
            check_generated_inventory(root)
            if first_choices is not None and len(options) - starting_choices >= first_choices:
                break
        summary = summarize_options(
            producer=producer,
            request=prepared.request_json_bytes,
            context=context,
            coverage=coverage,
            total=total,
            # This packet records an ordinary, fully examined prefix. The caller
            # retains the requested effort and stopping policy separately.
            budget=len(candidates)
            if (first_choices is not None or cancelled) and candidates
            else max_continuations,
            candidates=candidates,
            options=options,
            objective=objective,
            start_pair=start_pair,
        )
        files = {
            f.relative_to(root).as_posix(): f.read_bytes() for f in root.rglob("*") if f.is_file()
        }
    files.update(options_report(summary, files))
    require_inventory_size(len(files), sum(map(len, files.values())))
    if producer_identity() != producer:
        raise ValueError("HOP producer changed during exploration.")
    packet = ConstructionOptions._create(files, summary, render_options_text(summary))
    object.__setattr__(packet, "_roots", roots)
    return packet, receipts
