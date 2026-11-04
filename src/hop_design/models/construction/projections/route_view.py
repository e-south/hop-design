"""Read-only molecular facts needed for portrayal, separate from compiler admission.

These protocols do not validate a historical bundle or confer current compiler
authority. A caller must verify its producing record before projecting it. They
let rendering retain original identities without rebuilding a newer realization.
"""

from typing import Protocol

from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.complete.material import MaterialUse
from hop_design.models.construction.complete.pcr import DuplexFinalProductReference
from hop_design.models.construction.complete.program import ConstructionProgram
from hop_design.models.construction.complete.request import DesignAuthorityReference
from hop_design.models.construction.complete.source_preparation import (
    SourceDuplexPreparationAuthority,
)
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.construction.payload import PayloadSourceMap
from hop_design.models.construction.realization import FinalProductReference
from hop_design.models.molecular_state import CohesiveEnd, MolecularStrand, SequenceProjection


class MolecularProductView(Protocol):
    @property
    def reference(self) -> FinalProductReference | DuplexFinalProductReference: ...

    @property
    def strands(self) -> tuple[MolecularStrand, ...]: ...

    @property
    def cohesive_ends(self) -> tuple[CohesiveEnd, ...]: ...

    @property
    def design_projection(self) -> SequenceProjection:
        """Design sequence in its declared endpoint or pre-release parent frame."""
        ...


class MolecularRouteView(Protocol):
    @property
    def materialized_realization_id(self) -> str: ...

    @property
    def source_preparation(self) -> SourceDuplexPreparationAuthority: ...

    @property
    def construction_program(self) -> ConstructionProgram: ...

    @property
    def payload_source_map(self) -> PayloadSourceMap: ...

    @property
    def material_uses(self) -> tuple[MaterialUse, ...]: ...

    @property
    def foldback_authority(self) -> FoldbackLocalRealization: ...

    @property
    def basal_authority(self) -> BasalRealizationRecord | None: ...

    @property
    def design(self) -> DesignAuthorityReference: ...

    @property
    def final_product(self) -> MolecularProductView: ...
