# Constraint: material TeX overfull boxes are resolved

**Check:** `overfull-boxes.py`
**Applies to:** TeX `.log` files

TeX box messages do not contain the word `Warning`. Parse their own message
format. Ignore overflow below 1 pt, report 1 through 10 pt as minor, and report
more than 10 pt as major. Any reported overflow fails the constraint.

Detection and severity are adapted from `flonat/claude-research`,
`skills/shared/overfull-boxes.md` at commit
`e7007d0b1e465ef96de7338599ca04079e83a972` (MIT, Copyright 2026 Florian
Burnat).
