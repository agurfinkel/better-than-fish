#!/usr/bin/env python3
"""better-than-fish hooks: keep the sessions.md handoff alive across compaction.

Usage: btf_hook.py session-start | pre-compact | post-tool | stop

The notes directory is recorded per session in ${TMPDIR:-/tmp}/btf-<session_id>
whenever a Read/Write/Edit (or a Bash command naming a path) touches a file
inside a notes directory. That file survives compaction.

Reads the hook input JSON on stdin. Never fails the session: every path
exits 0, and any unexpected error produces no output.
"""

import json
import os
import re
import shlex
import subprocess
import sys
import time

ENTRY_LINE_CAP = 150
NOTES_AT = re.compile(r"notes at:\s*`?([^`\s][^`]*?)`?\s*$", re.IGNORECASE)
POINTER_FILES = ("GEMINI.md", "CLAUDE.md", "AGENTS.md", "CLAUDE.local.md")
INSTRUCTION_FILES = ("GEMINI.md", "CLAUDE.md", "AGENTS.md")

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


def is_antigravity(data):
    return "conversationId" in data or "workspacePaths" in data or "transcriptPath" in data


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


def enclosing_notes_dir(path):
    """Nearest ancestor of path (or path itself) that is a notes dir."""
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isdir(path):
        path = os.path.dirname(path)
    while True:
        if os.path.isdir(path) and is_notes_dir(path):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def find_notes_dir(data):
    recorded = load_state(data).get("notes")
    if recorded and os.path.isdir(recorded):
        return recorded
    env = os.environ.get("BTF_NOTES_DIR")
    if env:
        env = os.path.expanduser(env)
        return env if os.path.isdir(env) else None

    cwd = None
    if data.get("workspacePaths"):
        cwd = data["workspacePaths"][0]
    if not cwd:
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
    return os.path.join(notes, "GEMINI.md")


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
    sid = data.get("conversationId") or data.get("session_id") or "nosession"
    sid = re.sub(r"[^A-Za-z0-9_.-]", "_", str(sid))
    tmp = os.environ.get("TMPDIR") or "/tmp"
    return os.path.join(tmp, "btf-" + sid)


def load_state(data):
    try:
        with open(state_path(data), encoding="utf-8") as fh:
            state = json.load(fh)
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(data, **fields):
    state = load_state(data)
    state.update(fields)
    try:
        with open(state_path(data), "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    except OSError:
        pass


def emit(event, context):
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": event, "additionalContext": context}
    }))


def session_start(data):
    notes = find_notes_dir(data)
    if not notes:
        if is_antigravity(data):
            print(json.dumps({}))
        return
    sessions = os.path.join(notes, "sessions.md")
    heading, entry = latest_entry(sessions)
    conv = instruction_file(notes)
    parts = [
        "The better-than-fish notes directory is %s." % notes,
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

    if is_antigravity(data):
        print(json.dumps({
            "injectSteps": [
                {
                    "systemMessage": {
                        "systemMessage": "\n".join(parts)
                    }
                }
            ]
        }))
    else:
        if data.get("source", "compact") == "compact":
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


HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][\w-]*)\1")
CD_OR_C = re.compile(
    r"""(?x)
    (?:^|[;&|(]|&&|\|\|)\s*cd\s+(?P<cd>"[^"]+"|'[^']+'|[^\s;&|)]+)
    | \bgit\s+-C\s+(?P<gc>"[^"]+"|'[^']+'|[^\s;&|)]+)
    | (?:^|[;&|(]|&&|\|\|)\s*(?:cat|head|tail|less)\s+(?:-\S+\s+)*(?P<rd>"[^"]+"|'[^']+'|[^\s;&|)]+)
    """
)


def strip_heredocs(command):
    """Drop here-document bodies: they are file contents or input data,
    not paths the command works in (nor commands it runs)."""
    out, end = [], None
    for line in command.splitlines():
        if end is not None:
            if line.strip() == end:
                end = None
            continue
        out.append(line)
        m = HEREDOC.search(line)
        if m:
            end = m.group(2)
    return "\n".join(out)


def command_dirs(command):
    """Paths a shell command works in: `cd DIR`, `git -C DIR`, and the first
    file read by cat/head/tail/less.
    Other absolute paths in a command (arguments, strings, file contents)
    are not evidence of which notebook the session uses."""
    dirs = []
    for m in CD_OR_C.finditer(strip_heredocs(command)):
        d = (m.group("cd") or m.group("gc") or m.group("rd")).strip("'\"")
        if d.startswith(("/", "~/")):
            dirs.append(os.path.expanduser(d))
    return dirs[:8]


def touched_paths(data):
    if is_antigravity(data):
        tool_call = data.get("toolCall") or {}
        tool_name = tool_call.get("name") or ""
        args = tool_call.get("args") or {}
        if tool_name in ("run_command", "bash"):
            cmd = args.get("CommandLine") or args.get("command") or ""
            return command_dirs(cmd)
        if tool_name in ("read_file", "write_file", "edit_file"):
            p = args.get("Path") or args.get("path") or ""
            return [p] if p else []
        return []

    tool = data.get("tool_name")
    tin = data.get("tool_input") or {}
    if tool in ("Read", "Write", "Edit", "NotebookEdit"):
        p = tin.get("file_path") or tin.get("notebook_path")
        return [p] if p else []
    if tool == "Bash":
        return command_dirs(tin.get("command") or "")
    return []


def inside(path, directory):
    try:
        p = os.path.realpath(path)
        d = os.path.realpath(directory)
    except Exception:
        return False
    return p == d or p.startswith(d.rstrip(os.sep) + os.sep)


def record_notes_dir(data):
    """Remember the notes dir the agent just touched; latest wins."""
    for path in touched_paths(data):
        found = enclosing_notes_dir(path)
        if found:
            if load_state(data).get("notes") != found:
                save_state(data, notes=found)
            return


def post_tool(data):
    record_notes_dir(data)
    command = ""
    if is_antigravity(data):
        tool_call = data.get("toolCall") or {}
        tool_name = tool_call.get("name") or ""
        args = tool_call.get("args") or {}
        if tool_name in ("run_command", "bash"):
            command = args.get("CommandLine") or args.get("command") or ""
    else:
        if data.get("tool_name") == "Bash":
            command = (data.get("tool_input") or {}).get("command") or ""

    if command and MILESTONE.search(strip_heredocs(command)):
        notes = find_notes_dir(data)
        if notes:
            cwd = (data.get("workspacePaths") or [None])[0] or data.get("cwd") or os.getcwd()
            where = command_dirs(command) or [cwd]
            if not any(inside(d, notes) for d in where):
                save_state(data, milestone=time.time(), command=command[:500])
                if not is_antigravity(data):
                    emit(
                        "PostToolUse",
                        "Milestone command ran. Append a sessions.md handoff entry "
                        "(better-than-fish format) to %s before continuing, unless one was "
                        "written this turn." % os.path.join(notes, "sessions.md"),
                    )

    if is_antigravity(data):
        print(json.dumps({}))


def stop(data):
    if os.environ.get("BTF_ENFORCE_HANDOFF") != "1":
        return
    if data.get("stop_hook_active"):
        return
    state = load_state(data)
    if "milestone" not in state:
        return
    notes = find_notes_dir(data)
    if not notes:
        return
    sessions = os.path.join(notes, "sessions.md")
    try:
        mtime = os.path.getmtime(sessions)
    except OSError:
        mtime = 0.0
    if float(state.get("milestone", 0)) <= mtime:
        return

    reason = ("write the sessions.md handoff (%s): a milestone command ran "
              "after its last update: %s" % (sessions, state.get("command", "")[:200]))

    if is_antigravity(data):
        print(json.dumps({
            "decision": "continue",
            "reason": reason
        }))
    else:
        print(json.dumps({
            "decision": "block",
            "reason": reason
        }))


HANDLERS = {
    "session-start": session_start,
    "pre-compact": pre_compact,
    "post-tool": post_tool,
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
