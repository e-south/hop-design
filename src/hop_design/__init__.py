"""Public design-language facade for HOP Design."""

from hop_design._facade import PUBLIC_FACADE_NAMES as _PUBLIC_FACADE_NAMES
from hop_design.api import (
    check,
    collect_payloads,
    compile,
    create_spec,
    evaluate_basal_pairing,
    evaluate_foldback,
    evaluate_paired_stem_extension,
    expand_payload,
    load_csv_payloads,
    load_fasta_payloads,
    load_spec,
    load_verified_bundle,
    plan_design_space,
    project_released_strand_state,
    verify_bundle,
)
from hop_design.design.bundle import VerifiedHopBundle
from hop_design.design.design_space import (
    DesignSpaceBudgetExceededError,
    DuplicateDesignSequenceError,
)
from hop_design.design.loading import DEFAULT_SPEC_MAX_BYTES, SpecSourceLimitError
from hop_design.design.payloads import (
    DEFAULT_PAYLOAD_SOURCE_LIMITS,
    DuplicatePayloadError,
    PayloadSourceLimitError,
    VariantBudgetExceededError,
)
from hop_design.design.result import Compilation
from hop_design.export.bundle import BundleIntegrityError
from hop_design.models.basal import BasalPairingRequest
from hop_design.models.basal_policy import (
    BasalConstraintProfile,
    BasalDesignRequest,
    BasalEvaluation,
)
from hop_design.models.bundle import HopBundle
from hop_design.models.catalog import NickingAgent, ProcessingCatalog, ReleaseAgent
from hop_design.models.coordinates import BasePairCount, Boundary, NucleotideCount, Span
from hop_design.models.design_space import (
    BasalOption,
    DesignSpaceLimits,
    DesignSpacePlan,
    DesignSpaceRow,
    DuplicateDesignSequencePolicy,
    FoldbackOption,
    ReleaseOption,
    ResolvedDesignSpace,
)
from hop_design.models.diagnostics import CheckReport, Diagnostic, InfeasibleDesignError, Severity
from hop_design.models.foldback import (
    FoldbackConstraints,
    FoldbackEvaluation,
    FoldbackEvaluationRequest,
)
from hop_design.models.junction import (
    BasalJunction,
    FoldbackJunction,
    JunctionPairKind,
    JunctionPairObservation,
    Strand,
)
from hop_design.models.payload import DegeneratePayload, ExactPayload
from hop_design.models.plan import HairpinEncodingInsert
from hop_design.models.sources import (
    DuplicateSequencePolicy,
    PayloadCollection,
    PayloadExpansionResult,
    PayloadRecord,
    PayloadSourceLimits,
)
from hop_design.models.spec import DesignLimits, HopSpec, ResolvedHopSpec
from hop_design.models.stem import PairedStemExtension, PairedStemExtensionRequest
from hop_design.models.strand_state import (
    DuplexCut,
    NickEvent,
    ReleasedStrandState,
    ReleaseProjectionConstraints,
    ReleaseProjectionRequest,
    ReleaseProjectionResult,
    StrandExposureRoute,
)

__all__ = list(_PUBLIC_FACADE_NAMES)
