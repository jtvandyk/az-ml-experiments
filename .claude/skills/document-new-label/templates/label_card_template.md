# Label: `{{OUTCOME}}`

**Family:** {{FAMILY}}
**Source:** {{SOURCE}}
**Owner:** {{OWNER}}
**Card created:** {{TODAY}}

---

## 1. Operational definition

TODO: state the threshold rule in pseudocode. Examples by family:

- **onset** — `label_t = 1 if event_t >= THRESHOLD AND no event in [t-K, t-1]`
- **delta** — `label_t = 1 if indicator_t - indicator_{t-1} < -DELTA_THRESHOLD`
- **percentile** — `label_t = 1 if events_t > q90(events_{country, training_years})`
- **triangulated** — `label_t = 1 if source_A AND source_B`
- **weak-supervision** — list the labeling functions, then `P(label=1 | LFs) > 0.5`

```python
# TODO: paste the actual rule used in the source-pull or feature-engineering notebook
```

## 2. Base rate

| Window | Positives | Total country-years | Base rate |
|---|---|---|---|
| Train (≤2018) | TODO | TODO | TODO |
| Val (2019–2021) | TODO | TODO | TODO |
| Test (2022–2024) | TODO | TODO | TODO |

If base rate < 0.1%, AUPRC is the only meaningful headline metric — see `.claude/metric-interpretation-guide.md` §1.

## 3. Coverage

- **Countries included:** TODO (e.g. all African countries; or FEWS-NET set only)
- **Year range:** TODO–TODO
- **Missing-treatment:** TODO — choose one:
  - `0` (assume no event) — appropriate when source has full coverage
  - `NA` (unknown) — appropriate for partial coverage like FEWS-NET

## 4. Sensitivity to threshold / peace-spell window

For onset and delta families, document how the positive count changes as the
threshold or peace-spell window varies. This is a real result, not a tuning
artifact — small changes have large effects on rare-event class balance.

| Variant | Positives | Base rate | AUPRC ceiling (val) |
|---|---|---|---|
| TODO `K=1` | TODO | TODO | TODO |
| TODO `K=2` (chosen) | TODO | TODO | TODO |
| TODO `K=3` | TODO | TODO | TODO |
| TODO `K=5` | TODO | TODO | TODO |

State the rationale for the chosen variant in one sentence.

## 5. Source-agreement rate

(Only relevant for `triangulated` family — delete this section otherwise.)

- **Sources compared:** TODO
- **Agreement rate (both code positive | either codes positive):** TODO%
- **Sample of disagreements (with brief assessment):** TODO

## 6. Construct-validity gaps

What does this operational definition NOT capture? Be specific. Examples:

- TODO: "UCDP's 25-battle-death threshold misses sub-threshold violence and is biased toward media-covered conflicts."
- TODO: "Peace-spell window `K=2` codes a recurrence in year 4 as a *new* onset, even when it's clearly a continuation of the same conflict dynamics."
- TODO: "Coverage gap pre-2000 — earlier years exist in the source but are excluded by the panel start."

## 7. References

- TODO: Source dataset citation (e.g. UCDP-GED v23.1, Sundberg & Melander 2013)
- TODO: Methodology paper(s) that grounded the threshold choice
- TODO: Comparable label cards from prior projects, if any
