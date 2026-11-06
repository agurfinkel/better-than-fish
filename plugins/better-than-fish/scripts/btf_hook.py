#!/usr/bin/env python3
"""better-than-fish hooks: keep the sessions.md handoff alive across compaction.

Usage: btf_hook.py session-start | pre-compact | post-bash | stop

Reads the hook input JSON on stdin. Never fails the session: every path
exits 0, and any unexpected error produces no output.
"""

import json
import os
import re
import subprocess
import sys
import time

ENTRY_LINE_CAP = 150
NOTES_AT = re.compile(r"notes at:\s*`?([^`\s][^`]*?)`?\s*$", re.IGNORECASE)
POINTER_FILES = ("CLAUDE.md", "AGENTS.md", "CLAUDE.local.md")
INSTRUCTION_FILES = ("CLAUDE.md", "AGENTS.md")

# Commands that move shared state forward. `git tag` with no arguments or
# with -l/--list only lists, and `gh release view/list/download` only read,
# so those are not milestones.
MILESTONE = re.compile(
    r"""(?x)
    \bgit\b(?:\s+-[Cc]\s+\S+|\s+--?[\w-]+(?:=\S+)?)*\s+
        (?:push\b|tag\s+(?!-l\b|--list\b|-n\b)[^\s;&|])
    | \bgh\s+pr\s+(?:create|merge)\b
    | \bgh\s+release\s+(?:create|upload|edit|delete)\b
    """
)


def read_input():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def git_root(path):
    try:
        out = subprocess.run(
            ["git", "-C", path, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except Exception:
        pass
    return None


def is_notes_dir(path):
    return os.path.isfile(os.path.join(path, "sessions.md")) and any(
        os.path.isfile(os.path.join(path, f)) for f in INSTRUCTION_FILES
    )


def pointer_in(directory):
    """Return the dir named by a `notes at: PATH` line in directory's files."""
    for name in POINTER_FILES:
        path = os.path.join(directory, name)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    m = NOTES_AT.search(line)
                    if not m:
                        continue
                    target = os.path.expanduser(m.group(1).strip())
                    if not os.path.isabs(target):
                        target = os.path.join(directory, target)
                    target = os.path.normpath(target)
                    if os.path.isdir(target):
                        return target
        except OSError:
            continue
    return None


def find_notes_dir(data):
    env = os.environ.get("BTF_NOTES_DIR")
    if env:
        env = os.path.expanduser(env)
        return env if os.path.isdir(env) else None
    cwd = data.get("cwd") or os.getcwd()
    candidates = [cwd]
    root = git_root(cwd)
    if root and os.path.normpath(root) != os.path.normpath(cwd):
        candidates.append(root)
    for d in candidates:
        found = pointer_in(d)
        if found:
            return found
    # The session may run inside the notes directory itself.
    for d in candidates:
        if is_notes_dir(d):
            return d
    return None


def instruction_file(notes):
    for name in INSTRUCTION_FILES:
        if os.path.isfile(os.path.join(notes, name)):
            return os.path.join(notes, name)
    return os.path.join(notes, "CLAUDE.md")


def latest_entry(sessions_path):
    """Return (heading, text) of the last `## ` entry, capped in lines."""
    try:
        with open(sessions_path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return None, None
    start, fenced = None, False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("## "):
            start = i
    if start is None:
        return None, None
    entry = lines[start:]
    while entry and not entry[-1].strip():
        entry.pop()
    if len(entry) > ENTRY_LINE_CAP:
        dropped = len(entry) - ENTRY_LINE_CAP
        entry = entry[:ENTRY_LINE_CAP] + [
            "[... %d more lines in %s]" % (dropped, sessions_path)
        ]
    return lines[start][3:].strip(), "\n".join(entry)


def state_path(data):
    sid = re.sub(r"[^A-Za-z0-9_.-]", "_", str(data.get("session_id") or "nosession"))
    tmp = os.environ.get("TMPDIR") or "/tmp"
    return os.path.join(tmp, "btf-" + sid)


def emit(event, context):
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": event, "additionalContext": context}
    }))


def session_start(data):
    if data.get("source", "compact") != "compact":
        return
    notes = find_notes_dir(data)
    if not notes:
        return
    sessions = os.path.join(notes, "sessions.md")
    heading, entry = latest_entry(sessions)
    conv = instruction_file(notes)
    parts = [
        "Context was compacted. The better-than-fish notes directory is %s." % notes,
        "Project conventions are in %s." % conv,
    ]
    if entry:
        parts.append(
            "The most recent handoff entry in %s (\"%s\") follows. Read %s and "
            "this entry before acting; pending approvals listed there still "
            "require the user's explicit word." % (sessions, heading, conv)
        )
        parts.append("\n" + entry)
    else:
        parts.append(
            "%s has no `## ` entry yet. Read %s before acting; pending approvals "
            "still require the user's explicit word." % (sessions, conv)
        )
    emit("SessionStart", "\n".join(parts))


def pre_compact(data):
    notes = find_notes_dir(data)
    if not notes:
        return
    sessions = os.path.join(notes, "sessions.md")
    heading, _ = latest_entry(sessions)
    where = sessions + (" (latest entry: \"%s\")" % heading if heading else "")
    print(
        "Preserve verbatim in the summary: (1) every pending approval and the "
        "exact command or action waiting on the user's word; (2) standing "
        "constraints and permissions the user granted or withheld, with their "
        "scope; (3) branch, worktree, and commit state (hashes, what is pushed "
        "and what is local); (4) open tasks and who owns them; (5) the path to "
        "the latest handoff entry: %s." % where
    )


def post_bash(data):
    if data.get("tool_name") != "Bash":
        return
    command = (data.get("tool_input") or {}).get("command") or ""
    if not MILESTONE.search(command):
        return
    notes = find_notes_dir(data)
    if not notes:
        return
    try:
        with open(state_path(data), "w", encoding="utf-8") as fh:
            json.dump({"milestone": time.time(), "command": command[:500],
                       "notes": notes}, fh)
    except OSError:
        pass
    emit(
        "PostToolUse",
        "Milestone command ran. Append a sessions.md handoff entry "
        "(better-than-fish format) to %s before continuing, unless one was "
        "written this turn." % os.path.join(notes, "sessions.md"),
    )


def stop(data):
    if os.environ.get("BTF_ENFORCE_HANDOFF") != "1":
        return
    if data.get("stop_hook_active"):
        return
    try:
        with open(state_path(data), encoding="utf-8") as fh:
            state = json.load(fh)
    except (OSError, ValueError):
        return
    notes = state.get("notes") or find_notes_dir(data)
    if not notes:
        return
    sessions = os.path.join(notes, "sessions.md")
    try:
        mtime = os.path.getmtime(sessions)
    except OSError:
        mtime = 0.0
    if float(state.get("milestone", 0)) <= mtime:
        return
    print(json.dumps({
        "decision": "block",
        "reason": "write the sessions.md handoff (%s): a milestone command ran "
                  "after its last update: %s" % (sessions, state.get("command", "")[:200]),
    }))


HANDLERS = {
    "session-start": session_start,
    "pre-compact": pre_compact,
    "post-bash": post_bash,
    "stop": stop,
}


def main():
    try:
        handler = HANDLERS.get(sys.argv[1] if len(sys.argv) > 1 else "")
        if handler:
            handler(read_input())
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
