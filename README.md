# better-than-fish 🐟

A Claude Code, Codex, and Google Antigravity (`agy`) skill for **agent-driven research notebooks**. The user
directs; the agent writes, supersedes, distills, and indexes. The
point is to capture the *delta of understanding* that accumulates
across a conversation in a form that survives into the next one.

The name is the parable: don't hand the user a fish (one good answer
that evaporates with the session). Build the boat (a knowledge base
that compounds across sessions).

## What it does

When you're in a long-running technical investigation, this skill
governs how the agent maintains a structured knowledge base — three
tiers of durability, confidence markers, supersede-on-correction
discipline, weekly/monthly distillation, a curated sessions log,
and a parked loose-ends backlog.

The user role is supervisory. Trigger phrases drive specific actions:

- "note this" / "save this" — agent writes a journal entry
- "wrong, X" / "actually X" — agent finds and supersedes the related
  note, records what made the wrong claim plausible
- "park this" — moves current investigation to `loose-ends/parked.md`
  with full resume context
- "digest" — distills the journal into weekly/monthly summary
- "what do we know about X" — agent greps notes first, then answers

## What it isn't

- Not for one-off coding tasks
- Not human-navigable docs (those need different conventions)
- Not auto-magic — the user has to engage the triggers; the agent
  proposes proactive writes early on, switches to direct writes once
  defaults align

## Three tiers

```
durable/      [FACT] math, paper, source-grounded reality, recorded
              design patterns. Time-invariant.
empirical/    [EMP]  repeated empirical claims with version stamps.
              Stable but version-bound.
journal/      [OBS] [HYP] dated single events. Distill to empirical
              if they recur, fade if they're flukes.
```

Plus `loose-ends/parked.md` (backlog), `sessions.md` (curated session
index), and optional top-level concept directories for cross-cutting
tools.

## Install

This repo is a Claude Code **marketplace** with one plugin
(`better-than-fish`). Installation is a two-step dance: add the
marketplace, then install the plugin from it.

### From a git remote

```
/plugin marketplace add https://github.com/agurfinkel/better-than-fish
/plugin install better-than-fish@better-than-fish
```

### From a local clone

```
/plugin marketplace add /Users/you/certora/skills/better-than-fish
/plugin install better-than-fish@better-than-fish
```

The name appears twice: once for the marketplace, once for the plugin
— they happen to share the name in this single-plugin repo.

### Update later

```
/plugin marketplace update better-than-fish
```

### Uninstall

```
/plugin uninstall better-than-fish@better-than-fish
/plugin marketplace remove better-than-fish
```

### Manual symlink (for development of the skill itself)

```sh
ln -s /Users/you/certora/skills/better-than-fish/plugins/better-than-fish/skills/better-than-fish \
      ~/.claude/skills/better-than-fish
```

Bypasses the plugin system; live-edits flow through immediately.
Remove the symlink before using `/plugin install` to avoid collisions.

### Codex

Install the same skill with a symlink so edits in this repository are picked
up immediately:

```sh
mkdir -p ~/.codex/skills
ln -s /Users/you/certora/skills/better-than-fish/plugins/better-than-fish/skills/better-than-fish \
      ~/.codex/skills/better-than-fish
```

Restart Codex after installing it. Invoke the skill explicitly with
`$better-than-fish`, or use one of its trigger phrases such as "note this",
"park this", "digest weekly", or "what do we know about X?".

### Google Antigravity (`agy`)

Install the full plugin (including the `better-than-fish` skill, `notes-scribe` agent, and hooks) using the `agy` CLI:

```sh
agy plugin install /path/to/better-than-fish/plugins/better-than-fish
```

Or install the skill standalone via symlink:

```sh
mkdir -p ~/.gemini/config/skills
ln -s /path/to/better-than-fish/plugins/better-than-fish/skills/better-than-fish \
      ~/.gemini/config/skills/better-than-fish
```

## Configuration

| variable | meaning | default |
|---|---|---|
| `BTF_NOTES_DIR` | path to the notes directory | (asks once if unset) |
| `BTF_DIGEST_DAY` | weekday to remind about weekly digest | Friday |
| `BTF_ENFORCE_HANDOFF` | `1`: block stopping until a handoff follows a milestone | off |

All optional. The skill works with no configuration if the user
points the agent at the directory once; the agent records the choice in the
project's `GEMINI.md` or `AGENTS.md` (Antigravity), `AGENTS.md` (Codex), or `CLAUDE.md` (Claude Code).

## Compaction hooks (Claude Code)

The plugin installs hooks that keep the latest `sessions.md` entry in view
across compaction. The notes directory is recorded per session when the
agent reads a file in it (e.g. its `CLAUDE.md`). A `PreCompact` hook tells
the summarizer to keep pending approvals, permissions, branch and commit
state, and open tasks; a `SessionStart` hook re-injects the latest entry
afterwards; a `PostToolUse` hook asks for a handoff entry after `git
push`, `git tag`, `gh pr create/merge`, or `gh release`. They need
`python3` and do nothing when no notes directory is found. Details and a
`# Compact instructions` snippet for `CLAUDE.md`:
`plugins/better-than-fish/skills/better-than-fish/references/hooks.md`.

## Bootstrap

For a new project, ask the agent something like:

> Bootstrap better-than-fish notes at `<path>` for this project.

The agent creates the directory structure, writes a starter `AGENTS.md`
(Codex) or `CLAUDE.md` (Claude Code), and proposes initial `durable/` notes for any
project-stable facts that came up in the bootstrap conversation.
Subsequent sessions follow the trigger vocabulary above.

## Structure

```
better-than-fish/                            ← marketplace root
├── .claude-plugin/
│   └── marketplace.json                     ← lists the plugin
├── README.md
├── LICENSE
└── plugins/better-than-fish/                ← the plugin
    ├── .claude-plugin/plugin.json
    ├── hooks/hooks.json                      # compaction hooks
    ├── scripts/btf_hook.py                   # hook implementation
    └── skills/better-than-fish/
        ├── SKILL.md                          # shared skill instructions
        ├── agents/openai.yaml                # Codex UI metadata
        ├── references/
        │   ├── format.md                     # markers, file naming
        │   ├── distillation.md               # promotion criteria
        │   ├── corrections.md                # supersede pattern
        │   └── hooks.md                      # compaction hooks
        └── examples/
            ├── correction-walkthrough.md
            └── first-week-bootstrap.md
```

## License

MIT — see [LICENSE](LICENSE).

## Contributing

This skill emerged from real research workflow needs. Improvements
that strengthen the **triage** part (when does the agent decide a
finding is worth a note?) or the **distillation** part (when does
something graduate from journal → empirical → durable?) are
especially welcome.
