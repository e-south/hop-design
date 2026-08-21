"""Resolved processing-route contracts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from hop_design.models.basal import BasalEvaluation
from hop_design.models.base import HopModel
from hop_design.models.foldback import FoldbackEvaluation
from hop_design.models.junction import BasalJunction, FoldbackJunction
from hop_design.models.references import ReferenceId
from hop_design.models.stem import PairedStemExtension
from hop_design.models.strand_state import NickEvent, ReleasedStrandState


class DirectSynthesisStep(HopModel):
    """The explicit state transition used by the generic demonstration route."""

    step_id: str = Field(min_length=1)
    operation: Literal["direct_synthesis"] = "direct_synthesis"
    input_state: Literal["authored_spec"] = "authored_spec"
    output_state: Literal["hairpin_encoding_insert"] = "hairpin_encoding_insert"


class ProcessingRoute(HopModel):
    """One reusable, resolved physical implementation route."""

    route_id: ReferenceId
    kind: Literal["direct_synthesis"]
    description: str = Field(min_length=1)
    catalog_ref: ReferenceId
    foldback_junction: FoldbackJunction
    basal_junction: BasalJunction
    steps: tuple[DirectSynthesisStep, ...] = Field(min_length=1)


class ResolvedMechanicsStep(HopModel):
    """One ordered state transition in a resolved molecular-state graph."""

    step_id: str = Field(min_length=1)
    operation: Literal[
        "nick",
        "duplex_release",
        "foldback",
        "basal_pairing",
        "stem_extension_pairing",
        "terminal_nick",
        "assemble_insert",
    ]
    input_states: tuple[str, ...] = Field(min_length=1)
    output_state: str = Field(min_length=1)


class ComponentAssemblyRoute(HopModel):
    """Validated caller-supplied components assembled without a process claim."""

    route_id: ReferenceId
    kind: Literal["component_assembly"] = "component_assembly"
    description: str = Field(min_length=1)
    catalog_ref: ReferenceId
    foldback: FoldbackEvaluation
    basal: BasalEvaluation
    stem_extension: PairedStemExtension | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    steps: tuple[ResolvedMechanicsStep, ...] = Field(min_length=3)

    @model_validator(mode="after")
    def validate_route(self) -> ComponentAssemblyRoute:
        if self.foldback.report.has_errors:
            raise ValueError("Component assembly requires a feasible foldback evaluation.")
        if self.basal.decision.status == "reject":
            raise ValueError("Component assembly cannot contain a rejected basal evaluation.")
        expected: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
            (
                "foldback",
                "foldback",
                ("authored_foldback_precursor",),
                "foldback_junction",
            ),
            (
                "basal-pairing",
                "basal_pairing",
                ("authored_basal_arms",),
                "basal_junction",
            ),
        )
        if self.stem_extension is not None:
            expected += (
                (
                    "stem-extension-pairing",
                    "stem_extension_pairing",
                    ("authored_stem_extension_arms",),
                    "paired_stem_extension",
                ),
            )
        expected += (
            (
                "insert-assembly",
                "assemble_insert",
                (
                    "foldback_junction",
                    "basal_junction",
                    *(("paired_stem_extension",) if self.stem_extension is not None else ()),
                    "authored_payload",
                ),
                "hairpin_encoding_insert",
            ),
        )
        actual = tuple(
            (step.step_id, step.operation, step.input_states, step.output_state)
            for step in self.steps
        )
        if actual != expected:
            raise ValueError("Component assembly steps must match the declared state graph.")
        return self


class ResolvedMechanicsRoute(HopModel):
    """Resolved foldback, basal, and optional released-strand mechanics."""

    route_id: ReferenceId
    kind: Literal["resolved_events"] = "resolved_events"
    description: str = Field(min_length=1)
    catalog_ref: ReferenceId
    foldback: FoldbackEvaluation
    basal: BasalEvaluation
    stem_extension: PairedStemExtension | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    terminal_nick: NickEvent
    released_state: ReleasedStrandState | None
    steps: tuple[ResolvedMechanicsStep, ...] = Field(min_length=4)

    @model_validator(mode="after")
    def validate_route(self) -> ResolvedMechanicsRoute:
        if self.foldback.report.has_errors:
            raise ValueError("Resolved mechanics route requires a feasible foldback evaluation.")
        if self.foldback.retained_tract_span.start != self.foldback.nick_boundary:
            raise ValueError("Resolved foldback retained tract must begin at its nick boundary.")
        if self.basal.decision.status == "reject":
            raise ValueError("Resolved mechanics route cannot contain a rejected basal evaluation.")
        if self.terminal_nick.boundary.offset != len(self.basal.junction.left_arm):
            raise ValueError("Resolved terminal nick boundary must equal the basal arm length.")
        if (
            self.released_state is not None
            and self.released_state.active_product_sequence != self.foldback.precursor_sequence
        ):
            raise ValueError("Released active product must equal the foldback precursor input.")
        step_ids = tuple(step.step_id for step in self.steps)
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Resolved mechanics route step ids must be unique.")
        available_states = {
            "precursor_duplex",
            "authored_foldback_precursor",
            "authored_basal_arms",
            "authored_payload",
            "authored_stem_extension_arms",
        }
        for step in self.steps:
            if not set(step.input_states) <= available_states:
                raise ValueError(
                    "Resolved mechanics route inputs must reference available molecular states."
                )
            if step.output_state in available_states:
                raise ValueError("Resolved mechanics route outputs must be unique.")
            available_states.add(step.output_state)
        extension_step = (
            (
                (
                    "stem-extension-pairing",
                    "stem_extension_pairing",
                    ("authored_stem_extension_arms",),
                    "paired_stem_extension",
                ),
            )
            if self.stem_extension is not None
            else ()
        )
        extension_input = ("paired_stem_extension",) if self.stem_extension is not None else ()
        expected = (
            (
                ("nick", "nick", ("precursor_duplex",), "nicked_precursor"),
                (
                    "duplex-release",
                    "duplex_release",
                    ("nicked_precursor",),
                    "released_active_strand",
                ),
                (
                    "foldback",
                    "foldback",
                    ("released_active_strand",),
                    "foldback_junction",
                ),
                (
                    "basal-pairing",
                    "basal_pairing",
                    ("authored_basal_arms",),
                    "basal_junction",
                ),
                *extension_step,
                (
                    "terminal-nick",
                    "terminal_nick",
                    ("basal_junction",),
                    "terminal_nicked_basal_junction",
                ),
                (
                    "insert-assembly",
                    "assemble_insert",
                    (
                        "foldback_junction",
                        "terminal_nicked_basal_junction",
                        *extension_input,
                        "authored_payload",
                    ),
                    "hairpin_encoding_insert",
                ),
            )
            if self.released_state is not None
            else (
                (
                    "foldback",
                    "foldback",
                    ("authored_foldback_precursor",),
                    "foldback_junction",
                ),
                (
                    "basal-pairing",
                    "basal_pairing",
                    ("authored_basal_arms",),
                    "basal_junction",
                ),
                *extension_step,
                (
                    "terminal-nick",
                    "terminal_nick",
                    ("basal_junction",),
                    "terminal_nicked_basal_junction",
                ),
                (
                    "insert-assembly",
                    "assemble_insert",
                    (
                        "foldback_junction",
                        "terminal_nicked_basal_junction",
                        *extension_input,
                        "authored_payload",
                    ),
                    "hairpin_encoding_insert",
                ),
            )
        )
        actual = tuple(
            (step.step_id, step.operation, step.input_states, step.output_state)
            for step in self.steps
        )
        if actual != expected:
            raise ValueError("Resolved mechanics route steps must match the declared state graph.")
        return self


PlanProcessingRoute = Annotated[
    ProcessingRoute | ComponentAssemblyRoute | ResolvedMechanicsRoute,
    Field(discriminator="kind"),
]
