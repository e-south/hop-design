from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.models.payload import DegeneratePayload, ExactPayload


def test_exact_payload_normalizes_and_derives_paired_arm() -> None:
    payload = ExactPayload(sequence="acgtg")

    assert payload.sequence == "ACGTG"
    assert payload.paired_sequence == "CACGT"
    assert payload.kind == "exact"


def test_degenerate_payload_stays_symbolic_and_derives_paired_arm() -> None:
    payload = DegeneratePayload(sequence="aryn")

    assert payload.sequence == "ARYN"
    assert payload.paired_sequence == "NRYT"
    assert payload.kind == "degenerate"


def test_exact_payload_rejects_degenerate_sequence() -> None:
    with pytest.raises(ValidationError, match="exact DNA"):
        ExactPayload(sequence="ACNT")


@pytest.mark.parametrize("payload_type", [ExactPayload, DegeneratePayload])
def test_payload_models_forbid_unknown_fields(
    payload_type: type[ExactPayload] | type[DegeneratePayload],
) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        payload_type(sequence="ACGT", paired_sequence="ACGT")


def test_payload_models_are_immutable() -> None:
    payload = ExactPayload(sequence="ACGT")

    with pytest.raises(ValidationError, match="frozen"):
        payload.sequence = "TGCA"  # type: ignore[misc]


@pytest.mark.parametrize("payload_type", [ExactPayload, DegeneratePayload])
def test_payload_models_reject_non_string_sequences(
    payload_type: type[ExactPayload] | type[DegeneratePayload],
) -> None:
    with pytest.raises(ValidationError, match="must be a string"):
        payload_type(sequence=123)  # type: ignore[arg-type]
