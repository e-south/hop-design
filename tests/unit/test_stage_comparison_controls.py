"""Regional equality does not erase retained changes or unknown ancestry."""

from hop_design.design.construction.comparisons.controls import _facts, assess_stage_controls
from hop_design.models.construction.stage_controls import ResolvedStageControl
from hop_design.models.molecular_state import (
    EndChemistry,
    LineageStrand,
    MaterialBaseLineage,
    MolecularStrand,
)


def strand(sequence, end=EndChemistry.HYDROXYL):
    return MolecularStrand(
        strand_id="product",
        sequence=sequence,
        five_prime_end=end,
        three_prime_end=EndChemistry.HYDROXYL,
        lineage=tuple(
            MaterialBaseLineage(
                product_index=i,
                origin_id="source",
                origin_strand=LineageStrand.PRIMARY,
                origin_index=i,
            )
            for i in range(len(sequence))
        ),
    )


def test_loop_permission_does_not_allow_a_retained_substitution():
    labels = [["stem_primary", "loop", "loop", "stem_return"]]
    baseline = _facts((strand("AAAA"),), (), labels)
    changed_loop = _facts((strand("ATGA"),), (), labels)
    changed_stem = _facts((strand("CTGA"),), (), labels)
    assert baseline["non_loop_sequences"] == changed_loop["non_loop_sequences"]
    assert baseline["non_loop_sequences"] != changed_stem["non_loop_sequences"]
    control = ResolvedStageControl(
        property="non_loop_sequences", stage="endpoint", scope="set", members=("a", "b")
    )
    result = assess_stage_controls(
        (control,), {"a": {"endpoint": baseline}, "b": {"endpoint": changed_stem}}
    )
    assert result[0]["status"] == "different"
    assert result[0]["different_members"] == ["b"]


def test_unknown_region_is_unassessed_and_chemistry_remains_separate():
    known = _facts((strand("AA"),), (), [["loop", "stem_return"]])
    unknown = _facts((strand("AA", EndChemistry.PHOSPHATE),), (), [[None, "stem_return"]])
    assert unknown["non_loop_sequences"]["status"] == "unassessed"
    assert unknown["non_loop_pairing"]["status"] == "unassessed"
    assert unknown["terminal_chemistry"]["status"] == "assessed"
    assert unknown["terminal_chemistry"] != known["terminal_chemistry"]
    control = ResolvedStageControl(
        property="non_loop_sequences",
        stage="endpoint",
        scope="group",
        group="chosen",
        members=("a", "b"),
    )
    result = assess_stage_controls(
        (control,), {"a": {"endpoint": known}, "b": {"endpoint": unknown}, "other": {}}
    )
    assert result[0]["status"] == "unassessed"
    assert list(result[0]["unassessed_members"]) == ["b"]


def test_single_member_does_not_establish_shared_regional_control():
    control = ResolvedStageControl(
        property="non_loop_sequences", stage="endpoint", scope="set", members=("a",)
    )
    result = assess_stage_controls(
        (control,), {"a": {"endpoint": _facts((strand("AA"),), (), [["loop", "stem_return"]])}}
    )
    assert result[0]["status"] == "unassessed"
    assert result[0]["reason"] == "fewer_than_two_members"
