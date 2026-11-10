"""Place ordered route blocks without scaling molecules or inferring chronology."""

import math
from dataclasses import dataclass

from .primitives.style import SCENE_CLEARANCE, STAGE_GAP


@dataclass(frozen=True)
class BlockExtent:
    width: float
    height: float
    stem_anchor: float
    phase: str


@dataclass(frozen=True)
class BlockPosition:
    x: float
    y: float
    column: str


@dataclass(frozen=True)
class RoutePlacement:
    positions: tuple[BlockPosition, ...]
    width: float
    height: float
    continuation: tuple[float, float, float, float] | None


MARGIN = 32.0
GUTTER = 96.0
GAP = float(STAGE_GAP)
FINISH = frozenset({"hairpin_pcr_duplex", "clone_ready_duplex"})


def place_route(blocks: tuple[BlockExtent, ...]) -> RoutePlacement:
    """Two chronological columns, followed by centered copying/release states.

    Column breaks minimize the taller occupied column. Content determines spacing;
    sequence geometry and font sizes never change.
    """
    if not blocks:
        raise ValueError("A molecular route requires at least one block.")
    if any(
        not all(math.isfinite(v) for v in (b.width, b.height, b.stem_anchor))
        or b.width <= 0
        or b.height <= 0
        or not 0 <= b.stem_anchor <= b.width
        for b in blocks
    ):
        raise ValueError("Route blocks require finite positive bounds and an in-bounds anchor.")
    finish = next((i for i, b in enumerate(blocks) if b.phase in FINISH), len(blocks))
    if any(b.phase not in FINISH for b in blocks[finish:]):
        raise ValueError("Finishing states must follow the earlier route blocks.")
    early = blocks[:finish]

    def height(group: tuple[BlockExtent, ...]) -> float:
        return sum(b.height for b in group) + GAP * max(0, len(group) - 1)

    def width(group: tuple[BlockExtent, ...]) -> float:
        anchor = max((b.stem_anchor for b in group), default=0)
        return max((b.width + anchor - b.stem_anchor for b in group), default=0)

    split = min(
        range(1, len(early)),
        key=lambda i: (
            max(height(early[:i]), height(early[i:])),
            abs(height(early[:i]) - height(early[i:])),
        ),
        default=len(early),
    )
    columns = tuple(g for g in (early[:split], early[split:]) if g)
    widths = [width(g) for g in columns]
    upper_width = sum(widths) + GUTTER * max(0, len(columns) - 1)
    body_width = max(upper_width, max((b.width for b in blocks[finish:]), default=0))
    total_width = body_width + 2 * MARGIN
    upper_height = max((height(g) for g in columns), default=0)
    positions: list[BlockPosition] = []
    x = MARGIN + (body_width - upper_width) / 2
    continuation = None
    for column, (group, column_width) in enumerate(zip(columns, widths, strict=True)):
        y = MARGIN
        anchor = max(b.stem_anchor for b in group)
        for block in group:
            positions.append(BlockPosition(x + anchor - block.stem_anchor, y, str(column)))
            y += block.height + GAP
        if column == 0 and len(columns) == 2:
            continuation = (
                x + column_width / 2,
                y - GAP,
                x + column_width + GUTTER,
                MARGIN,
            )
        x += column_width + GUTTER
    # The column turn extends below its last block; reserve its bend plus the
    # same clearance used around ordinary operation arrows before the finish.
    y = MARGIN + upper_height + (24 + SCENE_CLEARANCE if columns and blocks[finish:] else 0)
    for block in blocks[finish:]:
        positions.append(BlockPosition((total_width - block.width) / 2, y, "full"))
        y += block.height + GAP
    bottom = max(p.y + b.height for p, b in zip(positions, blocks, strict=True))
    return RoutePlacement(tuple(positions), total_width, bottom + MARGIN, continuation)
