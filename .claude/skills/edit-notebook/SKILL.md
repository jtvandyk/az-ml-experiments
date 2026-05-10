---
name: edit-notebook
description: Apply structured cell-ID-keyed edits to a Jupyter notebook (.ipynb) using a small Python helper. Use when modifying notebooks where the Read/Edit tools struggle with size or where multiple cells need to change atomically.
---

# Edit notebook by cell ID

Pattern for applying edits to Jupyter notebooks via JSON manipulation. Faster and safer than line-based Edit on large notebooks; preserves cell IDs, outputs, and metadata.

## When to use

- Editing a notebook with cells too large to fit comfortably in the Read tool (typical: feature-engineering notebooks in `notebooks/02_feature_engineering/`).
- Atomic multi-cell edits (e.g. updating `RAW_PREFIXES`, `_join_iso3_source` call, and a comment block in one go).
- Notebook edits where the user expects idempotency on re-run.

## When NOT to use

- One-line tweaks where Edit works cleanly — don't reach for this.
- Edits that involve adding/removing cells or reordering — write a one-off Python script that mirrors the helper pattern instead (the helper assumes cells already exist).

## Steps

1. **Inspect the notebook to confirm cell IDs and structure.**

   ```bash
   python3 .claude/skills/edit-notebook/scripts/inspect_notebook.py <path/to/notebook.ipynb>
   ```

   Output is one line per cell: index, cell_type, id, first 90 chars of source. Use this to verify the cell IDs you intend to target actually exist before writing edits.

2. **Build the edits spec.** Two equivalent forms:

   - **Inline JSON** passed via stdin (best for 1–3 small edits):
     ```bash
     echo '{"edits":[{"cell_id":"cell-3","new_source":"..."}]}' \
       | python3 .claude/skills/edit-notebook/scripts/edit_notebook.py <notebook.ipynb> -
     ```
   - **Edits file** at `/tmp/edits.json` (best for many edits or long sources):
     ```json
     {
       "edits": [
         {"cell_id": "cell-3", "new_source": "..."},
         {"cell_id": "1d1b69ef", "old_substring": "foo", "new_substring": "bar"}
       ]
     }
     ```
     Then: `python3 .claude/skills/edit-notebook/scripts/edit_notebook.py <notebook.ipynb> /tmp/edits.json`

   Each edit must specify `cell_id` and exactly one of:
   - `new_source` — replace the entire cell source
   - `old_substring` + `new_substring` — verbatim substring replacement. Errors if not found (unless `optional: true`) **or** if the substring matches more than one site (unless `replace_all: true`). Make `old_substring` more specific to disambiguate.
   - `append` — append text to the existing source (with a leading newline if needed)

3. **Apply and verify.** The helper writes the notebook back with stable indent (`json.dumps(..., indent=1, ensure_ascii=False)` to match the project convention). Confirm with `git diff -- <notebook.ipynb>`.

## Repo conventions the helper respects

- **Indent style:** `indent=1` (matches what `notebooks/02_feature_engineering/03_engineer_derived_features.ipynb` and other recent edits use).
- **Trailing newline:** preserved.
- **Cell IDs:** unchanged. The helper errors if a `cell_id` is not found rather than appending a new cell — fail loud.
- **Outputs and execution counts:** untouched. Run notebooks separately if you need outputs refreshed.

## Helper scripts

- `scripts/inspect_notebook.py` — lists cells. Prints `[idx] type id  first-line-preview`.
- `scripts/edit_notebook.py` — applies an edits spec to a notebook in place.

Both scripts have `--help`. They are pure stdlib (no extra deps).
