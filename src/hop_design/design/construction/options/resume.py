"""Reuse a verified prefix while writing the next immutable options snapshot."""

from pathlib import Path
from typing import Any

from hop_design.export.publication import ProtectedRoot
from hop_design.models.construction.variants.objective import DesignSearchObjective

from ..public import VerifiedConstructionBundle
from .admission import captured_options


def resume_options(
    previous: str | Path,
    destination: Path,
    *,
    request: bytes,
    producer: dict[str, Any],
    budget: int,
    objective: DesignSearchObjective | None = None,
) -> tuple[dict[str, Any], dict[str, VerifiedConstructionBundle], ProtectedRoot]:
    """Replay prior outcomes and bind their exact local authorities before reuse."""
    with captured_options(previous) as (root, summary, receipts, protected):
        if summary.get("search_objective") != (
            objective.model_dump(mode="json") if objective else None
        ):
            raise ValueError("Continue options only under the same search objective.")
        if (root / "inputs/request.json").read_bytes() != request:
            raise ValueError("Continue options only under the same request and permissions.")
        if summary["producer"] != producer:
            raise ValueError("The HOP producer changed; start a new options discovery.")
        if summary["coverage"]["evaluated_pairs"] >= budget:
            raise ValueError("The continuation limit must exceed the already examined prefix.")
        for folder in ("locals", "candidates"):
            for source in (root / folder).rglob("*"):
                if source.is_file():
                    target = destination / source.relative_to(root)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.read_bytes())
        return summary, receipts, protected
