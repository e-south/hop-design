"""Shared region names and colors link teaching geometry to parameter axes."""

from .palette import BASAL, FOLDBACK, STEM, pale

REGIONS = {
    "assembly": ("Basal", pale(BASAL)),
    "closing": ("Foldback", pale(FOLDBACK)),
    "interfaces": ("Released insert", pale(STEM)),
    "whole": ("Construction", "#E3E7E8"),
}


def teaching_region(neighborhood: str) -> str:
    return (
        "closing"
        if neighborhood == "loop"
        else neighborhood
        if neighborhood in REGIONS
        else "whole"
    )
