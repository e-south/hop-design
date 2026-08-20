from __future__ import annotations

import hop_design as hop


def test_public_facade_exposes_standalone_mechanics_without_internal_imports() -> None:
    assert callable(hop.evaluate_foldback)
    assert callable(hop.search_foldback_arms)
    assert callable(hop.evaluate_basal_pairing)
    assert callable(hop.project_released_strand_state)
    assert callable(hop.expand_payload)
    assert callable(hop.load_fasta_payloads)
    assert callable(hop.load_csv_payloads)
    assert callable(hop.classify_motif_presence)
    assert callable(hop.scan_nicking_agent)
    assert callable(hop.scan_release_agent)
    assert hop.FoldbackConstraints.__module__.startswith("hop_design.")
    assert hop.BasalConstraintProfile.__module__.startswith("hop_design.")
    assert hop.ProcessingCatalog.__module__.startswith("hop_design.")
    assert hop.ReleaseProjectionRequest.__module__.startswith("hop_design.")


def test_public_facade_exposes_supporting_contracts_and_integrity_operations() -> None:
    public_contracts = (
        hop.BasalEvaluation,
        hop.BasalPairKind,
        hop.Boundary,
        hop.FoldbackEvaluation,
        hop.FoldbackSearchRequest,
        hop.FoldbackSearchResult,
        hop.BasalJunction,
        hop.FoldbackJunction,
        hop.JunctionPairKind,
        hop.JunctionPairObservation,
        hop.MotifPresenceReport,
        hop.PayloadCollection,
        hop.PayloadExpansionResult,
        hop.ReleaseProjectionResult,
        hop.ResolvedNickSite,
        hop.ResolvedReleaseSite,
        hop.Span,
        hop.Strand,
        hop.WorkflowView,
    )

    assert all(contract.__module__.startswith("hop_design.") for contract in public_contracts)
    assert callable(hop.load_spec)
    assert callable(hop.verify_bundle)
    assert issubclass(hop.DuplicatePayloadError, ValueError)
    assert issubclass(hop.VariantBudgetExceededError, ValueError)
    assert issubclass(hop.BundleIntegrityError, ValueError)
    assert issubclass(hop.InfeasibleDesignError, ValueError)
