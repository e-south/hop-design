"""A failed profiling run must not leave its generated discovery behind."""

import runpy
from pathlib import Path

import pytest

from hop_design import construction

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("failure", [ValueError("no preparation"), KeyboardInterrupt()])
def test_lifecycle_benchmark_removes_partial_outputs(monkeypatch, failure):
    benchmark = runpy.run_path(str(ROOT / "scripts/benchmarks/design_lifecycle.py"))
    created = []

    def interrupted(request, output, **kwargs):
        output.mkdir()
        (output / "partial.json").write_text("{}")
        created.append(output.parent)
        raise failure

    monkeypatch.setattr(construction, "discover_designs", interrupted)
    with pytest.raises(type(failure)):
        benchmark["run_once"](Path("intent.json"), 4)
    assert len(created) == 1
    assert not created[0].exists()


def test_profile_breakdown_separates_work_without_double_counting_children():
    benchmark = runpy.run_path(str(ROOT / "scripts/benchmarks/design_lifecycle.py"))
    package = str(ROOT / "src/hop_design")
    # cProfile entries are primitive calls, total calls, own time, cumulative
    # time, callers. The parent's cumulative time includes the child's work.
    stats = {
        (package + "/design/construction/surveys/evaluate.py", 75, "compile_continuation"): (
            2,
            2,
            0.2,
            1.2,
            {},
        ),
        (package + "/kernel/construction/release_population.py", 19, "admit_release_population"): (
            4,
            4,
            1.0,
            1.0,
            {},
        ),
        (package + "/design/construction/navigation/similarity.py", 14, "edit_distance"): (
            8,
            8,
            0.3,
            0.3,
            {},
        ),
    }
    report = benchmark["profile_breakdown"](stats)
    assert report["self_seconds"] == pytest.approx(1.5)
    groups = report["groups"]
    assert groups["endpoint_constraints"]["self_seconds"] == 1.0
    assert groups["molecular_distances"]["calls"] == 8
    assert sum(row["self_seconds"] for row in groups.values()) == pytest.approx(1.5)
    assert report["entry_calls"]["complete_attempt"]["calls"] == 2
    assert report["entry_calls"]["complete_attempt"]["inclusive_seconds"] == 1.2
    assert str(ROOT) not in str(report)
