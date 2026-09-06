# Constraint: Monte Carlo summaries include MCSE

**Check:** `mc-has-mcse.py`
**Applies to:** CSV or Parquet result tables whose filename contains `simulation`, `monte-carlo`, or `mc-results`

Tables that report bias, coverage, power, or rejection rates must include an
MCSE column for each reported metric family. Column matching normalizes common
separators and accepts forms such as `mean_bias`, `coverage_rate`,
`rejection.rate`, and `size`. Raw replication tables and files without a
recognized summary metric are ignored.

This check is adapted from the simulation discipline in
`pedrohcgs/claude-code-my-workflow` at commit
`9d371f0bf8a8bc99569feca3210ef5133af28d33` (MIT, Copyright 2026 Pedro H. C.
Sant'Anna).

The scanner reads CSV headers or Parquet schema metadata without loading table
rows. Install `waterology-research[constraints]` in the checker environment for
Parquet support. Missing Arrow support, unreadable files and invalid Parquet
produce a failed check.
