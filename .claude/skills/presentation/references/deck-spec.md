# Deck spec reference

`scripts/build_deck.py` builds the whole deck from one JSON file. The spec *is* the pyramid,
serialised - so write it top-down: `governing_thought` first, one `section` per argument, evidence
slides beneath each.

```bash
.venv/bin/python .claude/skills/presentation/scripts/build_deck.py <spec.json> -o presentations/<slug>.pptx
```

Optional: `--template <path.pptx>` and `--theme <path.json>` to build against a different template.

## Top level

```json
{
  "meta": {
    "title":    "Release v2.4 delivery outlook",
    "subtitle": "Monte Carlo forecast from 12 weeks of observed throughput",
    "audience": "Engineering leadership",
    "date":     "19 August 2026",
    "footer":   "Release v2.4 delivery outlook",
    "as_of":    "2026-08-19"
  },
  "slides": [ ... ]
}
```

`footer` and `as_of` appear on every numbered slide. Use `as_of` whenever the numbers are a
snapshot - a slide that outlives its data is how stale figures get quoted back at you.

## Fields every content slide takes

| Field | Meaning |
|---|---|
| `title` | The action title. A full-sentence assertion, never a label. Required. |
| `takeaway` | The "so what" strip along the bottom. One sentence. Omit only in the appendix. |
| `notes` | Speaker notes. What you say that is not on the slide. |

The builder warns when a content slide has no `takeaway`, or when a title is three words or
fewer and therefore probably a label.

## Slide types

### `title`
Opens the deck. Pulls `title`, `subtitle`, `audience` and `date` from `meta` unless overridden
per slide. Counted in the page numbering but not numbered.

### `governing_thought`
The apex. One per deck, immediately after the title slide.

```json
{"type": "governing_thought",
 "title": "v2.4 will not make 15 October - plan for 1 November and decide what to cut",
 "statement": "At the team's observed pace, v2.4 finishes 25 October at best and 1 November with the confidence a commitment needs - six weeks past the date currently on the roadmap.",
 "supports": ["...", "...", "..."],
 "takeaway": "The choice is not whether to slip, but whether to slip the date or the scope."}
```

`supports` are the argument sentences, rendered as *BECAUSE 1/2/3* cards. There must be exactly
one per `section` slide that follows - the builder checks this, because a mismatch means the deck
promises an argument it never makes.

The statement font steps down automatically as it gets longer. It is still a slide, not a
paragraph: past ~250 characters it stops being readable at the back of the room.

### `section`
An argument divider. One per supporting argument.

```json
{"type": "section", "number": 1,
 "statement": "The remaining scope is 84 issues and it is not shrinking"}
```

`statement` is the argument as a full sentence. `label` overrides the default "ARGUMENT n".

### `chart`

```json
{"type": "chart", "title": "...",
 "image": "presentations/assets/<slug>/throughput.png",
 "source": "data/forecasts/release-v24-forecast_forecast.csv, 10,000 trials, seed 42",
 "takeaway": "..."}
```

Scaled to fit and centred; aspect ratio preserved. `source` is a small line under the image -
include it whenever the number could be challenged.

### `bullets`
Up to four points. Strings, or objects with sub-points:

```json
{"type": "bullets", "title": "...",
 "bullets": [
   {"text": "Weekly throughput sits between 6 and 11 issues with no trend",
    "sub": ["Team-wide scope; release-only throughput is too thin to model."]},
   "Scope growth is modelled at 1.0 - splits make this worse, never better."
 ],
 "takeaway": "..."}
```

Five or more bullets shrink the type. That is a signal to split the slide, not a feature.

### `two_col`
Two options, before/after, or risk against mitigation. The right column is styled in the
highlight colour, so put the thing you want looked at there.

```json
{"type": "two_col", "title": "...",
 "left":  {"heading": "Move the date", "bullets": ["...", "..."]},
 "right": {"heading": "Cut the scope", "bullets": ["...", "..."]},
 "takeaway": "..."}
```

### `kpi`
Two to four headline numbers. The strongest opener after the governing thought when the audience
is executive.

```json
{"type": "kpi", "title": "The forecast in three numbers",
 "kpis": [
   {"value": "25 Oct", "label": "P50 - coin-flip finish date"},
   {"value": "1 Nov",  "label": "P85 - the date worth committing to", "emphasis": "highlight"}
 ],
 "takeaway": "..."}
```

`emphasis` is `accent` (default) or `highlight`. Highlight at most one.

### `table`

```json
{"type": "table", "title": "...",
 "columns": ["Confidence", "Weeks remaining", "Completion date"],
 "rows": [["P50", "9", "25 Oct 2026"], ["P85", "10", "1 Nov 2026"]],
 "highlight_rows": [1],
 "takeaway": "..."}
```

`highlight_rows` are zero-based over `rows` (excluding the header). Keep tables under about eight
rows and four columns; anything larger is an appendix exhibit.

### `next_steps`

```json
{"type": "next_steps", "title": "Three decisions this week keep the November date credible",
 "steps": [{"action": "Confirm 1 November, or authorise a scope cut",
            "owner": "Eng leadership", "when": "by Fri 21 Aug"}],
 "takeaway": "..."}
```

Owner and date are optional but a step without an owner is a wish.

### `appendix_divider` and `appendix`
Everything after the divider is exempt from the takeaway and action-title checks - backup
exhibits are allowed to be labels. `appendix` slides render as a chart if they carry `image`, a
table if they carry `columns`, otherwise bullets.

## Charts

Render to `presentations/assets/<slug>/`, styled from `assets/theme.json` so the deck reads as one
document.

```python
import json, pathlib, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

theme = json.loads(pathlib.Path(".claude/skills/presentation/assets/theme.json").read_text())
c = theme["colors"]
plt.rcParams.update({
    "font.family": theme["fonts"]["body"], "font.size": 11,
    "text.color": "#" + c["text"], "axes.labelcolor": "#" + c["muted"],
    "xtick.color": "#" + c["muted"], "ytick.color": "#" + c["muted"],
    "axes.edgecolor": "#" + c["rule"],
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "#" + c["background"], "axes.facecolor": "#" + c["background"],
})

fig, ax = plt.subplots(figsize=(11.4, 3.8), dpi=200)   # fills the slide's body band
...
ax.grid(axis="y", color="#" + c["rule"], linewidth=0.7)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig("presentations/assets/<slug>/throughput.png", bbox_inches="tight")
```

Rules that matter more than the styling:

- **`figsize=(11.4, 3.8)`** matches the body band. A squarer figure gets scaled down to fit the
  height and leaves the slide half empty.
- **`dpi=200`** or better. Charts are projected.
- **Colour carries meaning, or it is not there.** One accent for the series, `highlight` for the
  one thing the title is about, `muted` for context. Never a rainbow.
- **Label the point, not the axis.** If the title says P85 is 1 November, annotate that bar.
- **No chart junk** - no gridline on both axes, no legend when a direct label will do, no
  3D, no second y-axis.
- One chart per slide. Two charts is two slides or a comparison the title has to name.

## Adapting a branded template

Swap the file, not the code:

1. Save the corporate template as `assets/template.pptx`. It must contain layouts named
   **Title Slide**, **Section Header**, **Title Only** and **Blank** - the four that appear in
   virtually every PowerPoint template. The builder fails with a clear message listing the
   layouts it did find.
2. Set `assets/theme.json` to the brand's colours (hex, no `#`) and fonts. Every colour the
   builder draws comes from here.
3. If the brand slide size is 4:3, set `slide.width_in`/`height_in` and adjust `grid` - the
   `takeaway_top_in` and `footer_top_in` values are measured from the top.
4. Build a deck from [example-spec.json](example-spec.json) and look at it before using the
   template for real work.

`build_template.py` only regenerates the *neutral* template from `theme.json`. Never run it once a
branded `template.pptx` is in place - it overwrites it.

## Checking a built deck without PowerPoint

The builder's warnings catch structural drift. For geometry, read the shapes back:

```python
from pptx import Presentation
prs = Presentation("presentations/<slug>.pptx")
W, H = prs.slide_width.inches, prs.slide_height.inches
for i, slide in enumerate(prs.slides, 1):
    for sh in slide.shapes:
        if sh.left is None: continue
        l, t = sh.left / 914400, sh.top / 914400
        w, h = (sh.width or 0) / 914400, (sh.height or 0) / 914400
        if l < 0 or t < 0 or l + w > W + 0.01 or t + h > H + 0.01:
            print(f"slide {i}: {sh.name!r} out of bounds")
```

And read the titles alone - `slide.shapes.title.text` for each - which is the check that actually
matters.
