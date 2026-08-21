from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import hop_design as hop
from hop_design.export.bundle import BundleIntegrityError
from hop_design.kernel.bundle_identity import bundle_id, manifest_digest_for_bundle
from hop_design.models.basal import BasalDesignRequest, BasalPairingRequest
from hop_design.models.bundle import HopBundle
from hop_design.models.coordinates import Boundary, Span
from hop_design.models.diagnostics import InfeasibleDesignError
from hop_design.models.foldback import FoldbackEvaluationRequest
from hop_design.models.junction import Strand
from hop_design.models.payload import DegeneratePayload
from hop_design.models.plan import HopPlan
from hop_design.models.spec import DesignLimits, ResolvedHopSpec
from hop_design.models.strand_state import (
    DuplexCut,
    NickEvent,
    ReleaseProjectionConstraints,
    ReleaseProjectionRequest,
    StrandExposureRoute,
)
from hop_design.serialization import canonical_json_bytes, sha256_digest

verify_bundle = hop.verify_bundle


def _spec(*, foldback_arm: str = "CTGA") -> ResolvedHopSpec:
    return ResolvedHopSpec(
        schema="hop.resolved-design/v1",
        design_id="resolved-demo",
        payload=DegeneratePayload(sequence="N"),
        foldback=FoldbackEvaluationRequest(
            precursor_sequence="CCTCAGCA",
            nick_boundary=Boundary(offset=2),
            retained_tract_span=Span(start=Boundary(offset=2), end=Boundary(offset=6)),
            protected_region=Span(start=Boundary(offset=0), end=Boundary(offset=2)),
            turn_extension="T",
            foldback_arm=foldback_arm,
            constraints=hop.FoldbackConstraints(
                max_mismatches=0,
                terminal_paired_bp_min=4,
                terminal_paired_bp_max=4,
                max_uninterrupted_paired_bp=4,
                max_added_nt=5,
                required_turn_nt=3,
                allow_protected_region_mismatches=False,
            ),
        ),
        basal=BasalDesignRequest(
            pairing=BasalPairingRequest(
                left_arm="AAAA",
                right_arm="TTTT",
                allow_gt_wobble=True,
            ),
            constraints=hop.BasalConstraintProfile(
                require_terminal_watson_crick=True,
                max_active_hard_mismatches=0,
                max_active_non_watson_crick_pairs=0,
                forbid_active_middle_double_hard=True,
                minimum_active_support=4.0,
                maximum_active_disruption=0.0,
                require_outer_hard_for_active_double=True,
                reject_compact_profiles=(),
                reserve_compact_profiles=(),
            ),
            acceptance="active_only",
            terminal_nick=NickEvent(boundary=Boundary(offset=4), strand=Strand.TOP),
        ),
        release=None,
        defaults_ref="example:defaults/resolved@1",
        catalog_ref="example:processing-catalog/synthetic@1",
        constraint_profile_ref="example:constraint-profile/explicit@1",
        processing_route_ref="example:processing-route/resolved-events@1",
        constraints=DesignLimits(max_candidates=1),
    )


def _release_request() -> ReleaseProjectionRequest:
    return ReleaseProjectionRequest(
        precursor_top_strand="TGCTGAGGTTTT",
        origin=Boundary(offset=0),
        nick=NickEvent(boundary=Boundary(offset=0), strand=Strand.TOP),
        release_cut=DuplexCut(
            top=Boundary(offset=9),
            bottom=Boundary(offset=8),
        ),
        release_site_span=Span(
            start=Boundary(offset=8),
            end=Boundary(offset=12),
        ),
        route=StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK,
        constraints=ReleaseProjectionConstraints(
            require_release_site_downstream_of_nick=True,
            require_complete_downstream_separation=True,
        ),
    )


def _component_spec() -> ResolvedHopSpec:
    data = _spec().model_dump(by_alias=True)
    data["basal"]["terminal_nick"] = None
    data["processing_route_ref"] = "example:assembly-route/inherited-components@1"
    return ResolvedHopSpec.model_validate(data)


def test_resolved_spec_compiles_mechanics_into_one_verified_plan_and_bundle(tmp_path: Path) -> None:
    compilation = hop.compile(_spec())

    assert compilation.report.status == "valid"
    assert compilation.plan.processing_route.kind == "resolved_events"
    assert compilation.plan.processing_route.foldback.report.status == "valid"
    assert compilation.plan.processing_route.basal.decision.status == "active"
    assert compilation.plan.final_insert.sequence == "AAAANTCAGCATCTGANTTTT"
    assert compilation.plan.source_oligo.sequence == "CCTCAGCA"
    assert "expected-intermediates.json" in compilation.artifacts
    assert "foldback-view.json" in compilation.artifacts
    assert "foldback-view.svg" in compilation.artifacts
    assert "basal-view.json" in compilation.artifacts
    assert "basal-view.svg" in compilation.artifacts
    intermediates = json.loads(compilation.artifacts["expected-intermediates.json"])
    assert intermediates["foldback"]["effective_turn_sequence"] == "CAT"

    output = compilation.write(tmp_path / "bundle")
    assert verify_bundle(output) == compilation.bundle


def test_resolved_components_compile_without_claiming_a_processing_route(tmp_path: Path) -> None:
    compilation = hop.compile(_component_spec())

    assert compilation.report.status == "valid"
    assert compilation.plan.processing_route.kind == "component_assembly"
    assert [step.operation for step in compilation.plan.processing_route.steps] == [
        "foldback",
        "basal_pairing",
        "assemble_insert",
    ]
    assert compilation.plan.source_oligo.sequence == compilation.plan.final_insert.sequence
    foldback_view = json.loads(compilation.artifacts["foldback-view.json"])
    assert foldback_view["kind"] == "foldback_junction"
    assert [panel["panel_id"] for panel in foldback_view["panels"]] == ["foldback_junction"]
    basal_view = json.loads(compilation.artifacts["basal-view.json"])
    assert basal_view["kind"] == "basal_pairing"
    assert [panel["panel_id"] for panel in basal_view["panels"]] == ["basal_junction"]

    output = compilation.write(tmp_path / "component-bundle")
    assert verify_bundle(output) == compilation.bundle


def test_component_assembly_preserves_optional_non_payload_stem_context() -> None:
    spec = _component_spec().model_copy(
        update={
            "stem_extension": hop.PairedStemExtensionRequest(
                left_arm="GCTA",
                right_arm="TAAC",
                allow_gt_wobble=True,
            )
        }
    )

    compilation = hop.compile(spec)

    assert compilation.plan.final_insert.sequence == "AAAAGCTANTCAGCATCTGANTAACTTTT"
    assert tuple(feature.role for feature in compilation.plan.features) == (
        "basal_left_arm",
        "stem_extension_left_arm",
        "payload",
        "foldback_junction",
        "paired_payload",
        "stem_extension_right_arm",
        "basal_right_arm",
    )
    route = compilation.plan.processing_route
    assert route.kind == "component_assembly"
    assert route.stem_extension is not None
    assert route.stem_extension.hard_mismatch_count == 1
    assert [step.operation for step in route.steps] == [
        "foldback",
        "basal_pairing",
        "stem_extension_pairing",
        "assemble_insert",
    ]
    intermediates = json.loads(compilation.artifacts["expected-intermediates.json"])
    assert intermediates["stem_extension"]["left_arm"] == "GCTA"


def test_absent_stem_extension_does_not_change_the_v1_serialized_surface() -> None:
    spec = _component_spec()
    compilation = hop.compile(spec)

    assert "stem_extension" not in spec.model_dump(mode="json", by_alias=True)
    route = compilation.plan.processing_route
    assert "stem_extension" not in route.model_dump(mode="json")
    assert tuple(feature.role for feature in compilation.plan.features) == (
        "basal_left_arm",
        "payload",
        "foldback_junction",
        "paired_payload",
        "basal_right_arm",
    )


def test_component_assembly_rejects_a_release_event_without_a_terminal_nick() -> None:
    data = _component_spec().model_dump(by_alias=True)
    data["release"] = _release_request().model_dump()

    with pytest.raises(ValidationError, match="terminal nick"):
        ResolvedHopSpec.model_validate(data)


def test_bundle_verification_replays_resolved_spec_policy(tmp_path: Path) -> None:
    output = hop.compile(_spec()).write(tmp_path / "resolved-policy-drift")
    spec_path = output / "hop-spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["foldback"]["constraints"]["required_turn_nt"] = 99
    spec_content = canonical_json_bytes(spec)
    spec_digest = sha256_digest(spec_content)
    spec_path.write_bytes(spec_content)

    plan_path = output / "hop-plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["spec_digest"] = spec_digest
    plan_content = canonical_json_bytes(plan)
    plan_path.write_bytes(plan_content)

    provenance_path = output / "provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["spec_digest"] = spec_digest
    provenance_content = canonical_json_bytes(provenance)
    provenance_path.write_bytes(provenance_content)

    manifest_path = output / "hop-bundle.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    replacements = {
        "hop-spec.json": spec_content,
        "hop-plan.json": plan_content,
        "provenance.json": provenance_content,
    }
    for artifact in manifest["artifacts"]:
        content = replacements.get(artifact["path"])
        if content is not None:
            artifact["digest"] = sha256_digest(content)
            artifact["size_bytes"] = len(content)
    manifest["spec_digest"] = spec_digest
    manifest["plan_digest"] = sha256_digest(plan_content)
    provisional = HopBundle.model_validate_json(json.dumps(manifest))
    manifest_digest = manifest_digest_for_bundle(provisional)
    manifest["manifest_digest"] = manifest_digest
    manifest["bundle_id"] = bundle_id(
        design_id=manifest["design_id"], manifest_digest=manifest_digest
    )
    manifest_path.write_bytes(canonical_json_bytes(manifest))

    with pytest.raises(BundleIntegrityError, match="cannot be replayed"):
        verify_bundle(output)


def test_resolved_spec_returns_diagnostics_before_compile() -> None:
    invalid = _spec(foldback_arm="CTAA")

    report = hop.check(invalid)

    assert report.status == "infeasible"
    assert [item.code for item in report.diagnostics] == [
        "HOP-FOLD-002",
        "HOP-FOLD-004",
    ]
    with pytest.raises(InfeasibleDesignError, match="HOP-FOLD-002"):
        hop.compile(invalid)


def test_resolved_compile_carries_released_state_into_plan_views_and_artifacts() -> None:
    spec = _spec().model_copy(update={"release": _release_request()})

    compilation = hop.compile(spec)

    assert compilation.plan.processing_route.kind == "resolved_events"
    assert compilation.plan.processing_route.released_state is not None
    assert compilation.plan.processing_route.released_state.active_product_sequence == "CCTCAGCA"
    assert compilation.plan.source_oligo.sequence == spec.release.precursor_top_strand
    assert compilation.plan.source_oligo.sequence != compilation.plan.final_insert.sequence
    assert "released-workflow-view.json" in compilation.artifacts
    assert "released-workflow-view.svg" in compilation.artifacts


def test_resolved_route_graph_includes_terminal_nick_before_insert_assembly() -> None:
    for spec in (_spec(), _spec().model_copy(update={"release": _release_request()})):
        route = hop.compile(spec).plan.processing_route
        assert route.kind == "resolved_events"
        terminal_nick_index = next(
            index for index, step in enumerate(route.steps) if step.operation == "terminal_nick"
        )
        assembly_index = next(
            index for index, step in enumerate(route.steps) if step.operation == "assemble_insert"
        )
        terminal_nick = route.steps[terminal_nick_index]
        assembly = route.steps[assembly_index]

        assert terminal_nick.input_states == ("basal_junction",)
        assert terminal_nick.output_state == "terminal_nicked_basal_junction"
        assert "terminal_nicked_basal_junction" in assembly.input_states
        assert terminal_nick_index < assembly_index


def test_resolved_route_rejects_disconnected_release_and_foldback_states() -> None:
    disconnected = _spec().model_copy(
        update={
            "release": ReleaseProjectionRequest(
                precursor_top_strand="AACGTTGTTCCAA",
                origin=Boundary(offset=0),
                nick=NickEvent(boundary=Boundary(offset=0), strand=Strand.TOP),
                release_cut=DuplexCut(
                    top=Boundary(offset=10),
                    bottom=Boundary(offset=9),
                ),
                release_site_span=Span(
                    start=Boundary(offset=9),
                    end=Boundary(offset=13),
                ),
                route=StrandExposureRoute.BOTTOM_ACTIVE_AFTER_TOP_NICK,
                constraints=ReleaseProjectionConstraints(
                    require_release_site_downstream_of_nick=True,
                    require_complete_downstream_separation=True,
                ),
            )
        }
    )

    report = hop.check(disconnected)

    assert [item.code for item in report.diagnostics] == ["HOP-ROUTE-001"]
    with pytest.raises(InfeasibleDesignError, match="HOP-ROUTE-001"):
        hop.compile(disconnected)


def test_resolved_plan_rejects_disconnected_serialized_step_topology() -> None:
    data = hop.compile(_spec()).plan.model_dump(mode="json", by_alias=True)
    route = data["processing_route"]
    assert isinstance(route, dict)
    steps = route["steps"]
    assert isinstance(steps, list)
    second = steps[1]
    assert isinstance(second, dict)
    second["input_states"] = ["unrelated_state"]

    with pytest.raises(ValidationError, match="available molecular states"):
        HopPlan.model_validate_json(json.dumps(data))


def test_resolved_plan_rejects_route_source_and_layout_drift() -> None:
    source_drift = hop.compile(_spec()).plan.model_dump(mode="json", by_alias=True)
    source = source_drift["source_oligo"]
    assert isinstance(source, dict)
    source["sequence"] = "AAAA"

    with pytest.raises(ValidationError, match="actual route input"):
        HopPlan.model_validate_json(json.dumps(source_drift))

    role_drift = hop.compile(_spec()).plan.model_dump(mode="json", by_alias=True)
    features = role_drift["features"]
    assert isinstance(features, list)
    first = features[0]
    assert isinstance(first, dict)
    first["role"] = "payload"

    with pytest.raises(ValidationError, match="each physical role once"):
        HopPlan.model_validate_json(json.dumps(role_drift))


def test_resolved_route_rejects_duplicate_step_ids_in_serialized_plan() -> None:
    data = hop.compile(_spec()).plan.model_dump(mode="json", by_alias=True)
    route = data["processing_route"]
    assert isinstance(route, dict)
    steps = route["steps"]
    assert isinstance(steps, list)
    first, second = steps[:2]
    assert isinstance(first, dict) and isinstance(second, dict)
    second["step_id"] = first["step_id"]

    with pytest.raises(ValidationError, match="step ids must be unique"):
        HopPlan.model_validate_json(json.dumps(data))


def test_resolved_plan_rejects_derived_foldback_and_insert_drift() -> None:
    foldback_drift = hop.compile(_spec()).plan.model_dump(mode="json", by_alias=True)
    route = foldback_drift["processing_route"]
    assert isinstance(route, dict)
    foldback = route["foldback"]
    assert isinstance(foldback, dict)
    foldback["designed_sequence"] = "AAAA"

    with pytest.raises(ValidationError, match="designed sequence"):
        HopPlan.model_validate_json(json.dumps(foldback_drift))

    insert_drift = hop.compile(_spec()).plan.model_dump(mode="json", by_alias=True)
    features = insert_drift["features"]
    assert isinstance(features, list)
    junction_feature = features[2]
    assert isinstance(junction_feature, dict)
    junction_feature["sequence"] = "A" * len(junction_feature["sequence"])
    final_insert = insert_drift["final_insert"]
    assert isinstance(final_insert, dict)
    final_insert["sequence"] = "".join(feature["sequence"] for feature in features)

    with pytest.raises(ValidationError, match="resolved foldback junction"):
        HopPlan.model_validate_json(json.dumps(insert_drift))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("nick_boundary", {"offset": 999}, "inside the precursor"),
        ("nick_boundary", {"offset": 1}, "HOP-FOLD-001"),
        ("protected_region.end", {"offset": 999}, "inside the precursor"),
        ("terminal_paired_bp", 999, "paired run"),
        ("max_uninterrupted_paired_bp", 999, "paired run"),
    ],
)
def test_resolved_plan_rejects_serialized_foldback_state_drift(
    field: str,
    value: object,
    message: str,
) -> None:
    data = hop.compile(_spec()).plan.model_dump(mode="json", by_alias=True)
    route = data["processing_route"]
    assert isinstance(route, dict)
    foldback = route["foldback"]
    assert isinstance(foldback, dict)
    if field == "protected_region.end":
        foldback["protected_region"]["end"] = value
    else:
        foldback[field] = value

    with pytest.raises(ValidationError, match=message):
        HopPlan.model_validate_json(json.dumps(data))


def test_resolved_plan_rejects_serialized_terminal_nick_drift() -> None:
    data = hop.compile(_spec()).plan.model_dump(mode="json", by_alias=True)
    route = data["processing_route"]
    assert isinstance(route, dict)
    route["terminal_nick"]["boundary"]["offset"] = 999

    with pytest.raises(ValidationError, match="basal arm length"):
        HopPlan.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("catalog_ref", "example:processing-catalog/other@1", "catalog and lock"),
        ("foldback_junction_ref", "hop:foldback-junction/other@1", "foldback and lock"),
        ("basal_junction_ref", "hop:basal-junction/other@1", "basal and lock"),
    ],
)
def test_resolved_plan_rejects_lock_reference_drift(
    field: str,
    value: str,
    message: str,
) -> None:
    data = hop.compile(_spec()).plan.model_dump(mode="json", by_alias=True)
    lock = data["lock"]
    assert isinstance(lock, dict)
    lock[field] = value

    with pytest.raises(ValidationError, match=message):
        HopPlan.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("retained_partner_sequence", "NOT_DNA", "DNA"),
        ("release_cut.top", {"offset": 999}, "inside the precursor"),
        ("active_product_sequence", "AAAAAAAA", "derive from the precursor"),
    ],
)
def test_resolved_plan_rejects_serialized_release_state_drift(
    field: str,
    value: object,
    message: str,
) -> None:
    spec = _spec().model_copy(update={"release": _release_request()})
    data = hop.compile(spec).plan.model_dump(mode="json", by_alias=True)
    route = data["processing_route"]
    assert isinstance(route, dict)
    released = route["released_state"]
    assert isinstance(released, dict)
    if field == "release_cut.top":
        released["release_cut"]["top"] = value
    else:
        released[field] = value

    with pytest.raises(ValidationError, match=message):
        HopPlan.model_validate_json(json.dumps(data))


def test_reserve_basal_profile_requires_explicit_acceptance() -> None:
    spec = _spec()
    reserve_basal = spec.basal.model_copy(
        update={
            "pairing": BasalPairingRequest(
                left_arm="AAAA",
                right_arm="TGGT",
                allow_gt_wobble=True,
            ),
            "constraints": spec.basal.constraints.model_copy(
                update={
                    "max_active_hard_mismatches": 4,
                    "max_active_non_watson_crick_pairs": 4,
                    "minimum_active_support": 0.0,
                    "maximum_active_disruption": 4.0,
                    "reject_compact_profiles": (),
                }
            ),
        }
    )

    report = hop.check(spec.model_copy(update={"basal": reserve_basal}))

    assert [item.code for item in report.diagnostics] == [
        "HOP-BASAL-002",
        "HOP-BASAL-003",
    ]
