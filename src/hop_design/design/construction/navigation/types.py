"""Shared presentation types for admitted choices and captured evidence."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..editions.reader import AtlasEdition
    from ..intents.base import DesignChoices


type ChoiceSource = DesignChoices | AtlasEdition
type Record = dict[str, Any]
type Camera = tuple[float, float, float, float] | None
