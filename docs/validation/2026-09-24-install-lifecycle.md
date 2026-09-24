# Installation lifecycle validation

Date: 2026-09-24. Base: `05c2637`. Branch: `feature/remaining-todos`.
Validation ran in the isolated worktree on macOS with its Pixi environment.

| Check | Observed result |
| --- | --- |
| `pixi run pytest -q` after final code changes | 685 passed, 2 warnings, 59.45 seconds |
| Lifecycle regression file in the full suite | 37 tests |
| `pixi run ruff check .` | Pass |
| `pixi run waterology render --check` | Generated assets current |
| Constraints targeting the three changed Python files | 8/8 passed |
| `git diff --check` | Pass |
| Help for `uninstall` and `install-recover` | Exit 0 |

Warnings: Starlette reports an AnyIO deprecation; a Zotero fixture reports that
no API key is available and leaves references queued. No authenticated Zotero
write was attempted.

Tests cover four runtime layouts, two scopes, and two install modes in temporary
filesystems. They exercise modified and unowned files, retired assets, legacy
version metadata, runtime configuration protection, rollback, real subprocess
termination during pending transactions and committed cleanup, stale PID locks,
and recovery lock release after process death.

## Independent review

A separate reviewer examined destructive operations and supplied temporary
reproductions. Findings and final dispositions:

| Finding | Fix and evidence |
| --- | --- |
| Added dangling links and empty directories were invisible to ownership hashes | Fingerprint directory entries; preservation regressions pass |
| Recovery accepted edits after its initial validation | Serialize recovery and recheck destination, backup, stage, and parent paths before mutation; reviewer reproduction preserves the edit |
| Process death before journal creation left an unrecoverable PID lock | Validate exited process and clear the matching stale lock; regression passes |
| A file-based recovery guard survived process death | Use OS advisory locking; subprocess regression passes |
| Unix PID probing could terminate a Windows process | Use Windows synchronization handles; routing test forbids `os.kill` on Windows |
| Uninstall resnapshotted assets after ownership validation | Carry the verified snapshot through commit; injected edit is preserved |

The reviewer reran the last two regressions: 2 passed. No high-severity finding
remained open in that bounded review. The reviewer did not independently rerun
the complete suite.

The Windows probe follows the documented behavior of
[OpenProcess](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess)
and [WaitForSingleObject](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject).
[Python's Windows signal behavior](https://docs.python.org/3.13/library/os.html#os.kill)
explains why the Unix probe cannot be reused there.

## Qualification limits

Native Windows and Linux execution, archived historical installer versions,
native marketplace lifecycle operations, power-loss recovery, and adversarial
filesystem writers remain unqualified. The Windows API routing test uses a
mock and does not establish native API execution. Interrupted staging or
partial recursive backup cleanup can require manual inspection. See the
[operating guide](../install-lifecycle.md).

The plugin evaluation inspected pinned upstream source without installation or
benchmarking. It proposes future bounded retrieval and resume-record work, with
no imported implementation or skill changes. Existing user runtime installations
were not changed. The implementation remains in the isolated worktree.
