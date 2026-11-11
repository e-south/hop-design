"""Shared role ink and ordered blue ramp for molecular and population views."""

BASAL = "#0073E6"
STEM = "#F39A22"
FOLDBACK = "#21A374"
NUMERIC_BLUE = ("#66A8ED", "#338DE9", "#0073E6", "#0056AA", "#0C2043")


def pale(color: str) -> str:
    """Keep category hue in quiet region headings on a white page."""
    return "#" + "".join(
        f"{round(int(color[i : i + 2], 16) * 0.18 + 255 * 0.82):02X}" for i in (1, 3, 5)
    )
