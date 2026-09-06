# Git Worktree Cutoff

<!-- Adapted from Superpowers 6.3.0 using-git-worktrees (obra/superpowers, MIT), with Waterology-specific isolation rules. See ATTRIBUTION.md. -->

Before editing, inspect the branch, status, worktree inventory, Git directory,
and common Git directory. If already in a linked worktree, use it. Do not create
a nested worktree.

## Required isolation

Use a worktree when any condition is true:

- Another session may write to the same repository.
- The task changes executable code, tests, dependencies, build files, CI,
  schemas, plugin manifests, agent definitions, skills, hooks, or generated
  assets.
- The task spans several related files or needs an isolated test cycle.
- The current checkout contains unrelated changes.

Skills and agent instructions count as behavior. Their Markdown file type does
not make them documentation-only edits.

## Optional isolation

Working in place is optional only when every condition is true:

- This is the only writing session.
- The change affects documentation, comments, formatting, or one non-generated
  file.
- The change does not alter runtime or agent behavior.
- The checkout is clean.

Read-only sessions may share a checkout. When parallel writing is planned,
reserve `main` as the integration lane and give each writing session a named
branch and worktree.

The machine-checked examples in
[worktree-cases.yaml](worktree-cases.yaml) cover the required cutoff cases.

## Location and manager

Create development worktrees under the repository root at
`.worktrees/<sanitized-branch>`. Verify that `.worktrees/` is ignored before
creating the first one. Reuse an existing linked worktree even when it predates
this convention. Do not relocate or remove it without the required authority.

Use Worktrunk when `command -v wt` succeeds. Its configured default may place a
worktree beside the repository, so enforce the project location when creating
one:

```bash
wt --config-set 'worktree-path="{{ repo_path }}/.worktrees/{{ branch | sanitize }}"' \
  switch --create <branch> --base=@ --no-cd
```

Use `wt list` and `wt remove` for routine worktree management when available.
Inspect the state and command options before any merge or removal because those
operations may also change branches or commits. If Worktrunk is unavailable,
use Git worktree fallback commands with an explicit `.worktrees/<name>` path.

Waterology experiment worktrees under `.waterology/worktrees/` belong to the
experiment runtime. Do not use that directory for agent development worktrees.

## Safety checks

- Do not overwrite an existing branch or directory.
- Run project setup and baseline checks in the isolated checkout.
- Keep unrelated user changes intact. Integrate or remove a worktree only with
  the authority appropriate to that action.
