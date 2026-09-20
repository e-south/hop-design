"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/design/construction/foldback_space_public.py

Exposes replay-verified foldback sequence populations and exact member recovery.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from hop_design.design.source_documents import (
    DEFAULT_RESULT_MAX_BYTES,
    SourceDocumentLimitError,
    load_source_mapping,
)
from hop_design.export.publication import publish_directory_create_only
from hop_design.kernel.construction.foldback.domains import (
    FoldbackSequenceDomain,
    solve_foldback_sequence_domain,
)
from hop_design.kernel.construction.foldback.programs import FoldbackProgramCandidate
from hop_design.models.construction.foldback_space import (
    FoldbackSequenceRequest,
    FoldbackSequenceResult,
)
from hop_design.serialization import canonical_json_bytes

from .foldback.realization import _realization
from .foldback_space import discover_sequence_space, verify_sequence_space


@dataclass(frozen=True, init=False, repr=False)
class FoldbackSequenceSpace:
    """Portable complete local sequence sets admitted by deterministic molecular replay."""

    _result: FoldbackSequenceResult
    _json_bytes: bytes

    @classmethod
    def _create(cls, result: FoldbackSequenceResult) -> Self:
        content = canonical_json_bytes(result)
        if len(content) > DEFAULT_RESULT_MAX_BYTES:
            raise SourceDocumentLimitError(actual=len(content), max_bytes=DEFAULT_RESULT_MAX_BYTES)
        verified = verify_sequence_space(result)
        instance = object.__new__(cls)
        object.__setattr__(instance, "_result", verified)
        object.__setattr__(instance, "_json_bytes", content)
        return instance

    def _verified_source(self) -> FoldbackSequenceResult:
        if (
            not hasattr(self, "_result")
            or not hasattr(self, "_json_bytes")
            or canonical_json_bytes(self._result) != self._json_bytes
        ):
            raise ValueError("Foldback sequence receipt disagrees with its verified content.")
        return self._result

    @property
    def json_bytes(self) -> bytes:
        """Return complete canonical result JSON including program-supported sequence sets."""
        self._verified_source()
        return self._json_bytes

    @property
    def result_id(self) -> str:
        """Return content identity including request, implementation, and exact populations."""
        return self._verified_source().result_id

    @property
    def candidate_count(self) -> int:
        """Count independent sequence assignments across exact cases before constraints."""
        return self._verified_source().candidate_count

    @property
    def admitted_count(self) -> int:
        """Count distinct admitted configurations without multiplying enzyme support."""
        return self._verified_source().admitted_count

    def write(self, destination: str | Path) -> Path:
        """Atomically publish the verified result in a new directory."""
        content = self.json_bytes
        output = Path(destination)
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"Refusing to replace existing foldback sequence path: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
        try:
            (staging / "result.json").write_bytes(content)
            publish_directory_create_only(staging, output)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return output

    def member_json(self, *, case_id: str, rank: int, program_index: int) -> str:
        """Recover one lexicographic member through an explicitly selected supporting program."""
        result = self._verified_source()
        case = next((item for item in result.cases if item.case_id == case_id), None)
        if case is None:
            raise ValueError("Unknown foldback sequence case.")
        if type(rank) is not int or not 0 <= rank < case.sequences.cardinality:
            raise ValueError("Foldback member rank must lie within the admitted set.")
        if type(program_index) is not int or not 0 <= program_index < len(case.programs):
            raise ValueError("Foldback program index must lie within the examined roster.")
        word = case.sequences.member_at(rank)
        support = case.programs[program_index]
        if not support.sequences.contains(word):
            raise ValueError("Selected foldback program does not admit this member.")
        catalog = result.request.enzyme_provisioning.catalog
        program = FoldbackProgramCandidate(
            kind=support.kind,
            nick_enzyme=catalog.by_id(support.nick_enzyme_id),
            nick_orientation=support.nick_orientation,
            terminus_enzyme=(
                None
                if support.terminus_enzyme_id is None
                else catalog.by_id(support.terminus_enzyme_id)
            ),
            terminus_orientation=support.terminus_orientation,
        )
        domain = solve_foldback_sequence_domain(
            payload_sequence=case.payload_sequence, target=case.target, program=program
        )
        if not isinstance(domain, FoldbackSequenceDomain):
            raise ValueError("Admitted foldback member has no molecular placement.")
        record = _realization(
            request=result.request,
            payload_sequence=case.payload_sequence,
            target=case.target,
            route=program,
            solution=domain.materialize(word),
        )
        if isinstance(record, str):
            raise ValueError(f"Admitted foldback member failed molecular replay: {record}.")
        return canonical_json_bytes(
            {
                "schema": "hop.foldback-sequence-member/v1",
                "result_id": result.result_id,
                "case_id": case_id,
                "rank": rank,
                "program_index": program_index,
                "independent_sequence": word,
                "realization": record.model_dump(mode="json", by_alias=True),
            }
        ).decode("utf-8")


def discover_foldback_sequence_space(source_path: str | Path) -> FoldbackSequenceSpace:
    """Discover exact foldback populations from a finite JSON or YAML request."""
    mapping = load_source_mapping(source_path, source_label="HOP foldback sequence request")
    if mapping.get("schema") != "hop.foldback-sequence-request/v1":
        raise ValueError(
            f"Unsupported foldback sequence request schema: {mapping.get('schema')!r}."
        )
    request = FoldbackSequenceRequest.model_validate_json(json.dumps(mapping))
    return FoldbackSequenceSpace._create(discover_sequence_space(request))


def load_verified_foldback_sequence_space(result_path: str | Path) -> FoldbackSequenceSpace:
    """Load a complete result only after exact deterministic molecular rediscovery."""
    mapping = load_source_mapping(
        result_path, max_bytes=DEFAULT_RESULT_MAX_BYTES, source_label="HOP foldback sequence result"
    )
    if mapping.get("schema") != "hop.foldback-sequence-result/v1":
        raise ValueError(f"Unsupported foldback sequence result schema: {mapping.get('schema')!r}.")
    return FoldbackSequenceSpace._create(
        FoldbackSequenceResult.model_validate_json(json.dumps(mapping))
    )
