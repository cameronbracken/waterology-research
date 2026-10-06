# Local preferences

Run `waterology config context project-conventions` when a task leaves a choice
about identity, tools, collaboration, privacy, source credit, or visual design.
Use only the relevant settings. Do not copy personal context into artifacts or
publish it unless the user requests that disclosure. Identity is context for
explicit author/contact fields, not permission to change Git configuration.

The command resolves `WATEROLOGY_CONFIG`, then
`$XDG_CONFIG_HOME/waterology/config.toml`, then the home directory's
`.config/waterology/config.toml`. It reads optional Markdown files named by
`preferences.files` and `guidance.project-conventions` relative to that config.
No config means no personal guidance. Missing configured files are errors.
If the CLI is unavailable, resolve and read only these fields/files directly.
Never read credentials or dump unrelated configuration into a transcript.

User instructions and project requirements take precedence. Local settings
choose among otherwise open options; they do not change scientific gates or
permission boundaries. Other skills read their own `guidance` entries with
`waterology config context SKILL-NAME`. Rule entries such as `r-conventions`
use the same mechanism. Read local context once per task and refresh after
configuration changes. Do not edit installed or packaged skills to personalize.

Installers include this resolver for every user. They never copy the local
configuration or its referenced files into project or plugin assets.
