"""Shared strict model policy and private content-identity creation."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict


class HopModel(BaseModel):
    """Base contract that rejects coercion, mutation, and unknown fields."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        extra="forbid",
        validate_by_alias=True,
        validate_by_name=True,
    )


@dataclass(slots=True)
class _IdentityCreation:
    model: type[HopModel]
    field: str
    placeholder: str
    sealed: HopModel | None = None


def _create_with_content_identity[Model: HopModel](
    model: type[Model], field: str, kind: str, content: dict[str, object]
) -> Model:
    """Run the normal validators, generating only this new root's identity."""
    if field in content:
        raise TypeError(f"create() does not accept an existing {field}.")
    creation = _IdentityCreation(model, field, f"hop:{kind}/{'0' * 64}@1")
    result = model.model_validate({field: creation.placeholder, **content}, context=creation)
    if creation.sealed is not result:
        raise RuntimeError("New content identity was not sealed during validation.")
    return result


def _verify_or_set_content_identity(
    record: HopModel, field: str, expected: str, message: str, context: object
) -> None:
    """Set the factory root seal; all other inputs must supply the exact seal."""
    if (
        isinstance(context, _IdentityCreation)
        and context.model is type(record)
        and context.field == field
        and context.sealed is None
        and getattr(record, field) == context.placeholder
    ):
        object.__setattr__(record, field, expected)
        context.sealed = record
    elif getattr(record, field) != expected:
        raise ValueError(message)
