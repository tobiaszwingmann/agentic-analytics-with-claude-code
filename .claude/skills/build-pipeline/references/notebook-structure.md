# Notebook structure

`notebooks/prep_<slug>.ipynb` has five sections, in this order. Each begins with a markdown
header cell, followed by its code cells. Build the file with `nbformat`.

Keep it simple: the reader should be able to see the goal, what was assumed, what went in,
what was done, and what came out — without reading any code.

## 1. Goal

Markdown only. The analysis question in the user's own words, one paragraph on what the
prepared data must support, and the date of generation.

## 2. Assumptions

Markdown only. Everything the pipeline takes as given, so a reviewer can challenge it:

- Semantic layer `metadata.name` and `version` — governed definitions are reused verbatim.
- The governed dimensions and metrics used, listed by name.
- The deduplication rule applied to each entity, quoted from `entities:`.
- Each field normalization applied, quoted from the layer.
- The raw database is read-only and never written to.
- Missing values are never imputed.
- Anything the layer does not define that the user approved during planning.

## 3. Inputs

Parameters first — one cell, assignments only, no logic:

```python
DB_PATH = "data/agile_issues.db"
SEMANTIC_LAYER_PATH = "data/semantic_layer.yml"
OUTPUT_STEM = "data/prepared/<slug>"   # .parquet, .csv and _semantic_layer.yml hang off this
AS_OF_DATE = "YYYY-MM-DD"     # governed metrics are event-time aware
RELEASE = None                 # analysis-specific filter, None = all
```

Then imports, the read-only connection, the starting hash, and the loaded layer:

```python
import hashlib, json, pathlib, sqlite3
import pandas as pd, yaml

con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
DB_HASH_START = hashlib.sha256(pathlib.Path(DB_PATH).read_bytes()).hexdigest()
LAYER = yaml.safe_load(open(SEMANTIC_LAYER_PATH))
```

Confirm the connection rejects writes, print `DB_HASH_START`, and look governed SQL up by
name — raising on a miss, never falling back:

```python
def governed_sql(kind, name):
    for item in LAYER[kind]:
        if item["name"] == name:
            return item["sql"]["query"]
    raise KeyError(f"{kind}.{name} not in semantic layer")
```

Close the section by printing the shape of each source object read.

## 4. Steps

One numbered step per transformation, each a markdown line stating what it does and why,
followed by its code cell. Steps run in order and depend only on named variables from
earlier steps — no hidden state, no cell that must be run twice.

The usual sequence:

1. **Source checks** — run every `quality_checks` entry with `stage: source` before any
   transformation.
2. **Canonical entities** — build one dataframe per entity in `entities:`, applying that
   entity's `deduplication` rule exactly as written. For `issue`:
   `ROW_NUMBER() OVER (PARTITION BY issue_key ORDER BY updated DESC, id DESC) = 1`.
   Raw `issues` rows never reach a downstream frame without this step.
3. **Normalizations** — apply each field's `normalization` text literally: trim, parse,
   sentinel-to-NULL, date handling. Unparseable or blank stays NULL.
4. **Post-preparation checks** — run every `stage: post_preparation` check against the
   built entities.
5. **Joins and analysis tables** — join per `relationships:`, honouring cardinality. Around
   each `one_to_many` join, assert the driving entity's row count is unchanged or aggregate
   the many side first. Reuse governed metric SQL verbatim.
6. **Analysis-gate checks** — run every `stage: analysis_gate` check before anything is
   written.

Define the check harness once, in the first step that needs it:

```python
CHECK_RESULTS = []

def run_check(name):
    """Execute a quality_checks entry by name; record stage, severity, value, verdict."""
```

It reads `stage`, `severity`, `sql.query` and `pass_condition` from `LAYER`, appends a row to
`CHECK_RESULTS`, and raises when a `severity: error` check fails. Checks whose
`pass_condition` starts with "informational" are recorded, never raised on.

## 5. Outputs

The pipeline produces **exactly three files**, flat in `data/prepared/`:

| File | What it is |
|---|---|
| `<slug>.parquet` | the prepared table — typed, the analysis-ready artifact |
| `<slug>.csv` | the same table, for inspection and tools that need text |
| `<slug>_semantic_layer.yml` | the semantic layer describing that table |

One table, one grain. Do not write aggregates, roll-ups, or per-cut summaries — those are
`GROUP BY`s the analysis performs on this file, and pre-computing them duplicates governed
logic that then drifts. If the analysis genuinely needs a second grain that cannot be derived
from this table, stop and ask the user before writing a second file.

Write the two data files, assert `df.shape` matches between them, then re-hash the database,
`assert` it equals `DB_HASH_START`, and print both hashes.

### The prepared semantic layer

Build `<slug>_semantic_layer.yml` from `templates/tmpl_semantic_layer.yml`, describing the
prepared file rather than the raw database:

- `metadata` — name `<slug>_prepared`, a description naming the analysis it supports, owner
  carried from the source layer, and the generation date.
- `sources` — one source of `type: file`, `location: data/prepared/<slug>.parquet`, with one
  object whose `grain` is a one-line statement of what a row represents, its `primary_key`,
  and one `fields` entry per column: `data_type`, `description`, and the `normalization`
  already applied — quoted from the source layer, in past tense, since it is baked in.
- `entities` / `relationships` — the single entity this file holds; `deduplication` records
  the rule already applied. Relationships are usually empty for a single flat table.
- `dimensions` / `metrics` — carried forward from the source layer for the definitions this
  file supports, `definition_status: governed`, with SQL rewritten to read the prepared file
  instead of the raw tables. Never invent a definition here.
- `governance` — copied from the source layer unchanged.
- `quality_checks` — the `post_preparation` and `analysis_gate` checks, retargeted at the
  prepared file, so a consumer can re-verify it without the raw database.
- `lineage` — an extra block recording the source layer name and version, the notebook path,
  the parameters used, `DB_HASH_START`, and the row count.

Finish by printing the check results table and the three output paths, so the executed
notebook is the record of the run — no separate `check_results.csv` or `run_manifest.json`.
