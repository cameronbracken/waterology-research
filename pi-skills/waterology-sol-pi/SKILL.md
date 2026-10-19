---
name: waterology-sol-pi
description: >
  Delegate a coding task to SoL-Pi, a token-efficient Pi agent with Action
  Fusion, ObservationPack, Evidence-Preserving Reducer and Online Context
  Compact enabled, and report its answer, changes and cost. Use when the user
  asks to run something with SoL-Pi, wants a cheaper long-running worker, or
  wants to compare SoL-Pi against this agent.
---

<!-- Generated from skills/sol-pi/SKILL.md. Do not edit. -->

# SoL-Pi

SoL-Pi is a separate coding agent from [NVlabs/SoL-Pi](https://github.com/NVlabs/SoL-Pi).
The `sol-pi-run` launcher runs it from a local SoL-Pi checkout, in the Pi
release that checkout pins, with its own agent directory (`~/.sol-pi/agent`).
Models and logins come from the user's Pi (`~/.pi/agent/models.json` and
`auth.json`), which are linked and never changed.

## Before the first task

Check that the launcher is installed and ready. This makes no model call.

```bash
sol-pi-run doctor
```

Every line must read `[ok]`. If `sol-pi-run` is not on PATH, stop and point the
user to the upstream install steps in `examples/sol-pi-skill/README.md`: clone
SoL-Pi, link `bin/sol-pi-run` and `bin/sol-pi-context` into `~/.local/bin`, then
run `sol-pi-run setup`. If `doctor` reports a failure, run `sol-pi-run setup`
and `doctor` again. Do not edit `~/.sol-pi/agent/sol-pi.json` by hand.

## Hand off the current prompt

Use this path when the user's message starts with `/sol-pi`, `$sol-pi`, or a
request to hand the prompt to SoL-Pi. SoL-Pi, not you, should do the work and
continue from this conversation.

The upstream prompt hooks normally intercept `/sol-pi` (Claude Code) and
`$sol-pi` (Codex) before the model runs. If you are reading this for such a
message, the hook did not run. Do the hand-off below and mention at the end
that the hook path is not active.

1. Leading `-m <provider/model>` and `-t <effort>` are SoL-Pi options. The rest
   is the task. If no task text remains, ask for one and stop.
2. Write the task text exactly as the user wrote it to a temp file, such as
   `/tmp/sol-pi-task-<session-id>.md`. Do not reword it or add background.
   SoL-Pi receives this conversation as prefix context.
3. Start SoL-Pi from the current directory with this session as context, then
   wait in rounds. Repeat `wait` while it exits with code 3.

   ```bash
   sol-pi-run start --with-session [-m MODEL] [-t EFFORT] --task-file /tmp/sol-pi-task-<session-id>.md
   sol-pi-run wait <run-id> --timeout 540
   ```

   `--with-session` finds the calling session from `CLAUDE_CODE_SESSION_ID` in
   Claude Code or from `CODEX_THREAD_ID` and `CODEX_HOME` in Codex. Pass
   `--session-from <session-id>` if detection fails. It exports the
   conversation since the latest compaction and drops the hand-off request.
   `sol-pi-context` prints the same export.
4. Do not work on the task or edit its files while SoL-Pi runs.
5. When it finishes, check `git status` and `git diff` (skip outside a Git
   repository). Report SoL-Pi's answer, the changed files, the first `[sol-pi]`
   summary line and the run id.
6. If the result looks wrong, report what you saw. Do not fix it yourself or
   start another run with a reworded task unless the user asks. If SoL-Pi seems
   to have had the wrong context, run `sol-pi-context | head -20` and report
   which session it exported.

## Delegate a subtask

For a self-contained subtask with no conversation context, run from the
directory the task should operate in, or pass `--cwd`.

```bash
sol-pi-run run -- "fix the failing test in tests/test_io.py and run the suite"
sol-pi-run run -m provider/model -t medium --cwd /path/to/repo -- "task"
sol-pi-run run --task-file /tmp/task.md
```

The output starts with a summary: status, model, seconds, turns, cost, token
counts, how often each SoL-Pi mechanism fired, run id and session file. The
model's final reply follows. Add `--json` for machine-readable output. The exit
code is 0 only when the run finished normally.

Run tasks longer than a few minutes in the background:

```bash
id=$(sol-pi-run start -- "task")
sol-pi-run status "$id"
sol-pi-run wait "$id" --timeout 540
sol-pi-run result "$id"
sol-pi-run list
```

The default run timeout is 7200 s, and `--timeout 0` disables it. Each run
keeps `~/.sol-pi/runs/<id>/` with `prompt.md`, `events.jsonl`, `stderr.log`,
`result.json` and the Pi session.

## Safety

SoL-Pi edits files in place and runs shell commands with the user's
permissions. It has no sandbox. Delegate only work the user would let you do in
that directory, and review `git diff` afterwards. Never start `sol-pi-run tui`
from inside an agent session. It is for the user to drive directly.

## Network and sandboxes

SoL-Pi calls the model provider over the network. In the Codex
`workspace-write` sandbox the network is off by default. Request escalated
permissions for `sol-pi-run run`, `start` and `doctor --live`, or have the user
start Codex with `-c sandbox_workspace_write.network_access=true`. A provider
error such as `fetch failed` or `ENOTFOUND` usually means the network was
blocked. If `~/.sol-pi` is not writable, `sol-pi-run` keeps its config and run
records in `$TMPDIR/sol-pi-<uid>/`, and `doctor` prints which directory it uses.

## Models

`-m` takes a `provider/model` listed by `sol-pi-run models`. Without `-m`,
SoL-Pi uses `SOL_PI_MODEL`, then the default model in the user's Pi settings.
`-t` sets effort: off, minimal, low, medium, high (default), xhigh or max. The
reducer uses SoL-Pi's built-in route unless setup ran with
`--reducer provider/model`.

If a model lacks credentials, the user sets it up in their own Pi (`pi`, then
`/login`, or `~/.pi/agent/models.json`). Do not write credentials yourself.

## Reporting

Tell the user what SoL-Pi changed, whether it verified the result, and the cost
line from the summary. Cost covers the main model and the reducer at the prices
in the user's Pi model definitions. A model without prices counts as $0. Rerun
after a transient provider 429 or 503 error.
