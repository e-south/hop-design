# Contributing to HOP Design

HOP accepts focused changes that preserve its public ownership boundary and
scientific contracts. Start with the [maintainer map](docs/dev/README.md) for
code ownership and verification. Use the [user task index](docs/index.md) to
check the workflow affected by your change.

## Development loop

Install Node.js 22 or newer alongside Python/uv for the dependency-free browser
interaction tests. Node is a development requirement, not a HOP runtime dependency.

```bash
uv sync --locked
uv run pre-commit install
bash ./scripts/agent-preflight --strict
bash ./scripts/agent-verify --scope presentation  # for view-only changes
```

Choose the scope for the changed responsibility: `presentation` checks molecular
views and browser behavior; `source` runs all source tests and coverage; the
default `full` adds installed-package checks. Use `full` before merge or release,
for packaging/runtime-dependency changes, or when the boundary is uncertain.
Molecular rules, discovery, identity, admission and handoff changes require at
least `source`. The [verification map](docs/dev/performance.md#choose-the-verification-boundary)
defines these boundaries. Add `--workers 2` for a bounded parallel run; tests stay
grouped by fixture scope. Report the scope and worker count with the result.

Run the selected gate in the working checkout. Ignored runtime artifacts do not require
a clean copy: source checks use Git's tracked and nonignored inventory, while
the wheel smoke test checks the distributions themselves. See
[verification surfaces](SECURITY.md#verification-surfaces) for the exact boundary.

Add a failing test before changing behavior. Public schema or ownership changes
also require an ADR and updated schema/reference documentation. Generated bundle
digests must change only when the serialized contract changes intentionally.

## Module documentation

Start new Python modules with a purpose docstring. Include the project, repository
path and responsible team using this header:

```python
"""
--------------------------------------------------------------------------------
HOP Design
src/hop_design/path/to/module.py

Describe the module's responsibility in one sentence.

Maintainer(s): HOP Design contributors
--------------------------------------------------------------------------------
"""
```

Preserve existing author credits. A maintainer label identifies responsibility;
it does not assign authorship. Keep public operation details in their API docs
and use inline comments to explain non-obvious decisions.

## Test working files

Successful tests remove their temporary outputs. Shared fixtures remain available
until their module or session ends. Failed cases retain their working files;
pytest's normal retention keeps three sessions. To inspect a passing test's files,
use `-o tmp_path_retention_policy=all` for that focused run.

For an isolated run, set `PYTEST_DEBUG_TEMPROOT` to a new, empty directory. Remove
that owned scratch directory after reviewing the result. Interrupted processes
can leave locked temporary roots; establish their owner and process status before
removing them. Do not treat another repository's temporary files as HOP output.

Keep deliberate review artifacts and verification receipts separate from test
scratch. Preserve their requests, producer and checksums; do not archive every
temporary fixture merely because it was used in a passing test. When a shared
model changes, run its unit and contract checks before the expensive complete-route
suite. Merge/release verification still covers every test and installed-wheel parity.

## Pull requests

Keep pull requests narrow enough to review. Describe the contract affected,
negative-path tests, compatibility impact, and local verification. Main is
protected; changes merge through pull requests after required checks pass.

Do not include private datasets, application-specific identifiers, credentials,
machine-local paths, or output from neighboring repositories. See
[SECURITY.md](SECURITY.md) for vulnerability reports.
