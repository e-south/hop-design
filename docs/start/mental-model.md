---
doc_id: hop-mental-model
title: Five claims HOP keeps separate
intent: Establish the distinct claims made by design, discovery, methods, verification, and downstream use.
audience:
  - users
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
doc_type: explanation
journey:
  - compile
  - discover
  - method
  - verify
  - integrate
---

# Five claims HOP keeps separate

The most important HOP invariant is a chain of non-equivalences:

```text
a sequence exists
    != a production method is available
    != that method resolves for this request
    != the product fits a destination
    != the experiment succeeds
```

HOP represents those questions on five sibling surfaces.

## 1. Design language

A design declares hairpin anatomy and authored sequence. HOP derives the paired
payload, evaluates structural relationships, and produces one deterministic
`HairpinEncodingInsert`. Successful compilation establishes design identity;
it makes no production-method claim.

## 2. Discovery language

A discovery query asks a bounded competency question, such as which catalog
geometries can place a cut or support a declared junction. Its result reports
candidate identity, neutral order, and whether the declared space was completed,
proved infeasible, or truncated. Selection remains caller-owned.

## 3. Method language

A method request supplies exact materials to one named production method. A
successful method compiler derives exact molecular states, transitions, and a
destination-neutral product. Only the method plan owns temporal production
history. A design derivation owns no ordered production chronology, although a
resolved design may preserve caller-asserted nick or release geometry used to
derive its encoding.

## 4. Provenance and verification

Design and method bundles are separate immutable authorities. Byte checks and
semantic replay establish internal consistency. A digest-equality relation can
bind a design encoding to a method product's encoding projection, but one valid
bundle does not imply that a second valid bundle is related to it.

## 5. Ecosystem and downstream use

A caller may place a verified product in a larger construct, assess an exact
state, record protocol context, or interpret observations. Those activities do
not redefine HOP anatomy or retroactively change method feasibility.

```text
campaign or human intent
          |
          v
 design --+-- discovery -- caller selection
          |
          +-- named method -- destination-neutral product
          |
          +-- provenance and verification
                              |
                              v
             placement, assessment, study, execution
```

Continue with the [design language](../language/overview.md),
[discovery language](../discovery/overview.md), [method language](../methods/overview.md),
or [ecosystem ownership](../ecosystem/ownership-boundaries.md).
