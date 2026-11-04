"""Discovery advances useful preparations without changing the requested molecular space."""

from hop_design.design.construction.surveys import schedule as schedules
from hop_design.models.construction.surveys.targets import InterfaceTargetDomain


def test_discovery_can_finish_a_pending_preparation_before_visiting_every_end_word():
    schedule = schedules.DiscoverySchedule(
        InterfaceTargetDomain(), last={}, ended=set(), supported=set()
    )
    first = schedule.pop()
    schedule.update(first, step=0, supported=False, ended=False)
    assert schedule.pop() == first


def test_discovery_resumes_deterministically_and_does_not_starve_alternatives():
    domain = InterfaceTargetDomain(left_words=("AAAA", "CCCC"), right_words=("AAAA", "CCCC"))
    last, supported = {}, set()
    schedule = schedules.DiscoverySchedule(domain, last=last, ended=set(), supported=supported)
    for _ in range(1024):
        rebuilt = schedules.DiscoverySchedule(domain, last=last, ended=set(), supported=supported)
        target = schedule.pop()
        assert target == rebuilt.pop()
        last[target] = last.get(target, -1) + 1
        if target == 0:
            supported.add(target)
        schedule.update(target, step=last[target], supported=target in supported, ended=False)
    assert set(last) == {0, 1, 2, 3}
    assert min(last.values()) > 1


def test_discovery_gives_pending_work_a_useful_quantum_then_yields_to_new_options():
    schedule = schedules.DiscoverySchedule(
        InterfaceTargetDomain(), last={}, ended=set(), supported=set()
    )
    first = schedule.pop()
    for step in range(31):
        schedule.update(first, step=step, supported=False, ended=False)
        assert schedule.pop() == first
    schedule.update(first, step=31, supported=True, ended=False)
    assert schedule.pop() != first
