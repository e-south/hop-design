"""Shared region names and colors link teaching geometry to parameter axes."""

REGIONS = {
    "assembly": ("Basal", "#BDD9EC"),
    "closing": ("Foldback", "#CDE1D2"),
    "interfaces": ("Released insert", "#E3D3B8"),
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
