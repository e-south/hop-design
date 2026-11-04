"""A short requested prefix must not duplicate or remove ordinary target work."""

from hop_design.design.construction.surveys.schedule import CoverageSchedule
from hop_design.models.construction.surveys.targets import InterfaceTargetDomain


def test_preferred_target_runs_first_then_remains_in_ordinary_schedule():
    domain = InterfaceTargetDomain(left_words=("AAAA", "TTTT"), right_words=("AAAA", "TTTT"))
    schedule = CoverageSchedule(domain, last={}, ended=set(), supported=set())
    schedule.prefer_next(3)
    assert schedule.pop() == 3
    schedule.update(3, step=0, supported=False, ended=False)
    seen = []
    while (target := schedule.pop()) is not None:
        seen.append(target)
        schedule.update(target, step=1 if target == 3 else 0, supported=True, ended=True)
    assert sorted(seen) == [0, 1, 2, 3]
