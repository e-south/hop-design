"""Condition an upstream sequence domain on one explicit source release action.

This is a necessary placement condition in the supplied source frame. It does
not claim whole-route support or exclude alternative endpoint embeddings.
"""

from dataclasses import dataclass

from hop_design.kernel.construction.basal.programs import resolve_future_release_action
from hop_design.kernel.construction.sequence_sets import SequenceSetBuilder, SequenceSetLimitError
from hop_design.models.construction.basal_release import BasalFutureReleaseAction
from hop_design.models.construction.complete.source_preparation.policy import (
    ConstrainedSourceSsdnaPolicy,
    UpstreamSequenceLengthRange,
)
from hop_design.models.construction.sequence_sets import MAX_SEQUENCE_VARIABLES, SequenceSet
from hop_design.models.enzymes import CharacterizedEnzyme
from hop_design.models.sequence import iupac_bases, normalize_dna_sequence


def _context_pattern(policy: ConstrainedSourceSsdnaPolicy, length: int) -> tuple[str, int]:
    """Return the authored pattern and ordinary length-first address origin."""
    if type(length) is not int or length < 1:
        raise ValueError("Source context length must be a positive integer.")
    if length > MAX_SEQUENCE_VARIABLES:
        raise SequenceSetLimitError("Source context exceeds the sequence-set variable capacity.")
    specification = policy.upstream_sequence_spec
    if isinstance(specification, str):
        if length != len(specification):
            raise ValueError("Source context length is outside its authored domain.")
        return specification, 0
    assert isinstance(specification, UpstreamSequenceLengthRange)
    if not specification.min_length_nt <= length <= specification.max_length_nt:
        raise ValueError("Source context length is outside its authored domain.")
    size = len(iupac_bases(specification.base_spec))
    origin = sum(size**n for n in range(specification.min_length_nt, length))
    return specification.base_spec * length, origin


@dataclass(frozen=True)
class SourceContextPopulation:
    """Compact contexts for one action; members retain ordinary canonical ranks."""

    sequences: SequenceSet
    authored_pattern: str
    canonical_origin: int

    def member_at(self, ordinal: int) -> tuple[str, int]:
        word = self.sequences.member_at(ordinal)
        return word, self.canonical_rank(word)

    def canonical_rank(self, word: str) -> int:
        """Locate an authored word, including words outside the conditioned subset."""
        rank = 0
        for base, symbol in zip(word, self.authored_pattern, strict=True):
            domain = tuple(sorted(iupac_bases(symbol)))
            rank = rank * len(domain) + domain.index(base)
        return self.canonical_origin + rank


def admit_source_contexts(
    *,
    policy: ConstrainedSourceSsdnaPolicy,
    length_nt: int,
    local_source_sequence: str,
    payload_boundary_nt: int,
    enzyme: CharacterizedEnzyme,
    action: BasalFutureReleaseAction,
    max_decisions: int,
    max_operations: int,
) -> SourceContextPopulation:
    """Intersect context bases with the explicit source-site and end footprint.

    ``local_source_sequence`` is exact, oriented payload-forward, and begins
    immediately after the variable context. ``payload_boundary_nt`` is relative
    to that local sequence. The supplied window must contain every required base
    after the context. An insufficient right-hand window raises; it cannot prove
    incompatibility with unprovided downstream sequence. A site before the start
    of this explicit source is absent in this frame. Callers must separately prove
    that no added primer sequence or alternative embedding can supply it before
    using an empty population to exclude a whole-route branch.
    """
    pattern, origin = _context_pattern(policy, length_nt)
    if action.requirement.product_end != "left" or (
        action.requirement.recognition_material != "source_duplex"
    ):
        raise ValueError("Source conditioning requires an explicit source-material left action.")
    if resolve_future_release_action(enzyme, action.requirement) != action:
        raise ValueError("Source release action must match its exact enzyme definition.")
    local_source_sequence = normalize_dna_sequence(local_source_sequence, allow_degenerate=False)
    if type(payload_boundary_nt) is not int or not 0 <= payload_boundary_nt <= len(
        local_source_sequence
    ):
        raise ValueError("Payload boundary must lie within the exact local source window.")
    payload_boundary = length_nt + payload_boundary_nt
    end = action.source_end_placement(payload_boundary=payload_boundary, nick_offset_nt=0)
    assert end is not None
    windows = (action.source_recognition_placement(payload_boundary=payload_boundary), end)
    if any(start + len(word) > length_nt + len(local_source_sequence) for start, word in windows):
        raise ValueError("The exact local source window does not contain every required base.")
    domains = [set(iupac_bases(symbol)) for symbol in pattern]
    for start, word in windows:
        if start < 0:
            domains[0].clear()
            continue
        for position, symbol in enumerate(word, start=start):
            allowed = iupac_bases(symbol)
            if position < length_nt:
                domains[position].intersection_update(allowed)
            elif local_source_sequence[position - length_nt] not in allowed:
                domains[0].clear()
    builder = SequenceSetBuilder(
        length_nt=length_nt, max_nodes=max_decisions, max_operations=max_operations
    )
    sequences = builder.freeze(builder.from_domains(domains))
    return SourceContextPopulation(sequences, pattern, origin)


def protected_context_suffix_nt(
    *,
    local_prefix_nt: int,
    nick_offset_nt: int,
    adapter_annealing_nt: int,
    left_paired_gap_bp: int,
    left_end_nt: int,
) -> int:
    """Conservatively protect context that can reach association or the left end.

    Frame: variable context precedes an exact payload-forward local basal prefix;
    the bottom nick lies inside that prefix. Association extends upstream from
    that nick, while the left released footprint extends upstream from the payload.
    Protect their union, including paired bases that might later be discarded.
    The result can exceed the available context length; that is not an exclusion
    and must not be silently reinterpreted as a valid annealing span.

    This coordinate bound is not a general product-equivalence proof. Exact
    embedding, primer copying, auxiliary policies and complete-route admission
    remain required before any completion can replace preparation enumeration.
    """
    values = (
        local_prefix_nt,
        nick_offset_nt,
        adapter_annealing_nt,
        left_paired_gap_bp,
        left_end_nt,
    )
    if (
        any(type(value) is not int or value < 0 for value in values)
        or adapter_annealing_nt < 1
        or nick_offset_nt > local_prefix_nt
    ):
        raise ValueError("Context protection requires nonnegative counts and an embedded nick.")
    return max(
        0,
        nick_offset_nt + adapter_annealing_nt - local_prefix_nt,
        left_paired_gap_bp + left_end_nt - local_prefix_nt,
    )


@dataclass(frozen=True, init=False)
class SourceContextCompletionGroups:
    """Exact context groups over a protected suffix, not complete constructions.

    The input may contain correlated constraints. Projection existentially removes
    the remaining prefix; conditioning a group recovers its exact permitted full
    contexts without recombining independent marginals. No group is a molecular
    witness, and no candidate has been compiled merely because a group is nonempty.
    """

    sequences: SequenceSet
    protected_suffix_nt: int
    _projection: SequenceSet | None
    _max_decisions: int
    _max_operations: int

    @classmethod
    def create(
        cls,
        sequences: SequenceSet,
        *,
        protected_suffix_nt: int,
        max_decisions: int,
        max_operations: int,
    ) -> "SourceContextCompletionGroups":
        if (
            not isinstance(sequences, SequenceSet)
            or type(protected_suffix_nt) is not int
            or not 0 <= protected_suffix_nt <= sequences.length_nt
        ):
            raise ValueError("Protected suffix must lie within the exact context length.")
        # Validate resource bounds even when the protected projection is empty.
        builder = SequenceSetBuilder(
            length_nt=protected_suffix_nt or sequences.length_nt,
            max_nodes=max_decisions,
            max_operations=max_operations,
        )
        projection = (
            None
            if protected_suffix_nt == 0
            else builder.freeze(
                builder.project_window(
                    sequences,
                    start=sequences.length_nt - protected_suffix_nt,
                    end=sequences.length_nt,
                )
            )
        )
        instance = object.__new__(cls)
        for key, value in (
            ("sequences", sequences),
            ("protected_suffix_nt", protected_suffix_nt),
            ("_projection", projection),
            ("_max_decisions", max_decisions),
            ("_max_operations", max_operations),
        ):
            object.__setattr__(instance, key, value)
        return instance

    @property
    def group_count(self) -> int:
        return (
            int(self.sequences.cardinality > 0)
            if self._projection is None
            else self._projection.cardinality
        )

    def suffix_at(self, group: int) -> str:
        if type(group) is not int or not 0 <= group < self.group_count:
            raise ValueError("Completion group lies outside the projected context domain.")
        return "" if self._projection is None else self._projection.member_at(group)

    def group_of(self, context: str) -> int:
        if not self.sequences.contains(context):
            raise ValueError("Context is not a member of the exact input domain.")
        return (
            0
            if self._projection is None
            else self._projection.rank_of(context[-self.protected_suffix_nt :])
        )

    def completions(self, group: int) -> SequenceSet:
        """Recover a compact conditional domain; a selected word still needs admission."""
        suffix = self.suffix_at(group)
        if not suffix:
            return self.sequences
        builder = SequenceSetBuilder(
            length_nt=self.sequences.length_nt,
            max_nodes=self._max_decisions,
            max_operations=self._max_operations,
        )
        source = builder.import_set(self.sequences)
        pattern = builder.from_iupac("N" * (self.sequences.length_nt - len(suffix)) + suffix)
        return builder.freeze(builder.intersection(source, pattern))
