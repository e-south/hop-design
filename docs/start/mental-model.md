---
doc_id: hop-mental-model
title: Claims HOP keeps separate
intent: Establish the distinct claims made by payload specification, construction discovery, methods, verification, and downstream use.
audience:
  - users
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-30
doc_type: explanation
journey:
  - compile
  - discover
  - method
  - verify
  - integrate
---

# Claims HOP keeps separate

Start with the duplex sequence you want the hairpin to present. That payload
stays fixed while HOP searches the surrounding sequence and enzyme arrangements.
You can inspect where a junction is possible, what bases and cuts it requires,
and whether selected junctions can be completed into the requested product.

The most important HOP invariant is a chain of non-equivalences:

```text
a sequence exists
    != a production method is available
    != that method resolves for this request
    != the product fits a destination
    != the experiment succeeds
```

HOP represents those questions on sibling surfaces. The same separation holds
when the starting point is a bounded substrate space or a payload-centered
construction request.

## 1. Design language

A design declares hairpin anatomy and authored sequence. HOP derives the paired
payload, evaluates structural relationships, and produces one deterministic
`HairpinEncodingInsert`. Successful compilation establishes design identity;
it makes no production-method claim.

## 2. Construction discovery and composition

A construction request starts from the final duplex payload, selects a
source-realization route family and requested endpoint, and asks which exact
foldback and basal neighborhood realizations satisfy the declared geometry and
molecular constraints. Source coordinates are route-specific; they never
replace final-payload coordinates as the biological authority.

Foldback-local discovery treats the PCR-amplified material as a duplex. Unless
the caller constrains the physical nick strand, HOP searches both exact nick
strands by default and retains only routes permitted by the enzyme's declared
recognition orientation and cut contract.

Discovery is finite and traverses increasing retained overhead. An existence
search keeps a witness for each accessible work unit; an all-realizations search
keeps every exact alternative within its reported coverage. Results distinguish
exhausted, policy-stopped, and truncated searches from feasible, infeasible, or
unknown outcomes.
Grouping does not replace realization identity, and selection remains
caller-owned.

The file-oriented construction operation accepts local requests in one strict
source document and the design as a separate verified bundle. HOP discovers
and replay-verifies the local authorities, composes the bounded whole route,
requires the exact endpoint encoding to agree with the verified design, and
can persist one portable construction bundle. The source cannot assert design
or result identities.

## 3. Method language

A method request supplies exact materials to one named production method. A
successful method compiler derives exact modeled molecular states, transitions,
and a destination-neutral molecular-product model. Only a route or method plan owns temporal
production history. Construction routes use ordered reaction stages;
concurrent operations in one stage resolve against the same pre-stage state. A
design derivation owns no ordered production chronology.

The requested endpoint determines method obligations. A direct
single-stranded hairpin does not require adapter capture, PCR, or Type IIS end
generation merely because a clone-ready endpoint does.

Replay verifies that those modeled states and products follow from the request.
It does not establish laboratory execution, physical construction, or recovery
of a molecule.

## 4. Provenance and verification

Design, construction, and method bundles are distinct immutable authorities.
A construction bundle embeds and replay-verifies the design authority used for
whole-route composition. A method bundle records one named method request and
its derived products independently. Byte checks and semantic replay establish
internal consistency; one valid authority does not imply laboratory execution
or that an unrelated authority belongs to it.

## 5. Ecosystem and downstream use

A caller may place a verified product in a larger construct, assess an exact
state, record protocol context, or interpret observations. Those activities do
not redefine HOP anatomy or retroactively change method feasibility.

```text
campaign or human intent
          |
          v
 payload -+-- local discovery -- exact realizations
          |
          +-- route composition -- requested endpoint product
          |
          +-- provenance and verification
                              |
                              v
             study evidence, manuscript, downstream use
```

HOP owns the molecular computation through the verified endpoint projection.
Client studies own experimental observations and scientific asset
promotion. Manuscript systems own claims, evidence cutoff, and accepted
composition.

Continue with the [design language](../language/overview.md),
[discovery language](../discovery/overview.md), [method language](../methods/overview.md),
or [ecosystem ownership](../ecosystem/ownership-boundaries.md).
