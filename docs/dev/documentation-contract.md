# Write useful documentation

A reader should reach one working result before learning specialist controls.
Start each page with its title and the task it helps complete. Use the existing
[task index](../index.md) to route to guides and references.

## Guides

Show the input, the operation and an observable result. Keep commands copyable,
with short comments explaining intent. Use a small verified output or Python
REPL example when it helps a reader recognize success. Label placeholders and
excerpts. JSON remains valid JSON rather than acquiring comment syntax.

Put optional controls after the first complete workflow. Link to the owning
reference for field definitions instead of repeating its tables. Use a meaningful
heading or link to disclose detail; avoid administrative tables, document IDs,
verification dates and a fixed list of required sections. Git records editing
history. Runtime skills keep only the metadata their loader requires.

## References

Explain what callers supply, what HOP derives and which constraints apply. Name
units and coordinate frames where ambiguity could change a result. Describe
invalid input, an impossible request and an unfinished search distinctly.
Include identities and provenance where callers need them to reopen or verify a
result, rather than repeating internal machinery on every page.

A successful computation establishes modeled sequence and processing behavior.
Use “experimental evidence” for caller-owned observations. Keep this distinction
near the relevant claim without repeating a disclaimer in every paragraph.

## Check the result

Run `uv run python scripts/check_docs.py` to check titles, local links, heading
fragments, code fences and skill metadata. Exercise changed examples at their
owning CLI or Python boundary. Keep scientific values and public operations
unchanged during a prose edit.
