# Forecast notebook structure

`notebooks/forecast_<slug>.ipynb` has six sections, in this order. Each begins with a markdown
header cell, followed by its code cells. Build the file with `nbformat`.

A reader must be able to see the goal, what was assumed, what knobs exist, what went in, what was
simulated, and what came out — without reading any code. A second reader must be able to change
one slider and understand what moved.

## 1. Goal

Markdown only. The forecast question in the user's own words; one paragraph on what decision the
answer supports; the mode (`when will it finish` or `how much by a date`); and the date of
generation. State plainly that the output is a distribution, not a date.

## 2. Assumptions

Markdown only. Everything the simulation takes as given, so a reviewer can challenge it:

- Input: the prepared file, its semantic layer `metadata.name` and `version`, and its
  `lineage.parameters.AS_OF_DATE` — delivery state is frozen at that date.
- The governed dimensions and metrics used, by name, reused verbatim.
- **Throughput is the model.** Future weeks are drawn from observed weekly throughput; the
  simulation assumes the next weeks resemble the sampled ones.
- The history window, and why (team composition, process changes, holidays).
- The throughput scope — team-wide or release-only — and what it implies.
- The scope growth factor and what it stands for (splits, discovered work).
- Weeks with no deliveries: present as zeros on the calendar spine, never dropped.
- Missing values are never imputed; issues without estimates still count as scope.
- What the forecast does **not** model: dependencies, individual issue size, staffing changes,
  scope removal, work started but unfinished.
- Any constraint carried from the layer's `proposed_additions.notes` (e.g. story-point sums are
  ungoverned, so this forecasts issue counts).
- Any limitation the user accepted during planning (e.g. a stale input file).

## 3. Parameters

One cell, assignments only, no logic, no I/O. This is the whole control surface for a
reproducible run:

```python
INPUT_PARQUET   = "data/prepared/<slug>.parquet"
INPUT_LAYER     = "data/prepared/<slug>_semantic_layer.yml"
OUTPUT_CSV      = "data/forecasts/<slug>_forecast.csv"

MODE                    = "when"        # "when" = date to finish scope; "how_many" = items by TARGET_DATE
SCOPE_RELEASE           = "v2.4"        # None = all releases
AS_OF_DATE              = "2026-08-19"  # must equal the input layer's lineage AS_OF_DATE
TARGET_DATE             = None          # optional commitment date to test

TRIALS                  = 10_000
CONFIDENCE_LEVELS       = [0.50, 0.70, 0.85, 0.95]
HISTORY_WEEKS           = 12            # None = every complete week in the file
THROUGHPUT_SCOPE        = "team"        # "team" = all releases; "release" = SCOPE_RELEASE only
SCOPE_GROWTH_FACTOR     = 1.00          # 1.15 = assume 15 % more work appears
SCOPE_OVERRIDE          = None          # None = use the governed remaining count
RANDOM_SEED             = 42
SAMPLE_TRIALS_TO_PLOT   = 200           # trial paths drawn on the spaghetti chart
MAX_WEEKS               = 260           # simulation guard rail
```

Every later cell reads these names. No cell redefines one.

A markdown cell right after it lists each parameter in one line of plain language, so the notebook
is usable by someone who will only ever touch this cell.

## 4. Input file(s)

Imports, the read-only load, the input hash, and the loaded semantic layer:

```python
%matplotlib inline
import ast, hashlib, os, pathlib, math, datetime as dt
import numpy as np, pandas as pd, yaml
import matplotlib.pyplot as plt

# Paths in the Parameters cell are repo-root relative, but `nbconvert --execute` starts the
# kernel in the notebook's own directory. Without this line every path in the notebook breaks
# with FileNotFoundError the moment it is run headlessly. Matches prep_<slug>.ipynb.
os.chdir(pathlib.Path.cwd().parent if pathlib.Path.cwd().name == "notebooks" else pathlib.Path.cwd())

df = pd.read_parquet(INPUT_PARQUET)
INPUT_HASH_START = hashlib.sha256(pathlib.Path(INPUT_PARQUET).read_bytes()).hexdigest()
LAYER = yaml.safe_load(open(INPUT_LAYER))
```

**Every path in the notebook is repo-root relative and the `os.chdir` line above is mandatory.**
It is idempotent, so *Run All* in Jupyter Lab (where the cwd is already the repo root) and a
headless `nbconvert` run both land in the same place.

Then, in this section and nowhere else:

- Print the input path, row count, grain (from the layer), and `INPUT_HASH_START`.
- Assert `AS_OF_DATE == LAYER["lineage"]["parameters"]["AS_OF_DATE"]`, with a message explaining
  that a different as-of date requires re-running the preparation pipeline.
- Look governed definitions up by name, raising on a miss — never falling back:

  ```python
  def governed(kind, name):
      for item in LAYER[kind]:
          if item["name"] == name:
              return item
      raise KeyError(f"{kind}.{name} not in {INPUT_LAYER}")
  ```

- Re-run the layer's `analysis_gate` quality checks against `df` and print a pass/fail table. A
  `severity: error` failure raises — do not forecast off a file that fails its own gate.
- Show the head of the input and the delivery-state counts under the scope filter.

## 5. Steps

One numbered step per stage, each opened by a markdown line stating what it does and why,
followed by its code cell. Steps depend only on named variables from earlier steps.

1. **Scope** — remaining issues under the filter, from the governed `remaining_issue_count` SQL,
   then `× SCOPE_GROWTH_FACTOR` (rounded up), or `SCOPE_OVERRIDE`. Print delivered / excluded /
   remaining so the finish line is auditable.
2. **Throughput history** — governed `weekly_throughput`, reindexed onto a dense Monday spine so
   empty weeks are zeros, trimmed to `HISTORY_WEEKS`, filtered by `THROUGHPUT_SCOPE`. Print the
   series with count, min, median, mean and max. Warn if fewer than 6 weeks survive — a sample
   that small makes the tails meaningless.
3. **Simulate** — the seeded sampling loop from
   [simulation-and-visuals.md](simulation-and-visuals.md), returning a `RUN` dict holding the
   parameters used, the sampled history, the per-trial outcomes and the derived percentiles.
4. **Visualize** — every chart in that reference, in order.
5. **Interactive controls** — the `ipywidgets` panel. Moving a control and clicking re-runs step 3,
   redraws step 4 into the panel's output area, and updates `RUN` so the Result(s) section writes
   what is currently on screen. The panel's *initial* run renders as ordinary cell output, never
   into the `Output` widget — see
   [simulation-and-visuals.md](simulation-and-visuals.md#the-rule-that-keeps-it-executable);
   writing into a displayed `Output` widget deadlocks `nbconvert --execute`. Running the notebook
   headlessly never depends on any interaction.

Keep the simulation itself in one function, `simulate(...)`, called by both the parameter path and
the widget path. Two code paths that can disagree are a bug waiting to be shipped.

## 6. Result(s)

The plain-language answer first, as markdown printed from the numbers — for example:
*"P50 12 weeks (2026-11-08), P85 16 weeks (2026-12-06). Probability of hitting 2026-11-30: 68 %."*

Then write **exactly one file**, `data/forecasts/<slug>_forecast.csv`, one row per confidence
level, carrying the run's provenance so the file stands alone:

| column | what it is |
|---|---|
| `confidence_level` | 0.50, 0.70, … — one row each, ascending |
| `weeks_to_complete` | simulated weeks at that confidence (`MODE == "when"`) |
| `completion_date` | `AS_OF_DATE` + weeks, the Sunday closing the finishing week |
| `items_by_target_date` | items delivered by `TARGET_DATE` at that confidence (`MODE == "how_many"`) |
| `probability_of_target_date` | share of trials finishing on or before `TARGET_DATE`, repeated |
| `scope_remaining` | the finish line the trials were run against |
| `trials`, `history_weeks`, `throughput_scope`, `scope_growth_factor`, `random_seed` | the parameters that produced the row |
| `input_file`, `input_rows`, `input_sha256`, `as_of_date`, `notebook`, `generated_at` | provenance |

Columns that do not apply to the mode are written as NULL, not dropped — the file's shape is
stable across runs.

Finish by asserting the percentiles are monotonic, re-hashing the input parquet, asserting it
equals `INPUT_HASH_START`, and printing both hashes plus the output path. No other file is
written — no chart images, no per-trial dump, no run manifest. The executed notebook is the record.
