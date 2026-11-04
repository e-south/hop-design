"""Cross-target novelty counts requested classes, not unrelated word differences."""

from collections import Counter

from hop_design.design.construction.surveys.schedule import (
    DiscoverySchedule,
    InterfaceDiversitySchedule,
)
from hop_design.models.construction.surveys.targets import InterfaceTargetDomain

DOMAIN = InterfaceTargetDomain(left_words=("AAAA", "CCCC"), right_words=("AAAA", "CCCC"))
HINTS = {0: frozenset({"gap6"}), 1: frozenset({"gap6"}), 2: frozenset({"gap3"})}


def test_new_end_word_in_an_observed_gap_class_does_not_outrank_a_missing_gap():
    schedule = InterfaceDiversitySchedule(
        DOMAIN,
        last={},
        ended=set(),
        supported=set(),
        preferred=(1, 2),
        candidate_classes=HINTS,
        observed_classes=frozenset(),
    )
    assert schedule.pop() == 1
    schedule.observe_classes({"gap6"})
    schedule.update(1, step=0, supported=True, ended=False)
    assert schedule.pop() == 2


def test_unknown_candidates_remain_eligible_and_observations_are_bounded_to_hints():
    schedule = InterfaceDiversitySchedule(
        DOMAIN,
        last={},
        ended=set(),
        supported=set(),
        preferred=(1, 2),
        candidate_classes={0: frozenset({"gap6"}), 1: frozenset({"gap6"})},
        observed_classes=frozenset({"gap6"}),
    )
    schedule.observe_classes({f"other-{i}" for i in range(1000)})
    assert schedule.observed_classes == frozenset({"gap6"})
    visits = []
    for _ in range(600):
        target = schedule.pop()
        visits.append(target)
        schedule.update(target, step=visits.count(target) - 1, supported=False, ended=False)
    assert set(visits) == {0, 1, 2, 3}
    assert min(Counter(visits).values()) > 64


def test_mixed_success_failure_and_ending_resumes_across_two_quanta():
    last, ended, supported, observed = {}, set(), set(), set()

    def rebuild():
        return InterfaceDiversitySchedule(
            DOMAIN,
            last=last,
            ended=ended,
            supported=supported,
            preferred=(1, 2),
            candidate_classes=HINTS,
            observed_classes=frozenset(observed),
        )

    schedule = rebuild()
    visits = Counter()
    for _ in range(900):
        target = schedule.pop()
        assert target == rebuild().pop()
        assert target not in ended
        step = last.get(target, -1) + 1
        success = step % 5 == 0
        if success:
            supported.add(target)
            achieved = HINTS.get(target, frozenset({"unhinted"}))
            observed.update(achieved)
            schedule.observe_classes(achieved)
        finished = target == 2 and step == 90
        if finished:
            ended.add(target)
        last[target] = step
        schedule.update(target, step=step, supported=success, ended=finished)
        visits[target] += 1
    assert visits[2] == 91
    assert all(last[t] > 128 for t in (0, 1, 3))


def test_supported_targets_yield_to_later_interfaces_before_repeating_a_long_turn():
    words = ("AAAA", "CCCC", "GGGG", "TTTT")
    domain = InterfaceTargetDomain(left_words=words, right_words=words)
    last, supported = {}, set()

    def rebuild():
        return InterfaceDiversitySchedule(
            domain, last=last, ended=set(), supported=supported, preferred=tuple(range(16))
        )

    schedule = rebuild()
    visits = Counter()
    for _ in range(32):
        target = schedule.pop()
        assert target == rebuild().pop()
        visits[target] += 1
        last[target] = last.get(target, -1) + 1
        supported.add(target)
        schedule.update(target, step=last[target], supported=True, ended=False)
    assert set(range(7)) <= set(visits)
    assert visits[0] <= 16


def test_unresolved_interface_targets_keep_their_first_construction_effort():
    domain = InterfaceTargetDomain(left_words=("AAAA", "CCCC"), right_words=("AAAA", "CCCC"))
    ordinary = DiscoverySchedule(domain, last={}, ended=set(), supported=set())
    diverse = InterfaceDiversitySchedule(
        domain, last={}, ended=set(), supported=set(), preferred=()
    )
    last = {}
    for _ in range(300):
        target = ordinary.pop()
        assert diverse.pop() == target
        last[target] = last.get(target, -1) + 1
        for schedule in (ordinary, diverse):
            schedule.update(target, step=last[target], supported=False, ended=False)
