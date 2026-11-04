"""Admit immutable delta pages as one exact, contiguous hairpin choice snapshot."""

import json
import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any

from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.intents.execution import HairpinExecution
from hop_design.serialization import sha256_digest

from ..discovery.admission import CapturedDiscovery, captured_discovery
from ..discovery.explore import ScaffoldDiscovery
from ..discovery.molecules import stage_groups
from ..public import VerifiedConstructionBundle
from ..variants.admission import CapturedVariants, captured_generated_variants
from ..verification import local_replay_scope
from .hairpin_history import snapshot_paths, snapshot_source, validate_execution


def _prefix(record: dict[str, Any], prefix: str, fields: tuple[str, ...]) -> dict[str, Any]:
    value = deepcopy(record)
    for field in fields:
        value[field] = f"{prefix}/{value[field]}"
    return value


def _sources(root: Path, target: Path) -> list[Path]:
    """Legacy cumulative snapshots replace their prefix; delta pages extend it."""
    sources = [root / "scaffolds"] if (root / "scaffolds").exists() else []
    for snapshot in snapshot_paths(root):
        execution = HairpinExecution.model_validate_json((snapshot / "execution.json").read_bytes())
        source = snapshot / "scaffolds"
        if execution.schema_id.endswith("/v1"):
            sources = [source]
        else:
            sources.append(source)
        if snapshot == target:
            return sources
    raise ValueError("Selected hairpin page is not in this discovery history.")


@contextmanager
def _captured_page(
    source: Path,
    generated: tuple[ScaffoldDiscovery, dict[str, VerifiedConstructionBundle]] | None,
) -> Iterator[CapturedDiscovery]:
    if generated is not None:
        with captured_generated_variants(*generated, source) as captured:
            yield captured[0]
    else:
        with captured_discovery(source) as captured:
            yield captured


@contextmanager
def captured_hairpin_pages(
    target: Path,
    *,
    generated: tuple[ScaffoldDiscovery, dict[str, VerifiedConstructionBundle]] | None = None,
) -> Iterator[CapturedVariants]:
    """Every page replays independently; generation may reuse its own fresh last-page proof.

    Only this transient read view joins page files. Persisted snapshots contain
    new attempts once, and all older selections keep their original page chain.
    """
    target = target.resolve(strict=True)
    if target.parent.name != "hairpin-snapshots":
        raise ValueError("Hairpin page must belong to a discovery snapshot history.")
    discovery = target.parent.parent
    protected = ProtectedRoot.capture(discovery)
    execution = HairpinExecution.model_validate_json((target / "execution.json").read_bytes())
    selected_source, checked = snapshot_source(discovery, execution.snapshot_digest)
    if selected_source != target / "scaffolds" or checked != execution:
        raise ValueError("Selected hairpin page disagrees with its bound history.")
    sources = _sources(discovery, target)
    with (
        local_replay_scope(),
        tempfile.TemporaryDirectory(prefix="hop-hairpin-pages-") as temporary,
    ):
        root = Path(temporary)
        first = None
        combined = None
        options: list[dict[str, Any]] = []
        receipts: dict[str, VerifiedConstructionBundle] = {}
        count = 0
        total = None
        request_basis = None
        for index, source in enumerate(sources):
            # Both paths supply captured immutable files and complete route receipts.
            with _captured_page(
                source, generated if source == selected_source else None
            ) as captured:
                page_root, native, admitted, _ = captured
                request = json.loads((page_root / "intent/request.json").read_bytes())
                comparable = {
                    k: v for k, v in request.items() if k != "max_continuations_per_branch"
                }
                if request_basis is not None and comparable != request_basis:
                    raise ValueError(
                        "Hairpin pages changed their molecular permissions or objective."
                    )
                request_basis = comparable
                page = json.loads((page_root / "branches/0000/summary.json").read_bytes())
                coverage = page["coverage"]
                stop = count + coverage["evaluated_pairs"]
                if page.get("pair_window", {"start": 0, "stop": stop}) != {
                    "start": count,
                    "stop": stop,
                }:
                    raise ValueError("Hairpin pages omit or repeat a candidate window.")
                if total is not None and total != coverage["recorded_pairs"]:
                    raise ValueError("Hairpin pages disagree on the recorded local-pair space.")
                total, count = coverage["recorded_pairs"], stop
                if source != discovery / "scaffolds":
                    policy = HairpinExecution.model_validate_json(
                        (source.parent / "execution.json").read_bytes()
                    )
                    validate_execution(policy, page)
                prefix = f"pages/{index:04d}"
                # These are hard links to a private captured copy, never author files.
                shutil.copytree(page_root, root / prefix, copy_function=os.link)
                if first is None:
                    first = deepcopy(native)
                    shutil.copytree(page_root / "intent", root / "intent")
                elif native["producer"] != first["producer"]:
                    raise ValueError("Hairpin pages must share their producing implementation.")
                branch = _prefix(native["branches"][0], prefix, ("request", "report"))
                for failure in branch["failures"]:
                    failure["outcome"] = f"{prefix}/{failure['outcome']}"
                if combined is None:
                    combined = branch
                else:
                    if (
                        branch["local_coverage"] != combined["local_coverage"]
                        or branch["branch_id"] != combined["branch_id"]
                    ):
                        raise ValueError("Hairpin pages changed their local authority.")
                    combined["failures"].extend(branch["failures"])
                    combined["complete_preparations"] += branch["complete_preparations"]
                for original in native["options"]:
                    if original["label"] in receipts:
                        raise ValueError("Hairpin pages repeat a preparation address.")
                    option = _prefix(
                        original,
                        prefix,
                        ("portrait", "closing_drawing", "product_stages", "preparation"),
                    )
                    option["selection"] = {
                        k: f"{prefix}/{v}" for k, v in original["selection"].items()
                    }
                    options.append(option)
                    receipts[original["label"]] = admitted[original["label"]]
        if first is None or combined is None or total is None or count != execution.evaluated_pairs:
            raise ValueError("Hairpin page coverage disagrees with its execution history.")
        combined["coverage"] = {
            **combined["coverage"],
            "max_continuations": count,
            "evaluated_pairs": count,
            "unexamined_pairs": total - count,
            "completion": "recorded_pairs_examined" if count == total else "stopped_by_bound",
        }
        first["coverage"].update(
            evaluated_pairs=count,
            unexamined_pairs=total - count,
            exploration_complete=count == total
            and all(c["completion"] == "complete" for c in combined["local_coverage"].values()),
        )
        groups = stage_groups(options)
        first.update(
            branches=[combined],
            options=options,
            stage_groups=groups,
            molecules=groups[first["comparison_stage"]],
        )
        protected.require_unchanged()
        digest = sha256_digest((selected_source / "manifest.json").read_bytes())
        if digest != execution.snapshot_digest:
            raise ValueError("Selected hairpin page changed during admission.")
        yield (root, first, receipts, protected), None, protected, digest, None
