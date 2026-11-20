# waterology-research

Waterology is a lightweight set of research conventions, deliverable templates, deterministic verifiers, and scholarly reference tools for [Antigravity](https://antigravity.google/), [Claude Code](https://claude.com/claude-code), [Codex](https://openai.com/codex/), [OpenCode](https://opencode.ai/), and [Pi](https://pi.dev/). It supports reproducible computational research across Python, R, Julia, Fortran, Quarto, Markdown, and LaTeX without adding database ceremony or token overhead.

Research workflows are runtime neutral. Private machine details, accounts, and credentials stay in [personal configuration](docs/local-configuration.md).

## What Waterology provides

1. **Consistent conventions and output templates:** Shared language defaults (`project-conventions`, `setup-environment`, `r-code-style`, path-scoped `rules/`), concise technical prose (`writing-style`), standalone Markdown report bundles (`reports/<topic>-<YYYY-MM-DD>/`), earth-tone multi-panel plots (`figures`), and 7-role TikZ flowcharts (`diagrams`).
2. **Fast deterministic verifiers:** Standard-library Python checks (`constraints/check-all.py`, `check_tikz_svg.py`, `verify_report_bundle.py`, `check_plotly_layout.py`, `overfull_boxes.py`, `validate_bib.py`, `myst_to_quarto.py`) that catch path leaks, unseeded RNGs, hardcoded numbers, SVG/Plotly text collisions, LaTeX overflow, and fabricated DOIs at zero prompt cost until run.
3. **Reference and dataset tooling (`wgy` CLI and `waterology-mcp`):** 10 bounded tools covering 11 scholarly providers (`openalex`, `semantic-scholar`, `core`, `alphaxiv`, `alphaxiv-keyword`, `arxiv`, `pubmed`, `europepmc`, `biorxiv`, `medrxiv`, `crossref`), standalone `.zotero.toml` collection sync with local SHA-256 PDF caching, and Hugging Face Hub dataset/file inspection.
4. **Lightweight autonomous loops:** Git-backed iterative `autoresearch` over a frozen evaluation command and flat `results.yaml` ledger (scaling to native [TORC](https://github.com/NatLabRockies/torc) when distributed or Slurm execution is needed), plus optional [SoL-Pi](https://github.com/NVlabs/SoL-Pi) coding delegation (`sol-pi`).

## Layout

```text
skills/             17 canonical research, figure, report, and verification skills
agent-definitions/  3 canonical subagents (researcher, reviewer, engineer)
.agent/agents/      generated Antigravity agents
agents/             generated Claude Code agents
.codex/agents/      generated Codex agents
.opencode/agents/   generated OpenCode agents
pi-agents/          generated pi-subagents agents
pi-skills/          generated Pi skills
pi-prompts/         generated Pi command prompts
commands/           generated Claude Code command shims
rules/              path-scoped language and document conventions
constraints/        deterministic pass/fail checks run by check-all.py
templates/          latexmk, pipeline, and reproducibility passport templates
.mcp.json           Claude Code and Codex plugin MCP registration
.codex/config.toml  Codex project MCP registration
opencode.json       OpenCode project MCP registration
package.json        Pi package manifest
ATTRIBUTION.md      citation ledger for adapted upstream material
```

## Install

Install the development environment and runtime adapters:

```console
pixi install
pixi run waterology install antigravity
pixi run waterology install claude
pixi run waterology install codex
pixi run waterology install opencode
pixi run waterology install pi
pixi run waterology install all --dry-run
pixi run waterology doctor
```

Project scope is the default. Use `--scope user` for user configuration. `--target` is available only for project installs. Both `install` and `doctor` support `--json`. See [installation lifecycle](docs/install-lifecycle.md) for upgrades, `--mode link`, uninstall, and recovery.

For a user-scoped Codex install:

```console
pixi run waterology install codex --scope user
```

Root `skills/` is canonical. Codex loads skills and MCP from `.codex-plugin/plugin.json` (`pixi run reinstall-plugins --runtime codex`), while `waterology install codex` installs generated agents in `.codex/agents/`. See the [Codex plugin documentation](https://developers.openai.com/plugins/concepts/plugins), [OpenCode skills documentation](https://opencode.ai/docs/skills), and [OpenCode agent documentation](https://opencode.ai/v2/docs/agents).

Antigravity installs skills and agents under `.agent/skills/` and `.agent/agents/` (or `~/.gemini/config/skills/` and `~/.gemini/config/agents/` with `--scope user`). Register the MCP server with `agy mcp add waterology waterology-mcp`, or print registration snippets with `waterology mcp config <runtime>`.

Pi loads `package.json` directly (`pi install /path/to/waterology-research` and `pi install npm:pi-subagents`), including `pi-extensions/waterology-mcp.ts`.

For Claude Code marketplace installs from the local checkout or canonical remote:

```text
/plugin marketplace add ~/projects/waterology-research
/plugin marketplace add ssh://git@codeberg.org/waterology/waterology-research.git
/plugin install waterology@waterology
```

Troubleshooting: remove a stale `.waterology-install.lock` only after confirming that no Waterology install process is running.

Refresh the editable CLI/MCP tool (`wgy`, `waterology`, `waterology-mcp`) and installed Claude/Codex plugins during development with:

```console
pixi run reinstall-plugins --dry-run
pixi run reinstall-plugins
```

## Reference management and dataset discovery

The `wgy` alias and `waterology-mcp` expose the same 10 bounded operations. Check configured API keys (`ZOTERO_API_KEY`, `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `CORE_API_KEY`, `HF_TOKEN`) without printing secret values:

```console
wgy research-access
```

Search scholarly providers anywhere (returns `recorded: false` outside `.zotero.toml` workspaces without creating local state):

```console
wgy discover "streamflow forecasting" --provider openalex --limit 20
wgy discover "reservoir operations" --provider core --limit 20
wgy discover "LSTM" --provider alphaxiv-keyword
```

To bind a repository or paper folder to a Zotero collection with local SHA-256 PDF caching (`.waterology/references/pdfs/`), initialize standalone `.zotero.toml`:

```console
wgy zotero init "Streamflow paper references"
wgy discover "ensemble streamflow prediction" --provider semantic-scholar
wgy source-decision <search-id> <source-id> include "Baseline benchmark"
wgy zotero capture source.yaml
wgy zotero sync
wgy zotero status
```

Inspect Hugging Face Hub datasets, file trees, and small text files without downloading binary blobs:

```console
wgy hf-dataset-info cameronbracken/example-dataset
wgy hf-repo-files cameronbracken/example-dataset
wgy hf-repo-read-file cameronbracken/example-dataset README.md
```

## Skills, agents, and constraints

### Core skills (17) and command shims

| Skill | Command shim | Purpose |
| --- | --- | --- |
| `project-conventions` | - | Language/tool defaults, file formats, `light` vs `strict` reproducibility modes, MyST converter |
| `setup-environment` | - | Pixi, uv, rv, system R on macOS, direnv, and `strict` environment capture |
| `writing-style` | - | Concise technical prose, scientific writing, and Markdown delivery rules |
| `research-software-quality` | - | Proportional testing, debugging, verification, and Git worktree cutoff |
| `figures` | - | Scientific plots, earth-tone styling, multi-panel assembly, and Plotly layout checks |
| `diagrams` | - | 7-role TikZ flowcharts (`flowchart-tikz.sty`) and `check_tikz_svg.py` overlap verification |
| `reports` | - | Standalone Markdown report bundles (`reports/<slug>-<YYYY-MM-DD>/`) and interactive Quarto HTML |
| `compile-latex` | `/compile-latex` | Verified `latexmk` + XeLaTeX builds and overfull-box diagnostics |
| `publish-blog-post` | - | Quarto blog post drafting, WebP media preparation, and deployment checks |
| `literature-review` | `/lit` | Multi-provider literature review, deep research, ML recipe lookup, and Zotero sync |
| `bib-validate` | `/bib-validate` | BibTeX key typo detection and OpenAlex/Crossref DOI verification |
| `simulation-study` | `/simulation-study` | Monte Carlo study design, parallel RNG streams, failure accounting, and MCSE reporting |
| `research-review` | `/review` | Constructive peer critique and manuscript narrative/figure-arc restructuring |
| `audit-reproducibility` | `/audit-reproducibility` | Numeric claim-to-output audit, paper-code parity, and `pipeline.md` manifests |
| `r-code-style` | - | Tidyverse + `air` formatting, `=` assignment, and pipe layout |
| `autoresearch` | `/autoresearch` | Lightweight Git + frozen-evaluator iteration loop for research and engineering optimization |
| `sol-pi` | - | Delegate bounded coding subtasks to SoL-Pi (`sol-pi-run`) |

### Subagents (3)

- `researcher`: Parallel primary-source gatherer across scholarly APIs, web, repositories, and Hugging Face Hub.
- `reviewer`: Independent peer reviewer and reproducibility/statistical auditor with fresh context.
- `engineer`: Isolated implementation, bug-fix, and constrained-optimization worker.

### Deterministic constraints (`constraints/check-all.py`)

```bash
python3 constraints/check-all.py [PATH ...]
```

Enforces `no-absolute-paths`, `deterministic-seed`, `pixi-r-task-dollar`, `plotly-text-overlap`, `mc-has-mcse`, `conservation-tol`, `overfull-boxes`, and `no-hardcoded-results`.

## Documentation

- [Documentation index](docs/README.md)
- [Getting started](docs/getting-started.md)
- [Choosing artifact skills](docs/artifact-skills.md)
- [Personal configuration](docs/local-configuration.md)
- [Installation lifecycle](docs/install-lifecycle.md)
- [Native TORC setup](docs/torc.md)
- [Apptainer environments](docs/apptainer.md)

## AI use

Claude and Gemini models through Codex, Claude Code, and Antigravity assisted with skill consolidation, reference provider integration, documentation, and tests.

## License

MIT Copyright Cameron Bracken. Adapted material is credited in [ATTRIBUTION.md](ATTRIBUTION.md).
