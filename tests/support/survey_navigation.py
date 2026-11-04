"""Visit the next molecular address across any navigation-only checkpoints."""

import json

from hop_design.design.construction.surveys.navigation.advance import advance, cursor_after
from hop_design.models.construction.surveys.navigation import SurveySeekCursor


def next_page(plans, branches, limits, target, *, branch, page):
    cursor = cursor_after(plans, branches, limits, target, branch=branch, page=page)
    while True:
        address, _ = advance(
            plans, branches, limits, target, cursor, planes=frozenset(), exhaustion_proven=True
        )
        if address is None:
            return None
        if "seek" not in address:
            return address["branch"], address["page"]
        cursor = SurveySeekCursor.model_validate_json(json.dumps(address["seek"]))
