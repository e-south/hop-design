"""Figure geometry is budgeted in physical units before export."""

import pytest


def test_publication_contract_is_shared_and_cannot_silently_shrink_type():
    from hop_design.export.construction.presentation.print_contract import PUBLICATION

    assert PUBLICATION.width_pt == 504
    assert PUBLICATION.sequence_pt == 8
    assert PUBLICATION.annotation_pt >= 9
    assert 10 <= PUBLICATION.stage_title_pt <= 12
    assert PUBLICATION.units(PUBLICATION.annotation_pt, canvas_width=1200) * 504 / 1200 >= 9
    with pytest.raises(ValueError, match="positive"):
        PUBLICATION.units(9, canvas_width=0)
