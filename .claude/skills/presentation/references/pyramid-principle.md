# The Pyramid Principle, applied to a deck

Barbara Minto's rule: **ideas at any level are always summaries of the ideas grouped below
them.** One thought at the top, supported by a small group of arguments, each supported in turn
by evidence. The reader gets the answer first and the reasoning only if they want it.

Two consequences drive everything in this skill:

- **Answer first.** The governing thought goes on slide 2, not slide 12. A deck that builds to a
  conclusion is a deck whose conclusion gets missed.
- **Group, then summarise.** You never assemble slides and then write a summary. You settle the
  top, then the layer under it, then the evidence - which is why the interview order is audience,
  apex, arguments, slides.

```
                  GOVERNING THOUGHT
                  the answer, one sentence
                 /         |         \
        Argument 1    Argument 2    Argument 3      <- MECE, each a full sentence
        /      \       /      \       /      \
    evidence evidence   ...     ...   ...    ...    <- charts, tables, facts
```

## Framing the question: SCQA

Before drafting the apex, get the question straight. The governing thought is the **answer to
Q**, and it is the only thing on the pyramid that has to be true of *this* audience.

| | |
|---|---|
| **Situation** | What everyone already agrees on. "v2.4 is scheduled for 15 October." |
| **Complication** | What changed or what is wrong. "Nine weeks of throughput say that date is not reachable." |
| **Question** | What the complication forces the audience to ask. "Do we move the date or cut the scope?" |
| **Answer** | The governing thought. "v2.4 will not make 15 October - plan for 1 November and decide what to cut." |

If the Question is not one this audience can act on, the deck is aimed at the wrong room. Go back
and ask who is actually deciding.

A useful test: write the S and the C as the two sentences you would say out loud before slide 2.
If they take more than two sentences, the deck has a scoping problem, not a structure problem.

## What makes a governing thought

It must:

- **Answer, not describe.** "Churn is concentrated in accounts under 20 seats, and the fix is a
  pricing change" — not "We analysed churn by segment."
- **Be falsifiable.** Someone in the room could disagree with it. "There are several factors
  affecting delivery" is not a thought, it is a shrug.
- **Carry the so-what for this audience.** The same finding yields different apexes: an exec
  hears "the launch date moves six weeks unless we cut scope"; the delivery team hears "stop
  planning around 15 October and re-baseline this sprint".
- **Survive alone.** If they remember one sentence, this is it. Read it back with nothing else
  attached and see whether it still means something.

### The so-what ladder

Push each candidate up the ladder until it stops moving:

| Rung | Example | Fit for |
|---|---|---|
| Observation | "P85 completion is 1 November." | nobody - this is an output, not a message |
| Implication | "That is six weeks past the committed date." | analysts |
| Consequence | "The launch slips a quarter unless scope is cut." | steering committee |
| Decision | "Commit to 1 November, or cut ~40 issues this week." | executives |

Most first drafts sit on rung 1. Executive decks belong on rung 3 or 4.

## Building the argument layer

Each argument is a complete sentence that answers "why is the governing thought true?" - not a
topic label. "Throughput is stable at 8-9 per week, so there is no ramp to hope for" is an
argument. "Throughput" is a folder name.

Two ways to group, and mixing them is the most common structural failure:

- **Deductive** - premise, premise, therefore. Strong, but brittle: knock out one link and the
  whole chain fails. Use for two or three tight steps, rarely more.
- **Inductive** - several independent reasons of the same kind, all pointing the same way. More
  robust, easier to read, and what most decks should use. The test: can you name the group in one
  word? ("three reasons the date is unreachable")

### MECE, checked properly

- **Mutually exclusive** - no two arguments make the same point in different clothes. If
  argument 2's evidence would also serve argument 3, they are one argument.
- **Collectively exhaustive** - nothing load-bearing is missing. Ask what a hostile reader would
  say is unaddressed, and either add it or put it in the appendix with a reason.

Three arguments is the natural number. Two often means one argument split in half; five means
the grouping logic has not been found yet.

### Ordering

Pick an order the audience can feel, and say what it is:

- **Chronological** - what happened, what it caused, what happens next
- **Structural** - by segment, region, product; must be MECE by construction
- **Degree** - largest effect first; the default when in doubt

## Action titles

Every content slide's title is the message of that slide, as a sentence.

| Not this | This |
|---|---|
| Throughput analysis | Throughput has held at 8-9 issues per week for 12 weeks |
| Percentile table | No confidence level reaches 15 October |
| Options | Only two options close the gap - and one needs a product decision |
| Next steps | Three decisions this week keep the November date credible |

**The title test:** read every title in order, with nothing else on screen. That sequence must be
the whole argument, in order, and each title must ladder up to the governing thought. If a title
is a noun phrase, it has no message and the slide has no reason to exist yet. If a title is true
but does not support the apex, the slide belongs in the appendix.

The takeaway line at the bottom of each slide is not a second title - it is the "so what" the
evidence earns: what the reader should conclude, or do, having seen it.

## Editing the pyramid down

When the deck runs over the audience's budget, cut in this order:

1. Slides whose title does not ladder up to the apex → appendix or delete
2. Two slides making one point → merge
3. Method and caveats above the fold → appendix (keep a one-line pointer)
4. A fourth argument that is really a sub-point of another → demote it
5. Evidence that repeats what the chart already said → delete

Never cut by shrinking the font.

## Worked example

**Material.** A Monte Carlo forecast: 84 issues remaining, 12 weeks of throughput at 8-9/week,
P50 finishes 25 Oct, P85 1 Nov, P95 8 Nov, 0% probability of hitting 15 Oct.

**Audience.** Engineering leadership, 10 minutes, they own the date and the scope.

**SCQA.** S: v2.4 is committed for 15 October. C: nine weeks of delivery data say that is not
reachable. Q: move the date or cut the scope? A: ↓

**Governing thought.** *"v2.4 will not make 15 October - plan for 1 November and decide what to
cut."* (Rung 4. Names the decision and its cost.)

**Arguments** - inductive, three independent reasons, ordered by how hard they are to argue with:

1. The remaining scope is 84 issues and the backlog has not shrunk in four weeks.
2. Throughput is stable at 8-9 issues per week, so there is no ramp to hope for.
3. Even the optimistic tail of 10,000 simulations lands after 15 October.

**Rejected apexes, and why.** "The forecast shows P85 on 1 November" - rung 1, describes the
output. "Delivery is at risk" - not falsifiable, and it lets the room agree without deciding
anything.

The full deck built from this pyramid is in
[example-spec.json](example-spec.json).
