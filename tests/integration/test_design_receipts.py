"""Generated results reuse invocation-local proofs; reopening verifies afresh."""

from hop_design import construction
from hop_design.design.construction.complete import bundle
from hop_design.design.construction.execution import candidate
from tests.unit.test_construction_intent import STEM


def test_generated_hairpin_choices_do_not_replay_their_just_verified_candidates(
    tmp_path, monkeypatch
):
    original = bundle.load_verified_construction_bundle
    original_binding = bundle.bind_published_compilation
    loads = []
    bindings = []

    def observed(*args, **kwargs):
        loads.append(args[0])
        return original(*args, **kwargs)

    def observed_binding(*args, **kwargs):
        bindings.append(args[0])
        return original_binding(*args, **kwargs)

    monkeypatch.setattr(bundle, "load_verified_construction_bundle", observed)
    monkeypatch.setattr(candidate, "bind_published_compilation", observed_binding)
    choices = construction.discover_designs(
        {"stem_arm": STEM, "product": "hairpin"}, tmp_path / "designs", max_evaluations=2
    )
    assert choices.query()["matching_preparations"] == 1
    # Replay each staged candidate once, then bind its actual published bytes
    # to that fresh compilation instead of replaying it a second time.
    assert len(loads) == 2
    assert len(bindings) == 2
    reopened = construction.load_design_choices(tmp_path / "designs")
    assert reopened.query() == choices.query()
    assert len(loads) == 4  # Disk data cannot inherit a previous invocation's proof.
    assert len(bindings) == 2
