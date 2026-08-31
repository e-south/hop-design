"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/models/construction/complete/realization.py

Defines one exact materialized complete-construction realization.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import Field, model_validator

from hop_design.models.base import HopModel
from hop_design.models.construction.accounting import (
    MethodResolutionStatus,
    NeighborhoodClaimBoundary,
)
from hop_design.models.construction.basal import BasalRealizationRecord
from hop_design.models.construction.foldback import FoldbackLocalRealization
from hop_design.models.construction.payload import (
    ConstructionEndpoint,
    PayloadSourceMap,
    _content_id,
)
from hop_design.models.construction.realization import CompleteConstructionRealization
from hop_design.models.method import BindingOrientation

from .clone.validation import validate_clone_realization
from .evaluation_inputs import (
    derive_complete_payload_source_map,
    replay_linear_source_embedding,
)
from .material_disposition import (
    RouteMaterialDispositionSpan,
    derive_route_material_dispositions,
)
from .material_replay import (
    validate_foldback_annealing,
    validate_route_derivation,
    validate_route_material_lineage,
)
from .materials import validate_initial_material_state
from .pcr.validation import validate_pcr_realization
from .product import MaterializedFinalProduct
from .program import ConstructionProgram
from .request import DesignAuthorityReference, ExactConstructionMaterial
from .source_authority import validate_local_authorities
from .state import ConstructionStatePhase


class MaterializedConstructionRealization(HopModel):
    """Existing complete relation plus exact materials, chronology, and design binding."""

    materialized_realization_id: str = Field(
        pattern=r"^hop:materialized-construction/[0-9a-f]{64}@1$"
    )
    realization: CompleteConstructionRealization
    foldback_authority: FoldbackLocalRealization
    basal_authority: BasalRealizationRecord | None = None
    payload_source_map: PayloadSourceMap
    foldback_realization_id: str = Field(pattern=r"^hop:foldback-realization/[0-9a-f]{64}@1$")
    basal_realization_id: str | None = Field(
        default=None,
        pattern=r"^hop:basal-realization/[0-9a-f]{64}@1$",
    )
    materials: tuple[ExactConstructionMaterial, ...] = Field(min_length=1)
    construction_program: ConstructionProgram
    final_product: MaterializedFinalProduct
    design: DesignAuthorityReference
    geometry_ids: tuple[str, ...] = Field(min_length=1)
    relaxation_radii: tuple[int, ...] = Field(min_length=1)
    claim_boundary: NeighborhoodClaimBoundary
    route_material_dispositions: tuple[RouteMaterialDispositionSpan, ...] = Field(
        default=(),
        exclude_if=lambda value: not value,
    )

    @classmethod
    def create(cls, **content: object) -> MaterializedConstructionRealization:
        draft = cls.model_construct(materialized_realization_id="", **cast(Any, content))
        seed = draft.model_dump(mode="json", exclude={"materialized_realization_id"})
        return cls.model_validate(
            {
                "materialized_realization_id": _content_id("materialized-construction", 1, seed),
                **content,
            }
        )

    @model_validator(mode="after")
    def validate_realization(self) -> MaterializedConstructionRealization:
        DesignAuthorityReference.model_validate(self.design.model_dump(mode="python"))
        MaterializedFinalProduct.model_validate(self.final_product.model_dump(mode="python"))
        content = self.model_dump(mode="json", exclude={"materialized_realization_id"})
        if self.materialized_realization_id != _content_id("materialized-construction", 1, content):
            raise ValueError("Materialized identity must seal every complete-route fact.")
        if self.realization.precursor_sequence != self.materials[0].sequence_5prime:
            raise ValueError("Complete precursor must equal the caller-owned source material.")
        validate_local_authorities(
            foldback=self.foldback_authority,
            foldback_realization_id=self.foldback_realization_id,
            basal=self.basal_authority,
            basal_realization_id=self.basal_realization_id,
            local_realization_ids=self.realization.local_realization_ids,
        )
        validate_initial_material_state(self.construction_program.states[0], self.materials)
        endpoint = self.final_product.reference.endpoint
        is_direct = endpoint is ConstructionEndpoint.SSDNA_HAIRPIN
        if is_direct and self.route_material_dispositions:
            raise ValueError("Direct ssDNA endpoint cannot contain PCR-only material dispositions.")
        if endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX and (
            self.construction_program.states[-1].phase
            is not ConstructionStatePhase.HAIRPIN_PCR_DUPLEX
            or self.final_product.reference.topology != "linear_duplex"
        ):
            raise ValueError(
                "Materialized endpoint and topology must match exact route chronology."
            )
        if endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX and (
            self.construction_program.states[-1].phase
            is not ConstructionStatePhase.CLONE_READY_DUPLEX
            or self.final_product.reference.topology != "linear_duplex"
        ):
            raise ValueError("Clone-ready endpoint and topology must match exact route chronology.")
        if is_direct:
            validate_route_derivation(
                self.construction_program,
                foldback=self.foldback_authority,
                basal=self.basal_authority,
                materials=self.materials,
            )
            validate_route_material_lineage(self.construction_program, self.materials)
        validate_foldback_annealing(
            self.construction_program,
            foldback=self.foldback_authority,
            materials=self.materials,
        )
        _, _, embedding = replay_linear_source_embedding(
            foldback=self.foldback_authority,
            source_sequence=self.materials[0].sequence_5prime,
            complement_sequence=self.materials[1].sequence_5prime,
        )
        expected_payload_map = derive_complete_payload_source_map(
            foldback=self.foldback_authority,
            embedding=embedding,
            source_material_id=self.materials[0].material_id,
        )
        if self.payload_source_map != expected_payload_map:
            raise ValueError(
                "Payload source occurrence must derive from the exact lifted local authority."
            )
        if self.realization.final_product_id != self.final_product.reference.final_product_id:
            raise ValueError("Complete relation must bind the exact final product.")
        terminal = self.construction_program.states[-1]
        if self.final_product.strands != terminal.molecules:
            raise ValueError("Final product strands must equal the terminal construction state.")
        if self.final_product.reference.end_descriptors != tuple(
            end.value
            for strand in self.final_product.strands
            for end in (strand.five_prime_end, strand.three_prime_end)
        ):
            raise ValueError("Final product reference must seal exact terminal end chemistry.")
        projection = self.final_product.encoding_projection
        if is_direct:
            if (
                projection.source_span.start.offset != 0
                or projection.source_span.end.offset != len(terminal.molecules[0].sequence)
                or projection.orientation is not BindingOrientation.SAME_5TO3
            ):
                raise ValueError(
                    "Direct encoding projection must be full-span in the terminal "
                    "5-to-3 orientation."
                )
            if (
                self.final_product.reference.topology != "single_stranded_hairpin"
                or terminal.phase is not ConstructionStatePhase.LIGATED_PRODUCT
            ):
                raise ValueError(
                    "Materialized direct endpoint, topology, and terminal phase must be exact."
                )
        elif endpoint is ConstructionEndpoint.HAIRPIN_PCR_DUPLEX:
            validate_pcr_realization(self)
            expected_dispositions = derive_route_material_dispositions(
                materials=self.materials,
                program=self.construction_program,
                material_function_spans=self.final_product.material_function_spans,
            )
            if self.route_material_dispositions != expected_dispositions:
                raise ValueError(
                    "PCR route material dispositions must replay exact endpoint lineage "
                    "and removal."
                )
        elif endpoint is ConstructionEndpoint.CLONE_READY_DUPLEX:
            validate_clone_realization(self)
            expected_dispositions = derive_route_material_dispositions(
                materials=self.materials,
                program=self.construction_program,
                material_function_spans=self.final_product.material_function_spans,
            )
            if self.route_material_dispositions != expected_dispositions:
                raise ValueError(
                    "Clone route material dispositions must replay exact endpoint lineage "
                    "and removal."
                )
        else:
            raise ValueError(f"Unsupported materialized endpoint: {endpoint.value}.")
        stage_ids = tuple(
            stage.stage_id
            for program in self.construction_program.reaction_programs
            for stage in program.stages
        )
        if self.realization.stage_ids != stage_ids:
            raise ValueError("Complete relation must preserve every global enzyme stage.")
        if self.final_product.encoding_projection.sequence != self.design.encoding_sequence or (
            self.final_product.encoding_projection.sequence_digest != self.design.encoding_digest
        ):
            raise ValueError("Endpoint encoding projection must equal the verified HOP design.")
        if self.claim_boundary.method is not MethodResolutionStatus.RESOLVED:
            raise ValueError(
                "Exact materialized routes must declare resolved digital method status."
            )
        expected_geometry_ids = (
            *(
                (
                    _content_id(
                        "geometry",
                        1,
                        self.basal_authority.local_realization.achieved_geometry.model_dump(
                            mode="json"
                        ),
                    ),
                )
                if self.basal_authority is not None
                else ()
            ),
            _content_id(
                "geometry",
                1,
                self.foldback_authority.local_realization.achieved_geometry.model_dump(mode="json"),
            ),
        )
        expected_radii = (
            *(
                (self.basal_authority.relaxation_radius,)
                if self.basal_authority is not None
                else ()
            ),
            self.foldback_authority.relaxation_radius,
        )
        if self.geometry_ids != expected_geometry_ids or self.relaxation_radii != expected_radii:
            raise ValueError("geometry identities and radii must derive from local authorities.")
        return self


__all__ = ["MaterializedConstructionRealization"]
