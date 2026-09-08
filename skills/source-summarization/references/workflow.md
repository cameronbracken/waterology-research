# Source Summarization Workflow

Keep long source text on disk and read bounded windows. Derive a lowercase,
hyphenated slug from the source name or URL domain with at most five words.

## Configuration

Inline flags override environment variables:

- `--window-size` or `WATEROLOGY_SUMMARIZE_WINDOW_CHARS`, default `6000`.
- `--overlap` or `WATEROLOGY_SUMMARIZE_OVERLAP_CHARS`, default `500`.
- `--tier1-threshold` or `WATEROLOGY_SUMMARIZE_TIER1_THRESHOLD`, default
  `8000`.
- `--tier2-threshold` or `WATEROLOGY_SUMMARIZE_TIER2_THRESHOLD`, default
  `60000`.

Require `window-size > overlap` and
`tier1-threshold < tier2-threshold`. Stop with a clear configuration error when
either condition fails. Log the resolved values once.

## Fetch and validate

Create `docs/.notes/`. Resolve the source to
`docs/.notes/<slug>-raw.txt` before selecting a tier:

- For an exact GitHub repository URL, try its raw `README.md` on `main`, then
  `master`.
- Fetch another remote URL directly to disk so the full response does not enter
  model context.
- Copy a local text file. Extract a PDF with an available PDF text tool.

Stop if fetching or extraction fails, the file is under 50 bytes, or a file
over 1 KB contains fewer than 100 readable text characters. Measure decoded
text characters rather than bytes. If `docs/<slug>-summary.md` already exists,
ask whether to replace it or choose another slug.

## Select the bounded read tier

- _Tier 1_: below `tier1-threshold`, read the full text directly.
- _Tier 2_: from `tier1-threshold` through `tier2-threshold`, read sequential
  character windows and checkpoint notes after each window.
- _Tier 3_: above `tier2-threshold`, split into overlapping chunks and delegate
  each chunk to a separate `researcher` context.

Log the selected tier and character count.

### Tier 1

Read the raw file in full and write `docs/<slug>-summary.md`.

### Tier 2

Use a local helper process to decode the raw file into a string. For window
`n`, slice that decoded string from `n * window-size` through the next
`window-size` characters and write only that window to a temporary file. Read
the temporary file into model context. Do not seek by byte offset because a
byte position can split a UTF-8 character. Extract claims and evidence, append them to
`docs/.notes/<slug>-notes.md`, then continue. Log each completed window. Build
the final summary from the checkpoint file.

### Tier 3

Use the same decoded string approach to split the text into zero-padded chunk
files under `docs/.notes/`. Advance by `window-size - overlap` decoded
characters so adjacent chunks share context. Report the character count and
planned chunk count before delegating.

Give each `researcher` exactly one chunk, prohibit external search, and request
claims, methodology, cited evidence, and `BOUNDARY PARTIAL` labels for
incomplete boundary claims. Use the runtime's available delegation mechanism
and write each result to
`docs/.notes/<slug>-summary-chunk-NNN.md`.

Verify all expected chunk summaries. Record missing indices. During synthesis,
deduplicate claims, prefer the version with more context, and remove a boundary
label when an adjacent chunk supplies the complete claim.

## Summary contract

Write `docs/<slug>-summary.md` with:

- Source, date, tier, and window or chunk count.
- Three to seven central claims.
- Field context and technical hinges.
- Methodology, data, evidence, evaluation, and failure modes when present.
- Source stated limitations and grounded follow-up questions.
- A short verdict describing what the source establishes and who should read
  it.
- `Coverage gaps` for missing Tier 3 chunks, omitted when coverage is complete.
- `Sources` containing only the single confirmed source from the fetch step.

Do not add remembered citations or perform a verifier pass for this single
source summary. Confirm the final file exists before reporting completion.
