# Install, upgrade, uninstall, and recover

These commands manage files installed by `waterology install`. They support
Claude Code, Codex, OpenCode, and Pi, in project and user scopes. Native plugin
marketplace registrations and the Python package have separate uninstall
commands. The CLI reports that boundary after uninstall.

## Preview and remove

```bash
waterology uninstall codex --target ./example --dry-run --json
waterology uninstall codex --target ./example --json
waterology uninstall all --scope user --dry-run
```

The installer records ownership in `.waterology-install.json` manifests and,
where needed, runtime-specific manifests at the project root. Uninstall reads
those records and detects copy or link mode automatically. It removes only
recorded files, directories, and links whose fingerprints still match. An
unrecorded neighboring file stays in place. Removing a link leaves its target
untouched. Repeating uninstall is a no-op.

If a managed asset was edited, uninstall fails before removing other assets
for that runtime. Save the edit elsewhere and restore the managed copy before
retrying, or remove the installation manually. There is no uninstall force
option. An added empty directory or nested symlink also counts as a change.
Older manifests did not fingerprint every nested link or empty directory.
An older installation containing those entries can therefore require manual
inspection even if it was not edited. This conservative mismatch prevents
uninstall from treating unrecorded additions as safe to delete.

Malformed ownership records and paths outside managed asset families are
rejected. Empty runtime directories may remain.

`all` preflights every runtime before changing any of them. Each runtime has
its own transaction. If a later runtime fails during application, earlier
completed runtimes remain completed. Rerun after resolving the reported issue.

## Upgrade

Install the new Waterology package, then repeat the original install command:

```bash
waterology install codex --target ./example --json
waterology install pi --scope user --mode link --json
```

Existing manifests supply the ownership and prior version records. Installation
stages the new assets, removes unchanged retired assets, replaces changed
managed assets, and updates manifests in one recoverable transaction. The same
removal and rollback machinery supports uninstall. It avoids a separate,
unprotected interval between uninstalling and reinstalling.

Modified managed files block the upgrade. `--force` retains its existing role
for replacing modified skills and agents. It cannot replace modified runtime
configuration or delete a modified retired asset. Unowned configuration is
never overwritten. To change copy/link mode, uninstall first, then install in
the requested mode.

Schema 1 manifests are supported. Tests cover a synthetic prior-version
manifest and assets removed from the new catalog. They do not establish that
every historical package version or native marketplace installation upgrades
through this CLI.

## Interrupted operations

Caught exceptions trigger rollback. A transaction journal and sibling backups
allow recovery after the process exits unexpectedly:

```bash
waterology install-recover codex --target ./example --dry-run --json
waterology install-recover codex --target ./example --json
```

Select the same runtime and scope as the interrupted command. Recovery refuses
a live process and verifies destination, backup, and staged data before making
changes. Pending transactions restore the old installation. Committed
transactions finish backup cleanup. A process killed before journal creation
can leave a PID lock; recovery clears it only after the process has exited.

Recovery uses an OS advisory lock. Its coordination file remains on disk so
concurrent callers always lock the same file. The lock itself is released if
the recovery process dies. Windows uses byte locking; Unix uses `flock`.

Limits requiring manual inspection:

- A kill during staging can leave `.waterology-stage-*` sibling files. With no
  journal, recovery clears the stale PID lock but does not guess which orphan
  files can be deleted.
- A kill during recursive backup cleanup, or an external edit to recovery
  material, can leave a partial backup. Recovery refuses ambiguous data. Keep
  the journal and backups until their contents have been inspected.
- Concurrent external writers are not coordinated by Waterology's lock.
  Recovery rechecks paths, but this is not a filesystem security boundary.
- Subprocess interruption tests qualify process death on the test platform.
  Sudden power loss and filesystem corruption are not qualified.
