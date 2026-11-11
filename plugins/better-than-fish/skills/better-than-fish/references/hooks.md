# Compaction hooks (Claude Code)

The Claude Code plugin ships hooks in `hooks/hooks.json` that keep the
`sessions.md` handoff in view when a conversation is compacted. They run
`scripts/btf_hook.py` (python3, standard library only). Codex does not
load them.

Every hook first locates the notes directory for the current session:

1. `$BTF_NOTES_DIR`, if set (an explicit choice beats inference)
2. the directory recorded for this session in `${TMPDIR:-/tmp}/btf-<session_id>`.
   A `PostToolUse` hook records it whenever the agent reads, writes, or
   edits a file inside a notes directory (the nearest ancestor holding
   `sessions.md` plus `CLAUDE.md` or `AGENTS.md`), or runs a Bash command
   that works there: `cd DIR`, `git -C DIR`, or `cat`/`head`/`tail`/`less`
   of a file in it. Other paths in a command (arguments, strings,
   here-document bodies) do not count. The first notebook touched wins
   and stays the session's: a later notebook (a reference notebook, another
   project's notes) is recorded as one of the session's `others`, and
   tool calls made by subagents are not recorded. Pushes made inside any of
   these notebooks are not milestones. The
   file is keyed by session id, so it survives compaction, and each
   session keeps its own directory.
3. a `notes at: PATH` line in `CLAUDE.md`, `AGENTS.md`, or `CLAUDE.local.md`
   in the session's working directory, then in its git root. A relative
   PATH is resolved against the file's directory.
4. the working directory or git root itself, if it holds `sessions.md`
   and a `CLAUDE.md` or `AGENTS.md`

In practice: point the agent at the notes directory at session start (by
path, or through the skill). Its first step under "Reading discipline" is
to read `<notes>/CLAUDE.md` or `<notes>/AGENTS.md`, and that read records
the directory for the session.

If no directory is found, the hooks print nothing. They always exit 0.

## What each hook does

| event | effect |
|---|---|
| `PreCompact` | Its output becomes instructions for the compaction summary: keep pending approvals with their exact commands, standing constraints and permissions, branch and commit state, open tasks, and the path to the latest `sessions.md` entry. |
| `SessionStart` (matcher `compact`) | After compaction, adds the last `## ` entry of `sessions.md` (up to 150 lines) to context, with a pointer to the notes `CLAUDE.md`/`AGENTS.md`. Pending approvals in that entry still need the user's explicit word. |
| `PostToolUse` (`Read`, `Write`, `Edit`, `NotebookEdit`, `Bash`) | Records the session's notes directory (see above). After `git push`, `git tag <name>`, `gh pr create`, `gh pr merge`, or `gh release create/upload/edit/delete`, asks for a `sessions.md` handoff entry unless one was written this turn, and records the time in the session file. Pushes made in the notes directory itself (the handoff being saved) and text inside here-documents are not milestones. |
| `Stop` | Only with `BTF_ENFORCE_HANDOFF=1`: if a milestone ran after the last change to `sessions.md`, blocks the stop with "write the sessions.md handoff". It never blocks twice in a row (`stop_hook_active`). |

The `SessionStart` entry is the last `## ` heading in the file, so
`sessions.md` must stay in chronological order (newest at the bottom).

## Environment

| variable | meaning | default |
|---|---|---|
| `BTF_NOTES_DIR` | the notes directory; overrides the recorded one and the `notes at:` lookup | unset |
| `BTF_ENFORCE_HANDOFF` | `1` turns on the `Stop` check | unset (off) |

Set them in the shell that starts Claude Code, or in the `env` block of a
Claude Code settings file.

## Compact instructions for CLAUDE.md

The `PreCompact` hook covers this when the notes directory is found. For
sessions where it is not, or to state the rule once for all projects, add
this to a `CLAUDE.md`. Claude Code documents the `# Compact instructions`
section for the project-root `CLAUDE.md`.

```markdown
# Compact instructions

When summarizing the conversation, preserve verbatim:
- every pending approval, with the exact command or action that waits on
  the user's word; approvals do not carry over as granted
- standing constraints and permissions the user gave or withheld, and
  their scope
- branch, worktree, and commit state: hashes, what is pushed, what is local
- open tasks and who owns them
- the path to the latest sessions.md handoff entry and its heading
```
