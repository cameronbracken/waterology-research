# Getting started

Waterology installs opinionated research skills, 3 focused subagents (`researcher`, `reviewer`, `engineer`), deterministic verifiers, and 10 bounded reference/dataset MCP and CLI tools.

## Install

From a source checkout:

```console
pixi install
pixi run waterology --help
pixi run waterology doctor
```

Install the adapters needed by your project or user configuration (`--scope user`):

```console
pixi run waterology install antigravity --scope user
pixi run waterology install claude
pixi run waterology install codex
pixi run waterology install opencode
pixi run waterology install pi
```

To expose `waterology`, `wgy`, and `waterology-mcp` globally on `PATH` and refresh Claude/Codex plugins:

```console
pixi run reinstall-plugins
```

## Configure research API keys

Create optional private user settings (`~/.config/waterology/config.toml`) pointing at your `0600` dotenv file (default `~/.config/secrets/research.env`) so both CLI commands and stdio MCP servers receive `ZOTERO_API_KEY`, `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `CORE_API_KEY`, and `HF_TOKEN`:

```console
wgy config init
wgy research-access
```

## Track references in a paper or project repository

Initialize `.zotero.toml` at the repository root (no `waterology.toml` needed):

```console
wgy zotero init "Project reference library"
wgy discover "hydrologic drought" --provider openalex
wgy source-decision <search-id> <source-id> include "Core method reference"
wgy zotero sync
wgy zotero status
```

Outside `.zotero.toml` repositories, `wgy discover` and `wgy hf-*` run cleanly without writing local `.waterology/` state (`recorded: false`).
