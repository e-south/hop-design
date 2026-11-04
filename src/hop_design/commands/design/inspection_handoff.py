"""Durable preparation downloads outlive temporary inspection scenes."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from hop_design import construction

from .inspection_cache import state_key


def preparation_download(
    choices: construction.DesignChoices | construction.AtlasEdition,
    root: Path,
    selected: dict[str, Any],
) -> dict[str, Any]:
    path = root / "preparations" / state_key(selected)
    archive = path.with_suffix(".zip")
    if not archive.exists():
        if not path.exists():
            choices.retrieve(selected, path)
        with TemporaryDirectory(prefix=".handoff-", dir=root) as temporary:
            staged = Path(temporary) / "preparation.zip"
            with ZipFile(staged, "x") as zipped:
                for file in sorted(path.rglob("*")):
                    if file.is_file():
                        info = ZipInfo(file.relative_to(path).as_posix(), (1980, 1, 1, 0, 0, 0))
                        info.compress_type = ZIP_DEFLATED
                        zipped.writestr(info, file.read_bytes())
            os.link(staged, archive)
    return {
        "selection": selected,
        "archive": "/files/" + archive.relative_to(root).as_posix(),
        "directory": path.relative_to(root).as_posix(),
    }
