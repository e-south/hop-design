"""
--------------------------------------------------------------------------------
HOP Design
tests/contract/test_reaction_stages.py

Contract tests for characterized enzymes and state-aware reaction stages.

Module Author(s): Eric J. South
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hop_design.kernel.reactions import assess_reaction_stage, scan_actionable_sites
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.diagnostics import CheckReport
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    CharacterizedEnzymeCatalog,
    EnzymeClass,
    EnzymeProvisioningPolicy,
    EnzymeRole,
    EnzymeRoleRestriction,
    RecognitionOrientationSemantics,
    ResultingEndModel,
    SubstrateRequirement,
    TargetMolecule,
    VendorMetadata,
    characterized_enzyme_catalog_digest,
    characterized_enzyme_digest,
)
from hop_design.models.physical import SiteOrientation
from hop_design.models.reactions import (
    DeclaredEnzymeBinding,
    ReactionMolecule,
    ReactionOperation,
    ReactionStage,
    ReactionStageAssessment,
    ReactionState,
)
from hop_design.models.references import ExternalRef
from hop_design.models.sequence import reverse_complement_iupac


def _nickase(
    *,
    enzyme_id: str = "example:enzyme/nick-a@1",
    motif: str = "AAGC",
    cut_offset: int = 1,
    vendor_name: str = "Vendor A",
) -> CharacterizedEnzyme:
    return CharacterizedEnzyme(
        schema="hop/characterized-enzyme/v1",
        enzyme_id=enzyme_id,
        canonical_name=enzyme_id.rsplit("/", maxsplit=1)[-1],
        enzyme_class=EnzymeClass.NICKASE,
        target_molecule=TargetMolecule.DNA,
        recognition_pattern=motif,
        recognition_orientation_semantics=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
        recognition_length=len(motif),
        substrate_requirement=SubstrateRequirement.DUPLEX_DNA,
        cut_offset_reference_strand=cut_offset,
        cut_offset_complement_strand=None,
        resulting_end_model=ResultingEndModel.NICK,
        characterization_source=ExternalRef(
            system="literature",
            kind="enzyme-characterization",
            id=f"source-{enzyme_id}",
        ),
        vendor_metadata=(VendorMetadata(vendor_name=vendor_name, catalog_number="TEST-001"),),
    )


def _restriction_enzyme() -> CharacterizedEnzyme:
    return CharacterizedEnzyme(
        schema="hop/characterized-enzyme/v1",
        enzyme_id="example:enzyme/cut-a@1",
        canonical_name="cut-a",
        enzyme_class=EnzymeClass.DUPLEX_RESTRICTION,
        target_molecule=TargetMolecule.DNA,
        recognition_pattern="CCGG",
        recognition_orientation_semantics=RecognitionOrientationSemantics.BOTH_ORIENTATIONS,
        recognition_length=4,
        substrate_requirement=SubstrateRequirement.DUPLEX_DNA,
        cut_offset_reference_strand=5,
        cut_offset_complement_strand=1,
        resulting_end_model=ResultingEndModel.DUPLEX_BREAK,
        characterization_source=ExternalRef(
            system="literature",
            kind="enzyme-characterization",
            id="source-cut-a",
        ),
        vendor_metadata=(),
    )


def _catalog(*enzymes: CharacterizedEnzyme) -> CharacterizedEnzymeCatalog:
    return CharacterizedEnzymeCatalog(
        schema="hop/characterized-enzyme-catalog/v1",
        catalog_id="example:enzyme-catalog/reaction-test@1",
        enzymes=enzymes,
    )


def _policy(*enzymes: CharacterizedEnzyme) -> EnzymeProvisioningPolicy:
    return EnzymeProvisioningPolicy(
        catalog=_catalog(*enzymes),
        allowed_enzyme_ids=tuple(enzyme.enzyme_id for enzyme in enzymes),
        forbidden_enzyme_ids=(),
        reserved_enzyme_ids=(),
        max_operations=8,
        role_restrictions=(),
    )


def _duplex(molecule_id: str, sequence: str) -> ReactionMolecule:
    return ReactionMolecule(
        molecule_id=molecule_id,
        reference_sequence_5prime=sequence,
        complement_sequence_5prime=reverse_complement_iupac(sequence),
    )


def _binding(
    *,
    start: int,
    motif_length: int,
    reference_cut: int,
    complement_cut: int | None = None,
) -> DeclaredEnzymeBinding:
    return DeclaredEnzymeBinding(
        recognition_span=Span(
            start=Boundary(offset=start),
            end=Boundary(offset=start + motif_length),
        ),
        orientation=SiteOrientation.FORWARD,
        reference_cut=Boundary(offset=reference_cut),
        complement_cut=(Boundary(offset=complement_cut) if complement_cut is not None else None),
    )


def test_vendor_metadata_does_not_change_characterized_enzyme_identity() -> None:
    first = _nickase(vendor_name="Vendor A")
    second = _nickase(vendor_name="Vendor B")

    assert first != second
    assert characterized_enzyme_digest(first) == characterized_enzyme_digest(second)
    assert characterized_enzyme_catalog_digest(_catalog(first)) == (
        characterized_enzyme_catalog_digest(_catalog(second))
    )


def test_recognition_span_and_cut_coordinates_are_distinct() -> None:
    enzyme = _restriction_enzyme()
    state = ReactionState(
        state_id="pre-cut",
        molecules=(_duplex("source", "CCGGAA"),),
    )

    sites = scan_actionable_sites(state=state, enzyme=enzyme)
    forward = next(site for site in sites if site.orientation is SiteOrientation.FORWARD)

    assert (forward.recognition_span.start.offset, forward.recognition_span.end.offset) == (0, 4)
    assert forward.reference_cut.offset == 5
    assert forward.complement_cut == Boundary(offset=1)


def test_provisioning_policy_validates_allowed_forbidden_reserved_and_roles() -> None:
    nickase = _nickase()
    restriction = _restriction_enzyme()
    catalog = _catalog(nickase, restriction)
    policy = EnzymeProvisioningPolicy(
        catalog=catalog,
        allowed_enzyme_ids=(nickase.enzyme_id, restriction.enzyme_id),
        forbidden_enzyme_ids=(),
        reserved_enzyme_ids=(),
        max_operations=2,
        role_restrictions=(
            EnzymeRoleRestriction(
                role=EnzymeRole.STRAND_EXPOSURE,
                allowed_enzyme_ids=(nickase.enzyme_id,),
            ),
        ),
    )

    assert policy.permits(nickase.enzyme_id, role=EnzymeRole.STRAND_EXPOSURE)
    assert not policy.permits(restriction.enzyme_id, role=EnzymeRole.STRAND_EXPOSURE)
    assert policy.permits(restriction.enzyme_id, role=EnzymeRole.END_GENERATION)

    reserved_policy = EnzymeProvisioningPolicy(
        catalog=catalog,
        allowed_enzyme_ids=(nickase.enzyme_id,),
        forbidden_enzyme_ids=(),
        reserved_enzyme_ids=(restriction.enzyme_id,),
        max_operations=2,
        role_restrictions=(),
    )
    assert not reserved_policy.permits(restriction.enzyme_id, role=EnzymeRole.END_GENERATION)

    with pytest.raises(ValidationError, match="must not overlap"):
        EnzymeProvisioningPolicy(
            catalog=catalog,
            allowed_enzyme_ids=(nickase.enzyme_id,),
            forbidden_enzyme_ids=(nickase.enzyme_id,),
            reserved_enzyme_ids=(),
            max_operations=2,
            role_restrictions=(),
        )

    with pytest.raises(ValidationError, match="reserved"):
        EnzymeProvisioningPolicy(
            catalog=catalog,
            allowed_enzyme_ids=(nickase.enzyme_id,),
            forbidden_enzyme_ids=(),
            reserved_enzyme_ids=(restriction.enzyme_id,),
            max_operations=2,
            role_restrictions=(
                EnzymeRoleRestriction(
                    role=EnzymeRole.END_GENERATION,
                    allowed_enzyme_ids=(restriction.enzyme_id,),
                ),
            ),
        )


def test_concurrent_operations_resolve_against_the_same_pre_stage_state() -> None:
    first = _nickase()
    second = _nickase(
        enzyme_id="example:enzyme/nick-b@1",
        motif="CCGA",
        cut_offset=2,
    )
    state = ReactionState(
        state_id="duplex-source",
        molecules=(_duplex("source", "AAGCCCGA"),),
    )
    stage = ReactionStage(
        stage_id="concurrent-nicks",
        pre_state_id=state.state_id,
        operations=(
            ReactionOperation(
                operation_id="nick-left",
                enzyme_id=first.enzyme_id,
                role=EnzymeRole.STRAND_EXPOSURE,
                molecule_id="source",
                intended_binding=_binding(start=0, motif_length=4, reference_cut=1),
            ),
            ReactionOperation(
                operation_id="nick-right",
                enzyme_id=second.enzyme_id,
                role=EnzymeRole.STRAND_EXPOSURE,
                molecule_id="source",
                intended_binding=_binding(start=4, motif_length=4, reference_cut=6),
            ),
        ),
    )

    assessment = assess_reaction_stage(state=state, stage=stage, policy=_policy(first, second))

    assert not assessment.report.has_errors
    assert assessment.resolved_against_state_id == "duplex-source"
    assert [binding.operation_id for binding in assessment.intended_bindings] == [
        "nick-left",
        "nick-right",
    ]


def test_duplex_only_enzyme_is_inactive_on_single_stranded_dna() -> None:
    state = ReactionState(
        state_id="single-strand",
        molecules=(
            ReactionMolecule(
                molecule_id="single",
                reference_sequence_5prime="AAGC",
                complement_sequence_5prime=None,
            ),
        ),
    )

    assert scan_actionable_sites(state=state, enzyme=_nickase()) == ()


def test_absent_or_not_yet_assembled_molecule_is_not_scanned() -> None:
    state = ReactionState(
        state_id="before-assembly",
        molecules=(_duplex("present", "TTTT"),),
    )

    assert scan_actionable_sites(state=state, enzyme=_nickase()) == ()


def test_mismatch_disrupted_recognition_site_is_inactive() -> None:
    state = ReactionState(
        state_id="mismatched-duplex",
        molecules=(
            ReactionMolecule(
                molecule_id="source",
                reference_sequence_5prime="AAGC",
                complement_sequence_5prime="GCTA",
            ),
        ),
    )

    assert scan_actionable_sites(state=state, enzyme=_nickase()) == ()


def test_undeclared_actionable_site_is_reported_as_a_hard_failure() -> None:
    enzyme = _nickase()
    state = ReactionState(
        state_id="duplicate-site-source",
        molecules=(_duplex("source", "AAGCAAGC"),),
    )
    stage = ReactionStage(
        stage_id="one-declared-nick",
        pre_state_id=state.state_id,
        operations=(
            ReactionOperation(
                operation_id="declared-nick",
                enzyme_id=enzyme.enzyme_id,
                role=EnzymeRole.STRAND_EXPOSURE,
                molecule_id="source",
                intended_binding=_binding(start=0, motif_length=4, reference_cut=1),
            ),
        ),
    )

    assessment = assess_reaction_stage(state=state, stage=stage, policy=_policy(enzyme))

    assert assessment.report.has_errors
    assert [item.code for item in assessment.report.diagnostics] == ["HOP-STAGE-004"]
    assert [
        (site.recognition_span.start.offset, site.recognition_span.end.offset)
        for site in assessment.undeclared_bindings
    ] == [(4, 8)]


def test_conflicting_concurrent_cuts_fail_stage_assessment() -> None:
    enzyme = _nickase()
    state = ReactionState(
        state_id="shared-site-source",
        molecules=(_duplex("source", "AAGC"),),
    )
    declared = _binding(start=0, motif_length=4, reference_cut=1)
    stage = ReactionStage(
        stage_id="conflicting-nicks",
        pre_state_id=state.state_id,
        operations=(
            ReactionOperation(
                operation_id="first-nick",
                enzyme_id=enzyme.enzyme_id,
                role=EnzymeRole.STRAND_EXPOSURE,
                molecule_id="source",
                intended_binding=declared,
            ),
            ReactionOperation(
                operation_id="second-nick",
                enzyme_id=enzyme.enzyme_id,
                role=EnzymeRole.STRAND_EXPOSURE,
                molecule_id="source",
                intended_binding=declared,
            ),
        ),
    )

    assessment = assess_reaction_stage(state=state, stage=stage, policy=_policy(enzyme))

    assert assessment.report.has_errors
    assert "HOP-STAGE-005" in {item.code for item in assessment.report.diagnostics}


def test_stage_assessment_is_strict_and_frozen() -> None:
    assessment = ReactionStageAssessment(
        stage_id="stage",
        resolved_against_state_id="state",
        intended_bindings=(),
        undeclared_bindings=(),
        report=CheckReport(),
    )

    with pytest.raises(ValidationError, match="frozen"):
        assessment.stage_id = "changed"
    with pytest.raises(ValidationError, match="Extra inputs"):
        ReactionStageAssessment(
            stage_id="stage",
            resolved_against_state_id="state",
            intended_bindings=(),
            undeclared_bindings=(),
            report=CheckReport(),
            undocumented_status="accepted",  # type: ignore[call-arg]
        )
