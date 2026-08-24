---
name: monte-carlo-forecast
description: Run a Monte Carlo forecast on a prepared dataset and deliver it as an executed Jupyter notebook. Use when the user asks to forecast a completion or delivery date, ask "will we make it by X", estimate how much will be done by a date, quantify delivery risk with confidence levels, run a simulation or Monte Carlo, or invokes /monte-carlo-forecast. Suggests a dataset from data/prepared/, sends the user to /build-pipeline when no prepared data exists, reuses or replaces an existing forecast notebook after asking, and writes exactly one forecast file per notebook.
---

# Monte Carlo Forecast

Turn a delivery question into a probabilistic answer: simulate thousands of futures from
observed throughput, and report the answer as confidence levels rather than a single date.

The deliverable is a notebook the user can also drive themselves — parameters at the top,
interactive controls inside, charts that show what the simulation actually did.

## Inputs

| What | Where |
|---|---|
| Prepared table (read-only input) | `data/prepared/<slug>.parquet` |
| Its semantic layer | `data/prepared/<slug>_semantic_layer.yml` |
| Source semantic layer (context only) | `data/semantic_layer.yml` |
| Generated notebook | `notebooks/forecast_<slug>.ipynb` |
| Forecast output | `data/forecasts/<slug>_forecast.csv` |

`<slug>` is the prepared dataset's slug (e.g. `release-v24-forecast`). A second forecast on the
same dataset gets a variant suffix: `notebooks/forecast_<slug>-<variant>.ipynb` writing
`data/forecasts/<slug>-<variant>_forecast.csv`. Never two notebooks writing one file.

## Hard rules

1. **No prepared data → no forecast.** If `data/prepared/` holds no `.parquet`, stop and tell the
   user to run `/build-pipeline` first. Do not forecast off the raw database.
2. **The prepared file is the only data input, and it is read-only.** Hash the parquet before and after the run and assert it matches.
3. **Governed definitions are authoritative.** Scope, throughput and every other quantity come
   from the prepared file's semantic layer, using its embedded SQL verbatim.
   `allow_governed_metric_sql_rewrite` is `false`.
4. **`proposed_additions:` are not governed.** For `release-v24-forecast` this means story-point
   forecasting is off the table — the file supports issue-count forecasting only. Do not work
   around it; say so and forecast counts.
5. **Never impute.** Missing estimates, absent weeks and unassigned releases stay as they are.
   A week with no deliveries is a zero-throughput week only if the calendar spine says the week
   existed — never drop it silently and never invent one.
6. **Assumptions are the user's, not yours.** Every modelling choice that is not fixed by the
   semantic layer — history window, throughput scope, scope growth, trials, confidence levels —
   is asked for, defaulted visibly, and written into the notebook's Assumptions section.
7. **Seeded and reproducible.** Every simulation runs from an explicit `RANDOM_SEED`. Two runs of
   the same notebook with the same parameters produce the same numbers.
7b. **The notebook must execute headlessly, cold, with no interaction.** Two mistakes break this
   every time and both are designed out in the references, not debugged later: paths are
   repo-root relative so the notebook needs the `os.chdir` line (`nbconvert` starts the kernel in
   `notebooks/`), and the widget panel's initial run renders as ordinary cell output — writing
   into a displayed `ipywidgets.Output` deadlocks the executor until its timeout.
8. **One notebook, exactly one output file.** No side tables, no per-cut CSVs, no chart PNGs
   written to disk. The executed notebook is the record of the run.
9. **Never silently overwrite an existing forecast notebook.** Ask first (step 2).

## Steps

### 1. Find the prepared data and suggest a dataset

```bash
ls -1 data/prepared/*.parquet 2>/dev/null
```

- **Nothing found** → stop here. Tell the user there is no prepared data to forecast from and
  that `/build-pipeline` builds it, governed by `data/semantic_layer.yml`. Offer to run it. Do
  not improvise a dataset from the raw database.
- **Exactly one** → suggest it by name, with its grain and row count read from
  `data/prepared/<slug>_semantic_layer.yml` (`metadata.description`, `sources[].objects[].grain`,
  `lineage.row_count`), and confirm it is the one to forecast.
- **Several** → list them with slug, grain, row count and the analysis each was built for, and
  recommend the one whose `metadata.description` matches the user's question. Ask which.

### 2. Check for an existing forecast notebook

```bash
ls -1 notebooks/forecast_*.ipynb 2>/dev/null
```

If one already exists for the chosen dataset, do not touch it yet. Read its Goal, Parameters and
Result cells and tell the user what it currently forecasts, with the parameters and headline
percentiles from its last run. Then ask which they want:

| Choice | What you do |
|---|---|
| **Re-run it unchanged** | Skip to step 6 with the notebook as-is (refreshed input data, same assumptions). |
| **Update its parameters and re-run** | Edit the Parameters cell only, then step 6. Never patch a later cell to work around a parameter. |
| **Create a new forecast** | Ask for a short variant name, generate `notebooks/forecast_<slug>-<variant>.ipynb`, leave the existing notebook and its output file untouched. |

If the user's new question is materially different from the existing notebook's Goal, say so and
recommend a new notebook rather than an in-place edit.

### 3. Read the prepared semantic layer and check freshness

Read `data/prepared/<slug>_semantic_layer.yml` in full — it carries the governed metrics you must
reuse, the `proposed_additions` notes that constrain the forecast, and a `lineage` block.

Compare `lineage.source_database_sha256` with the current raw database:

```bash
shasum -a 256 data/agile_issues.db
```

If they differ, the prepared file predates the current raw data. Report it and offer the
`prepare-<slug>` skill (or `/build-pipeline`) before forecasting. If the user wants to proceed
anyway, record it in the notebook's Assumptions as a stated limitation.

Also note `lineage.parameters.AS_OF_DATE`. Delivery state is frozen at that date; a forecast from
a different as-of date needs the pipeline re-run, not a recomputation here.

### 4. Collect the inputs and assumptions from the user

Ask for these — one round, with the defaults visible, using the prepared layer to fill in what it
already knows. Do not ask about anything the layer fixes.

| Input | Default / source | Why it matters |
|---|---|---|
| Forecast question | from the user | Becomes the notebook Goal, verbatim. |
| Mode | `when` | `when` = date to finish a known scope. `how_many` = items done by a target date. |
| Scope filter | the release named in the question | Which rows count as the backlog. |
| Remaining scope | governed `remaining_issue_count` under the filter | The finish line. Show the governed number before accepting an override. |
| Throughput history window | all complete weeks; suggest last 8–12 | Old weeks may describe a different team. |
| Throughput scope | team-wide | Release-only throughput is thin and understates capacity; team-wide assumes the team stays on this release. State whichever is chosen. |
| Scope growth factor | `1.0` | Splits and newly discovered work inflate the backlog. `1.15` = 15 % more work than the backlog shows. |
| Trials | `10000` | More trials, smoother tails. |
| Confidence levels | `0.50, 0.70, 0.85, 0.95` | The rows of the output file. |
| Target date | none | If given, the notebook reports the probability of hitting it. |
| Random seed | `42` | Reproducibility. |

Then play the assumptions back as a short list and get a yes before generating anything. If the
question needs a quantity the layer does not define, ask rather than invent it — the layer's
`governance.missing_or_ambiguous_definition` is `ask`.

### 5. Generate the notebook

Write `notebooks/forecast_<slug>.ipynb` with `nbformat`, following
[references/notebook-structure.md](references/notebook-structure.md): six sections — **Goal**,
**Assumptions**, **Parameters**, **Input file(s)**, **Steps**, **Result(s)** — each opened by a
markdown header, parameters isolated in one assignments-only cell, no hidden state between steps.

The simulation algorithms, the required charts and the interactive control panel are specified in
[references/simulation-and-visuals.md](references/simulation-and-visuals.md). Follow it: the
charts are the point of the notebook, not decoration.

### 6. Execute it in a fresh kernel

```bash
python3 -m venv .venv 2>/dev/null; .venv/bin/pip install -q pandas pyarrow pyyaml numpy matplotlib ipywidgets jupyter ipykernel nbconvert
```

```bash
.venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 notebooks/forecast_<slug>.ipynb
```

`--execute` always starts a fresh kernel, so the run proves the notebook works from a cold start
with the parameter cell alone — no widget interaction required. If it fails, fix the **generator**
and regenerate the whole notebook; never patch cells or outputs by hand.

Two failures account for almost every broken first run. Build them out rather than debugging them:

| Symptom | Cause | Fix |
|---|---|---|
| `FileNotFoundError` on the input parquet | `nbconvert` starts the kernel in `notebooks/`, but the Parameters cell holds repo-root relative paths | the mandatory `os.chdir` line in the imports cell |
| A cell hangs, then ends at *exactly* the timeout value, kernel at 0 % CPU | the widget cell's initial run writes into a displayed `ipywidgets.Output`, re-parenting iopub messages so the executor never sees idle | initial run renders as ordinary cell output; `Output` only for click-driven redraws |

A hang is not slowness. Confirm with `ps -o %cpu` on the kernel, then bisect with the traced
preprocessor in
[references/simulation-and-visuals.md](references/simulation-and-visuals.md#when-execution-hangs)
rather than raising the timeout. If the notebook includes computational heavy analysis, 
use simple parameters (like fewer trial runs) and consider this more as a smoke test instead of running the 
full-fledged analysis just for test purposes.

### 7. Verify the run

- Exactly one file was written under `data/forecasts/`, and it is the one this notebook owns.
- The prepared parquet hash printed at the start matches the one printed at the end.
- The percentiles are monotonic (P50 ≤ P70 ≤ P85 ≤ P95) and every confidence level asked for is
  present as a row.
- The analysis-gate quality checks the prepared layer carries still pass against the input file.

### 8. Hand the notebook over

Tell the user they can drive it themselves:

```bash
.venv/bin/jupyter lab notebooks/forecast_<slug>.ipynb
```

Edit the Parameters cell and *Run All* for a reproducible run, or move the sliders in the
**Steps → interactive controls** cell to explore, then run the **Result(s)** cell to write the
file with whatever is currently loaded.

## Report back

Close with: the forecast question; the notebook path; the input file with its row count and grain;
the governed definitions used by name; the remaining scope and the throughput history the
simulation drew from (weeks, min/median/max); the percentile table (confidence → weeks →
date, or → item count); the probability of hitting the target date if one was given; the single
output path; the before/after hash of the input parquet; and the assumptions a reviewer should
challenge first.

State the result as a range with confidence attached. Never report a single date as *the*
forecast, and never round a P50 into a promise.
