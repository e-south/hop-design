"""A spawned browser invocation delegates molecular work to the public API."""

from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any

from hop_design import construction


def execute_discovery(
    connection: Connection,
    stopped: Any,
    directory: Path,
    request: dict[str, Any] | None,
    evaluations: int,
    first_choices: int | None,
) -> None:
    latest: construction.DiscoveryProgress | None = None

    def observe(event: construction.DiscoveryProgress) -> None:
        nonlocal latest
        latest = event
        connection.send(
            {"kind": "progress", "progress": event.model_dump(mode="json", by_alias=True)}
        )

    try:
        options: dict[str, Any] = {
            "max_evaluations": evaluations,
            "first_choices": first_choices,
            "on_progress": observe,
            "should_stop": stopped.is_set,
        }
        choices = (
            construction.discover_designs(request, directory, **options)
            if request is not None
            else construction.continue_design_discovery(directory, **options)
        )
        explanation = choices.explain()
        connection.send(
            {
                "kind": "finished",
                "status": "cancelled"
                if latest and latest.termination_reason == "cancelled"
                else "completed",
                "message": None,
                "resumable": "continue_search" in explanation["actions"],
                "matching_preparations": explanation["matching_preparations"],
            }
        )
    except construction.DiscoveryCancelled as error:
        connection.send(
            {
                "kind": "finished",
                "status": "cancelled",
                "message": str(error),
                "resumable": (directory / "intent").is_dir(),
            }
        )
    except Exception as error:
        connection.send(
            {"kind": "finished", "status": "failed", "message": str(error), "resumable": False}
        )
    finally:
        connection.close()
