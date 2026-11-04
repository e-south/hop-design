"""Export the shared all-state atlas for one explicit complete preparation."""

import json
from pathlib import Path
from typing import Annotated

import typer

from hop_design import construction


def atlas_command(
    options: Annotated[Path, typer.Argument(help="Verified discovery or edit result.")],
    choices: Annotated[Path, typer.Argument(help="Saved conditional choice packet.")],
    option: Annotated[str, typer.Option(help="Explicit compatible preparation.")],
    output: Annotated[Path, typer.Option("--out", help="New atlas packet directory.")],
    focus: Annotated[Path | None, typer.Option(help="State-qualified address JSON.")] = None,
) -> None:
    """Inspect every recorded state without editing requirements or selecting a preparation."""
    try:
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing output: {output}")
        pool = construction.load_scaffold_exploration(options)
        admitted = construction.load_scaffold_variant_choices(pool, choices)
        packet = construction.inspect_scaffold_atlas(
            pool,
            admitted,
            {
                "result_digest": pool.result_digest,
                "query_digest": json.loads(admitted.json_bytes)["query_digest"],
                "option_label": option,
                "focus": json.loads(focus.read_bytes()) if focus else None,
            },
        )
        packet.write(output)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="OPTIONS/CHOICES/--option/--out") from error
    typer.echo(packet.report_text)
