from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from hop_design.models.sequence import (
    SequenceValidationError,
    normalize_dna_sequence,
    reverse_complement_iupac,
)

IUPAC_DNA = "ACGTRYSWKMBDHVN"


@pytest.mark.parametrize(
    ("raw", "allow_degenerate", "expected"),
    [
        ("acgt", False, "ACGT"),
        (" ac gt\n", False, "ACGT"),
        ("acgt ryswkmbdhvn", True, IUPAC_DNA),
    ],
)
def test_normalize_dna_sequence_accepts_only_declared_representation_changes(
    raw: str,
    allow_degenerate: bool,
    expected: str,
) -> None:
    assert normalize_dna_sequence(raw, allow_degenerate=allow_degenerate) == expected


@pytest.mark.parametrize("raw", ["", " \n\t", "ACGU", "ACGZ", "AC-GT", "ACGT1"])
def test_normalize_dna_sequence_rejects_invalid_input(raw: str) -> None:
    with pytest.raises(SequenceValidationError):
        normalize_dna_sequence(raw, allow_degenerate=True)


def test_exact_normalization_rejects_ambiguity_symbols() -> None:
    with pytest.raises(SequenceValidationError, match="exact DNA"):
        normalize_dna_sequence("ACNT", allow_degenerate=False)


def test_normalization_rejects_non_string_input() -> None:
    with pytest.raises(SequenceValidationError, match="must be a string"):
        normalize_dna_sequence(42, allow_degenerate=True)  # type: ignore[arg-type]


def test_reverse_complement_covers_complete_dna_iupac_alphabet() -> None:
    assert reverse_complement_iupac(IUPAC_DNA) == "NBDHVKMWSRYACGT"


@given(st.text(alphabet=IUPAC_DNA, min_size=1, max_size=128))
def test_reverse_complement_is_an_involution(sequence: str) -> None:
    assert reverse_complement_iupac(reverse_complement_iupac(sequence)) == sequence
