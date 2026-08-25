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

## Safety checks

- Prefer the runtime's native worktree support when available.
- For a manual worktree, use the repository's declared location or its existing
  `.worktrees/` directory and verify that the parent is ignored.
- Do not overwrite an existing branch or directory.
- Run project setup and baseline checks in the isolated checkout.
- Keep unrelated user changes intact. Integrate or remove a worktree only with
  the authority appropriate to that action.
