"""New complete-route records seal once; independent inputs still verify seals."""

from __future__ import annotations

import importlib

import pytest
from pydantic import ValidationError

from hop_design.models.construction.complete import ConstructionProgram, ConstructionState
from tests.integration.test_complete_construction_clone import _valid_clone_result


@pytest.fixture(scope="module")
def realization(tmp_path_factory):
    result, *_ = _valid_clone_result(tmp_path_factory.mktemp("identity-creation"))
    return result.realizations[0]


def _content(record, field):
    return {name: getattr(record, name) for name in type(record).model_fields if name != field}


@pytest.mark.parametrize(
    ("attribute", "field", "kind"),
    (
        ("state", "state_id", "construction-state"),
        ("construction_program", "program_id", "construction-program"),
        ("source_preparation", "authority_id", "source-duplex-preparation"),
        (None, "materialized_realization_id", "materialized-construction"),
    ),
)
def test_factory_seals_once_and_independent_inputs_verify(
    realization, attribute, field, kind, monkeypatch
):
    record = (
        realization.construction_program.states[0]
        if attribute == "state"
        else getattr(realization, attribute)
        if attribute
        else realization
    )
    model = type(record)
    module = importlib.import_module(model.__module__)
    content_id = module._content_id
    calls = []

    def count(value_kind, version, content):
        if value_kind == kind:
            calls.append(content)
        return content_id(value_kind, version, content)

    monkeypatch.setattr(module, "_content_id", count)
    assert model.create(**_content(record, field)) == record
    assert len(calls) == 1
    calls.clear()
    assert model.model_validate(record.model_dump(mode="python")) == record
    assert len(calls) == 1
    assert model.model_validate_json(record.model_dump_json()) == record

    data = record.model_dump(mode="python")
    data[field] = f"hop:{kind}/{'0' * 64}@1"
    for context in (None, {"create": True, "field": field}, {"seal_identity": True}):
        with pytest.raises(ValidationError, match="identity"):
            model.model_validate(data, context=context)
    with pytest.raises(TypeError):
        model.create(**record.model_dump(mode="python"))
    with pytest.raises((ValidationError, TypeError), match=r"Extra inputs|unexpected keyword"):
        model.create(**_content(record, field), unknown="reject")


def test_program_creation_does_not_reseal_nested_state(realization):
    program = realization.construction_program
    state = program.states[0].model_copy(
        update={"state_id": f"hop:construction-state/{'0' * 64}@1"}
    )
    content = _content(program, "program_id")
    content["states"] = (state, *program.states[1:])
    with pytest.raises(ValidationError, match="Construction-state identity"):
        ConstructionProgram.create(**content)


def test_state_creation_retains_strict_fields_and_molecular_checks(realization):
    state = realization.construction_program.states[0]
    with pytest.raises(ValidationError, match="tuple"):
        ConstructionState.create(molecules=list(state.molecules))
    with pytest.raises(ValidationError, match="unique"):
        ConstructionState.create(molecules=state.molecules * 2)


def test_failed_creation_does_not_leak_identity_generation(realization):
    program = realization.construction_program
    content = _content(program, "program_id")
    content["transitions"] = ()
    with pytest.raises(ValidationError):
        ConstructionProgram.create(**content)
    data = program.model_dump(mode="python")
    data["program_id"] = f"hop:construction-program/{'0' * 64}@1"
    with pytest.raises(ValidationError, match="identity"):
        ConstructionProgram.model_validate(data)
    assert ConstructionProgram.create(**_content(program, "program_id")) == program
