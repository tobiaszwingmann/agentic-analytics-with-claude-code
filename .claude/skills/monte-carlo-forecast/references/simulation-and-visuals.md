# Simulation, charts and controls

The algorithms, the required figures, and the interactive panel. Follow the shapes here; the
numbers come from the run.

## The model

Weekly-throughput sampling. Each simulated future week draws, with replacement, one observed
weekly throughput from the history window. Weeks accumulate until the scope is met.

Everything is seeded and vectorised — one `numpy` call, not a Python loop over trials.

```python
def simulate(history, scope, trials, seed, max_weeks, weeks_to_target=None):
    """history: 1-D array of observed weekly throughput (zeros included).
       Returns a dict; the same function serves the parameter run and the widget run."""
    rng    = np.random.default_rng(seed)
    draws  = rng.choice(np.asarray(history, dtype=float), size=(trials, max_weeks), replace=True)
    cum    = draws.cumsum(axis=1)

    hit    = cum >= scope
    landed = hit.any(axis=1)
    weeks  = np.where(landed, hit.argmax(axis=1) + 1.0, np.nan)   # first week the line is crossed

    items_by_target = cum[:, weeks_to_target - 1] if weeks_to_target else None

    return {"draws": draws, "cum": cum, "weeks": weeks, "landed": landed,
            "items_by_target": items_by_target, "scope": scope, "history": history}
```

Report `1 - landed.mean()` when any trial fails to finish inside `MAX_WEEKS` — a non-trivial share
means the throughput cannot absorb the scope, and no percentile hides that.

### Reading percentiles in the right direction

The two modes read opposite tails. Get this wrong and the notebook lies confidently.

```python
# MODE == "when": higher confidence = MORE weeks
weeks_at = np.percentile(run["weeks"][run["landed"]], conf * 100)

# MODE == "how_many": higher confidence = FEWER items
items_at = np.percentile(run["items_by_target"], (1 - conf) * 100)
```

"P85 = 16 weeks" means 85 % of trials finished in 16 weeks or fewer. "P85 = 40 items" means 85 %
of trials delivered at least 40 items. Say it that way in the notebook, in words.

### Weeks to dates

Forecast weeks start on the first Monday on or after `AS_OF_DATE`; the completion date is the
Sunday that closes the finishing week — the same Monday-to-Sunday convention the prepared layer
uses for `delivery_week_start` / `delivery_week_end`.

```python
def week_to_date(n_weeks):
    as_of  = pd.Timestamp(AS_OF_DATE)
    monday = as_of + pd.Timedelta(days=(7 - as_of.dayofweek) % 7)
    return (monday + pd.Timedelta(weeks=int(np.ceil(n_weeks)) - 1) + pd.Timedelta(days=6)).date()
```

`weeks_to_target` for `how_many` mode is the count of whole forecast weeks between that Monday and
`TARGET_DATE`.

### Throughput history

Reindex the governed `weekly_throughput` output onto a dense Monday spine between the first and
last observed delivery week, filling gaps with `0` — a week the team delivered nothing is
evidence, and dropping it biases the forecast optimistic. Only complete weeks exist in the
prepared file, so nothing needs trimming at the tail.

## Charts

Five figures, in this order, one per cell, each with a title that states what it shows and a
one-line markdown caption above it saying what to conclude. Keep the crowd grey and the answer
coloured; the reader's eye should land on the percentile lines.

**1. Throughput history.** Bar chart of issues delivered per week over the history window, with a
median line. Beside it (or below), a histogram of the same values — this is literally the pool the
simulation draws from, so the reader can see the model's raw material. Mark weeks excluded by
`HISTORY_WEEKS` in a lighter shade if any were dropped.

**2. Trial paths ("spaghetti").** Cumulative items delivered vs. forecast week, one thin
translucent line per sampled trial (`SAMPLE_TRIALS_TO_PLOT`, default 200 of 10 000 — say in the
caption that it is a sample and how many). Draw a horizontal line at `scope`, and overlay the
median path and the P85 path in a strong colour. This is the chart that makes Monte Carlo
intuitive: many futures, one target line, a spread of crossing points.

```python
idx = rng_plot.choice(TRIALS, size=min(SAMPLE_TRIALS_TO_PLOT, TRIALS), replace=False)
for i in idx:
    ax.plot(weeks_axis, run["cum"][i], lw=0.5, alpha=0.08, color="tab:blue")
ax.axhline(run["scope"], color="black", ls="--", label=f"scope = {run['scope']:,} issues")
```

**3. Completion distribution.** Histogram of `weeks` (one bin per week), with vertical lines at
every level in `CONFIDENCE_LEVELS`, each annotated with its week number *and* its calendar date.
If `TARGET_DATE` is set, mark it and shade the region beyond it.

**4. Probability curve (the S-curve).** Cumulative share of trials finished by week `w`, plotted
against dates on the x-axis. Horizontal guides at the confidence levels, and — when a target date
exists — a callout reading *"P(finish by 2026-11-30) = 68 %"*. This is the chart a stakeholder
should be shown first.

**5. Fan chart.** Cumulative delivery over time as percentile bands (10–90 and 25–75 shaded,
median as a line), with the scope line crossing it. Shows how the uncertainty widens week by week
rather than only at the finish.

In `how_many` mode, charts 3 and 4 switch subject: a histogram of items delivered by
`TARGET_DATE`, and a curve of *"probability of delivering at least N items"*. Charts 1, 2 and 5
are unchanged.

Use plain `matplotlib` (no seaborn in this environment), `%matplotlib inline`, figures around
`figsize=(10, 5)`, thousands separators on counts, dates formatted `%Y-%m-%d`, and a legend on
every figure that has more than one series.

## Interactive controls

An `ipywidgets` panel at the end of **Steps**. It re-runs `simulate(...)` and redraws the figures;
it never writes files.

### The rule that keeps it executable

**The initial run must render as ordinary cell output. Only click-driven redraws may write into
the `Output` widget.**

This is not a style preference. Writing into a *displayed* `Output` widget re-parents the kernel's
iopub messages to the widget's comm, so `nbconvert --execute` never sees the idle status that ends
the cell. The kernel finishes the work in under a second and then sits at 0 % CPU until the
executor's timeout expires — a 900-second hang that looks like a slow simulation but is a
message-routing deadlock. It cannot happen on a click, because a click implies a live frontend.

Rendering the first run as plain cell output also makes the executed notebook a complete record:
the charts are real outputs, visible in exported HTML and on GitHub, rather than empty widget
placeholders.

```python
import ipywidgets as W
from IPython.display import display

w_trials  = W.IntSlider(value=TRIALS, min=1_000, max=50_000, step=1_000,
                        description="Trials", continuous_update=False)
w_history = W.IntSlider(value=HISTORY_WEEKS or len(FULL), min=4, max=len(FULL),
                        description="History wks", continuous_update=False)
w_growth  = W.FloatSlider(value=SCOPE_GROWTH_FACTOR, min=1.0, max=2.0, step=0.05,
                          description="Scope x", continuous_update=False)
w_seed    = W.IntText(value=RANDOM_SEED, description="Seed")
w_conf    = W.SelectMultiple(options=[0.5, 0.7, 0.85, 0.95, 0.99],
                             value=tuple(CONFIDENCE_LEVELS), description="Confidence")
w_go      = W.Button(description="Re-run simulation", button_style="primary")
out       = W.Output()


def run_forecast(target=None):
    """target=None -> ordinary cell output (headless-safe, and the run of record).
       target=out  -> redraw inside the Output widget; only ever reached from a click."""
    global RUN, SUMMARY, WIDGET_STATE
    hist   = history_for(w_scope.value, w_history.value)
    levels = sorted(w_conf.value) or [0.5]
    RUN     = simulate(history=hist.values, scope=scope_for(w_growth.value),
                       trials=w_trials.value, seed=w_seed.value, max_weeks=MAX_WEEKS,
                       weeks_to_target=WEEKS_TO_TARGET)
    SUMMARY = summarize(RUN, levels)
    WIDGET_STATE = {"trials": w_trials.value, "history_weeks": len(hist),
                    "throughput_scope": w_scope.value, "scope_growth_factor": w_growth.value,
                    "random_seed": w_seed.value, "confidence_levels": levels}

    def body():
        display(SUMMARY)
        draw_all(RUN, SUMMARY)

    if target is None:
        body()
    else:
        with target:
            target.clear_output(wait=True)
            body()


w_go.on_click(lambda _btn: run_forecast(out))
display(W.VBox([W.HBox([w_trials, w_history]), W.HBox([w_growth, w_seed]), w_conf, w_go, out]))
run_forecast()          # plain cell output - never `run_forecast(out)` here
```

Rules for the panel:

- It calls the same `simulate` and the same `draw_all` as the parameter path. No second
  implementation of the model.
- It updates the module-level `RUN`, `SUMMARY` and `WIDGET_STATE`, so re-running the **Result(s)**
  cell writes whatever the user last explored — with the widget values recorded in the output
  file's parameter columns, not the stale ones from the Parameters cell.
- A headless `nbconvert --execute` run must produce the full forecast without any widget
  interaction: `run_forecast()` is called once at the end of the cell with the parameter defaults.
- Slider ranges stay inside what the data supports — the history slider can never exceed the
  number of observed weeks.
- Widgets are built and displayed in the *same* cell that first renders. An `Output` created in
  one cell and written to from another hits the same re-parenting deadlock.

## When execution hangs

A cell that finishes at *exactly* the executor's timeout value (120.0 s under
`--ExecutePreprocessor.timeout=120`) is deadlocked on message routing, not computing. Check the
kernel with `ps -o %cpu`: 0 % confirms it. Bisect it by executing the notebook through a traced
preprocessor rather than guessing:

```python
import time, nbformat
from nbconvert.preprocessors import ExecutePreprocessor

class Traced(ExecutePreprocessor):
    def preprocess_cell(self, cell, resources, index):
        t = time.time()
        r = super().preprocess_cell(cell, resources, index)
        print(f"[cell {index}] {time.time()-t:6.1f}s", flush=True)
        return r

nb = nbformat.read(NB, as_version=4)
Traced(timeout=60, kernel_name="python3").preprocess(nb, {"metadata": {"path": "notebooks/"}})
```

To trace *inside* a cell whose output is being captured by a widget, write markers with
`sys.__stderr__.write(...)` — that bypasses the kernel's output redirection and reaches the
executor's console, where captured `print` never will.
