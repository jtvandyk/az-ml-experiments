---
name: refactor-backlog-add
description: Append a consistently-formatted entry to docs/refactor-backlog.md (creating it if missing). Use when surfacing a deferred refactor, known bug, or follow-up that won't be fixed in the current change.
---

# Add an entry to the refactor backlog

Locks in a consistent format so the backlog stays scannable: every entry has a title, priority, problem, proposed fix, and blast-radius assessment. Auto-numbers entries.

## When to use

- You've finished a fix or feature but spotted adjacent issues you don't want to address in the same change.
- A code review surfaced a concern that's real but out of scope.
- You're about to commit and want to capture tech debt before it slips your mind.

## When NOT to use

- Bugs you're fixing right now — just fix them.
- Speculative "we might want to refactor X someday" notes — those rot. The bar is "real, bounded, has a proposed fix."

## Steps

1. **Draft the four fields** before invoking the script:
   - **Title** — imperative phrase (e.g. "Vectorise Section C spatial spillover").
   - **Problem** — what's wrong, with a file/cell pointer.
   - **Proposed fix** — concrete approach, not "TBD."
   - **Blast radius** — what files change; what could regress; how to verify.

2. **Pick a priority** — `high` (blocks correctness or shipping), `medium` (real cost, no immediate forcing function), `low` (nice-to-have).

3. **Run the script:**

   ```bash
   python3 .claude/skills/refactor-backlog-add/scripts/add_backlog_entry.py \
       --title "Vectorise Section C spatial spillover" \
       --priority medium \
       --problem "notebooks/02_feature_engineering/03_engineer_derived_features.ipynb cell 73d861a2 writes per-row via df.at[idx, col] = value, which is O(n) per write." \
       --fix "Build per-feature pd.Series, then concat + merge once at the end." \
       --blast-radius "Single cell in 02/03. Output should be byte-identical to the current implementation; add a simple regression test that runs both implementations on a 100-row panel and asserts equality."
   ```

   The script appends an auto-numbered entry to `docs/refactor-backlog.md`. If the file doesn't exist, the script creates it with a standard header.

4. **Verify with `git diff -- docs/refactor-backlog.md`** before committing.

## Entry format

Each entry is a `## <NN>. <Title>` heading followed by the four fields:

```markdown
## 7. Vectorise Section C spatial spillover

**Priority:** medium

**Problem.**
notebooks/02_feature_engineering/03_engineer_derived_features.ipynb cell
73d861a2 writes per-row via `df.at[idx, col] = value`, which is O(n) per
write.

**Proposed fix.**
Build per-feature pd.Series, then concat + merge once at the end.

**Blast radius.**
Single cell in 02/03. Output should be byte-identical to the current
implementation; add a simple regression test that runs both implementations
on a 100-row panel and asserts equality.

---
```

## Helper script

- `scripts/add_backlog_entry.py` — pure stdlib; auto-numbers; creates the file with a header if missing.
