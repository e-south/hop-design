"""DNA sequence validation and IUPAC-aware pairing."""

from __future__ import annotations

EXACT_DNA_ALPHABET = frozenset("ACGT")
IUPAC_DNA_ALPHABET = frozenset("ACGTRYSWKMBDHVN")

_IUPAC_BASES = {
    "A": frozenset("A"),
    "C": frozenset("C"),
    "G": frozenset("G"),
    "T": frozenset("T"),
    "R": frozenset("AG"),
    "Y": frozenset("CT"),
    "S": frozenset("CG"),
    "W": frozenset("AT"),
    "K": frozenset("GT"),
    "M": frozenset("AC"),
    "B": frozenset("CGT"),
    "D": frozenset("AGT"),
    "H": frozenset("ACT"),
    "V": frozenset("ACG"),
    "N": frozenset("ACGT"),
}

_IUPAC_COMPLEMENT = str.maketrans(
    {
        "A": "T",
        "C": "G",
        "G": "C",
        "T": "A",
        "R": "Y",
        "Y": "R",
        "S": "S",
        "W": "W",
        "K": "M",
        "M": "K",
        "B": "V",
        "D": "H",
        "H": "D",
        "V": "B",
        "N": "N",
    }
)


class SequenceValidationError(ValueError):
    """Raised when a sequence violates its declared DNA alphabet."""


def normalize_dna_sequence(raw: str, *, allow_degenerate: bool) -> str:
    """Normalize case and formatting whitespace, then validate a DNA sequence."""
    if not isinstance(raw, str):
        raise SequenceValidationError("DNA sequence must be a string.")

    normalized = "".join(character for character in raw.upper() if not character.isspace())
    if not normalized:
        raise SequenceValidationError("DNA sequence must contain at least one nucleotide.")

    alphabet = IUPAC_DNA_ALPHABET if allow_degenerate else EXACT_DNA_ALPHABET
    invalid = sorted(set(normalized) - alphabet)
    if invalid:
        description = "DNA IUPAC" if allow_degenerate else "exact DNA"
        invalid_text = ", ".join(invalid)
        raise SequenceValidationError(
            f"Sequence must use the {description} alphabet; invalid symbols: {invalid_text}."
        )
    return normalized


def reverse_complement_iupac(sequence: str) -> str:
    """Return the reverse complement of an exact or symbolic DNA sequence."""
    normalized = normalize_dna_sequence(sequence, allow_degenerate=True)
    return normalized.translate(_IUPAC_COMPLEMENT)[::-1]


def iupac_bases(symbol: str) -> frozenset[str]:
    """Return the concrete DNA bases represented by one IUPAC symbol."""
    if not isinstance(symbol, str):
        raise SequenceValidationError("DNA IUPAC symbol must be a string.")
    normalized = symbol.strip().upper()
    if len(normalized) != 1 or normalized not in _IUPAC_BASES:
        raise SequenceValidationError(f"Unknown DNA IUPAC symbol: {symbol!r}.")
    return _IUPAC_BASES[normalized]
