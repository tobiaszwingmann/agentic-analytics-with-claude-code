---
name: build-pipeline
description: Build a governed data-preparation pipeline as a Jupyter notebook driven by data/semantic_layer.yml. Use when the user asks to prepare, clean, transform, or model data for an analysis; to build a data pipeline, prep layer, or analysis-ready dataset; or invokes /build-pipeline. Produces a modular notebook in notebooks/, executes it in a fresh kernel, runs the semantic-layer quality checks, verifies the raw database is untouched, and saves a project-specific Skill that re-runs the pipeline on demand.
---

# Data Preparation Pipeline

Turn a stated analytical need into an executed, quality-checked preparation notebook
whose logic comes from the governed semantic layer — not from ad-hoc judgment.

## Inputs

| What | Where |
|---|---|
| Governed semantic layer | `data/semantic_layer.yml` |
| Semantic layer template | `templates/tmpl_semantic_layer.yml` |
| Raw database (read-only) | `data/agile_issues.db` |
| Generated notebook | `notebooks/prep_<slug>.ipynb` |
| Prepared table | `data/prepared/<slug>.parquet` + `.csv` |
| Its semantic layer | `data/prepared/<slug>_semantic_layer.yml` |
| Generated re-run Skill | `.claude/skills/prepare-<slug>/SKILL.md` |

`<slug>` is a short kebab-case name for the analysis (e.g. `release-v24-forecast`).

## Hard rules

1. **The raw database is read-only.** Open it only via a read-only URI
   (`sqlite3.connect("file:data/agile_issues.db?mode=ro", uri=True)`).
   Never `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ATTACH ... AS` for writing, or `VACUUM`.
2. **Governed definitions are authoritative.** `governance.allow_governed_metric_sql_rewrite`
   is `false` — copy embedded metric SQL verbatim. Do not re-derive, "improve", or inline a
   different version of a governed definition.
3. **`proposed_additions:` are not governed.** Never use one without explicit user approval.
4. **Missing or ambiguous definition → ask.** `governance.missing_or_ambiguous_definition` is
   `"ask"`. If the requested analysis needs a definition the layer does not carry, stop and ask
   the user rather than inventing one.
5. **Never impute.** Missing values stay missing unless the layer prescribes a normalization.
6. **`severity: error` check fails → stop.** Report the failure; do not continue to later stages
   or write outputs. `severity: warning` failures are recorded and execution continues.
7. **One prepared table, not a folder of them.** The pipeline outputs a single analysis-ready
   table at one grain, written as Parquet and CSV, plus its own semantic layer. Aggregates,
   roll-ups and per-cut summaries are the analysis's job — pre-computing them here duplicates
   governed logic that then drifts out of sync. If the analysis truly needs a second grain that
   cannot be derived from the prepared table, ask the user before writing a second file.

## Steps

### 1. Ask what the analysis is

Ask the user: **"What analysis should the prepared data support?"**

Skip the question only if the invocation already states it (e.g. `/build-pipeline forecast
release v2.4 completion`). Capture the answer before touching anything else — it determines
which sources, dimensions, and metrics the pipeline pulls through. If the answer is broad,
ask one round of follow-ups (grain, time window, release/segment scope, required metrics).

### 2. Read the semantic layer

Read `data/semantic_layer.yml` in full — it is ~1400 lines, so read it, do not grep for
fragments. Note `version` and `metadata.name`; the notebook records them for provenance.

### 3. Identify what the analysis requires

Write a short plan and show it to the user before generating anything. Cover:

- **Target grain** — what one row of the prepared table represents, and the columns it carries.
  Everything else in this list serves that one table.
- **Sources** — objects under `sources:` needed, and their declared grain.
- **Entities** — canonical entities from `entities:`, with each entity's `deduplication` rule.
  Raw `issues` rows are not at issue grain and must never be counted directly.
- **Fields** — the specific fields required, and each field's `normalization` text.
- **Governed definitions** — the `dimensions:` and `metrics:` the analysis depends on, by name,
  with their embedded SQL reused as-is.
- **Joins** — the entries in `relationships:` needed, with cardinality; state the fan-out risk
  for any `one_to_many` join and how the pipeline avoids double counting.
- **Normalizations** — trims, numeric parsing, sentinel-to-NULL mappings, date handling.
- **Quality checks** — every entry in `quality_checks:` whose `target` is in scope, grouped by
  `stage` (`source`, `post_preparation`, `analysis_gate`).

Flag anything the layer does not define, and ask (rule 4).

### 4. Generate the notebook

Write `notebooks/prep_<slug>.ipynb` following
[references/notebook-structure.md](references/notebook-structure.md): five sections — **Goal**,
**Assumptions**, **Inputs**, **Steps**, **Outputs** — each opened by a markdown header, with
parameters isolated in one cell and no hidden state between steps. Build it with `nbformat`
rather than hand-writing JSON.

### 5. Execute it in a fresh kernel

Ensure the environment exists, then execute top to bottom — no partial or interactive runs:

```bash
python3 -m venv .venv 2>/dev/null; .venv/bin/pip install -q pandas pyyaml jupyter ipykernel nbconvert
```

```bash
.venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 notebooks/prep_<slug>.ipynb
```

`--execute` always starts a fresh kernel, so the run proves the notebook is reproducible from a
cold start. If execution fails, fix the notebook and re-run the whole thing — never patch the
outputs by hand.

### 6. Run the semantic-layer quality checks

The checks run inside the notebook at their declared stage, each evaluated against its
`pass_condition`. After execution, read the check results table out of the executed notebook and
report every check with its stage, severity, observed value, and pass/fail. A failed `error`
check means the pipeline did not succeed — say so plainly.

### 7. Confirm the raw database is unchanged

Hash the database before and after the run and compare:

```bash
shasum -a 256 data/agile_issues.db
```

Take the hash before step 5, take it again after, and report both. The notebook additionally
asserts its own connection is read-only. If the hashes differ, treat it as a failure, report it
immediately, and do not save the re-run Skill.

### 8. Save the project-specific re-run Skill

Write `.claude/skills/prepare-<slug>/SKILL.md` from
[references/rerun-skill-template.md](references/rerun-skill-template.md). It re-runs this exact
notebook, re-runs the checks, and re-verifies the database hash — it does not regenerate the
notebook. Tell the user the new skill exists and that it becomes available in a new session.

## Report back

Close with: the analysis question, the notebook path, the grain and row count of the prepared
table, the governed definitions used by name, the check results (stage / severity / pass or
fail), the before/after database hashes, the three output paths, and the name of the re-run
skill.
