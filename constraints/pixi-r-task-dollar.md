# Constraint: no `$` in R commands inside pixi tasks

**Type:** constraint (deterministic, scriptable pass/fail)
**Check:** `pixi-r-task-dollar.py`
**Applies to:** `pixi.toml` task definitions that invoke R

## Rule

pixi runs task commands through deno_task_shell, which expands `$var` even
inside single-quoted strings (verified: `pixi run "echo '$path.sep'"` prints
`.sep`). An R one-liner embedded in a `pixi.toml` task therefore must not
contain `$` at all. The expansion is silent: `.Platform$path.sep` becomes
`.Platform.sep`, which mangles the R expression without an obvious error.

Write the R accessor forms that avoid `$`:

```toml
# wrong: $path expands to nothing under deno_task_shell
libpath = "R -e 'cat(.libPaths()[1], .Platform$path.sep)'"

# right
libpath = "R -e 'cat(.libPaths()[1], .Platform[[\"path.sep\"]])'"
```

Longer R code belongs in a script file run via `Rscript path/to/script.R`,
where the shell never sees the `$`.

## Why this is a constraint, not a convention

Lines in a `pixi.toml` task section that both invoke R and contain `$` can be
found mechanically, so the rule is enforced by script rather than judgment.

## Limits

The check is line-based within `[tasks]`-family sections; a multi-line TOML
string could evade it. That gap has not occurred in practice.

## Escape hatch

Append `# waterology: allow-task-dollar` to a task line that intentionally
uses shell expansion (a genuine `$VAR` meant for deno_task_shell, not R). The
check skips flagged lines.

---
*Constraint pattern adapted from edwinhu/workflows (MIT, per README).*
