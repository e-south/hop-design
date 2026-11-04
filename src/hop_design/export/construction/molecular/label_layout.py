"""A single collision domain for names, cuts, dimensions and material bindings."""

import json
from html import escape

from .primitives.style import LABEL_CLEARANCE
from .primitives.typography import text_width

Box = tuple[float, float, float, float]


def coalesce_horizontal(boxes: list[Box]) -> list[Box]:
    """Exact union of overlapping horizontal obstacles; retain every gap."""
    result: list[Box] = []
    for x, y, width, height in sorted(boxes, key=lambda b: (b[1], b[3], b[0])):
        if result:
            a, b, w, h = result[-1]
            if b == y and h == height and x <= a + w:
                result[-1] = (a, b, max(a + w, x + width) - a, h)
                continue
        result.append((x, y, width, height))
    return result


class LabelPlacer:
    def __init__(
        self,
        occupied: list[Box] | None = None,
        *,
        top: float = 40,
        horizontal_bounds: tuple[float, float] | None = None,
    ) -> None:
        self.occupied = list(occupied or ())
        self.top = top
        self.horizontal_bounds = horizontal_bounds

    def place(self, x: float, y: float, text: str, *, size: int = 12) -> Box:
        width, height = max(14, text_width(text, size) + 4), size + 5
        return self._place_box(x, y - size, width, height)

    def _place_box(self, x: float, top: float, width: float, height: float) -> Box:
        low, high = self.horizontal_bounds or (18, float("inf"))
        if width > high - low:
            raise ValueError("Molecular annotation exceeds its print window; wrap it first.")
        x = min(max(low, x), high - width)
        desired = max(self.top, top)
        # A bounded local search: original anchor, centered/left alternatives,
        # and nearby obstacle edges. Distant horizontal jumps are not candidates.
        xs = {x, max(low, x - width / 2), max(low, x - width)}
        reach = max(width, 144)
        for a, b, w, h in self.occupied:
            if b < desired + height + LABEL_CLEARANCE and b + h > desired - LABEL_CLEARANCE:
                xs.update(
                    v
                    for v in (a - width - LABEL_CLEARANCE, a + w + LABEL_CLEARANCE)
                    if low <= v <= high - width and abs(v - x) <= reach
                )
        candidates = []
        for left in xs:
            obstacles = [
                (b, h)
                for a, b, w, h in self.occupied
                if left < a + w + LABEL_CLEARANCE and left + width + LABEL_CLEARANCE > a
            ]
            ys = {desired, self.top}
            for b, h in obstacles:
                ys.update((b - height - LABEL_CLEARANCE, b + h + LABEL_CLEARANCE))
            for top in ys:
                if top < self.top or any(
                    top < b + h + LABEL_CLEARANCE and top + height + LABEL_CLEARANCE > b
                    for b, h in obstacles
                ):
                    continue
                candidates.append((left, top, width, height))
        if candidates:
            box = min(
                candidates,
                key=lambda q: ((q[0] - x) ** 2 + (q[1] - desired) ** 2, abs(q[0] - x), q[1], q[0]),
            )
            self.occupied.append(box)
            return box
        raise ValueError("Molecular annotation layout has no finite available boundary.")

    def block(self, x: float, y: float, lines: list[tuple[str, str, str, int]]) -> str:
        """Keep related lines together while reserving their combined extent."""
        width = max(text_width(label, size) + 4 for _, label, _, size in lines)
        height = sum(size + 5 for _, _, _, size in lines) + 8 * (len(lines) - 1)
        a, b, w, h = self._place_box(x, y - lines[0][3], width, height)
        rows = [f'<g data-annotation-block="true" data-drawing-box="{a} {b} {w} {h}">']
        for kind, label, color, size in lines:
            box = escape(json.dumps([a, b, text_width(label, size) + 4, size + 5]), quote=True)
            rows.append(
                f'<text data-label-kind="{kind}" data-label-box="{box}" '
                f'x="{a}" y="{b + size}" font-size="{size}" fill="{color}">'
                f"{escape(label)}</text>"
            )
            b += size + 13
        return "".join(rows) + "</g>"

    def text(self, kind: str, x: float, y: float, label: str, color: str, size: int = 12) -> str:
        a, b, width, height = self.place(x, y, label, size=size)
        leader = ""
        if abs(b + size - y) > 3 or abs(a - x) > 3:
            leader = (
                f'<path d="M{x},{y + 4} L{min(max(x, a), a + width)},'
                f'{min(max(y + 4, b), b + height)}" fill="none" '
                f'stroke="{color}" stroke-opacity=".22" stroke-width="1"/>'
            )
        box = escape(json.dumps([a, b, width, height]), quote=True)
        return (
            leader + f'<text data-label-kind="{kind}" data-label-box="{box}" '
            f'x="{a}" y="{b + size}" font-size="{size}" fill="{color}">'
            f"{escape(label)}</text>"
        )
