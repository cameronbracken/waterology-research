# MCP log pagination validation

Validated in the existing `feature/remaining-todos` worktree on macOS.

- `pixi run pytest -q`: 699 passed, 2 warnings, 62.13 seconds.
- `pixi run ruff check .`: passed.
- `pixi run waterology render --check`: generated assets current.
- Constraints on the eight changed/new Python paths: 8/8 passed.
- `git diff --check`: passed.

Warnings were the existing Starlette/AnyIO deprecation and a Zotero fixture
without an API key. No live Zotero writes were performed.

Regression coverage includes byte pagination with complete UTF-8 characters,
literal queries across the scan boundary, one-character search continuation,
empty files, missing matches, invalid byte replacement, file-change tokens,
invalid size/range arguments, symlink rejection, selected session streams and
attempts, archive streams, and MCP request/response validation.

The MCP client tests run an in-process server. They establish tool dispatch and
response behavior, not installation into a running external client. The existing
full-log service and CLI paths are unchanged. The new tool response is a page
object and clients must refresh tool schemas after running the updated server.

No index, runtime hook, or upstream plugin dependency was introduced. No native
Windows/Linux execution or external MCP-client refresh was attempted. Original
logs are retained; the snapshot token detects filesystem changes and is not a
content integrity checksum. See [the response contract](../mcp-log-reading.md).
