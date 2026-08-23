from __future__ import annotations

import hop_design as hop
import hop_design.discovery as discovery
import hop_design.methods as methods
import hop_design.views as views

ROOT_FACADE = {
    "DEFAULT_PAYLOAD_SOURCE_LIMITS",
    "DEFAULT_SPEC_MAX_BYTES",
    "BasalConstraintProfile",
    "BasalDesignRequest",
    "BasalEvaluation",
    "BasalJunction",
    "BasalOption",
    "BasalPairingRequest",
    "BasePairCount",
    "Boundary",
    "BundleIntegrityError",
    "Compilation",
    "DegeneratePayload",
    "DesignLimits",
    "DesignSpaceBudgetExceededError",
    "DesignSpaceLimits",
    "DesignSpacePlan",
    "DesignSpaceRow",
    "Diagnostic",
    "DuplexCut",
    "DuplicateDesignSequenceError",
    "DuplicateDesignSequencePolicy",
    "DuplicatePayloadError",
    "DuplicateSequencePolicy",
    "ExactPayload",
    "FoldbackConstraints",
    "FoldbackEvaluation",
    "FoldbackEvaluationRequest",
    "FoldbackJunction",
    "FoldbackOption",
    "HairpinEncodingInsert",
    "HopSpec",
    "InfeasibleDesignError",
    "JunctionPairKind",
    "JunctionPairObservation",
    "NickEvent",
    "NickingAgent",
    "NucleotideCount",
    "PairedStemExtension",
    "PairedStemExtensionRequest",
    "PayloadCollection",
    "PayloadExpansionResult",
    "PayloadRecord",
    "PayloadSourceLimitError",
    "PayloadSourceLimits",
    "ProcessingCatalog",
    "ReleaseAgent",
    "ReleaseOption",
    "ReleaseProjectionConstraints",
    "ReleaseProjectionRequest",
    "ReleaseProjectionResult",
    "ResolvedDesignSpace",
    "ResolvedHopSpec",
    "Severity",
    "Span",
    "SpecSourceLimitError",
    "Strand",
    "StrandExposureRoute",
    "VariantBudgetExceededError",
    "VerifiedHopBundle",
    "check",
    "collect_payloads",
    "compile",
    "create_spec",
    "evaluate_basal_pairing",
    "evaluate_foldback",
    "evaluate_paired_stem_extension",
    "expand_payload",
    "load_csv_payloads",
    "load_fasta_payloads",
    "load_spec",
    "load_verified_bundle",
    "plan_design_space",
    "project_released_strand_state",
    "verify_bundle",
}

DISCOVERY_OPERATIONS = {
    "classify_motif_presence",
    "scan_nicking_agent",
    "scan_release_agent",
    "search_basal_candidates",
    "search_basal_processing_geometries",
    "search_basal_processing_routes",
    "search_foldback_arms",
    "search_foldback_precursors",
    "search_hairpin_junction_routes",
    "search_nicking_placements",
    "search_released_foldback_geometries",
    "search_released_foldback_precursors",
}

METHOD_OPERATIONS = {
    "compile_linear_source_method_bundle",
    "compile_linear_source_multinick_hairpin_pcr",
    "list_method_capabilities",
    "load_verified_method_bundle",
    "resolve_linear_source_hairpin_pcr_materials",
    "verify_method_bundle",
}

VIEW_OPERATIONS = {
    "build_basal_pairing_view",
    "build_basal_view",
    "build_foldback_junction_view",
    "build_foldback_view",
    "build_hairpin_junction_route_view",
    "build_method_trajectory_view",
    "build_released_foldback_precursor_view",
    "build_released_workflow_view",
    "render_workflow_svg",
}

DISCOVERY_FACADE = {
    "AdditionalNickConstraint",
    "BasalCandidate",
    "BasalCandidateExclusionStatus",
    "BasalCandidateExclusionSummary",
    "BasalCandidateSearchLimits",
    "BasalCandidateSearchRequest",
    "BasalCandidateSearchResult",
    "BasalProcessingGeometryRequest",
    "BasalProcessingGeometrySearchLimits",
    "BasalProcessingGeometrySearchResult",
    "BasalProcessingRouteSearchLimits",
    "BasalProcessingRouteSearchResult",
    "CandidateRejectionCode",
    "CandidateRejectionSummary",
    "CandidateSearchStatus",
    "CandidateSearchTruncation",
    "FoldbackPairingDomain",
    "FoldbackPrecursorCandidate",
    "FoldbackPrecursorSearchLimits",
    "FoldbackPrecursorSearchRequest",
    "FoldbackPrecursorSearchResult",
    "FoldbackSearchLimits",
    "FoldbackSearchRequest",
    "FoldbackSearchResult",
    "HairpinJunctionRouteSearchLimits",
    "HairpinJunctionRouteSearchResult",
    "MotifPresenceReport",
    "NickingPlacementBlocker",
    "NickingPlacementFeasibility",
    "NickingPlacementHit",
    "NickingPlacementSearchLimits",
    "NickingPlacementSearchResult",
    "NickingPlacementTarget",
    "NickingPlacementTruncation",
    "ReleasedFoldbackBaseDomain",
    "ReleasedFoldbackGeometryRequest",
    "ReleasedFoldbackGeometrySearchLimits",
    "ReleasedFoldbackGeometrySearchResult",
    "ReleasedFoldbackPrecursorBlocker",
    "ReleasedFoldbackPrecursorCandidate",
    "ReleasedFoldbackPrecursorSearchLimits",
    "ReleasedFoldbackPrecursorSearchRequest",
    "ReleasedFoldbackPrecursorSearchResult",
    "ResolvedNickSite",
    "ResolvedReleaseSite",
} | DISCOVERY_OPERATIONS

METHOD_FACADE = {
    "AdapterAnnealedComplex",
    "AdapterAnnealingRequest",
    "BindingOrientation",
    "CohesiveEnd",
    "CovalentBond",
    "DenaturedFragmentSet",
    "DestinationReadiness",
    "EndChemistry",
    "Fragment",
    "FragmentLengthSelection",
    "HairpinPcrDuplex",
    "LengthSelectedFragmentSet",
    "LineageDirection",
    "LineageStrand",
    "LigatedHairpin",
    "LigationEndPreparation",
    "LinearSourceHairpinPcrMaterialsPlan",
    "LinearSourceHairpinPcrMaterialsSpec",
    "LinearSourceMultinickHairpinPcrPlan",
    "LinearSourceMultinickHairpinPcrRequest",
    "LinearSourceMultinickHairpinPcrResult",
    "MaterialBaseLineage",
    "MethodBundle",
    "MethodCapability",
    "MethodCompilation",
    "MethodImplementationStatus",
    "MethodInputExactness",
    "MethodKind",
    "MethodOutcome",
    "MethodResolutionError",
    "MethodResolutionStatus",
    "MolecularStrand",
    "MultiSiteNickedDuplex",
    "OligoBinding",
    "OligoModification",
    "ProcessMaterial",
    "ProcessMaterialRole",
    "ProcessOligo",
    "PrimerBinding",
    "RestrictionDigestProduct",
    "SequenceProjection",
    "SourcePcrDuplex",
    "StrandEnd",
    "StrandPairObservation",
    "VerifiedMethodBundle",
} | METHOD_OPERATIONS

VIEW_FACADE = {
    "TrackDirection",
    "ViewFeature",
    "ViewPairing",
    "ViewPanel",
    "ViewTrack",
    "WorkflowView",
} | VIEW_OPERATIONS


def test_package_root_is_the_exact_design_language_facade() -> None:
    assert set(hop.__all__) == ROOT_FACADE
    assert len(hop.__all__) == len(ROOT_FACADE)
    assert all(hasattr(hop, name) for name in hop.__all__)

    for specialized_name in DISCOVERY_OPERATIONS | METHOD_OPERATIONS | VIEW_OPERATIONS:
        assert not hasattr(hop, specialized_name)


def test_discovery_facade_exposes_bounded_queries_and_contracts() -> None:
    assert set(discovery.__all__) == DISCOVERY_FACADE
    assert len(discovery.__all__) == len(DISCOVERY_FACADE)
    assert all(hasattr(discovery, name) for name in discovery.__all__)
    assert all(callable(getattr(discovery, name)) for name in DISCOVERY_OPERATIONS)
    for contract in (
        discovery.BasalCandidateSearchRequest,
        discovery.FoldbackPrecursorSearchResult,
        discovery.HairpinJunctionRouteSearchResult,
        discovery.ReleasedFoldbackGeometrySearchResult,
    ):
        assert contract.__module__.startswith("hop_design.")


def test_method_facade_exposes_one_named_method_boundary() -> None:
    assert set(methods.__all__) == METHOD_FACADE
    assert len(methods.__all__) == len(METHOD_FACADE)
    assert all(hasattr(methods, name) for name in methods.__all__)
    assert all(callable(getattr(methods, name)) for name in METHOD_OPERATIONS)
    for contract in (
        methods.LinearSourceHairpinPcrMaterialsSpec,
        methods.LinearSourceMultinickHairpinPcrRequest,
        methods.MethodBundle,
        methods.MethodCapability,
        methods.RestrictionDigestProduct,
    ):
        assert contract.__module__.startswith("hop_design.")


def test_view_facade_exposes_projection_and_rendering_only() -> None:
    assert set(views.__all__) == VIEW_FACADE
    assert len(views.__all__) == len(VIEW_FACADE)
    assert all(hasattr(views, name) for name in views.__all__)
    assert all(callable(getattr(views, name)) for name in VIEW_OPERATIONS)
    assert views.WorkflowView.__module__.startswith("hop_design.")
    assert not hasattr(views, "compile")
