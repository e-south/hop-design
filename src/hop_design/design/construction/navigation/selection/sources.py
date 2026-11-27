"""
--------------------------------------------------------------------------------
HOP Design
hop-design/src/hop_design/design/construction/navigation/selection/sources.py

Read selection documents and resolve saved-view or guided-sample receipts.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from pathlib import Path
from typing import cast

from hop_design.design.source_documents import load_source_mapping
from hop_design.models.construction.variants.sampling import GuidedSampleReceipt
from hop_design.serialization import canonical_json_bytes

from ...intents.base import Source
from ..types import ChoiceSource, Record
from .sampling import guided_sample


def selection_document(source: Source) -> Record:
    """Check the document shape before choosing its receipt validator."""
    raw = load_source_mapping(source) if isinstance(source, str | Path) else source
    if not isinstance(raw, dict):
        raise ValueError("Selection must be a JSON object.")
    if any(not isinstance(key, str) for key in raw):
        raise ValueError("Selection keys must be strings.")
    if not isinstance(raw.get("schema", ""), str):
        raise ValueError("Selection schema must be a string.")
    return raw


def selection_source(choices: ChoiceSource, source: Source) -> Record:
    """Replay guided receipts before admitting their ordinary selection."""
    raw = selection_document(source)
    if raw.get("schema", "").startswith("hop.atlas-view/"):
        return cast(Record, choices.restore_view(raw)["selection"])
    if raw.get("schema") != "hop.guided-sample/v1":
        return raw
    receipt = GuidedSampleReceipt.model_validate_json(canonical_json_bytes(raw))
    replay = guided_sample(
        choices,
        seed=receipt.seed,
        query=receipt.query,
        stage=receipt.stage,
        history=receipt.history,
        different_loop=receipt.strategy == "loop/v1",
    )
    if replay != receipt.model_dump(mode="json", by_alias=True):
        raise ValueError(
            "Guided sample receipt disagrees with its recorded pool or sampling inputs."
        )
    return receipt.selection
