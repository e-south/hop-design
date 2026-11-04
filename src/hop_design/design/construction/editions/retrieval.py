"""An edition capture owns one fully admitted, read-only survey snapshot."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from hop_design.design.runtime import producer_identity

from ..intents.base import PreparationReceipt, Source
from ..intents.comparisons import source_value
from ..intents.inserts.selection import native_selection
from ..intents.results import InsertDesignChoices
from ..navigation.types import ChoiceSource
from ..surveys.admission import open_survey
from ..surveys.execute import load_request
from ..surveys.retrieve import retrieve_admitted_witness

type RetrievePreparation = Callable[[Source, Path], PreparationReceipt]


@contextmanager
def capture_retrieval(choices: ChoiceSource) -> Iterator[RetrievePreparation]:
    if not isinstance(choices, InsertDesignChoices):
        yield choices.retrieve
        return
    request = load_request(choices._directory / "intent/request.json")
    index, limits = open_survey(
        choices._directory / "survey.sqlite", request=request, producer=producer_identity()
    )
    with index:

        def retrieve(selection: Source, destination: Path) -> PreparationReceipt:
            # Preserved selections own extra comparison files and their own routing.
            if source_value(selection).get("schema") != "hop.interface-survey-selection/v1":
                return choices.retrieve(selection, destination)
            return retrieve_admitted_witness(
                index,
                limits,
                selection=native_selection(choices, selection),
                destination=choices._output(destination),
            )

        yield retrieve
