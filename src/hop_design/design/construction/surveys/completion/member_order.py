"""Different starting words inside admitted populations, with exact member addresses."""

import json
from hashlib import shake_256

from ..coordinates import interleaved_at
from .navigation import CompletionFrontierLimitError

type RepresentativeFrame = tuple[int, tuple[int, ...]]


def validate_frame(frame: RepresentativeFrame) -> None:
    if (
        not isinstance(frame, tuple)
        or len(frame) != 2
        or type(frame[0]) is not int
        or frame[0] < 0
        or not isinstance(frame[1], tuple)
        or not 1 <= len(frame[1]) <= 8
        or any(type(n) is not int or n < 0 for n in frame[1])
    ):
        raise ValueError("A representative frame needs a canonical target and geometry address.")


def foldback_member_ranks(
    sizes: tuple[int, ...],
    position: int,
    frame: RepresentativeFrame,
    *,
    maximum_items: int,
) -> list[int]:
    """Rotate each finite program, then recover its canonical interleaved rank.

    The target/geometry/program frame deterministically chooses the initial
    member. Cyclic traversal retains every admitted word exactly once; it does
    not claim uniform molecular sampling. Bound storage before sorting ranks.
    """
    if sum(size > position for size in sizes) > maximum_items:
        raise CompletionFrontierLimitError("Local program-page frontier bound reached.")
    ranks = []
    for program, size in enumerate(sizes):
        if position >= size:
            continue
        offset = _offset(size, program, frame)
        member = (position + offset) % size
        rank = sum(min(n, member) for n in sizes) + sum(n > member for n in sizes[:program])
        ranks.append(rank)
    return sorted(ranks)


def _offset(size: int, program: int, frame: RepresentativeFrame) -> int:
    encoded = json.dumps(
        ["foldback-representative/v1", frame, program], separators=(",", ":")
    ).encode()
    return int.from_bytes(shake_256(encoded).digest((size.bit_length() + 7) // 8 + 8), "big") % size


def foldback_member_position(sizes: tuple[int, ...], rank: int, frame: RepresentativeFrame) -> int:
    """Recover visitation depth without changing the member's canonical address."""
    validate_frame(frame)
    program, member = interleaved_at(sizes, rank)
    return (member - _offset(sizes[program], program, frame)) % sizes[program]
