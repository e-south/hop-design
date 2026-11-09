# Resolve optional construction intent before discovery

## Context

A user can know the stem and intended product without knowing which sticky ends,
scaffold dimensions or preparation methods to choose. Requiring an exact end pair
at entry makes the user choose before seeing complete alternatives. Exhaustive
interface coverage is a different task from finding initial preparations.

## Decision

`ConstructionIntent` expresses a supplied stem, intended product and optional
constraints. Resolution intersects that intent with a captured, versioned
construction context and produces an existing strict request. The result records
authored intent, effective permissions and their origin. Execution quotas remain
separate from molecular permissions.

`DesignChoices` is the common query, selection, figure, atlas and retrieval
interface. Endpoint implementations delegate to the existing survey or scaffold
owners. Exact compilation and full preparation verification remain unchanged.
A selected preparation retains its identity across both figures and material
retrieval. Public CLI and companion clients consume these same objects.

Omitted end words express no preference within the declared interface type.
Exact words remain hard constraints. Independent lists of alternatives explicitly
permit their Cartesian combinations. Joint pair rosters are rejected by this
entry contract; they are never silently converted into independent lists.

## Consequences

First use requires a stem and intended product. Default geometry, enzymes and
materials are inspectable rather than copied into every user request. Filtering
recorded results does not evaluate more candidates or relax requirements.

Insert discovery can resume its saved search. Hairpin endpoints use the existing
bounded scaffold backend and preserve their own final state, with no insert-release
requirement. Progressive execution publishes immutable verified prefixes and resumes
only unexamined pairs, with the stopping policy separate from molecular permissions.
Repeated queries reuse an admitted immutable pool; rendering
and retrieval retain their existing verification boundaries.

Reference-bound refinement and required comparison extend this same object.
The intent facade binds a caller's saved selection to a snapshot; variant query
and comparison owners retain molecular preservation and membership assessment.
All path eligibility and conditional counts consume their decisions. A new
preservation query describes a molecule's surroundings independently of the
filters used to find that molecule. Native parameter-only queries and v1 single
selections remain valid; preserved selections and set selections have explicit
schemas. CLI adapters and companion recipes do not implement comparison logic.

See the [introductory workflow](../../guides/discover-designs.md) for the public
commands and the [Python interface](../../reference/python-api.md) for integration.
