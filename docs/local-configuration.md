# Personal configuration

Waterology is a personal research package published for others to use. It ships
opinionated defaults for design, tools, writing, and workflow. Those choices
belong in canonical skills and rules, where they are maintained and discovered
together. Private context and optional overrides belong in the global
configuration and local Markdown files. Runtime installations include the
resolver; they never copy those local files into a project, wheel, or plugin cache.

| Public package | Local configuration only |
| --- | --- |
| Tool and language choices, environment workflow, coding style | Machine inventories, interpreter locations, private aliases and project paths |
| Palettes, themes, figure formats, report and diagram workflow | Account details, compute targets, allocation identifiers, service endpoints |
| Prose conventions, public writing examples, source attribution | Personal values, long-term vision, private notes and identity settings |
| Reusable blog layout, media preparation, provider preferences | Site credentials, private destinations, deployment secrets |

An author's public papers can inform the package's house style without making
that author the identity of every installed user. User instructions, project
requirements, and local overrides can replace package defaults where applicable.

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
research-review = ["reviews.md"]
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

For example, `preferences.md` can hold personal values and private collaboration
context. `r.md` can point to a machine's formatter configuration. `blog.md` can
supply a private site location or destination. Files can also provide deliberate
local overrides, but do not copy a whole package workflow there just to change
one setting. Machine guidance can point to an existing private inventory rather
than duplicating it. Credentials remain in SSH, provider stores, Keychain, or
environment variables.

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
These context commands are internal helpers; the user does not need to name
them to activate a skill. Normal prompts select skills through their descriptions.
For a new skill that needs private context, put the resolver instruction in its
canonical entry point. Changing a local file takes effect at its next read;
restart a running task if its agent has already read the older contents.

The scientific prose reference includes public papers that informed the house
style. Local writing examples are optional overrides or additions. Neither a
bundled citation nor a configured source proves that the current agent has
read its text. Supply prose analysis or retrieve the originals when the task
requires it. Public source credit does not set the installed user's identity.

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

When consolidating local guidance, move reusable defaults into the matching
canonical skills and rules. Retain only private context and intentional overrides
locally, remove obsolete config references, and validate every remaining path.
Keep a private backup until the migration is verified. Do not copy an entire
personal directory into the repository. Reinstall cached plugins or owned copies
after package changes; link installations see updated source directly. Start a
new agent session when its skill catalog still reflects the previous install.

Removing content from the latest commit does not remove it from earlier
commits. Before first public publication, audit the complete history intended
for the public repository. Prepare a separate sanitized clone when other
worktrees depend on the original history. Rewriting history changes commit IDs
and invalidates historical signatures. Preserve author/committer identity as
appropriate, sign new commits, and verify all public refs and packaged artifacts.
Private backups and the original development repository must not be pushed as
public branches or tags.
