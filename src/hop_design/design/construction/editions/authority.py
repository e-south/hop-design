"""Check selected authority bytes and descriptor agreement without drawing them."""

from typing import TYPE_CHECKING

from hop_design.models.construction.complete.realization import MaterializedConstructionRealization
from hop_design.models.construction.variants.similarity import MolecularDescriptor

from ..navigation.molecular_descriptor import molecular_descriptor
from .comparison import captured_route
from .descriptors import descriptor_index

if TYPE_CHECKING:
    from .reader import AtlasEdition


def admitted_route(edition: "AtlasEdition", identity: str) -> MaterializedConstructionRealization:
    route = captured_route(edition, identity)
    check_descriptor(route, descriptor_index(edition).get(identity))
    return route


def check_descriptor(
    route: MaterializedConstructionRealization, expected: MolecularDescriptor
) -> None:
    actual = molecular_descriptor(route)
    if expected.retained_terminal_bases is None:
        # Older editions attest full tails, before retained-tail projection existed.
        # Compare every captured field without retroactively changing that scope.
        actual = actual.model_copy(update={"retained_terminal_bases": None})
    if actual != expected:
        raise ValueError("Captured descriptor disagrees with its complete molecular authority.")
