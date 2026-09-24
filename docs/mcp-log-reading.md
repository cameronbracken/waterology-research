# Bounded MCP log reads

`read_run_logs` and `read_session_logs` now return one page object inside the
usual `{ok, result}` envelope. This replaces their previous full-log response
shapes. The CLI log commands and existing full-log Python services retain their
behavior. Full files remain on disk.

| Argument | Default | Meaning |
| --- | --- | --- |
| `stream` | Run: `stdout`; session: `events` | Run: `stdout` or `stderr`; session: `events` or `stderr` |
| `attempt` | Latest session attempt | Select an older session attempt explicitly; session tool only |
| `offset` | `0` | Starting source byte offset |
| `max_bytes` | `8192` | Source bytes in a page, between 4 and 65,536 |
| `query` | None | Case-sensitive literal UTF-8 text, 1 to 256 bytes; no regex |
| `snapshot` | None | Optional change token returned by a prior page |

Example tool arguments:

```json
{"session_id":"session-0123456789abcdef","attempt":1,"stream":"events","query":"ERROR","max_bytes":8192}
```

A search scans at most 1 MiB from the requested offset. On a match, the page
begins at that match and includes subsequent text. It does not collect every
matching line. Without a match, the page is empty and `match_found` is false.
Continue with `next_offset` even when the page is empty. Only a null
`next_offset` means the end of the current file was reached. Search overlap
preserves matches crossing scan boundaries.

The response reports `content`, `path`, the stream and run/session identity,
`offset`, `end_offset`, `next_offset`, `total_bytes`, `returned_bytes`,
`content_utf8_bytes`, `truncated`, `snapshot`, `match_found`, and `scanned_bytes`.
Session responses also identify the selected attempt. `truncated` means the
response is not the complete file. The content can begin or end within a line,
so an events page is text, not a promise of independently parseable JSONL.

Follow the returned byte offset instead of computing one from text length.
Valid UTF-8 characters are kept intact at page ends. Invalid input bytes are
replaced for display, so encoded display text can be larger than the source
byte budget. JSON escaping and response metadata also add transport bytes.

Pass the returned snapshot on subsequent calls to detect changed files. It is
a token derived from file identity, size, and timestamps, not a cryptographic
content checksum. A mismatch or change during reading returns an input error.
For an actively growing log, restart from the desired offset without the old
token to obtain a new snapshot. This is not an immutable live-log view.

Always select stderr separately when investigating failures. An INFO tail does
not establish that earlier attempts or the beginning of the log were clean.
Use `inspect_session` to inspect the available attempts. Reads remain restricted
to the selected run/session's recorded log paths and reject symlinked logs.

These tools need no search database, index lifecycle, additional executor, or
context-mode integration. To use changed tool schemas, the MCP process must run
this code and the client must reconnect to refresh its tool list.
