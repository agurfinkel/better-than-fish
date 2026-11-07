# better-than-fish

Agent-driven research notebooks for **Google Antigravity (`agy`)**, **Claude Code**, and **Codex**.

The user directs; the agent writes, supersedes, distills, and indexes. Captures the delta of understanding across conversations in a durable knowledge base.

---

## Installation

### Google Antigravity (`agy`)

**Option 1: Install the complete plugin (Skill + Subagent + Hooks)**

From a local clone:
```sh
agy plugin install /path/to/better-than-fish/plugins/better-than-fish
```

To verify the installation:
```sh
agy plugin list
agy plugin validate ~/.gemini/config/plugins/better-than-fish
```

**Option 2: Install as a standalone skill**

If you only want the `better-than-fish` skill without lifecycle hooks:
```sh
mkdir -p ~/.gemini/config/skills
ln -s /path/to/better-than-fish/plugins/better-than-fish/skills/better-than-fish \
      ~/.gemini/config/skills/better-than-fish
```

### Claude Code

From the repository root (marketplace):
```sh
/plugin marketplace add https://github.com/agurfinkel/better-than-fish
/plugin install better-than-fish@better-than-fish
```

### Codex

Symlink the skill into your Codex skills directory:
```sh
mkdir -p ~/.codex/skills
ln -s /path/to/better-than-fish/plugins/better-than-fish/skills/better-than-fish \
      ~/.codex/skills/better-than-fish
```

---

## What This Plugin Bundles

- **Skill (`better-than-fish`)**: Governs the 3-tier notebook structure (`durable/`, `empirical/`, `journal/`), confidence markers (`[FACT]`, `[EMP]`, `[OBS]`, `[HYP]`, `[OPEN]`, `[SUPERSEDED]`), and distillation workflows.
- **Subagent (`notes-scribe`)**: A dedicated scribe agent that records findings, updates `sessions.md`, parks items, and commits notebook updates.
- **Hooks (`hooks.json`)**:
  - `SessionStart`: Injects the latest `sessions.md` handoff and project conventions at session start.
  - `PostToolUse`: Detects milestone commands (`git push`, `git tag`, `gh pr create/merge`, `gh release`).
  - `Stop`: Ensures a handoff entry is written before stopping when `BTF_ENFORCE_HANDOFF=1`.

---

## Getting Started

1. **Bootstrap a notes directory**:
   In any project conversation, ask:
   > *"Bootstrap better-than-fish notes at `<path>` for this project."*

   Or add a pointer to your project root's `GEMINI.md` or `AGENTS.md`:
   ```markdown
   notes at: /path/to/notes
   ```

2. **Core Triggers**:
   - `"note this"` / `"save this"` — record the current finding into `journal/`
   - `"wrong, [correction]"` / `"actually [correction]"` — supersede previous note in place and record the corrected claim
   - `"park this"` — move current topic to `loose-ends/parked.md`
   - `"digest"` / `"digest weekly"` — distill recent journal entries into `weekly/` or `monthly/`
   - `"what do we know about X"` — grep notes first and summarize prior understanding
