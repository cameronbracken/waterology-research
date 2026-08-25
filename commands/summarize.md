---
description: Summarize a research source (paper, report, README, PDF) using a windowed read that keeps the source on disk instead of injecting it raw into context.
argument-hint: <source> [--window-size <chars>] [--overlap <chars>] [--tier1-threshold <chars>] [--tier2-threshold <chars>]
---

<!-- Adapted from Feynman (companion-inc/feynman, MIT). See ATTRIBUTION.md. -->

Summarize the following research source: $ARGUMENTS

Derive a short slug from the source filename or URL domain (lowercase, hyphens, no filler words, at most 5 words — e.g. `attention-is-all-you-need`). Use it for all files in this run.

## Why a windowed read

Injecting a full document into context degrades earlier content as the window fills (context rot) above roughly 15k tokens. This workflow keeps the document on disk and reads only bounded windows, so context pressure is proportional to the window size, not the document size. For short inputs (Tier 1), direct reading is safe and windowing would only add friction.

## Runtime knobs

Support inline flags and environment variables so behavior can be tuned per run or globally. Inline flags override environment variables.

- `--window-size <chars>` or `WATEROLOGY_SUMMARIZE_WINDOW_CHARS` (default: `6000`)
- `--overlap <chars>` or `WATEROLOGY_SUMMARIZE_OVERLAP_CHARS` (default: `500`)
- `--tier1-threshold <chars>` or `WATEROLOGY_SUMMARIZE_TIER1_THRESHOLD` (default: `8000`)
- `--tier2-threshold <chars>` or `WATEROLOGY_SUMMARIZE_TIER2_THRESHOLD` (default: `60000`)

Validate `window-size > overlap` and `tier1-threshold < tier2-threshold`; if invalid, stop with a clear configuration error. Log resolved values once: `[summarize] config window=<w> overlap=<o> tier1=<t1> tier2=<t2>`.

## Step 1 — Fetch, validate, measure

Run all guards before any tier logic. A failure here is cheap; a failure mid-Tier-3 is not.

- **GitHub repo URL** (`https://github.com/owner/repo`, exactly 4 slashes): fetch the raw README instead — try `https://raw.githubusercontent.com/{owner}/{repo}/main/README.md`, then `/master/README.md`.
- **Remote URL**: fetch to disk with `curl -sL -o docs/.notes/<slug>-raw.txt <url>`. Do NOT use `WebFetch` here — its return value enters context directly, defeating the on-disk principle.
- **Local file or PDF**: copy or extract to `docs/.notes/<slug>-raw.txt`. For PDFs, extract text via `pdftotext` first.
- **Empty or failed fetch**: if the file is < 50 bytes, stop and surface the error — do not proceed to tier selection.
- **Binary content**: if the file is > 1 KB but has < 100 readable text characters, stop and report that the content appears binary or unextracted.
- **Existing output**: if `docs/<slug>-summary.md` already exists, ask whether to overwrite or use a different slug.

Measure decoded text characters (not bytes). Log: `[summarize] source=<source> slug=<slug> chars=<count>`.

## Step 2 — Choose tier

| Chars | Tier | Strategy |
|---|---|---|
| < tier1-threshold | 1 | Direct read — full content enters context (safe for short inputs) |
| tier1-threshold – tier2-threshold | 2 | Windowed bash extraction, progressive notes to disk |
| > tier2-threshold | 3 | Bash chunking + parallel `researcher` subagents |

Log: `[summarize] tier=<N> chars=<count>`.

## Tier 1 — Direct read

Read `docs/.notes/<slug>-raw.txt` in full, summarize using the output format, write to `docs/<slug>-summary.md`.

## Tier 2 — Windowed read

The document stays on disk. Extract `<window-size>`-char windows with bash (the Read tool uses line offsets, not char offsets, so bash is required for exact char-boundary windows):

```python
with open("docs/.notes/<slug>-raw.txt", encoding="utf-8") as f:
    f.seek(n * WINDOW_SIZE)
    window = f.read(WINDOW_SIZE)
```

For each window: extract key claims and evidence, append them to `docs/.notes/<slug>-notes.md` before reading the next window (the checkpoint — processed windows survive an interruption), and log `[summarize] window <N>/<total> done`. Synthesize the notes into `docs/<slug>-summary.md`.

## Tier 3 — Parallel chunks

Each chunk gets a fresh `researcher` subagent context, so no subagent sees more than `<window-size>` chars. Overlap matters because multi-sentence arguments span chunk boundaries.

Chunk the document with bash (zero-pad indices so files sort correctly):

```python
import os
os.makedirs("docs/.notes", exist_ok=True)
with open("docs/.notes/<slug>-raw.txt", encoding="utf-8") as f:
    text = f.read()
chunk_size, overlap = WINDOW_SIZE, OVERLAP
chunks, i = [], 0
while i < len(text):
    chunks.append(text[i : i + chunk_size])
    i += chunk_size - overlap
for n, chunk in enumerate(chunks):
    with open(f"docs/.notes/<slug>-chunk-{n:03d}.txt", "w", encoding="utf-8") as f:
        f.write(chunk)
print(f"[summarize] chunks={len(chunks)} chunk_size={chunk_size} overlap={overlap}")
```

Briefly note "Source is ~<chars> chars -> <N> chunks -> <N> researcher subagents. Continuing." then continue automatically. Launch one `researcher` per chunk via the `Task` tool, each told to read ONLY its chunk file, extract (1) key claims, (2) methodology, (3) cited evidence, mark any boundary-spanning claim `BOUNDARY PARTIAL`, and write to `docs/.notes/<slug>-summary-chunk-NNN.md`. Do not have them search the web — this is single-source summarization.

After all return, verify every expected chunk-summary file exists; note missing indices for the Coverage gaps section. When synthesizing, deduplicate claims (keep the most complete formulation), resolve boundary conflicts in favor of the version with more context, and drop `BOUNDARY PARTIAL` markers where a complete version exists in a neighbor. Write to `docs/<slug>-summary.md`.

## Output format

All tiers produce `docs/<slug>-summary.md`:

```markdown
# Summary: [document title or source filename]

**Source:** [URL or file path]
**Date:** [YYYY-MM-DD]
**Tier:** [1 / 2 (N windows) / 3 (N chunks)]

## Key Claims
[3-7 most important assertions, each a bullet]

## Field Context
[Where the source positions itself and what remains source-inferred rather than externally checked. Use /lit for a corpus-level view.]

## Technical Hinges
[2-4 contributions or decisions the source turns on, ranked by originality; name the contrast with prior work when the source gives evidence.]

## Methodology From Primitives
[Approach, data, evidence type, evaluation, baselines, failure modes from first principles. Omit only when there is no methodology section.]

## Limitations
[What the source explicitly flags as weak, incomplete, or out of scope]

## Follow-up Questions
[3 questions grounded in the source that would change the next research decision]

## Verdict
[One paragraph: what this document establishes, its credibility, who should read it]

## Sources
1. [Title or filename] — [URL or file path]

## Coverage gaps *(Tier 3 only — omit if all chunks succeeded)*
[Missing chunk indices and approximate byte ranges]
```

Before stopping, verify on disk that `docs/<slug>-summary.md` exists. Sources contains only the single source confirmed reachable in Step 1 — no verifier pass is needed because no URLs were constructed from memory.
