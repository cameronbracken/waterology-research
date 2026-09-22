# Personal configuration

Waterology ships shared research workflows without a personal identity, writing
corpus, machine inventory, or personal preferences. Keep those in the global
configuration and optional local Markdown files. Runtime installations include
the instructions for reading them; they never copy your configuration or its
contents into a project, wheel, or plugin cache.

## Location and precedence

Run `waterology config path` to find the active file. Resolution is:

1. `WATEROLOGY_CONFIG`, if set.
2. `$XDG_CONFIG_HOME/waterology/config.toml`, if set.
3. `.config/waterology/config.toml` under your home directory.

`waterology config init` creates an empty file with private permissions where
supported. It never replaces an existing file. Missing configuration means no
personal settings. Invalid configuration and missing explicitly referenced
files produce errors. Use the same environment variables in your shell and
agent runtime so both resolve the same configuration.

Existing `[profiles]` and `trusted_profiles` remain supported. Adding personal
settings does not require changing compute profiles. Trusting a profile retains
the personal sections. `waterology config show`, `schema`, and `refresh` still
refer to project configuration, not this private global file.

Explicit user instructions and project requirements take precedence over local
preferences. Local preferences choose among otherwise open options. They do not
change permission requirements, frozen protocols, or scientific acceptance
criteria. Identity settings do not automatically change Git identity or sign
commits. Package authorship and copyright are independent of user identity.

## Example configuration

All values below are fictional. Add only the sections you need.

```toml
trusted_profiles = []

[identity]
name = "Example Researcher"
email = "researcher@example.org"
git_name = "researcher"
orcid = ""

[preferences]
files = ["preferences.md"]

[writing]
files = ["writing.md", "scientific-writing.md"]
papers = [] # optional DOI strings, URLs, or local paper paths

[guidance]
project-conventions = ["development.md", "machines.md"]
python-conventions = ["python.md"]
r-conventions = ["r.md"]
quarto-conventions = ["reports.md"]
setup-environment = ["environments.md"]
figure-style = ["figures.md"]
paper-writing = ["reports.md"]
publish-blog-post = ["blog.md"]

[profiles.local]
mode = "local"
api_url = "http://localhost:8080/torc-service/v1"

[dashboard]
profile = "local"
host = "127.0.0.1"
llm_provider = "openai"
openai_base_url = "http://localhost:4000/v1"
openai_model = "example-model"
api_key_env = "LOCAL_LLM_API_KEY"
```

Every referenced Markdown file must exist. Paths are relative to the global
configuration directory; absolute and home-relative paths are also supported.
Keep these files outside repositories. Do not put credentials in them.
`guidance` accepts any skill or rule name with a list of local Markdown files.
All personal sections are optional; strings default to empty and lists to `[]`.
The dashboard host defaults to loopback. Its profile must be explicitly selected.

For example, `preferences.md` can describe collaboration and privacy choices.
`r.md` can select an assignment style, formatter configuration, line width, and
editor markers. `figures.md` can specify palette, theme, dimensions, and export
formats. `blog.md` can supply a site's location, frontmatter, media destinations,
image tools, and preview/build commands. Machine guidance can point to an
existing private inventory rather than duplicating it. Credentials remain in
SSH, provider stores, Keychain, or environment variables.

## Reading local guidance

```console
waterology config context project-conventions
waterology config context writing-style
waterology config context figure-style
```

These commands intentionally output the requested personal guidance for the
agent. They do not fetch papers or execute the text. Do not paste their output
into public issues, logs, or documents. Only `project-conventions` includes the
identity section. Every context includes `preferences.files`; `writing-style`
also includes `writing.files` and `writing.papers`. Other context names include
only their matching `guidance` entry in addition to common preferences. Files
are deduplicated in order. Keep task-specific information in `guidance` instead
of the common preferences file.

Skills with personal choices invoke the corresponding context command. If the
CLI is unavailable in a plugin-only install, the shared project-conventions
reference documents the same path resolution for reading local files directly.
For additional skills, request that the agent read `waterology config context
SKILL-NAME` or add that instruction to your private user guidance. Changing a
local file takes effect at its next read; restart a running task if its agent
has already read the older contents.

Writing examples are optional. The package does not select papers on your
behalf or claim that a configured source has been read. Supply your own prose
analysis in a local Markdown file or have the agent retrieve/read the selected
papers under your normal access rules. Public source credits in
`ATTRIBUTION.md` record the package's origins, not an installed user's corpus.

## Dashboard launcher

`waterology config dashboard --dry-run` prints the launch arguments without
reading credentials or starting a process. `waterology config dashboard` starts
`torc-dash` using `dashboard.profile` and the optional LLM settings. The repository
script `scripts/run-torc-dash.sh` delegates to this command.

`api_key_env` names the environment variable holding the API key; it is not the
key itself. TORC reads `TORC_PASSWORD` from the environment. On macOS, the optional
`dashboard.torc_password_keychain_service` names a Keychain service to query for
the current `$USER` when `TORC_PASSWORD` is absent. On other systems, use the
environment or your credential manager. A missing configured credential fails
the launch. The launcher never prints credential values.

## Installation, sharing, and migration

The same resolver is included in copy/link installs for Claude Code, Codex,
OpenCode, and Pi, and in packaged/plugin skills. No local configuration is needed
to install. Each user supplies their own file. Keep the global configuration
outside the checkout; copying an entire home/config directory into a repository
would defeat this separation.

To migrate older personal defaults, save them into private Markdown files,
reference those files in the global configuration, and reinstall the updated
skills. Remove obsolete personal files from any unmanaged old installations.
Reinstallation of an owned copy updates the skill directory and removes its
obsolete bundled reference. Link installations see the updated source directly.
Do not put local overrides back into canonical skills.

Removing content from the latest commit does not remove it from earlier
commits. Before first public publication, audit the complete history intended
for the public repository. Prepare a separate sanitized clone when other
worktrees depend on the original history. Rewriting history changes commit IDs
and invalidates historical signatures. Preserve author/committer identity as
appropriate, sign new commits, and verify all public refs and packaged artifacts.
Private backups and the original development repository must not be pushed as
public branches or tags.
