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
from hop_design.models.molecular_state import LineageStrand

from .clone.validation import validate_clone_realization
from .evaluation_inputs import (
    derive_complete_payload_source_map,
    replay_linear_source_embedding,
)
from .material import ExactConstructionMaterial, MaterialUse, validate_complete_material_uses
from .material.replay import (
    validate_foldback_annealing,
    validate_route_derivation,
    validate_route_material_lineage,
)
from .material_disposition import (
    RouteMaterialDispositionSpan,
    derive_route_material_dispositions,
)
from .pcr.validation import validate_pcr_realization
from .product import MaterializedFinalProduct
from .program import ConstructionProgram
from .request import DesignAuthorityReference
from .source_authority import validate_local_authorities
from .source_partition import SourcePartitionBinding
from .source_partition.plan import SourcePartitionPlan
from .source_preparation import SourceDuplexPreparationAuthority
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
    source_preparation: SourceDuplexPreparationAuthority
    source_partition_plan: SourcePartitionPlan | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    source_partition_binding: SourcePartitionBinding | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    materials: tuple[ExactConstructionMaterial, ...] = Field(min_length=1)
    material_uses: tuple[MaterialUse, ...] = Field(min_length=2)
    construction_program: ConstructionProgram
    final_product: MaterializedFinalProduct
    design: DesignAuthorityReference
    geometry_ids: tuple[str, ...] = Field(min_length=1)
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
        SourceDuplexPreparationAuthority.model_validate(
            self.source_preparation.model_dump(mode="python")
        )
        content = self.model_dump(mode="json", exclude={"materialized_realization_id"})
        if self.materialized_realization_id != _content_id("materialized-construction", 1, content):
            raise ValueError("Materialized identity must seal every complete-route fact.")
        if self.realization.precursor_sequence != self.materials[0].sequence_5prime:
            raise ValueError("Complete precursor must equal the prepared source strand.")
        prepared_materials = tuple(
            binding.material for binding in self.source_preparation.produced_material_bindings
        )
        if prepared_materials != self.materials[:2]:
            raise ValueError(
                "Complete source materials must equal the exact source-preparation products."
            )
        if self.source_preparation.source_ssdna.sequence_5prime != (
            self.realization.precursor_sequence
        ):
            raise ValueError("Complete precursor must map to the exact source ssDNA specification.")
        external_materials = (
            self.source_preparation.source_ssdna,
            self.source_preparation.forward_primer.oligo,
            self.source_preparation.reverse_primer.oligo,
            *self.materials[2:],
        )
        for material in (*prepared_materials, *external_materials):
            ExactConstructionMaterial.model_validate(material.model_dump(mode="python"))
        if len(self.material_uses) != len(self.materials) or tuple(
            item.material_id for item in self.material_uses
        ) != tuple(item.material_id for item in self.materials):
            raise ValueError("Complete material-use registry must bind every ordered material.")
        if len({item.use_id for item in self.material_uses}) != len(self.material_uses):
            raise ValueError("Complete material-use registry requires distinct contextual uses.")
        if self.material_uses[:2] != (
            self.source_preparation.prepared_top_use,
            self.source_preparation.prepared_bottom_use,
        ):
            raise ValueError("Complete route must begin with prepared source material uses.")
        validate_local_authorities(
            foldback=self.foldback_authority,
            foldback_realization_id=self.foldback_realization_id,
            basal=self.basal_authority,
            basal_realization_id=self.basal_realization_id,
            local_realization_ids=self.realization.local_realization_ids,
        )
        if self.construction_program.states[0] != self.source_preparation.product_state:
            raise ValueError(
                "Complete route must begin with the exact source-preparation product state."
            )
        endpoint = self.final_product.reference.endpoint
        is_direct = endpoint is ConstructionEndpoint.SSDNA_HAIRPIN
        if is_direct and self.source_partition_plan is not None:
            raise ValueError("A PCR source-partition plan requires a PCR-bearing endpoint.")
        validate_complete_material_uses(self.material_uses, is_direct=is_direct)
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
                material_uses=self.material_uses,
            )
        validate_route_material_lineage(
            self.construction_program,
            self.materials,
            material_uses=self.material_uses,
            material_orientations={
                self.material_uses[0].use_id: LineageStrand.PRIMARY,
                self.material_uses[1].use_id: LineageStrand.COMPLEMENTARY,
                **{item.use_id: LineageStrand.PRIMARY for item in self.material_uses[2:]},
            },
        )
        validate_foldback_annealing(
            self.construction_program,
            foldback=self.foldback_authority,
            materials=self.materials,
            material_uses=self.material_uses,
        )
        _, _, embedding = replay_linear_source_embedding(
            foldback=self.foldback_authority,
            source_sequence=self.materials[0].sequence_5prime,
            complement_sequence=self.materials[1].sequence_5prime,
        )
        expected_payload_map = derive_complete_payload_source_map(
            foldback=self.foldback_authority,
            embedding=embedding,
            source_material_id=self.source_preparation.source_ssdna.material_id,
        )
        if self.payload_source_map != expected_payload_map:
            raise ValueError(
                "Payload source occurrence must derive from the exact lifted local authority."
            )
        if (
            self.source_preparation.payload_source_span
            != self.payload_source_map.segments[0].source_span
        ):
            raise ValueError(
                "Source preparation payload span must equal the exact route payload mapping."
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
                material_uses=self.material_uses,
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
                material_uses=self.material_uses,
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
        if self.geometry_ids != expected_geometry_ids:
            raise ValueError("Geometry identities must derive from local authorities.")
        return self


__all__ = ["MaterializedConstructionRealization"]
