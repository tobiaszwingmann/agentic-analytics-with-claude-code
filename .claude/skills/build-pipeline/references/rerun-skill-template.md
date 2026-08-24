# Re-run Skill template

Written to `.claude/skills/prepare-<slug>/SKILL.md` in step 8, after a successful run only.
Replace every `<...>` placeholder with concrete values from the run. The generated skill
**re-runs** the notebook; it never regenerates or edits it.

```markdown
---
name: prepare-<slug>
description: Re-run the governed data preparation for <analysis question in one line>. Use when the raw data has been refreshed, when data/prepared/<slug>.parquet is stale or missing, before any analysis that depends on them, or when the user asks to refresh, rebuild, or re-prepare <slug> data.
---

# Prepare: <analysis title>

Executes `notebooks/prep_<slug>.ipynb`, which prepares data for:
**<analysis question>**

Governed by `data/semantic_layer.yml` v<version>. Governed definitions used:
<comma-separated metric and dimension names>.

## When to run

- The raw database `data/agile_issues.db` changed.
- `data/prepared/<slug>.parquet` is missing, stale, or partially written.
- An analysis is about to consume those tables and their freshness is unverified.

## Run it

1. Record the starting hash of the raw database:

   ```bash
   shasum -a 256 data/agile_issues.db
   ```

2. Ensure the environment exists:

   ```bash
   python3 -m venv .venv 2>/dev/null; .venv/bin/pip install -q pandas pyyaml jupyter ipykernel nbconvert
   ```

3. Execute the notebook top to bottom in a fresh kernel:

   ```bash
   .venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 notebooks/prep_<slug>.ipynb
   ```

4. Re-hash the database and confirm it matches step 1:

   ```bash
   shasum -a 256 data/agile_issues.db
   ```

## Parameters

The Inputs section of the notebook holds every parameter. To change one — `AS_OF_DATE`, a release
filter, the output directory — edit that cell and re-run the whole notebook. Never edit a
later cell to work around a parameter.

## Report

Read the check results table from the executed notebook and report every check with its
stage, severity and verdict, plus the row count of `data/prepared/<slug>.parquet` and the
two database hashes.

## Outputs

Three files, overwritten in place on every run:

- `data/prepared/<slug>.parquet` — the prepared table, <one line: what one row is>
- `data/prepared/<slug>.csv` — the same table as text
- `data/prepared/<slug>_semantic_layer.yml` — its semantic layer, including lineage

Aggregates and cuts are the analysis's job; this pipeline does not pre-compute them.

## Failure handling

- A `severity: error` check failed → the preparation failed. Report the check name and its
  observed value. Do not use the outputs.
- The database hashes differ → stop and report immediately; something wrote to the raw
  source, which the pipeline forbids.
- The notebook needs structural change (new fields, new joins, a new governed definition) →
  do not patch it here. Run `/build-pipeline` to regenerate it from the semantic layer.
```
