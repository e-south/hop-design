"""Exact bit-parallel comparisons retain the explanatory dynamic-program oracle."""

from itertools import product
from random import Random

from hop_design.design.construction.navigation.numerical.edit_pattern import EditPattern
from hop_design.design.construction.navigation.similarity import edit_distance


def test_bit_patterns_match_all_small_binary_words():
    words = tuple(tuple(word) for n in range(7) for word in product("AC", repeat=n))
    for word in words:
        pattern = EditPattern(word)
        for other in words:
            assert pattern.distance(other) == edit_distance(word, other)


def test_patterns_handle_long_words_and_structured_contacts_without_bit_truncation():
    rng = Random(23)
    alphabet = (("A", "T", "watson_crick"), ("G", "T", "wobble"), ("G", "C", "watson_crick"))
    for length in (0, 1, 63, 64, 65, 127, 129):
        word = tuple(rng.choices(alphabet, k=length))
        pattern = EditPattern(word)
        for other_length in (0, 2, 64, 130):
            other = tuple(rng.choices(alphabet, k=other_length))
            assert pattern.distance(other) == edit_distance(word, other)


def test_reused_pattern_is_unchanged_by_a_comparison():
    pattern = EditPattern(tuple("GATTACA"))
    assert pattern.distance(tuple("GACTATA")) == 2
    assert pattern.distance(tuple("GATTACA")) == 0
    assert pattern.distance(()) == 7
    assert pattern.distance(tuple("GACTATA")) == 2
