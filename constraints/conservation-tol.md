# Constraint: declared conservation checks close within tolerance

**Check:** `conservation-tol.py`
**Applies to:** `conservation-check.json`, `.yaml`, and `.yml` evidence files

A conservation evidence file declares `metric`, signed `error`, and positive
`tolerance`. The check passes when `abs(error) <= tolerance`. It fails for a
nonfinite value, a nonpositive tolerance, malformed evidence, or an error above
tolerance. Projects opt in by producing a named evidence file from their
domain calculation.

The evidence must use compatible units for error and tolerance. This generic
constraint checks the declared comparison. The project remains responsible for
computing mass, energy, volume, or other conserved quantities correctly.
