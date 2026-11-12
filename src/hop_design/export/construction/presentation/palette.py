"""Validated molecular colors; population color encodings are independent."""

import re
from dataclasses import dataclass


def rgb_channels(color: str) -> tuple[int, int, int]:
    """Accept one complete opaque SVG hex color, never a partial parse."""
    if not isinstance(color, str) or re.fullmatch(r"#[0-9a-fA-F]{6}", color) is None:
        raise ValueError("Use a six-digit hex color, for example #85BCF3.")
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


@dataclass(frozen=True, slots=True)
class MolecularPalette:
    name: str
    basal: str
    stem: str
    foldback: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("A molecular palette needs a nonempty name.")
        for color in (self.basal, self.stem, self.foldback):
            rgb_channels(color)


MOLECULAR_PALETTE = MolecularPalette("compass-pastel", "#85BCF3", "#F9CF95", "#94D3BC")
BASAL, STEM, FOLDBACK = (
    MOLECULAR_PALETTE.basal,
    MOLECULAR_PALETTE.stem,
    MOLECULAR_PALETTE.foldback,
)
NUMERIC_BLUE = ("#66A8ED", "#338DE9", "#0073E6", "#0056AA", "#0C2043")
POPULATION_ACCENT = NUMERIC_BLUE[2]


def annotation_ink(color: str) -> str:
    """Keep recognition labels and bands in their region's darker hue."""
    return "#" + "".join(f"{round(channel * 0.48):02X}" for channel in rgb_channels(color))


def pale(color: str) -> str:
    """Keep category hue in quiet region headings on a white page."""
    return "#" + "".join(
        f"{round(channel * 0.18 + 255 * 0.82):02X}" for channel in rgb_channels(color)
    )
