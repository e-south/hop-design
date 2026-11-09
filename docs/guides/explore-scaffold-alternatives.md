# Explore scaffold alternatives and revise permissions

Start with the [stem-first workflow](discover-designs.md). Use these operations
when the obtained preparations do not yet offer the comparison you need. The
examples assume the public `construction` facade is imported and `stem` contains
your supplied sequence.

## Find different scaffold options

Ask for contrasts when another preparation with the same geometry would not help:

```bash
# Prioritize permitted scaffold alternatives while preserving the stem.
hop-design design discover \
  --stem ATAACTTCGTATAGCATACATTATACGAAGTTAT \
  --product released_insert --diversify loop_nt \
  --evaluations 16 --out loop-options --format text
```

`--diversify` changes the search order within the saved permissions. Repeat it for
joint dimensions, such as `--diversify foldback_arm_bp`. The same option works for
direct and adapter-ligated hairpins. The first-result policy remains available
when finding any complete preparation matters more than finding contrasts.

The Python equivalent is:

```python
# Discover from the same intent through Python.
choices = construction.discover_designs(
    {"stem_arm": stem, "product": "released_insert"},
    "loop-options",
    max_evaluations=16,
    objective={"kind": "diversity", "parameters": ["loop_nt"]},
)
progress = choices.query()["search_objective"]
```

`progress` identifies the dimensions, their molecular stages, and observed and
currently matching classes. These counts use complete preparations. A change of
end word alone does not count toward a loop-size objective. Continuation retains
the objective and examines more of the same permissions.

For insert routes using scaffold completion, search also responds to what it
has found. Within each search wave, it favors requested classes without a
complete witness. Failed candidates do not mark a class as covered. Earlier
unfinished work stays reachable, and continuation retains the same order and
observed classes. Hairpin option discovery stratifies its recorded local pairs;
its complete-result counts use the same definitions.

Available objectives cover loop length or loop sequence, foldback arm,
join displacement, nick strand, basal nick offset and adapter annealing minimum.
Use `foldback_method` or `basal_method` to seek different nickases in those roles.
These count the named nickase, not every enzyme in its preparation; direct
hairpins have no basal-method objective. Insert discovery also supports release
method, left/right sticky-end words and end-to-stem gaps.

For insert method objectives, use a context with
`source_context_objective: "paired_scaffold_completions"`. The scheduler reads
method identities from admitted local populations without expanding their
sequences, then gives priority to requested classes lacking a complete witness
within the current search wave. `all_words` does not support these two objectives.
Hairpin options instead stratify recorded local choices by the same nickase
identities. Neither mode introduces an unpermitted method or discards earlier
unfinished work, and a method contrast need not produce a different molecule.
Only parameters applicable to the requested product are accepted. Use
`--diversify loop_word` to explore sequence differences without supplying loop
words first. HOP reads candidates from the conditioned sequence domain and counts
the words in complete preparations. Use `loop_nt` for size contrasts; a loop word
already determines its size, so the two are not separate diversity objectives.
Neither requires a sticky-end word. An explicit permitted list of loop words
continues to restrict the search when a particular comparison is wanted.

When loop words are unspecified, insert discovery spreads its early geometry
search across permitted loop sizes. Different sizes lead to different sequence
populations; the actual words then guide sequence exploration and result counts.
Explicit words of the same size remain distinct choices. This ordering changes
neither the permitted molecules nor the requirement for a complete preparation.

For scaffold-completion searches, HOP also checks a bounded set of foldback cases
against existing sequence and source-primer requirements. Proven-empty cases receive
later priority; unknown and unexamined cases remain eligible. This avoids repeatedly
combining an empty foldback with different basal arrangements before a first result.

If the context permits only one value, a diversity objective cannot broaden it.
A stopped search also cannot establish that an unobserved class is impossible.

For a broader set of cloning interfaces, use:

```python
# Name the molecular features whose diversity should guide allocation.
objective = {
    "kind": "diversity",
    "parameters": ["left_end_word", "right_end_word", "left_gap", "right_gap"],
}
```

Pass this to the same `discover_designs` call, or repeat `--diversify` with those
names in the CLI. No end word needs to be supplied. Interface objectives favor
other targets after finding support, using joint sequence constraints to suggest
promising combinations. A bounded suggestion pass never excludes other targets;
each returned preparation still passes complete construction verification.
The suggestion pass spreads effort across permitted basal settings. Once an end
pair has a complete preparation, shorter continuation turns let other interfaces
enter sooner. Unresolved pairs keep their effort to reach a first preparation;
supported pairs remain available for further geometry and sequence alternatives.
Loop-only objectives instead favor contrasts within a shared interface. The
query's `search_objective.target_policy` records that distinction. More interface
breadth can mean fewer loop alternatives at the same computation budget.

## Preview a small permission change

Use a compact edit when the permitted arm range or method prevents the desired
comparison. Save this as `changes.json`:

```json
{"parameters": [{"key": "foldback_arm_bp", "minimum": 3, "maximum": 5}]}
```

```bash
# Preview an explicit permission change in a new result directory.
hop-design design revise designs --changes changes.json --out revised-permissions
hop-design design discover --revision revised-permissions \
  --diversify foldback_arm_bp --evaluations 16 --out revised-designs
```

The first command only previews the edit. Its report shows before/after domains
and conflicts with retained requirements. The second explicitly evaluates the
captured request. The parent discovery and any selections remain unchanged.
Before a first discovery, use `design revise --request intent.json` instead of an
existing result directory.

From Python, call `preview = choices.revise(changes)`, inspect
`preview.report_text`, then `preview.execute("revised-designs", ...)`. A saved
preview can be relocated and loaded with `construction.load_design_revision`.

For a method edit, use `{"methods": {"basal": ["Nb.BtsI"]}}`. HOP resolves the
name against the captured enzyme catalog and shows the affected role permissions.
If the characterization is absent, include its explicit catalog definition in
`add_enzymes`, including its recognition and cleavage requirements. Existing
hard method requirements and forbidden-method policies still apply.

An arm edit can exceed a retained-length limit. The preview identifies that
dependency; an explicit `"retained_limits_nt": {"foldback": 20}` can revise the
limit when appropriate. Fixed materials remain fixed. A ready preview means the
declarations agree; complete construction is established by execution.
