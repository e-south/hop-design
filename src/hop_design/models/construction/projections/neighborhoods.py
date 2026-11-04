"""One anatomy vocabulary for conditional choices, drawings and molecular picking."""

from hop_design.models.construction.variants.query import Neighborhood

NEIGHBORHOOD_REGIONS: dict[Neighborhood, frozenset[str]] = {
    "loop": frozenset({"loop"}),
    "closing": frozenset({"closing_primary", "closing_return"}),
    "assembly": frozenset({"open_primary", "open_return", "terminal_primary", "terminal_return"}),
    "stem": frozenset({"stem_primary", "stem_return"}),
    "interfaces": frozenset(),
}


def molecular_neighborhood(region: str | None) -> Neighborhood | None:
    if region in NEIGHBORHOOD_REGIONS:
        return region
    for neighborhood, regions in NEIGHBORHOOD_REGIONS.items():
        if region in regions:
            return neighborhood
    return "assembly" if region == "open" else None
