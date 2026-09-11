# Public repository preparation

The publication repository contains shared workflows with optional private user
configuration. Read [Personal configuration](../local-configuration.md) for
identity, local guidance, writing examples, compute profiles, and dashboard setup.

## Verification

The implementation was integrated into the development repository in signed
commit `6f1fa9b`. The sanitized source tree at `83569e5` matches that implementation
byte for byte. The publication clone was verified using the existing locked
Pixi environment with its own `src` directory on the import path.

- Full suite against the sanitized clone: 611 passed, 2 warnings. Warnings were
  the existing Starlette deprecation and a fixture's missing Zotero API key.
- Ruff: passed. Generated runtime assets: current. Waterology constraints: 8/8.
- Focused tests cover configuration precedence, empty defaults, local file
  refreshes, identity/corpus selection, profile preservation, sanitized errors,
  dashboard credential handling, and copy/link installs for all three runtimes.
- An independent review identified an incomplete plugin-only fallback. The
  corrected shared fallback was reviewed again with no remaining findings.
- Wheel: 226 archive entries. Source archive: 320 entries. Both passed the
  selected personal-content and cache-file scans.

## History boundary

The scan at `83569e5` covered 936 text blobs across all 86 reachable commits.
The repository contained only `refs/heads/main`, no tags and no configured
remote. Git's unreachable-object check reported no leftover objects.

A custom scan found no private-key patterns, known provider-token patterns,
credential-bearing URLs, homelab addresses, selected personal-context markers,
or personal email strings in file contents. The remaining literal credential
matches were test fixtures. This is a bounded pattern/content inspection, not a
guarantee that every possible secret format has been detected.

Personal historical file versions were removed. Their current generic,
configurable replacements were restored in signed commit `83569e5`. Other file
history was retained with personal contact strings generalized. Commit author
and committer names/emails remain intact. Rewriting changed historical commit
IDs and removed their invalid signatures. Public authorship and source credits
remain in LICENSE and ATTRIBUTION; they are not user defaults.

Older commits no longer contain the purged files and may not be independently
buildable. This is the deliberate cost of retaining the remaining development
history while excluding personal content. This verification record is a later,
documentation-only commit.

The original development repository retains its private history and unrelated
worktrees. It is not the publication repository. No remote publication was
performed during this preparation.
