# Personal configuration

Waterology ships shared defaults for tools, visual design, prose, and workflows in canonical skills and rules. Private credentials, account details, and machine context stay outside repositories in `~/AGENTS.md` and `~/.config/waterology/config.toml`.

## Location and precedence

Run `wgy config path` to print the active user configuration path:

1. `WATEROLOGY_CONFIG`, if set.
2. `$XDG_CONFIG_HOME/waterology/config.toml`, if set.
3. `~/.config/waterology/config.toml`.

`wgy config init` creates a `0600` template without overwriting an existing file:

```toml
[credentials]
file = "~/.config/secrets/research.env"

[identity]
name = "Example Researcher"
email = "researcher@example.org"
git_name = "researcher"
orcid = ""

[preferences]
files = []

[writing]
files = []
papers = []

[guidance]
```

## Research API credentials for CLI and MCP

MCP clients often launch `waterology-mcp` outside interactive shells, bypassing `direnv`. Both `wgy` and `waterology-mcp` automatically fill missing `ZOTERO_API_KEY`, `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `CORE_API_KEY`, and `HF_TOKEN` variables from `[credentials].file` (which must have `0600` permissions). Existing environment variables take precedence, and secret values are never printed or persisted in records.

Verify availability with:

```console
wgy research-access
```

## Zero-overhead personal context

Keep global machine, account, Git, and HPC guidance in `~/AGENTS.md`, where every harness loads it automatically without extra shell calls. Skills do not run subprocesses on activation to query `config.toml`.
