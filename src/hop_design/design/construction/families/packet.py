"""Family packet identities on the shared atomic construction packet writer."""

from dataclasses import dataclass
from typing import ClassVar

from ..packets.publication import ConstructionPacket, SourceBoundConstructionPacket


@dataclass(frozen=True, init=False, repr=False)
class FamilyPacket(ConstructionPacket):
    """A family packet retains the established family inventory schema."""

    _packet_schema: ClassVar[str] = "hop.construction-family-packet/v1"


@dataclass(frozen=True, init=False, repr=False)
class SourceBoundFamilyPacket(SourceBoundConstructionPacket):
    """A family packet published outside its captured authorities."""

    _packet_schema: ClassVar[str] = "hop.construction-family-packet/v1"
