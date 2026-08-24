# Task 2 report: asset discovery in checkouts and wheels

## Implementation

Added `AssetCatalog` and `AssetNotFoundError` in `waterology.runtime.assets`.
The catalog discovers an explicit source root, the repository checkout, or the
packaged `waterology_assets` resources. It resolves safe relative paths,
rejects parent traversal and missing assets, and enumerates skill directories.

Added the complete Hatch wheel force-include map required by the task. Hatch
requires every force-included source to exist during the editable package build,
so minimal `.gitkeep` placeholders were added for asset directories created by
later tasks (`agent-definitions`, `.codex-plugin`, `.codex/agents`, and
`.opencode/agents`).

## Files changed

- `src/waterology/runtime/assets.py`
- `tests/runtime/test_assets.py`
- `pyproject.toml`
- `agent-definitions/.gitkeep`
- `.codex-plugin/.gitkeep`
- `.codex/agents/.gitkeep`
- `.opencode/agents/.gitkeep`

The Pixi-generated `pixi.lock` was left untracked and is not part of this task
commit.

## TDD evidence

### RED

The required tests were written before the production module. The required
focused command initially failed during collection with the expected missing
module error:

```text
$ pixi run pytest tests/runtime/test_assets.py -v
E   ModuleNotFoundError: No module named 'waterology.runtime.assets'
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

### GREEN

After implementing the catalog and adding the placeholders needed for Hatch's
force-include sources, the required focused command passed:

```text
$ pixi run pytest tests/runtime/test_assets.py -v
2 passed in 0.46s
```

## Tests and exact results

- Focused asset tests: `2 passed in 0.46s`.
- Full test suite: `4 passed in 0.08s`.
- Ruff lint on changed Python files: `All checks passed!`.
- Ruff format check on changed Python files: `2 files already formatted`.
- Waterology constraints: `3/3 passed`.

## Self review

Reviewed path resolution and traversal protection, checkout and packaged
resource discovery, sorted skill directory output, exact force-include entries,
test assertions, and the resulting untracked file set. The required Task 1
Pixi correction remains untouched.

## Concerns

The full force-include map references directories produced by later tasks.
Without source placeholders, Hatch fails while building the editable package,
which prevents the required Pixi test command from running. The placeholders
are intentionally empty and can be replaced by those later task outputs.
