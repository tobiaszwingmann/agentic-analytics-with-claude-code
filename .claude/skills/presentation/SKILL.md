---
name: presentation
description: Turn findings into a PowerPoint deck structured by the Pyramid Principle. Use when the user asks to build a presentation, slide deck, PPTX, board or steering-committee deck, an executive readout, or to "present", "pitch" or "turn this into slides" - whether the input is a forecast, an analysis notebook, a report or notes pasted into chat. Asks who the audience is, proposes a governing thought and the supporting arguments, gets both confirmed, and only then fills the template.
---

# Presentation

A deck is an argument, not a container for findings. This skill builds the argument first -
one answer at the top, a small number of arguments holding it up, evidence under each - and
fills the PowerPoint template only once the user has signed off on that structure.

The order matters and is not negotiable: **audience → governing thought → arguments → slides.**
Building slides before the pyramid is agreed produces a deck that has to be rebuilt.

## Inputs and outputs

| What | Where |
|---|---|
| Insight material | anything the user points at or pastes - notebook, CSV, report, notes |
| Deck template | `.claude/skills/presentation/assets/template.pptx` |
| Design system | `.claude/skills/presentation/assets/theme.json` |
| Chart images | `presentations/assets/<slug>/*.png` |
| Finished deck | `presentations/<slug>.pptx` |

`<slug>` is a short kebab-case name for the deck (`release-v24-outlook`, `q3-churn-readout`).

## Hard rules

1. **Never build slides before the pyramid is confirmed.** Audience, governing thought and
   arguments are three separate checkpoints with three separate yes-es. Do not merge them into
   one question and do not proceed on silence.
2. **Never invent a number.** Every figure on a slide traces to something the user supplied. If
   the argument needs a number you do not have, say so and ask - an approximation on a slide
   becomes a quoted fact in the next meeting.
3. **Every content-slide title is a full-sentence assertion.** "Throughput is stable at 8-9
   issues per week" - never "Throughput analysis". A reader who reads only the titles must get
   the whole argument.
4. **One message per slide.** If a slide needs two titles, it is two slides.
5. **Two to four supporting arguments, three by default.** More than four means the pyramid has
   not been thought through; fewer than two means it is a single claim, not an argument.
6. **The arguments must be MECE** - no overlap, nothing load-bearing left out - and each must be
   a complete sentence that would survive a "so what?".
7. **Anything that does not hold up the governing thought goes to the appendix or gets cut.**
   Interesting is not a reason to keep a slide.
8. **Respect the audience's slide budget** (table below). A deck that runs long was not edited.
9. **Never silently overwrite an existing deck.** Check `presentations/` first and ask.
10. **The user's wording wins.** When they rewrite the governing thought, use their sentence
    verbatim - do not "improve" it on the way into the deck.

## Steps

### 1. Get the material

Take whatever the user pointed at and read it properly before proposing anything - a notebook's
result cells, a CSV, a report, notes in the chat. If they have not pointed at anything, ask what
the deck is about and what evidence exists.

Then say back, in three or four lines, what you understand the findings to be. Getting this wrong
is cheap to fix now and expensive to fix after the deck exists.

### 2. Ask who the audience is

This is the one question that must be asked every time, and it is asked before anything else is
proposed. Do not guess it from the material.

Ask three things in one round:

- **Who is in the room** - role and seniority.
- **What decision they own**, or what you want them to do differently after the deck.
- **How long you have**, and whether it is presented live or read cold.

Offer concrete profiles rather than an open question. Their answer sets the budget:

| Audience | Slides | Depth | What the governing thought must do |
|---|---|---|---|
| Executive / board | 5-8 | No method, no caveats above the fold | Name a decision and its cost |
| Steering committee | 8-12 | Options and risk, method in appendix | Force a choice between real options |
| Delivery / product team | 10-16 | Method visible, assumptions on the slide | Change what the team does next sprint |
| Analyst / peer review | 12-20 | Full method, limitations up front | State the finding and its confidence |

If it is read cold rather than presented, titles and takeaway lines carry the whole argument -
say so, and write them accordingly.

### 3. Propose the governing thought

One sentence at the apex of the pyramid: the answer to the question the audience actually has.

Offer **two or three candidates** with a recommendation, not one take-it-or-leave-it option. They
differ in what they ask the audience to do, not in wording.

A governing thought that works:

- answers the audience's question rather than describing the analysis
  ("v2.4 will not make 15 October" — not "We ran a Monte Carlo forecast")
- is a complete, falsifiable sentence someone could disagree with
- carries the "so what" for *this* audience - a decision, a cost, a consequence
- survives being the only thing they remember

Read [references/pyramid-principle.md](references/pyramid-principle.md) before drafting these if
the situation is at all complex - it covers SCQA framing, the "so what" ladder, and how to tell a
governing thought from a summary.

**Stop and wait for the user to pick or rewrite one.**

### 4. Propose the supporting arguments

With the apex fixed, propose the layer under it: two to four arguments, each a full sentence,
each one a reason the governing thought is true. Show them as a tree, with the evidence you would
put under each - this is the mini-pyramid layer, and it is where the deck is actually won.

Play it back like this:

```
v2.4 will not make 15 October - plan for 1 November and decide what to cut
│
├─ 1. The remaining scope is 84 issues and the backlog has not shrunk in four weeks
│     ├─ chart: remaining scope by week, flat since mid-July
│     └─ table: 84 open, 12 in progress, 0 closed net over 4 weeks
│
├─ 2. Throughput is stable at 8-9 issues per week, so there is no ramp to hope for
│     ├─ chart: weekly throughput, 12 weeks, no trend
│     └─ bullets: closing the gap needs ~14/week sustained
│
└─ 3. Even the optimistic tail of 10,000 simulations lands after 15 October
      ├─ chart: percentile fan, P50 25 Oct → P95 8 Nov
      └─ table: percentile → weeks → date
```

Check the set before showing it: does each argument survive "so what?", is anything overlapping,
and would the three together actually convince a sceptic? Say which argument you think is
weakest and why - the user is the one who knows whether it will hold in the room.

**Stop and wait for approval.** Expect edits here; they are cheap now and expensive later.

### 5. Render the charts

Only after the tree is agreed, and only for the evidence it calls for. Write PNGs to
`presentations/assets/<slug>/`, styled from `assets/theme.json` so they match the deck.

The matplotlib recipe, the figure size that fills the slide band, and the rules on what to plot
are in [references/deck-spec.md](references/deck-spec.md#charts). Charts that need data you do not
have are a reason to go back to step 4, not a reason to approximate.

### 6. Write the spec and build

The deck is built from a JSON spec - the pyramid, serialised. Write it to a temporary path (the
session scratchpad, not the repo), then:

```bash
.venv/bin/python .claude/skills/presentation/scripts/build_deck.py <spec.json> -o presentations/<slug>.pptx
```

Every slide type and field is documented in
[references/deck-spec.md](references/deck-spec.md), with a complete worked example in
[references/example-spec.json](references/example-spec.json). The spec's shape mirrors the
pyramid: one `governing_thought` slide, one `section` per argument, evidence slides beneath.

The builder prints structural warnings - a missing takeaway line, a label-shaped title, a
mismatch between the arguments named at the apex and the sections that follow. **Fix the deck,
not the warning.** Each one means the pyramid and the slides have drifted apart.

If `python-pptx` is missing:

```bash
.venv/bin/pip install -q python-pptx
```

### 7. Verify before handing over

- The slide count is inside the audience's budget.
- The builder reported no warnings.
- **Read the titles alone, in order.** They must tell the whole argument with nothing else on
  screen. If they do not, the deck is not finished.
- Every number on a slide traces to the source material.
- Charts are legible at the size they are placed - open one and look.

### 8. Hand it over

Report: the deck path; the audience it is written for; the governing thought; the supporting
arguments as one line each; the slide count; where the charts came from; and the one assumption
or weak link a hostile reader would attack first.

## Adapting to a branded template

The generated template is deliberately neutral. To move the deck onto a corporate template,
replace `assets/template.pptx` with a file that has the four standard layouts - *Title Slide*,
*Section Header*, *Title Only*, *Blank* - and edit `assets/theme.json` to its colours and fonts.
No code changes. Details in
[references/deck-spec.md](references/deck-spec.md#adapting-a-branded-template).

To regenerate the neutral template after editing `theme.json`:

```bash
.venv/bin/python .claude/skills/presentation/scripts/build_template.py
```
