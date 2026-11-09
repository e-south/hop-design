"""Recognition obligations constrain shared variables before relational expansion."""

import itertools

from hop_design.kernel.construction import release_constraints as module
from hop_design.kernel.construction.foldback.domains import SequenceVariable as Variable
from hop_design.kernel.construction.release_constraints import _window_masks
from hop_design.models.sequence import iupac_bases, reverse_complement_iupac

BASES = tuple("ACGT")


def test_short_site_normalizes_repeated_domains_once(monkeypatch):
    calls = []

    def counted(bases):
        calls.append(None)
        return sorted(bases)

    monkeypatch.setattr(module, "sorted", counted, raising=False)
    domains = (tuple("TGCAA"),) * 128
    masks = _window_masks(domains, (Variable(0), Variable(127, True)), ((0, "RT"),))
    assert masks == (("A", "G"),) + (BASES,) * 126 + (("A",),)
    assert len(calls) == 1
    assert domains == (tuple("TGCAA"),) * 128


def test_complemented_aliases_intersect_the_same_variable():
    expression = (Variable(0), Variable(0, True), Variable(1))
    assert _window_masks((BASES, BASES), expression, ((0, "RTY"),)) == (
        ("A",),
        ("C", "T"),
    )
    assert _window_masks((BASES, BASES), expression, ((0, "ATN"), (0, "C"))) is None


def test_impossible_auxiliary_position_rejects_even_outside_the_visible_window():
    assert _window_masks((BASES, ()), (Variable(0),), ((0, "A"),)) is None


def test_two_flanks_jointly_constrain_the_same_underlying_base():
    masks = _window_masks((BASES,), (Variable(0),), ((0, "R"),))
    assert masks == (("A", "G"),)
    assert _window_masks(masks, (Variable(0, True),), ((0, "T"),)) == (("A",),)
    assert _window_masks(masks, (Variable(0, True),), ((0, "A"),)) is None


def test_literal_conflicts_and_out_of_frame_windows_are_empty():
    expression = ("A", Variable(0))
    assert _window_masks((BASES,), expression, ((0, "C"),)) is None
    assert _window_masks((BASES,), expression, ((-1, "A"),)) is None
    assert _window_masks((BASES,), expression, ((2, "A"),)) is None


def test_small_literal_oracle_preserves_shared_and_complemented_copies():
    expression = (Variable(0), Variable(1, True), Variable(0, True), "G", Variable(2))
    choices = tuple(bases for count in range(5) for bases in itertools.combinations(BASES, count))
    for first, second, word in itertools.product(
        choices, choices, ("NNN", "RNT", "CGG", "ATG", "YYY", "AAA")
    ):
        domains = (first, second, ("G", "T"))
        expected = set()
        for bases in itertools.product(*domains):
            literal = "".join(
                item
                if isinstance(item, str)
                else reverse_complement_iupac(bases[item.index])
                if item.complemented
                else bases[item.index]
                for item in expression
            )
            if all(
                base in iupac_bases(symbol) for base, symbol in zip(literal[:3], word, strict=True)
            ):
                expected.add(bases)
        masks = _window_masks(domains, expression, ((0, word),))
        obtained = set() if masks is None else set(itertools.product(*masks))
        assert obtained == expected
