# Verification and Review

<!-- Adapted from Superpowers 6.3.0 verification-before-completion and requesting-code-review (obra/superpowers, MIT). See ATTRIBUTION.md. -->

## Completion claims

Before saying that work is complete, fixed, clean, or passing:

1. Identify the command or inspection that proves the claim.
2. Run it after the final change.
3. Read the complete output and exit status.
4. Report the observed result, including failures or skipped checks.

A previous run, partial suite, or clean diff does not prove a different claim.
Match each statement to fresh evidence.

## Review cutoff

Use an independent reviewer when any of these applies:

- The user requests a review.
- The change is broad, risky, difficult to reverse, or affects a release.
- The deliverable supports a publication, public result, or consequential
  decision.
- A fresh perspective would materially reduce uncertainty after a complex fix.

Routine patches do not require a separate review cycle. Delegate only when an
agent is available and authorized. Give a reviewer the requirements, base and
head revisions, changed files, and verification evidence. Resolve important
findings before integration and explain any finding you reject.
