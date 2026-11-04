"""Sampling an admitted pool while preserving query and selection history."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .inspection import DesignInspectionSession


def sample_preparation(
    session: "DesignInspectionSession", payload: dict[str, Any]
) -> dict[str, Any]:
    with session._action():
        session._check(payload, optional={"seed", "strategy", "stage"})
        strategy = payload.get("strategy", session._state["exploration"]["strategy"])
        seed = payload.get("seed", session._state["exploration"]["seed"])
        stage = payload.get("stage", session._state["family_stage"])
        history = tuple(session._history)
        if strategy == "loop":
            if session._state["selection"] is None:
                raise ValueError("Select an eligible preparation before changing its loop.")
            identity = session._state["selection"]["materialized_realization_id"]
            if not history or history[-1] != identity:
                history = (*history, identity)
        sampled = session.designs.sample(
            seed=seed,
            query=session._state["choices"]["query"],
            strategy=strategy,
            **({"stage": stage, "history": history} if strategy in {"families", "loop"} else {}),
        )
        selected = sampled.get("selection", sampled)
        session._remember()
        session._history = list(history)
        session._state["choices"] = session.designs.query(selected.get("query"))
        session._state["presentation"] = {**session._state["presentation"], "family_stage": stage}
        session._state["exploration"] = {
            **session._state["exploration"],
            "seed": (seed + 1) % 2**64,
            "strategy": strategy,
        }
        session._show(
            selected,
            reference=session._state["selection"],
            receipt=sampled if strategy in {"families", "loop"} else None,
        )
        session._state["family_stage"] = stage
        return session.state()
