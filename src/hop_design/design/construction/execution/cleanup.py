"""Prove permitted removal using the already selected source nicking methods."""

from pathlib import Path

from hop_design.models.construction.complete.composition_domain import source_context_count
from hop_design.models.construction.complete.evaluation import CompositionRejectionCode
from hop_design.models.construction.source_partition.policy import SacrificialFragmentPolicy
from hop_design.models.construction.source_partition.request import (
    ConstructionSourcePartitionPolicy,
    SourcePartitionEnumerationPolicy,
)
from hop_design.models.enzymes import (
    CharacterizedEnzyme,
    CharacterizedEnzymeCatalog,
    EnzymeClass,
    EnzymeProvisioningPolicy,
)

from ..complete.bundle import ConstructionCompilation
from ..public import compile_construction_from_local_realizations
from ..source import _load_construction_source
from ..source_partition.construction import construction_partition_request
from ..source_partition.discovery import discover_source_partitions
from ..source_partition.public import SourcePartitionDiscovery
from .context import LocalSelection


def compile_request_candidate(
    source_path: str | Path,
    *,
    design_bundle_path: str | Path,
    selection: LocalSelection,
    cleanup: SacrificialFragmentPolicy | None,
) -> ConstructionCompilation:
    """Compile one candidate, optionally proving cleanup before ordinary replay.

    A partition is specific to a source molecule. Survey completion pages already
    specialize source contexts; direct requests must do so explicitly. The exact
    compiler continues to consume a verified partition, never a permission.
    """
    if cleanup is not None:
        source = _load_construction_source(source_path)
        if (
            source_context_count(source.composition.materialization.source_preparation.source_ssdna)
            > 1
        ):
            raise ValueError(
                "Source cleanup requires an exact source context per candidate. "
                "Use released-insert discovery to examine source alternatives separately, or "
                "specify one upstream and downstream source sequence."
            )
    complete = compile_construction_from_local_realizations(
        source_path, design_bundle_path=design_bundle_path, **selection
    )
    if cleanup is None:
        return complete
    verified = selected_source_cleanup(complete, cleanup)
    if verified is None:
        return complete
    partition, identity = verified
    return compile_construction_from_local_realizations(
        source_path,
        design_bundle_path=design_bundle_path,
        **selection,
        source_partition=partition,
        source_partition_realization_id=identity,
    )


def selected_source_cleanup(
    compilation: ConstructionCompilation,
    permission: SacrificialFragmentPolicy,
) -> tuple[SourcePartitionDiscovery, str] | None:
    """Return a verified fixed-program cleanup, never a waiver of an extra site.

    This permission allows additional cuts by the source methods already chosen
    for this local pair. It does not introduce another enzyme search dimension.
    Every actionable site is replayed and the exact required survivors checked.
    """
    result = compilation._verified_source().result
    if result.realizations or not result.combination_dispositions:
        return None
    if len(result.combination_dispositions) != 1:
        raise ValueError(
            "Automatic source cleanup requires one exact source and local pair; "
            "use design discovery to evaluate the permitted alternatives separately."
        )
    choice = result.combination_dispositions[0]
    if (
        choice.rejection_reason is not CompositionRejectionCode.GLOBAL_ACTIONABLE_SITE_CONFLICT
        or result.basal_authority is None
    ):
        return None
    foldback = next(
        item
        for item in result.foldback_authority.realizations
        if item.foldback_realization_id == choice.foldback_realization_id
    )
    basal = next(
        item
        for item in result.basal_authority.realizations
        if item.basal_realization_id == choice.basal_realization_id
    )
    selected_ids = {binding.enzyme_id for binding in foldback.enzyme_bindings}
    selected_ids.add(basal.basal_nick.enzyme_id)
    definitions: dict[str, CharacterizedEnzyme] = {}
    for provisioning in (
        result.foldback_authority.neighborhood.request.enzyme_provisioning,
        result.basal_authority.discovery.request.enzyme_provisioning,
    ):
        for enzyme in provisioning.catalog.enzymes:
            if enzyme.enzyme_id in selected_ids:
                if enzyme.enzyme_id in definitions and definitions[enzyme.enzyme_id] != enzyme:
                    raise ValueError("Source methods disagree on an enzyme definition.")
                definitions[enzyme.enzyme_id] = enzyme
    if any(enzyme.enzyme_class is not EnzymeClass.NICKASE for enzyme in definitions.values()):
        return None
    ids = tuple(sorted(selected_ids))
    # A local foldback uses at most two enzymes plus one basal nickase. Exhaust
    # this finite subset domain, then select the exact already-chosen program.
    if not ids or len(ids) > 3 or set(ids) != set(definitions):
        raise ValueError("Source cleanup requires the recorded local nickase definitions.")
    count = 2 ** len(ids) - 1
    policy = ConstructionSourcePartitionPolicy(
        enzyme_provisioning=EnzymeProvisioningPolicy(
            catalog=CharacterizedEnzymeCatalog(
                catalog_id="hop:enzyme-catalog/selected-source-cleanup@1",
                enzymes=tuple(definitions[key] for key in ids),
            ),
            allowed_enzyme_ids=ids,
            forbidden_enzyme_ids=(),
            reserved_enzyme_ids=(),
            max_operations=len(ids),
            role_restrictions=(),
        ),
        fragment_policy=permission,
        max_enzymes_per_program=len(ids),
        enumeration=SourcePartitionEnumerationPolicy(
            max_search_nodes=count,
            max_realizations=count,
        ),
    )
    request = construction_partition_request(result, policy, combination_ordinal=0)
    # Opting into cleanup admits all cuts made by this fixed source program,
    # rather than borrowing a local-junction operation quota. A duplex has at
    # most two strand boundaries per position; the certificate checks the actual
    # cuts, discarded lengths and unchanged required survivors.
    request = request.model_copy(
        update={
            "enzyme_provisioning": request.enzyme_provisioning.model_copy(
                update={"max_operations": 2 * len(request.source.top_sequence_5prime)}
            )
        }
    )
    partition = SourcePartitionDiscovery._create(discover_source_partitions(request))
    matching = [item for item in partition._result.realizations if item.enzyme_ids == ids]
    if not matching:
        return None
    if len(matching) != 1:
        raise ValueError("A fixed source program must have one canonical fragment partition.")
    return partition, matching[0].realization_id
