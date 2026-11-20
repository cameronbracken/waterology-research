# Private context and local overrides

Package skills and rules own shared defaults for tools, visual design, writing, and workflow. Personal identity, machine inventories, account details, and credentials stay outside repositories in `~/AGENTS.md` and `~/.config/waterology/config.toml` (with API keys in `~/.config/secrets/research.env` or macOS Keychain).

User instructions and established project conventions take precedence over global preferences and package defaults. Never copy private local configuration or credentials into repository files, commit messages, or public artifacts.

Do not spawn shell commands to query local configuration on routine skill loads. Read `~/.config/waterology/config.toml` directly only when a task explicitly involves user configuration or an optional local override file is known to exist.
