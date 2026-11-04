"""Translate terminal intent into bounded candidate settings, never product facts."""

from dataclasses import dataclass
from itertools import product
from typing import Any

from hop_design.kernel.construction.basal.domains import solve_basal_sequence_domain
from hop_design.kernel.construction.basal.programs import BasalPlacementFailure
from hop_design.models.construction.complete.source_preparation.policy import FixedSourceSsdnaPolicy
from hop_design.models.construction.discovery.request import ScaffoldDiscoveryRequest
from hop_design.models.construction.search import BasalGeometryDomain

from ..basal.traversal import iter_basal_work_units


@dataclass(frozen=True)
class TerminalSetting:
    nick: int
    annealing: int
    tail: str


def _inside(interval: dict[str, int] | None, value: int) -> bool:
    return interval is None or interval["minimum"] <= value <= interval["maximum"]


def _conflict(field: str, value: Any, inherited: str, prior: Any, edit: str) -> dict[str, Any]:
    return {
        "requested_field": field,
        "requested_value": value,
        "inherited_field": inherited,
        "inherited_value": prior,
        "explicit_edit": edit,
    }


def _source_positions(request: ScaffoldDiscoveryRequest) -> set[tuple[int, int]]:
    """Possible (nick offset, stem start) settings before complete molecular admission."""
    product_request = request.product
    basal = product_request.construction_source().basal
    assert basal is not None
    source = product_request.materialization.source_preparation.source_ssdna
    positions: set[tuple[int, int]] = set()
    assert product_request.basal is not None
    assert isinstance(basal.geometry_domain, BasalGeometryDomain)
    if isinstance(source, FixedSourceSsdnaPolicy):
        # Every literal occurrence is only a candidate. Complete source embedding
        # and the achieved-state requirement decide whether it is the actual stem.
        sequence = source.material.sequence_5prime
        for start in range(len(sequence)):
            if sequence.startswith(product_request.stem_arm, start):
                positions.update((n, start) for n in product_request.basal.geometry.nick_offsets_nt)
                if len(positions) > 256:
                    raise ValueError(
                        "Terminal preview exceeds 256 fixed-source candidate positions."
                    )
        return positions
    context = getattr(source, "upstream_sequence_spec", "")
    lengths = (
        (len(context),)
        if isinstance(context, str)
        else range(context.min_length_nt, context.max_length_nt + 1)
    )
    if len(lengths) > 256:
        raise ValueError("Terminal preview exceeds 256 source lengths; narrow the upstream domain.")
    # Placement solving reuses the basal kernel, including enzyme-dependent source
    # offsets. It does not enumerate bases or assert reaction feasibility.
    targets = basal.geometry_domain.exact_targets()
    levels = set()
    for index, target in enumerate(targets):
        if index >= 256:
            raise ValueError("Terminal preview exceeds 256 basal geometries; narrow the domain.")
        levels.add(len(target.pairing_constraints) + target.nick_offset_nt)
    examined = 0
    for level in sorted(levels):
        if level > basal.search.max_retained_overhead_nt:
            continue
        for unit in iter_basal_work_units(basal, retained_overhead_nt=level):
            examined += 1
            if examined > 256:
                raise ValueError(
                    "Terminal preview exceeds 256 placements; narrow geometry or methods."
                )
            domain = solve_basal_sequence_domain(
                payload_sequence=unit.payload_sequence,
                target=unit.target,
                endpoint=basal.endpoint,
                program=unit.program,
            )
            if isinstance(domain, BasalPlacementFailure):
                continue
            positions.update(
                (unit.target.nick_offset_nt, n + domain.payload_span.start.offset) for n in lengths
            )
            if len(positions) > 256:
                raise ValueError(
                    "Terminal preview exceeds 256 source positions; narrow the domain."
                )
    return positions


def terminal_settings(
    request: ScaffoldDiscoveryRequest, scaffold: dict[str, Any]
) -> tuple[list[TerminalSetting] | None, list[dict[str, Any]]]:
    """V2 authorizes prefix trimming or caller-supplied exact tails during redesign."""
    five, three = scaffold.get("five_prime_unpaired_nt"), scaffold.get("three_prime_unpaired_nt")
    if (five is None and three is None) or request.preparation_changes.adapter_redesign != "allow":
        return None, []
    if request.product.endpoint.value != "adapter_ligated_hairpin":
        return [], [
            _conflict(
                "scaffold",
                scaffold,
                "product.endpoint",
                request.product.endpoint.value,
                "Terminal redesign currently supports the adapter_ligated_hairpin endpoint. "
                "Request that endpoint or preserve preparation settings "
                "and check achieved termini.",
            )
        ]
    adapter = request.product.materialization.adapter_ligation
    assert adapter is not None
    inherited_tail = getattr(adapter, "three_prime_handle_sequence", "")
    declared = request.preparation_changes.three_prime_tail_sequences
    if declared is not None:
        tails = sorted(word for word in declared if _inside(three, len(word)))
    elif three is None:
        tails = [inherited_tail]
    else:
        tails = [inherited_tail[:n] for n in range(len(inherited_tail) + 1) if _inside(three, n)]
    if not tails:
        return [], [
            _conflict(
                "scaffold.three_prime_unpaired_nt",
                three,
                "product.materialization.adapter_ligation",
                adapter.model_dump(mode="json"),
                "No permitted tail has this length. Supply exact three_prime_tail_sequences "
                "under preparation_changes or explicitly revise the terminal requirement; "
                "length alone does not authorize new bases.",
            )
        ]
    basal = request.product.basal
    assert basal is not None
    geometry = basal.geometry
    open_side = scaffold.get("open_side_paired_positions")
    settings: set[tuple[int, int]] = set()
    if five is None:
        paired = (
            [None] if open_side is None else range(open_side["minimum"], open_side["maximum"] + 1)
        )
        if len(paired) > 256:
            raise ValueError("Terminal preview exceeds 256 paired dimensions; narrow the range.")
        minimum = geometry.minimum_adapter_annealing_nt or max(
            1, len(request.product.expanded_pairing_constraints())
        )
        settings.update(
            (nick, minimum if size is None else max(1, size - nick))
            for nick, size in product(geometry.nick_offsets_nt, paired)
        )
    else:
        for nick, start in sorted(_source_positions(request)):
            # A candidate terminal prefix plus pairing reaches the authored stem.
            lower, upper = five["minimum"], min(five["maximum"], start)
            if upper - lower > 256:
                raise ValueError("Terminal preview exceeds 256 terminal lengths; narrow the range.")
            for unpaired in range(lower, upper + 1):
                annealing = start - nick - unpaired
                if annealing >= max(
                    1, len(request.product.expanded_pairing_constraints())
                ) and _inside(open_side, start - unpaired):
                    settings.add((nick, annealing))
    if not settings:
        return [], [
            _conflict(
                "scaffold.five_prime_unpaired_nt",
                five,
                "scaffold.open_side_paired_positions"
                if open_side is not None
                else "product.basal.geometry",
                open_side if open_side is not None else geometry.model_dump(mode="json"),
                "No candidate pairing span satisfies these dimensions within the declared source "
                "and local contacts. Explicitly revise a conflicting dimension "
                "or source permission.",
            )
        ]
    if len(settings) * len(tails) > 256:
        raise ValueError(
            "Terminal expansion exceeds 256 branches; narrow terminal ranges or sequences."
        )
    return [
        TerminalSetting(nick, annealing, tail)
        for (nick, annealing), tail in product(sorted(settings), tails)
    ], []
