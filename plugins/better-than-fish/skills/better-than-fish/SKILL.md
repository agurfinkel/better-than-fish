---
name: better-than-fish
description: Maintain agent-driven research notebooks that preserve technical understanding across sessions. Use for long-running technical research and engineering investigations when the user says "note this", "save this", "park this", "digest", corrects an earlier claim, asks "what do we know about X", wants to bootstrap structured research notes, or wants durable, empirical, journal, correction, session, and loose-end records maintained on their behalf. Do not use for one-off coding tasks, ticket tracking, or notes primarily intended for human navigation.
---

# better-than-fish

A skill for agent-driven research notebooks. The user directs; the agent
writes, supersedes, distills, and indexes. The point is to capture the
**delta of understanding** that accumulates over a conversation in a form
that survives into the next one.

The name is the parable: don't hand the user a fish (one good answer that
evaporates with the session). Build the boat (a knowledge base that
compounds across sessions).

## When this skill is in scope

This skill is for **technical research and engineering investigations** where:
- Insights accumulate over time
- Some claims are durable (paper-grounded, source-verified) and others are
  speculative (working hypotheses)
- The corpus grows large enough that an agent can't hold it in context
- The human is the director, not the writer

Out of scope: one-off coding tasks, things with their own ticketing system,
notes meant for human navigation (those need different conventions —
indexing, tags, searchability).

## Where notes live

Notes live in a single project directory configured by the user. The agent
discovers it in this order:

1. `$BTF_NOTES_DIR` env var, if set
2. An `AGENTS.md` or `CLAUDE.md` in the current project root that says
   "notes at: PATH". Prefer the host-native file (`AGENTS.md` for Codex,
   `CLAUDE.md` for Claude Code); honor either when already present.
3. The agent asks the user once, records the answer in the project's
   host-native instruction file, and uses it from then on

The directory layout is:

```
<notes-dir>/
  AGENTS.md or         <= 80 lines. Project-stable conventions only.
  CLAUDE.md
                          No active-investigation content; that lives in
                          journal/. Always loaded.
  durable/             [FACT] — math, paper, source-grounded reality,
                          recorded design patterns. Time-invariant or
                          near-invariant.
  empirical/           [EMP] — repeated empirical claims, version-bound.
                          Things that have been observed multiple times
                          and aren't flukes, but aren't math/paper
                          truths either. Each note carries a "verified
                          against" version stamp.
  journal/YYYY-MM/     [OBS], [HYP] — single events, dated.
                          Append-only stream of investigation entries.
  weekly/YYYY-Www.md   distilled weekly digests
  monthly/YYYY-MM.md   distilled monthly digests
  loose-ends/parked.md  parked explorations with enough context to resume
  sessions.md           chronological index of significant conversation
                          sessions and what they produced. Added per
                          session that moves durable state forward.
  papers/              source corpus (PDFs, papers, etc.)
  <concept>/           top-level directories for tools or concepts that
                          cut across investigations (e.g. lemur/ for
                          analysis tooling). See "Top-level concept
                          directories" below.
```

Subdirectories under `durable/`, `empirical/`, and `journal/` are
organized by topic when the corpus grows beyond ~30 files in one folder.

### The three tiers

The split between `durable/`, `empirical/`, and `journal/` reflects how
likely a claim is to survive over time:

- **`durable/`**: math facts (e.g. McCormick is the convex envelope of
  xy in a box), paper-grounded design (the z3 NLA waterfall), source-
  grounded reality (the `force_phase` API at smt_context.h:1097),
  **recorded design patterns** (an experimental design we tried — the
  pattern itself is durable even if the experiment turned out to be
  inconclusive).
- **`empirical/`**: claims supported by repeated empirical observation.
  "Ramped Gröbner closes more on Lyapunov benchmarks" — true now, not a
  math fact, but consistently observed. Each empirical note is bound to
  a specific code version and may go stale when the code changes.
- **`journal/`**: single observations and hypotheses from one
  investigation session. Some will distill to empirical, some will be
  flukes that fade.

The user's framing: **"Anything empirical is durable but only for that
version."** Promotion across tiers happens via distillation (see
`references/distillation.md`).

### Top-level concept directories

Tools and concepts that cut across multiple investigations may earn
their own top-level directory in the notes (e.g. `lemur/` for analysis
tooling). These hold design docs, prototype code, accumulated artifacts
(small SQLite DBs, etc.) — anything that needs to outlive a particular
worktree or investigation thread.

When a concept directory's content matures (gets implemented in
production, lands in a library), it migrates out, and a thin pointer
note in `durable/` describes its conceptual role.

## Confidence markers — the core discipline

Every claim in a note carries a marker. The marker is a tag at the start of
the relevant paragraph, in square brackets:

- `[FACT]` — math, paper, source-verified, or recorded design pattern.
  Should cite a source (paper section, file:line, commit hash) when
  applicable. Lives in `durable/`. Time-invariant or near-invariant.
- `[EMP]` — empirical claim that has been observed multiple times.
  Carries a "Verified against" version stamp (z3 commit, build, etc.).
  Lives in `empirical/`. Version-bound; may go stale with code changes.
- `[OBS YYYY-MM-DD]` — single empirical observation, dated. Lives in
  `journal/`. Distills to `empirical/` if it survives repetition.
- `[HYP]` — working hypothesis, untested or partially tested. The most
  fragile category. Lives in `journal/` until verified or refuted.
- `[OPEN]` — known unknown. Has a corresponding entry in `loose-ends/`.
- `[SUPERSEDED → path]` — claim was wrong; left as a trail to the corrected
  version, never silently deleted.

The user's framing: **what persists is true.** A `[HYP]` that survives
weeks of work without contradiction earns promotion to `[OBS]`, then to
`[EMP]` once observed across multiple investigations, then potentially
to `[FACT]` if it becomes math/paper/source-grounded. The markers make
this explicit instead of guessed.

See `references/format.md` for full conventions and `references/corrections.md`
for the supersede pattern.

## Triggers

The agent acts on these phrases without further confirmation:

- **"note this"** / **"save this"** — write a journal entry for the current
  finding. Use today's date.
- **"wrong, [correction]"** or **"actually [correction]"** — find the related
  note (grep), supersede it with `[SUPERSEDED → ...]`, write a new note with
  the correct claim, and append a brief "why I was misled" line. This is the
  highest-value action. Never delete the wrong note silently.
- **"park this"** — move the current investigation to `loose-ends/parked.md`
  with the five-field format (Status, Context, Why parked, To resume,
  Effort estimate).
- **"digest"** — read journal entries since the last digest, write the
  weekly or monthly summary. Promote anything that's been referenced
  multiple times to `durable/`.
- **"what do we know about X"** — grep notes first, summarize what's there,
  then answer. Don't re-derive what's already written down.

The user may add project-specific triggers in the project's `AGENTS.md` or
`CLAUDE.md`.

## Proactive writes (without being told)

The agent commits writes proactively in these situations:

1. **After a substantive finding.** If the user says "we are learning a lot",
   "interesting", or similar markers of insight, propose a journal entry.
   First conversation in a new project: propose every write before
   committing. Once the user's defaults are clear, switch to writing
   directly with a session-end summary of writes.

2. **On corrections.** If the user corrects a claim the agent made
   (in conversation or in notes), supersede immediately. Even if the
   user doesn't say "wrong" explicitly — recognize the correction.

3. **Before context-window pressure.** If the conversation is approaching
   limits or the user is wrapping up, flush the conversation's durable
   findings to `journal/` so they survive the session. Also append a
   `sessions.md` entry summarizing what the session produced and what
   corrections were made — see "Sessions log" below.

4. **When asked about a topic, grep first.** Before answering "what do we
   know about X", read the existing notes. Don't re-explain things the
   user already taught.

## Reading discipline

At the start of any session involving the project:

1. Read `<notes-dir>/AGENTS.md` or `<notes-dir>/CLAUDE.md` for project
   conventions and triggers. Prefer the host-native file when both exist.
   Do this as soon as the notes directory is known; in Claude Code the
   read also records the directory for the compaction hooks.
2. Skim `durable/` index (filenames + descriptions) to understand the
   landscape.
3. Read the most recent weekly digest if it exists — it tells you the
   current state of investigation.
4. Read recent (`< 7 days`) journal entries that may be relevant to the
   current task.

Don't read everything — the system is sized so that this onboarding is
cheap. If the user asks about something specific, grep for that topic in
notes/.

## Distillation (consolidation)

This is the practice that makes the system work. Without it, you accumulate
a write-only journal.

- **Weekly digest** (Friday-ish, or when the user types "digest weekly"):
  read the past week's journal entries, write a 1-page summary in
  `weekly/YYYY-Www.md`. Identify which `[HYP]`s survived, which got
  superseded, which `[OBS]`s are durable patterns vs single-instance
  noise. Move durable ones up the chain.

- **Monthly digest** (first Monday of new month or "digest monthly"):
  read 4 weekly digests, write `monthly/YYYY-MM.md`. Promote anything
  referenced across multiple weeks to `durable/`.

- **Promotion to `durable/`** is the agent's call, but propose it: "I've
  seen X referenced in 3 weekly digests. Propose promoting to durable.
  OK?" — if the user agrees, the note moves with `[FACT]` (or `[OBS]` if
  not source-grounded). Don't promote silently.

See `references/distillation.md` for examples of well-vs-poorly-done digests.

## Loose ends

`loose-ends/parked.md` is a backlog of investigations that were started or
considered but not pursued. Each entry has five fields:

```markdown
## <one-line title>
**Status:** parked YYYY-MM-DD
**Context:** what's the question, what's known so far, why it matters
**Why parked:** what was prioritized instead
**To resume:** concrete next steps an agent can pick up cold
**Effort estimate:** rough wall-time, e.g., "~30 min" or "~half-day"
**References:** links to related notes by filename
```

When the user says "what should I work on next?" or "I have an hour, pick
something" — grep for `Effort estimate.*30 min` (or similar) and propose
the matching items.

## Sessions log

`sessions.md` at the notes-dir root is a curated chronological index of
**significant** conversation sessions. Not a log of every conversation
— add an entry only when the session produced notes, code, or
decisions worth pointing back to.

Each entry has:

- **Date** (header)
- **Session** — the conversation's short name, if the host exposes one.
  Lets agents and humans correlate the entry with
  the actual conversation log. Backtick-quoted: `\`session-name\``.
- **Theme** — one-line description of what the session was about
- **Key outputs** — list of new/modified notes, prototype code, etc.
- **Critical corrections** — if the user corrected the agent's framing
  during the session, list the corrections (also captured in superseded
  notes). This is high-value content; surfaces when an investigation's
  understanding pivoted.
- **Status** — complete / paused / superseded by later session
- **Next-session pickup candidates** — pointers to `loose-ends/parked.md`
  entries or open questions that came up.

The agent maintains this file. When wrapping up a session that produced
durable content, propose appending an entry; user reviews and approves.

For a new agent in a future session, `sessions.md`'s most recent entry
is the fastest way to know "what's the state of play here?" — faster
than reading the most recent journal entry.

In Claude Code, the plugin's hooks re-inject the most recent entry after
compaction and ask for a new entry after milestone commands (`git push`,
`git tag`, `gh pr create/merge`, `gh release`). See `references/hooks.md`.

## Anti-patterns

Things that look reasonable but degrade the system:

- **Writing notes that summarize without an interpretation.** "We tried X
  and saw Y" is incomplete. "...and our reading is Z because W" is the
  durable form.
- **Deleting wrong notes instead of superseding them.** The correction
  trail is the highest-value content; don't lose it.
- **Notes about transient state.** PR-1483 status, today's runner load,
  etc. — these belong in PR descriptions or task tools, not the knowledge
  base.
- **Heavy schemas.** YAML frontmatter, mandatory fields, long templates —
  any of these mean fewer notes get written. The marker tags + a date are
  sufficient structure.
- **Reading everything before answering.** Grep specifically. The system
  scales because the agent doesn't need to load the whole corpus.

## Bootstrap

For a new project: follow `examples/first-week-bootstrap.md`. The agent
creates the directory structure, draws conventions from the user's first
session, and writes a starter host-native instruction file (`AGENTS.md` for
Codex or `CLAUDE.md` for Claude Code) in the notes directory.

## Configuration

| variable | meaning | default |
|---|---|---|
| `BTF_NOTES_DIR` | path to the notes directory | (asks once if unset) |
| `BTF_DIGEST_DAY` | which weekday to remind about weekly digest | Friday |
| `BTF_ENFORCE_HANDOFF` | `1`: block stopping until a handoff follows a milestone (Claude Code hooks) | off |

All are optional. The skill works with no configuration if the user
points the agent at the directory once.

## Files in this skill

- `SKILL.md` — this file.
- `references/format.md` — marker conventions, file naming, frontmatter.
- `references/distillation.md` — promotion criteria and digest examples.
- `references/corrections.md` — the supersede pattern, "why I was misled".
- `references/hooks.md` — Claude Code compaction hooks and the
  `# Compact instructions` snippet.
- `examples/correction-walkthrough.md` — a worked correction example.
- `examples/first-week-bootstrap.md` — what notes should exist after
  one week of use.
