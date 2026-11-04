"""Indexed scheduling preserves the declared coverage ordering after every outcome."""

from hop_design.design.construction.surveys.schedule import CoverageSchedule
from hop_design.models.construction.surveys.targets import InterfaceTargetDomain


def test_every_declared_pair_gets_an_attempt_within_two_full_rosters():
    domain = InterfaceTargetDomain()
    schedule = CoverageSchedule(domain, last={}, ended=set(), supported=set())
    last = {}
    # All targets remain open: unsuccessful attempts must not leave most of
    # the 65,536-pair roster untouched while early pairs accumulate retries.
    for tick in range(130_816):
        target = schedule.pop()
        assert target is not None
        last[target] = last.get(target, -1) + 1
        schedule.update(target, step=last[target], supported=False, ended=False)
        if tick == 65_535:
            schedule = CoverageSchedule(domain, last=last, ended=set(), supported=set())
    assert len(last) == 65_536
    assert min(last.values()) >= 0


def test_failed_first_branches_get_compensating_attempts_before_all_new_pairs():
    domain = InterfaceTargetDomain(left_words=("AAAA", "CCCC"), right_words=("AAAA", "CCCC"))
    schedule = CoverageSchedule(domain, last={}, ended=set(), supported=set())
    visits = []
    last = {}
    for _ in range(4):
        target = schedule.pop()
        visits.append(target)
        last[target] = last.get(target, -1) + 1
        schedule.update(target, step=last[target], supported=False, ended=False)
    # The diagonal covers every word. Retry those targets with their next
    # permitted continuation before spreading the same failed first branch
    # across all off-diagonal pairs.
    assert visits == [0, 3, 0, 3]


def test_unknown_pairs_precede_supported_alternatives_within_the_same_wave():
    domain = InterfaceTargetDomain(left_words=("AAAA", "CCCC"), right_words=("AAAA", "CCCC"))
    schedule = CoverageSchedule(domain, last={0: 0, 3: 0}, ended=set(), supported={0, 3})
    assert schedule.pop() == 1
    schedule.update(1, step=0, supported=False, ended=False)
    assert schedule.pop() == 2
    schedule.update(2, step=0, supported=False, ended=False)
    assert schedule.pop() == 0
    schedule.update(0, step=1, supported=True, ended=False)
    assert schedule.pop() == 3


def test_compensation_waves_still_advance_every_pending_pair():
    domain = InterfaceTargetDomain(left_words=("AAAA", "CCCC"), right_words=("AAAA", "CCCC"))
    schedule = CoverageSchedule(domain, last={}, ended=set(), supported=set())
    counts = dict.fromkeys(range(4), 0)
    for _ in range(10):
        target = schedule.pop()
        counts[target] += 1
        schedule.update(target, step=counts[target] - 1, supported=False, ended=False)
    assert min(counts.values()) >= 2


def test_indexed_schedule_matches_exhaustive_priority_scan_and_restart():
    domain = InterfaceTargetDomain(left_words=("AAAA", "CCCC", "TTTT"))
    last, ended, supported = {}, set(), set()
    schedule = CoverageSchedule(domain, last=last, ended=ended, supported=supported)
    for tick in range(900):
        left = {domain.pair_at(t)[0] for t in supported}
        right = {domain.pair_at(t)[1] for t in supported}
        expected = min(
            (t for t in range(domain.pair_count) if t not in ended),
            key=lambda t: (
                last.get(t, -1) + 1 + (domain.coverage_rank(t) // domain.left_count).bit_length(),
                int(domain.pair_at(t)[0] in left) + int(domain.pair_at(t)[1] in right),
                int(t in supported),
                domain.coverage_rank(t),
            ),
            default=None,
        )
        assert schedule.pop() == expected
        if expected is None:
            break
        last[expected] = last.get(expected, -1) + 1
        complete, exhausted = tick % 11 == 0, tick % 4 == 0
        if complete:
            supported.add(expected)
        if exhausted:
            ended.add(expected)
        schedule.update(expected, step=last[expected], supported=complete, ended=exhausted)
        if tick == 425:
            schedule = CoverageSchedule(domain, last=last, ended=ended, supported=supported)


def test_unresolved_words_do_not_starve_supported_geometry_alternatives():
    domain = InterfaceTargetDomain(left_words=("AAAA", "CCCC"), right_words=("AAAA", "CCCC"))
    schedule = CoverageSchedule(domain, last={}, ended=set(), supported=set())
    counts = dict.fromkeys(range(4), 0)
    visits = []
    for _ in range(6):
        target = schedule.pop()
        visits.append(target)
        counts[target] += 1
        # Only AAAA/AAAA has support. All other targets remain unresolved,
        # and every target has further exact continuations available.
        schedule.update(target, step=counts[target] - 1, supported=target == 0, ended=False)
    assert visits == [0, 3, 3, 1, 2, 0]
    assert counts == {0: 2, 1: 1, 2: 1, 3: 2}


def test_missing_words_keep_priority_within_rounds_after_restart():
    domain = InterfaceTargetDomain(
        left_words=("AAAA", "CCCC", "TTTT"), right_words=("AAAA", "CCCC", "TTTT")
    )
    last, supported = {}, set()
    schedule = CoverageSchedule(domain, last=last, ended=set(), supported=supported)
    visits = []
    for position in range(9):
        target = schedule.pop()
        visits.append(target)
        last[target] = last.get(target, -1) + 1
        complete = target == 0
        if complete:
            supported.add(target)
        schedule.update(target, step=last[target], supported=complete, ended=False)
        if position == 4:
            schedule = CoverageSchedule(domain, last=last, ended=set(), supported=supported)
    assert visits == [0, 4, 8, 4, 8, 5, 1, 6, 0]
