"""Small CLI translations; optional-intent semantics remain in the construction facade."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import typer

if TYPE_CHECKING:
    from hop_design import construction


@contextmanager
def errors() -> Iterator[None]:
    try:
        yield
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


def intent(
    request: Path | None,
    stem: str | None,
    product: str | None,
    context: str | None,
    left: str | None,
    right: str | None,
) -> Path | dict[str, Any]:
    flags = (stem, product, context, left, right)
    if request is not None:
        if any(value is not None for value in flags):
            raise ValueError("Use either --request or molecular flags, not both.")
        return request
    if stem is None or product is None:
        raise ValueError("Supply --stem and --product; end words are optional.")
    value: dict[str, Any] = {"stem_arm": stem, "product": product}
    if context is not None:
        value["context"] = context
    ends = {side: word for side, word in (("left", left), ("right", right)) if word is not None}
    if ends:
        value["ends"] = ends
    return value


def emit(value: Any) -> None:
    typer.echo(json.dumps(value, sort_keys=True))


def write_selection(selected: dict[str, Any], output: Path | None, directory: Path) -> None:
    save_document(selected, output, directory)
    emit(selected)


def save_document(value: dict[str, Any], output: Path | None, directory: Path) -> None:
    """Create a caller-owned JSON document without replacing discovery authority."""
    if output is not None:
        root = directory.resolve(strict=True)
        if output.resolve(strict=False).is_relative_to(root):
            raise ValueError("Write the JSON document outside the saved discovery directory.")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x") as handle:
            json.dump(value, handle, sort_keys=True)


def load_choices(
    directory: Path, member: str | None = None
) -> "construction.DesignChoices | construction.AtlasEdition":
    from hop_design import construction

    choices = (
        construction.load_atlas_edition(directory)
        if (directory / "edition.json").exists()
        else construction.load_design_choices(directory)
    )
    return choices if member is None else choices.member(member)
