"""Shared molecular ink and type; sizes are native units, not page-fit scales."""

from hashlib import sha256

INK = "#182B34"
BACKBONE = "#334B58"
CONTACT = "#70838A"
BASE_SIZE = 20
ANNOTATION_SIZE = 48
TERMINAL_SIZE = 32
TITLE_SIZE = 56
FONT_FAMILY = "Helvetica, Arial, sans-serif"
REGION_COLORS = {"stem": "#B95300", "assembly": "#005F9E", "closing": "#006B52", "loop": "#006B52"}
REGION_OPACITY = 1
SITE_HALF_WIDTH = 18
CUT_HALF_WIDTH = 16
CUT_REACH = 38
LABEL_CLEARANCE = 6
SCENE_TOP = 160
STAGE_GAP = 0
SCENE_CLEARANCE = 18
PRIMER_CLEARANCE = 36
ADAPTER_APPROACH = 52
OPERATION_GAP = 28
OPERATION_ARROW_LENGTH = 64
OPERATION_STROKE = 5


def luminance(color: str) -> float:
    channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return sum(
        value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True)
    )


def contrast_ratio(a: str, b: str) -> float:
    low, high = sorted((luminance(a), luminance(b)))
    return (high + 0.05) / (low + 0.05)


def base_ink(region: str, tile_fill: str | None = None) -> str:
    """Choose small nucleotide ink against its actual opaque region or change tile."""
    background = (
        tile_fill if tile_fill and tile_fill != "none" else REGION_COLORS.get(region, "#AAB2B8")
    )
    return max((INK, "#FFFFFF"), key=lambda ink: contrast_ratio(ink, background))


def object_id(kind: str, *identity: str) -> str:
    """SVG-safe names distinguish repeated occurrences across processing states."""
    digest = sha256("\0".join(identity).encode()).hexdigest()[:16]
    return f"{kind}-{digest}"


def site_color(role: str) -> str:
    if role in {"basal_nick", "strand_exposure"}:
        return "#176487"
    if role == "foldback_nick":
        return "#146F54"
    return "#965A13"
