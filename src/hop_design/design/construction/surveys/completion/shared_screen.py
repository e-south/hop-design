"""Bounded request-wide necessary relations, inverted into candidate basal frames."""

from collections.abc import Callable
from dataclasses import dataclass
from itertools import product
from math import prod

from hop_design.kernel.construction.sequence_sets import SequenceSetLimitError
from hop_design.models.construction.product_pairing import ProductConstraintConflict
from hop_design.models.construction.sequence_sets import SequenceSet
from hop_design.serialization import canonical_json_bytes, sha256_digest

from ...execution.feedback import DiscoveryCancelled
from ..geometry_order import GeometryOrder
from ..navigation.pages import Geometry
from .frame_admission import BasalAdmissions

# Computation/storage bounds only. Larger requests retain ordinary discovery.
MAX_SCREEN_FRAMES = 32768
MAX_SCREEN_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True)
class BasalScreen:
    """Only established necessary contradictions remove a frame from navigation.

    Exact targets and all foldback cases still receive ordinary full evaluation.
    Every invocation derives this screen afresh; no saved molecular claim is
    trusted because a cache or previous target happened to contain it.
    """

    admissions: BasalAdmissions
    groups: tuple[tuple[SequenceSet, tuple[Geometry, ...]], ...]
    unknown: tuple[Geometry, ...]
    digest: str
    frame_count: int

    @classmethod
    def build(
        cls, admissions: BasalAdmissions, *, should_stop: Callable[[], bool] | None = None
    ) -> "BasalScreen | None":
        sizes = admissions.branches.geometry_sizes
        factors = tuple(sizes[i] for i in (0, 1, 2, 3, 5))
        count = prod(factors)
        if count > MAX_SCREEN_FRAMES:
            return None
        groups: dict[str, tuple[SequenceSet, list[Geometry]]] = {}
        unknown: list[Geometry] = []
        facts: list[tuple[tuple[int, ...], str | None]] = []
        size = 0
        for frame in product(*(range(n) for n in factors)):
            if should_stop is not None and should_stop():
                raise DiscoveryCancelled("Stopped while screening shared basal constraints.")
            geometry = (*frame[:4], 0, frame[4])
            try:
                found = admissions.resolve(0, geometry)
            except (ProductConstraintConflict, SequenceSetLimitError):
                found = None
            if found is None:
                unknown.append(geometry)
                facts.append((frame, None))
                continue
            relation, digest = found
            if digest not in groups:
                size += len(canonical_json_bytes(relation))
                if size > MAX_SCREEN_BYTES:
                    return None  # Never publish a truncated negative screen.
                groups[digest] = relation, []
            groups[digest][1].append(geometry)
            facts.append((frame, digest))
        return cls(
            admissions,
            tuple((relation, tuple(frames)) for relation, frames in groups.values()),
            tuple(unknown),
            sha256_digest(canonical_json_bytes(facts)),
            count,
        )

    @property
    def facts(self) -> dict[str, object]:
        return {
            "scope": "necessary_end_pair_screen",
            "frames": self.frame_count,
            "unknown_frames": len(self.unknown),
            "distinct_relations": len(self.groups),
            "frame_relations_digest": self.digest,
        }

    def candidates(self, target: int, order: GeometryOrder) -> tuple[Geometry, ...]:
        words = "".join(self.admissions.branches.request.targets.pair_at(target))
        if tuple(map(len, order.costs)) != self.admissions.branches.geometry_sizes:
            raise ValueError("Shared screen order differs from its request dimensions.")
        frames = list(self.unknown)
        for relation, group in self.groups:
            if relation.contains(words):
                frames.extend(group)
        # The fixed foldback coordinate contributes the same cost to every key.
        return tuple(sorted(frames, key=lambda g: (order.cost(g), g)))
