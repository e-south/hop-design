"""Open one inspection shell for admitted live choices or a frozen atlas edition."""

from pathlib import Path

from ..construction.editor.server import EditorServer
from .common import load_choices
from .inspection import DesignInspectionSession


def create_design_server(
    directory: Path,
    output: Path,
    *,
    port: int = 0,
    member: str | None = None,
    receipt: Path | None = None,
) -> EditorServer:
    choices = load_choices(directory, member)
    if choices.resolution.get("schema") == "hop.design-family-preview/v1":
        raise ValueError("Choose a required stem with --member; design query lists the family.")
    session = DesignInspectionSession(choices, output)
    try:
        if receipt is not None:
            session.restore(
                {"token": session.state()["token"], "receipt": choices.restore_view(receipt)}
            )
        return EditorServer(session, port)
    except BaseException:
        session.close()
        raise
