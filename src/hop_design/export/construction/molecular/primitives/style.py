"""Shared molecular ink and type; sizes are native units, not page-fit scales."""

from hashlib import sha256

INK = "#182B34"
BACKBONE = "#334B58"
CONTACT = "#70838A"
BASE_SIZE = 16
ANNOTATION_SIZE = 48
TERMINAL_SIZE = 32
TITLE_SIZE = 56
FONT_FAMILY = "Helvetica, Arial, sans-serif"
REGION_COLORS = {"stem": "#CE7171", "assembly": "#409AC0", "closing": "#55A47A", "loop": "#55A47A"}
REGION_OPACITY = 0.78
SITE_HALF_WIDTH = 18
CUT_HALF_WIDTH = 16
CUT_REACH = 38
LABEL_CLEARANCE = 6
SCENE_TOP = 160
STAGE_GAP = 0
SCENE_CLEARANCE = 24
PRIMER_CLEARANCE = 44
ADAPTER_APPROACH = 52
OPERATION_GAP = 28
OPERATION_ARROW_LENGTH = 96


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
