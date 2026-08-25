import subprocess
from pathlib import Path

from waterology.core.errors import WaterologyError


class GitCommandError(WaterologyError):
    code = "git_command_failed"


def git_output(repository: Path, *arguments: str) -> str:
    completed = _run_git(repository, *arguments)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "Git command failed"
        raise GitCommandError(
            message,
            details={"arguments": list(arguments), "returncode": completed.returncode},
        )
    return completed.stdout.strip()


def resolve_commit(repository: Path, reference: str) -> str:
    return git_output(repository, "rev-parse", "--verify", f"{reference}^{{commit}}")


def branch_exists(repository: Path, branch: str) -> bool:
    completed = _run_git(repository, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}")
    if completed.returncode in {0, 1}:
        return completed.returncode == 0
    message = completed.stderr.strip() or "Unable to inspect Git branch"
    raise GitCommandError(message, details={"branch": branch})


def add_worktree(repository: Path, path: Path, branch: str, commit: str) -> None:
    git_output(repository, "worktree", "add", "-b", branch, str(path), commit)


def commit_contains(repository: Path, commit: str, path: str) -> bool:
    completed = _run_git(repository, "cat-file", "-e", f"{commit}:{path}")
    if completed.returncode in {0, 128}:
        return completed.returncode == 0
    message = completed.stderr.strip() or "Unable to inspect Git commit"
    raise GitCommandError(message, details={"commit": commit, "path": path})


def current_commit(repository: Path) -> str:
    return resolve_commit(repository, "HEAD")


def current_branch(repository: Path) -> str | None:
    completed = _run_git(repository, "symbolic-ref", "--quiet", "--short", "HEAD")
    if completed.returncode == 0:
        return completed.stdout.strip()
    if completed.returncode == 1:
        return None
    message = completed.stderr.strip() or "Unable to inspect the current Git branch"
    raise GitCommandError(message)


def is_ancestor(repository: Path, ancestor: str, descendant: str) -> bool:
    completed = _run_git(repository, "merge-base", "--is-ancestor", ancestor, descendant)
    if completed.returncode in {0, 1}:
        return completed.returncode == 0
    message = completed.stderr.strip() or "Unable to inspect Git commit ancestry"
    raise GitCommandError(
        message,
        details={"ancestor": ancestor, "descendant": descendant},
    )


def is_clean(repository: Path) -> bool:
    return git_output(repository, "status", "--porcelain=v1", "--untracked-files=all") == ""


def _run_git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
