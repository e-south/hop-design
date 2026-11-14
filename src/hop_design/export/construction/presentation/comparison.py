"""Display groups for the captured comparison; these do not define its distance."""

from .palette import BASAL, STEM, pale

COMPARISON_GROUPS = {
    "shape": {"label": "Geometry", "fill": "#E3EBE9"},
    "sequences": {"label": "Sequence", "fill": pale(BASAL)},
    "interfaces": {"label": "Ends", "fill": pale(STEM)},
}
