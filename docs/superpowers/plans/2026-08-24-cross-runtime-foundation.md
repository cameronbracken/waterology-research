# Cross Runtime Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing repository into a tested Waterology package that Claude Code, Codex, and OpenCode can discover and install without changing the existing research workflows.

**Architecture:** A small Python package owns asset discovery, agent rendering, validation, and safe installation. Canonical Markdown agent definitions render into the native Claude Code, Codex, and OpenCode formats. Root skills remain canonical; their content becomes fully runtime neutral in the next plan, which must use behavioral tests for each edited skill.

**Tech Stack:** Python 3.11+, Typer, Rich, Pydantic 2, PyYAML, Hatchling, Pixi, pytest, Ruff, JSON, TOML, Markdown

**Spec:** `docs/superpowers/specs/2026-08-24-waterology-platform-design.md`

## Global Constraints

- Preserve the working Claude Code plugin and every existing command during this plan.
- Use `waterology` for the product, Python package, executable, and manifest name.
- Set the release version to `0.2.0` in Python, Claude Code, and Codex metadata.
- Keep `skills/` as the canonical Agent Skills directory.
- Keep generated Claude Code, Codex, and OpenCode agent files in version control.
- Do not edit skill behavior in this plan. The next plan must use `superpowers:writing-skills` and one RED-GREEN-REFACTOR cycle for each changed skill.
- Support project installs by default. Require `--scope user` for writes under a user's runtime configuration directories.
- Refuse to overwrite any destination that a Waterology install manifest does not own.
- Support `--dry-run` and JSON output for installer and diagnostic commands.
- Use argument arrays for subprocesses. Do not invoke a shell from Python.
- Keep the implementation portable across Linux, macOS, and Windows.
- Format and lint Python with Ruff.
- Run implementation work through test driven development.
- Sign every commit as `researcher <researcher@example.org>` and never add a coauthor trailer.
- Do not push.

## Planned file map

```text
pyproject.toml                         package metadata and wheel asset map
pixi.toml                              development environment and tasks
src/waterology/__init__.py             package version
src/waterology/__main__.py             python -m waterology entry point
src/waterology/cli.py                  Typer command tree
src/waterology/runtime/assets.py       source and wheel asset discovery
src/waterology/runtime/agents.py       canonical agent parser and model
src/waterology/runtime/render.py       native agent renderers
src/waterology/runtime/validate.py     manifests, skills, and generated asset checks
src/waterology/runtime/install.py      install plans, preflight, copy, and link operations
src/waterology/runtime/doctor.py       runtime and asset diagnostics
src/waterology_assets/__init__.py      wheel resource package marker
agent-definitions/*.md                 canonical agent sources
agents/*.md                            generated Claude Code agents
.codex/agents/*.toml                   generated Codex agents
.opencode/agents/*.md                  generated OpenCode agents
.codex-plugin/plugin.json              Codex plugin manifest
.claude-plugin/plugin.json             updated Claude Code manifest
.claude-plugin/marketplace.json        updated Claude marketplace description
AGENTS.md                               canonical repository guidance
CLAUDE.md                               thin Claude Code adapter
README.md                               three-runtime installation and use
ROADMAP.md                              platform slice tracking
tests/runtime/                          focused Python tests
tests/packaging/                        wheel and manifest tests
```

---

### Task 1: Python package and command shell

**Files:**
- Create: `pyproject.toml`
- Create: `pixi.toml`
- Create: `src/waterology/__init__.py`
- Create: `src/waterology/__main__.py`
- Create: `src/waterology/cli.py`
- Create: `src/waterology/runtime/__init__.py`
- Create: `src/waterology_assets/__init__.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: no earlier task
- Produces: `waterology.cli.app: typer.Typer`, `waterology.__version__: str`, and the `waterology` console script

- [ ] **Step 1: Write the failing CLI tests**

```python
from typer.testing import CliRunner

from waterology.cli import app


runner = CliRunner()


def test_version_is_0_2_0() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "0.2.0"


def test_help_names_the_research_package() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Waterology research workflows" in result.stdout
```

- [ ] **Step 2: Run the tests and confirm the package is absent**

Run: `pixi run pytest tests/test_cli.py -v`

Expected: FAIL during collection with `ModuleNotFoundError: No module named 'waterology'`.

- [ ] **Step 3: Add the package metadata and Pixi environment**

Use this package contract in `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[project]
name = "waterology"
version = "0.2.0"
description = "Research workflows for Claude Code, Codex, and OpenCode"
readme = "README.md"
requires-python = ">=3.11"
license = { file = "LICENSE" }
authors = [
  { name = "Cameron Bracken", email = "researcher@example.org" },
]
dependencies = [
  "pydantic>=2.8,<3",
  "pyyaml>=6.0,<7",
  "rich>=13.9,<15",
  "typer>=0.16,<1",
]

[project.scripts]
waterology = "waterology.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/waterology", "src/waterology_assets"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Use this Pixi contract:

```toml
[workspace]
channels = ["conda-forge"]
platforms = ["osx-arm64", "osx-64", "linux-64", "win-64"]

[dependencies]
python = ">=3.11"
pip = ">=25"

[pypi-dependencies]
waterology = { path = ".", editable = true }

[feature.dev.dependencies]
build = ">=1.3"
pytest = ">=8.4"
pytest-cov = ">=6.2"
ruff = ">=0.12"

[environments]
default = { features = ["dev"], solve-group = "default" }

[tasks]
test = "pytest"
lint = "ruff check ."
format = "ruff format ."
check = { depends-on = ["lint", "test"] }
```

- [ ] **Step 4: Implement the minimal command shell**

```python
# src/waterology/__init__.py
__version__ = "0.2.0"
```

```python
# src/waterology/cli.py
import typer

from waterology import __version__

app = typer.Typer(
    help="Waterology research workflows for Claude Code, Codex, and OpenCode.",
    no_args_is_help=True,
)


def _version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version,
        is_eager=True,
        help="Show the Waterology version.",
    ),
) -> None:
    """Run Waterology commands."""
```

```python
# src/waterology/__main__.py
from waterology.cli import app

app()
```

- [ ] **Step 5: Run focused tests and formatting**

Run: `pixi install`

Run: `pixi run pytest tests/test_cli.py -v`

Expected: 2 passed.

Run: `pixi run ruff check src tests`

Expected: exit 0.

- [ ] **Step 6: Commit the package shell**

```bash
git add pyproject.toml pixi.toml src tests/test_cli.py
git -c user.name=researcher -c user.email=researcher@example.org commit -S -m "feat: add waterology command package"
```

### Task 2: Asset discovery in checkouts and wheels

**Files:**
- Create: `src/waterology/runtime/assets.py`
- Create: `tests/runtime/test_assets.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `waterology` and `waterology_assets` packages from Task 1
- Produces: `AssetCatalog.discover(source_root: Path | None = None) -> AssetCatalog`, `AssetCatalog.path(relative: str) -> Path`, and `AssetCatalog.skill_directories() -> tuple[Path, ...]`

- [ ] **Step 1: Write failing asset catalog tests**

```python
from pathlib import Path

import pytest

from waterology.runtime.assets import AssetCatalog, AssetNotFoundError


def test_catalog_uses_an_explicit_source_root(tmp_path: Path) -> None:
    skill = tmp_path / "skills" / "example" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: example\ndescription: Use when testing.\n---\n")

    catalog = AssetCatalog.discover(tmp_path)

    assert catalog.path("skills/example/SKILL.md") == skill.resolve()
    assert catalog.skill_directories() == (skill.parent.resolve(),)


def test_catalog_rejects_parent_traversal(tmp_path: Path) -> None:
    (tmp_path / "skills").mkdir()
    catalog = AssetCatalog.discover(tmp_path)

    with pytest.raises(AssetNotFoundError, match="outside the asset root"):
        catalog.path("../secret.txt")
```

- [ ] **Step 2: Run the focused tests and confirm the module is absent**

Run: `pixi run pytest tests/runtime/test_assets.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'waterology.runtime.assets'`.

- [ ] **Step 3: Implement checkout and wheel discovery**

```python
from dataclasses import dataclass
from importlib import resources
from pathlib import Path


class AssetNotFoundError(ValueError):
    pass


@dataclass(frozen=True)
class AssetCatalog:
    root: Path

    @classmethod
    def discover(cls, source_root: Path | None = None) -> "AssetCatalog":
        if source_root is not None:
            return cls(source_root.resolve())

        checkout = Path(__file__).resolve().parents[3]
        if (checkout / "skills").is_dir() and (checkout / "pyproject.toml").is_file():
            return cls(checkout)

        packaged = Path(str(resources.files("waterology_assets")))
        if (packaged / "skills").is_dir():
            return cls(packaged.resolve())
        raise AssetNotFoundError("Waterology assets are missing")

    def path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        try:
            candidate.relative_to(self.root.resolve())
        except ValueError as error:
            raise AssetNotFoundError(f"Asset is outside the asset root: {relative}") from error
        if not candidate.exists():
            raise AssetNotFoundError(f"Asset does not exist: {relative}")
        return candidate

    def skill_directories(self) -> tuple[Path, ...]:
        return tuple(sorted(path.parent.resolve() for path in self.root.glob("skills/*/SKILL.md")))
```

- [ ] **Step 4: Add wheel asset mappings**

Add these mappings to `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel.force-include]
"skills" = "waterology_assets/skills"
"commands" = "waterology_assets/commands"
"rules" = "waterology_assets/rules"
"constraints" = "waterology_assets/constraints"
"agents" = "waterology_assets/agents"
"agent-definitions" = "waterology_assets/agent-definitions"
".claude-plugin" = "waterology_assets/.claude-plugin"
".codex-plugin" = "waterology_assets/.codex-plugin"
".codex/agents" = "waterology_assets/.codex/agents"
".opencode/agents" = "waterology_assets/.opencode/agents"
"ATTRIBUTION.md" = "waterology_assets/ATTRIBUTION.md"
"LICENSE" = "waterology_assets/LICENSE"
```

- [ ] **Step 5: Run the focused tests**

Run: `pixi run pytest tests/runtime/test_assets.py -v`

Expected: 2 passed.

- [ ] **Step 6: Commit asset discovery**

```bash
git add pyproject.toml src/waterology/runtime/assets.py tests/runtime/test_assets.py
git -c user.name=researcher -c user.email=researcher@example.org commit -S -m "feat: discover packaged waterology assets"
```

### Task 3: Canonical agent definitions

**Files:**
- Create: `src/waterology/runtime/agents.py`
- Create: `agent-definitions/researcher.md`
- Create: `agent-definitions/reviewer.md`
- Create: `agent-definitions/verifier.md`
- Create: `agent-definitions/writer.md`
- Create: `tests/runtime/test_agents.py`

**Interfaces:**
- Consumes: `AssetCatalog` from Task 2 and the bodies of the four existing `agents/*.md` files
- Produces: `AgentDefinition`, `parse_agent(path: Path) -> AgentDefinition`, and `load_agents(catalog: AssetCatalog) -> tuple[AgentDefinition, ...]`

- [ ] **Step 1: Write failing parser and source tests**

```python
from pathlib import Path

from waterology.runtime.agents import load_agents, parse_agent
from waterology.runtime.assets import AssetCatalog


def test_parse_agent_reads_neutral_metadata(tmp_path: Path) -> None:
    source = tmp_path / "researcher.md"
    source.write_text(
        "---\n"
        "name: researcher\n"
        "description: Gather evidence from primary sources.\n"
        "capabilities: [read, write, shell, web]\n"
        "---\n\n"
        "Gather evidence.\n"
    )

    agent = parse_agent(source)

    assert agent.name == "researcher"
    assert agent.capabilities == ("read", "write", "shell", "web")
    assert agent.body == "Gather evidence.\n"


def test_repository_has_four_sorted_canonical_agents() -> None:
    agents = load_agents(AssetCatalog.discover())

    assert [agent.name for agent in agents] == [
        "researcher",
        "reviewer",
        "verifier",
        "writer",
    ]
    assert all("WebSearch" not in agent.body for agent in agents)
    assert all("WebFetch" not in agent.body for agent in agents)
    assert all("`Bash`" not in agent.body for agent in agents)
    assert all(chr(0x2014) not in agent.body for agent in agents)
```

- [ ] **Step 2: Run the focused tests and confirm the parser is absent**

Run: `pixi run pytest tests/runtime/test_agents.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'waterology.runtime.agents'`.

- [ ] **Step 3: Implement the validated canonical model and parser**

```python
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from waterology.runtime.assets import AssetCatalog

Capability = Literal["read", "write", "shell", "web"]
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", re.DOTALL)


class AgentDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = Field(min_length=1, max_length=1024)
    capabilities: tuple[Capability, ...]
    body: str = Field(min_length=1)
    source_path: Path


def parse_agent(path: Path) -> AgentDefinition:
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"Agent lacks YAML frontmatter: {path}")
    metadata = yaml.safe_load(match.group(1))
    return AgentDefinition.model_validate(
        {**metadata, "body": match.group(2).lstrip("\n"), "source_path": path}
    )


def load_agents(catalog: AssetCatalog) -> tuple[AgentDefinition, ...]:
    source_dir = catalog.path("agent-definitions")
    return tuple(parse_agent(path) for path in sorted(source_dir.glob("*.md")))
```

- [ ] **Step 4: Create the four canonical source files**

Move each existing prompt body from `agents/<name>.md` into
`agent-definitions/<name>.md`. Keep its attribution comment and substantive
instructions. Use this exact metadata table:

| Name | Capabilities | Description source |
|---|---|---|
| `researcher` | `read, write, shell, web` | Existing researcher description, with `evidence gatherer` written without a hyphen |
| `reviewer` | `read, write, shell, web` | Existing reviewer description, with the em dash replaced by a colon |
| `verifier` | `read, write, shell, web` | Existing verifier description |
| `writer` | `read, write, shell` | Existing writer description |

Replace runtime tool labels in the four bodies with capability language:

| Existing label | Canonical wording |
|---|---|
| `WebSearch` | `the runtime's web search tool` |
| `WebFetch` | `the runtime's page reader` |
| `` `Bash` `` | `the runtime's shell` |
| `Task tool` | `the runtime's subagent mechanism` |

Keep named optional services such as Kagi, OpenAlex, and Consensus because they
describe research sources rather than one model runtime. Replace every em dash
in the four canonical files with punctuation that can be typed on a standard
US keyboard.

- [ ] **Step 5: Run parser and source tests**

Run: `pixi run pytest tests/runtime/test_agents.py -v`

Expected: 2 passed.

Run: `pixi run ruff check src tests/runtime/test_agents.py`

Expected: exit 0.

- [ ] **Step 6: Commit canonical agents**

```bash
git add agent-definitions src/waterology/runtime/agents.py tests/runtime/test_agents.py
git -c user.name=researcher -c user.email=researcher@example.org commit -S -m "refactor: define runtime-neutral research agents"
```

### Task 4: Native agent renderers

**Files:**
- Create: `src/waterology/runtime/render.py`
- Create: `tests/runtime/test_render.py`
- Modify: `.gitignore`
- Replace: `agents/researcher.md`
- Replace: `agents/reviewer.md`
- Replace: `agents/verifier.md`
- Replace: `agents/writer.md`
- Create: `.codex/agents/researcher.toml`
- Create: `.codex/agents/reviewer.toml`
- Create: `.codex/agents/verifier.toml`
- Create: `.codex/agents/writer.toml`
- Create: `.opencode/agents/researcher.md`
- Create: `.opencode/agents/reviewer.md`
- Create: `.opencode/agents/verifier.md`
- Create: `.opencode/agents/writer.md`

**Interfaces:**
- Consumes: `AgentDefinition` and `load_agents()` from Task 3
- Produces: `render_claude(agent) -> str`, `render_codex(agent) -> str`, `render_opencode(agent) -> str`, and `render_agents(catalog, output_root, check=False) -> tuple[Path, ...]`

- [ ] **Step 1: Write failing native format tests**

```python
import tomllib
from pathlib import Path

import yaml

from waterology.runtime.agents import AgentDefinition
from waterology.runtime.render import render_claude, render_codex, render_opencode


def sample_agent(tmp_path: Path) -> AgentDefinition:
    return AgentDefinition(
        name="researcher",
        description="Gather primary evidence.",
        capabilities=("read", "write", "shell", "web"),
        body="Gather evidence and cite it.\n",
        source_path=tmp_path / "researcher.md",
    )


def split_markdown_frontmatter(text: str) -> tuple[dict[str, object], str]:
    _, frontmatter, body = text.split("---", 2)
    return yaml.safe_load(frontmatter), body


def test_claude_renderer_maps_capabilities(tmp_path: Path) -> None:
    metadata, body = split_markdown_frontmatter(render_claude(sample_agent(tmp_path)))
    assert metadata["name"] == "researcher"
    assert metadata["tools"] == (
        "Read, Grep, Glob, Write, Edit, Bash, WebSearch, WebFetch, "
        "mcp__kagi__kagi_search_fetch, mcp__kagi__kagi_extract"
    )
    assert "Generated from agent-definitions/researcher.md" in body


def test_codex_renderer_is_valid_toml(tmp_path: Path) -> None:
    rendered = render_codex(sample_agent(tmp_path))
    data = tomllib.loads(rendered)
    assert data == {
        "name": "researcher",
        "description": "Gather primary evidence.",
        "developer_instructions": "Gather evidence and cite it.\n",
    }


def test_opencode_renderer_uses_v2_subagent_format(tmp_path: Path) -> None:
    metadata, body = split_markdown_frontmatter(render_opencode(sample_agent(tmp_path)))
    assert metadata == {"description": "Gather primary evidence.", "mode": "subagent"}
    assert "Gather evidence and cite it." in body
```

- [ ] **Step 2: Run the tests and confirm the renderer is absent**

Run: `pixi run pytest tests/runtime/test_render.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'waterology.runtime.render'`.

- [ ] **Step 3: Implement deterministic render functions**

Use `yaml.safe_dump(..., sort_keys=False)` for Markdown frontmatter and
`json.dumps()` for TOML string values. JSON quoted strings are valid TOML basic
strings and safely preserve line breaks in agent bodies.

```python
import json
from pathlib import Path

import yaml

from waterology.runtime.agents import AgentDefinition, load_agents
from waterology.runtime.assets import AssetCatalog

CLAUDE_TOOLS = {
    "read": ("Read", "Grep", "Glob"),
    "write": ("Write", "Edit"),
    "shell": ("Bash",),
    "web": (
        "WebSearch",
        "WebFetch",
        "mcp__kagi__kagi_search_fetch",
        "mcp__kagi__kagi_extract",
    ),
}


def render_claude(agent: AgentDefinition) -> str:
    tools = tuple(tool for capability in agent.capabilities for tool in CLAUDE_TOOLS[capability])
    frontmatter = yaml.safe_dump(
        {"name": agent.name, "description": agent.description, "tools": ", ".join(tools)},
        sort_keys=False,
    ).rstrip()
    marker = f"<!-- Generated from agent-definitions/{agent.name}.md. Do not edit. -->"
    return f"---\n{frontmatter}\n---\n\n{marker}\n\n{agent.body}"


def render_codex(agent: AgentDefinition) -> str:
    return (
        f"# Generated from agent-definitions/{agent.name}.md. Do not edit.\n"
        f"name = {json.dumps(agent.name)}\n"
        f"description = {json.dumps(agent.description)}\n"
        f"developer_instructions = {json.dumps(agent.body)}\n"
    )


def render_opencode(agent: AgentDefinition) -> str:
    frontmatter = yaml.safe_dump(
        {"description": agent.description, "mode": "subagent"},
        sort_keys=False,
    ).rstrip()
    marker = f"<!-- Generated from agent-definitions/{agent.name}.md. Do not edit. -->"
    return f"---\n{frontmatter}\n---\n\n{marker}\n\n{agent.body}"
```

Add the stale output error and `render_agents()` with this exact destination
map and behavior:

```python
DESTINATIONS = {
    "claude": ("agents", ".md", render_claude),
    "codex": (".codex/agents", ".toml", render_codex),
    "opencode": (".opencode/agents", ".md", render_opencode),
}


class GeneratedAssetsStaleError(RuntimeError):
    def __init__(self, paths: tuple[Path, ...]) -> None:
        self.paths = paths
        super().__init__("Generated agent files are stale")


def render_agents(
    catalog: AssetCatalog,
    output_root: Path,
    check: bool = False,
) -> tuple[Path, ...]:
    changed: list[Path] = []
    for agent in load_agents(catalog):
        for directory, suffix, renderer in DESTINATIONS.values():
            destination = output_root / directory / f"{agent.name}{suffix}"
            expected = renderer(agent)
            current = destination.read_text(encoding="utf-8") if destination.exists() else None
            if current == expected:
                continue
            changed.append(destination)
            if not check:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(expected, encoding="utf-8")
    paths = tuple(sorted(changed))
    if check and paths:
        raise GeneratedAssetsStaleError(paths)
    return paths
```

- [ ] **Step 4: Allow only generated Codex agents through `.gitignore`**

Replace the broad `.codex/` rule with:

```gitignore
.codex/*
!.codex/agents/
!.codex/agents/*.toml
```

- [ ] **Step 5: Render and test the repository agents**

Run: `pixi run python -c "from pathlib import Path; from waterology.runtime.assets import AssetCatalog; from waterology.runtime.render import render_agents; render_agents(AssetCatalog.discover(), Path('.'))"`

Run: `pixi run pytest tests/runtime/test_render.py tests/runtime/test_agents.py -v`

Expected: 5 passed.

Run: `pixi run python -c "from pathlib import Path; from waterology.runtime.assets import AssetCatalog; from waterology.runtime.render import render_agents; render_agents(AssetCatalog.discover(), Path('.'), check=True)"`

Expected: exit 0 with no changed files.

- [ ] **Step 6: Commit the renderer and generated agents**

```bash
git add .gitignore agent-definitions agents .codex/agents .opencode/agents src/waterology/runtime/render.py tests/runtime/test_render.py
git -c user.name=researcher -c user.email=researcher@example.org commit -S -m "feat: render agents for three runtimes"
```

### Task 5: Runtime manifests and asset validation

**Files:**
- Create: `.codex-plugin/plugin.json`
- Create: `src/waterology/runtime/validate.py`
- Create: `tests/runtime/test_validate.py`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

**Interfaces:**
- Consumes: version `0.2.0`, root `skills/`, and generated agents from Task 4
- Produces: `ValidationIssue`, `validate_assets(catalog) -> tuple[ValidationIssue, ...]`, and matching Claude Code and Codex plugin metadata

- [ ] **Step 1: Write failing manifest and skill validation tests**

```python
import json

from waterology.runtime.assets import AssetCatalog
from waterology.runtime.validate import validate_assets


def test_runtime_manifests_have_matching_identity() -> None:
    catalog = AssetCatalog.discover()
    claude = json.loads(catalog.path(".claude-plugin/plugin.json").read_text())
    codex = json.loads(catalog.path(".codex-plugin/plugin.json").read_text())

    assert claude["name"] == codex["name"] == "waterology"
    assert claude["version"] == codex["version"] == "0.2.0"
    assert "Claude Code plugin" not in claude["description"]
    assert codex["skills"] == "./skills/"


def test_repository_assets_validate_cleanly() -> None:
    assert validate_assets(AssetCatalog.discover()) == ()
```

- [ ] **Step 2: Run the tests and observe missing Codex assets**

Run: `pixi run pytest tests/runtime/test_validate.py -v`

Expected: FAIL because `.codex-plugin/plugin.json` and `validate_assets` do not exist.

- [ ] **Step 3: Add the Codex manifest and update Claude metadata**

Use this Codex manifest contract:

```json
{
  "name": "waterology",
  "version": "0.2.0",
  "description": "Reproducible computational research workflows for Claude Code, Codex, and OpenCode.",
  "author": {
    "name": "Cameron Bracken",
    "email": "researcher@example.org",
    "url": "https://codeberg.org/waterology"
  },
  "homepage": "https://codeberg.org/waterology/waterology-cc",
  "repository": "https://codeberg.org/waterology/waterology-cc",
  "license": "MIT",
  "keywords": ["research", "reproducibility", "hydrology", "scientific-computing"],
  "skills": "./skills/",
  "interface": {
    "displayName": "Waterology",
    "shortDescription": "Reproducible computational research workflows",
    "longDescription": "Research agents, skills, and reproducibility conventions for computational science.",
    "developerName": "Cameron Bracken",
    "category": "Productivity",
    "capabilities": ["Interactive", "Write"],
    "brandColor": "#6B7D58",
    "defaultPrompt": [
      "Review this analysis for reproducibility.",
      "Survey the literature and track every source.",
      "Plan a bounded research experiment."
    ]
  }
}
```

Apply the same version, description, author name, Codeberg URLs, and concise
keywords to `.claude-plugin/plugin.json`. Update the marketplace description to
say that Waterology supports Claude Code, Codex, and OpenCode while preserving
the existing Claude marketplace structure.

- [ ] **Step 4: Implement repository validation**

```python
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import yaml

from waterology import __version__
from waterology.runtime.assets import AssetCatalog
from waterology.runtime.render import GeneratedAssetsStaleError, render_agents

SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MANIFESTS = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json")


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str


def _validate_manifests(catalog: AssetCatalog) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for relative in MANIFESTS:
        data = json.loads(catalog.path(relative).read_text(encoding="utf-8"))
        for field in ("name", "version", "description", "author", "license"):
            if not data.get(field):
                issues.append(ValidationIssue(relative, "missing-field", field))
        if data.get("name") != "waterology":
            issues.append(ValidationIssue(relative, "wrong-name", str(data.get("name"))))
        if data.get("version") != __version__:
            issues.append(ValidationIssue(relative, "wrong-version", str(data.get("version"))))
    return issues


def _frontmatter(path: Path) -> dict[str, object]:
    parts = path.read_text(encoding="utf-8").split("---", 2)
    if len(parts) != 3:
        raise ValueError("missing YAML frontmatter")
    return yaml.safe_load(parts[1])


def _validate_skills(catalog: AssetCatalog) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen: set[str] = set()
    for directory in catalog.skill_directories():
        path = directory / "SKILL.md"
        relative = path.relative_to(catalog.root).as_posix()
        try:
            data = _frontmatter(path)
        except (ValueError, yaml.YAMLError) as error:
            issues.append(ValidationIssue(relative, "invalid-frontmatter", str(error)))
            continue
        name = str(data.get("name", ""))
        description = str(data.get("description", ""))
        if not SKILL_NAME.fullmatch(name) or name != directory.name:
            issues.append(ValidationIssue(relative, "invalid-name", name))
        if name in seen:
            issues.append(ValidationIssue(relative, "duplicate-name", name))
        seen.add(name)
        if not 1 <= len(description) <= 1024:
            issues.append(ValidationIssue(relative, "invalid-description", str(len(description))))
    return issues


def _validate_generated_agents(catalog: AssetCatalog) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    try:
        render_agents(catalog, catalog.root, check=True)
    except GeneratedAssetsStaleError as error:
        issues.extend(
            ValidationIssue(path.as_posix(), "stale-generated-agent", "rendered content differs")
            for path in error.paths
        )
    for path in sorted(catalog.path(".codex/agents").glob("*.toml")):
        try:
            tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            issues.append(
                ValidationIssue(path.relative_to(catalog.root).as_posix(), "invalid-toml", str(error))
            )
    for directory in ("agents", ".opencode/agents"):
        for path in sorted(catalog.path(directory).glob("*.md")):
            try:
                _frontmatter(path)
            except (ValueError, yaml.YAMLError) as error:
                issues.append(
                    ValidationIssue(
                        path.relative_to(catalog.root).as_posix(),
                        "invalid-frontmatter",
                        str(error),
                    )
                )
    return issues


def validate_assets(catalog: AssetCatalog) -> tuple[ValidationIssue, ...]:
    issues = [
        *_validate_manifests(catalog),
        *_validate_skills(catalog),
        *_validate_generated_agents(catalog),
    ]
    return tuple(sorted(issues, key=lambda issue: (issue.path, issue.code)))
```

Add targeted tests for a mismatched skill directory, duplicate skill name,
malformed Codex TOML, and stale generated agent. Each helper must return issues
without writing files.

- [ ] **Step 5: Run validation tests and the Codex plugin validator**

Run: `pixi run pytest tests/runtime/test_validate.py -v`

Expected: 2 passed.

Run the `plugin-creator` skill's `scripts/validate_plugin.py` against a temporary
copy of this checkout whose outer directory is named `waterology`. The staged
name satisfies the Codex validator without renaming the user's working copy.

Expected: valid plugin, complete fields, and no missing asset paths.

- [ ] **Step 6: Commit runtime manifests and validation**

```bash
git add .claude-plugin .codex-plugin src/waterology/runtime/validate.py tests/runtime/test_validate.py
git -c user.name=researcher -c user.email=researcher@example.org commit -S -m "feat: add codex plugin manifest"
```

### Task 6: Safe install planning

**Files:**
- Create: `src/waterology/runtime/install.py`
- Create: `tests/runtime/test_install_plan.py`

**Interfaces:**
- Consumes: `AssetCatalog` from Task 2
- Produces: `Runtime`, `InstallScope`, `InstallMode`, `InstallAction`, `InstallPlan`, and `build_install_plan(runtime, scope, target, mode, catalog) -> InstallPlan`

- [ ] **Step 1: Write failing destination and dry plan tests**

```python
from pathlib import Path

from waterology.runtime.assets import AssetCatalog
from waterology.runtime.install import (
    InstallMode,
    InstallScope,
    Runtime,
    build_install_plan,
)


def test_project_codex_plan_uses_shared_skills_and_codex_agents(tmp_path: Path) -> None:
    plan = build_install_plan(
        runtime=Runtime.CODEX,
        scope=InstallScope.PROJECT,
        target=tmp_path,
        mode=InstallMode.COPY,
        catalog=AssetCatalog.discover(),
    )

    destinations = {action.destination.relative_to(tmp_path).as_posix() for action in plan.actions}
    assert ".agents/skills/project-conventions" in destinations
    assert ".codex/agents/researcher.toml" in destinations
    assert all(action.operation == "copy" for action in plan.actions)


def test_project_claude_plan_keeps_command_shims(tmp_path: Path) -> None:
    plan = build_install_plan(
        runtime=Runtime.CLAUDE,
        scope=InstallScope.PROJECT,
        target=tmp_path,
        mode=InstallMode.LINK,
        catalog=AssetCatalog.discover(),
    )

    destinations = {action.destination.relative_to(tmp_path).as_posix() for action in plan.actions}
    assert ".claude/skills/deep-research" in destinations
    assert ".claude/agents/researcher.md" in destinations
    assert ".claude/commands/deepresearch.md" in destinations
    assert all(action.operation == "link" for action in plan.actions)


def test_project_opencode_plan_uses_v2_paths(tmp_path: Path) -> None:
    plan = build_install_plan(
        runtime=Runtime.OPENCODE,
        scope=InstallScope.PROJECT,
        target=tmp_path,
        mode=InstallMode.COPY,
        catalog=AssetCatalog.discover(),
    )

    destinations = {action.destination.relative_to(tmp_path).as_posix() for action in plan.actions}
    assert ".opencode/skills/project-conventions" in destinations
    assert ".opencode/agents/researcher.md" in destinations
```

- [ ] **Step 2: Run the focused tests and confirm install types are absent**

Run: `pixi run pytest tests/runtime/test_install_plan.py -v`

Expected: FAIL because `waterology.runtime.install` does not exist.

- [ ] **Step 3: Define install types**

```python
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Runtime(StrEnum):
    CLAUDE = "claude"
    CODEX = "codex"
    OPENCODE = "opencode"


class InstallScope(StrEnum):
    PROJECT = "project"
    USER = "user"


class InstallMode(StrEnum):
    COPY = "copy"
    LINK = "link"


@dataclass(frozen=True)
class InstallAction:
    source: Path
    source_id: str
    destination: Path
    operation: str
    manifest: Path


@dataclass(frozen=True)
class InstallPlan:
    runtime: Runtime
    scope: InstallScope
    mode: InstallMode
    actions: tuple[InstallAction, ...]
```

- [ ] **Step 4: Implement exact project and user destinations**

Use these destination mappings:

| Runtime | Project assets | User assets |
|---|---|---|
| Claude Code | `.claude/skills`, `.claude/agents`, `.claude/commands` | `~/.claude/skills`, `~/.claude/agents`, `~/.claude/commands` |
| Codex | `.agents/skills`, `.codex/agents` | `~/.agents/skills`, `~/.codex/agents` |
| OpenCode | `.opencode/skills`, `.opencode/agents` | `${XDG_CONFIG_HOME:-~/.config}/opencode/skills`, `${XDG_CONFIG_HOME:-~/.config}/opencode/agents` |

Use `Path.home()` only inside the `USER` branch. Resolve OpenCode's user base
from `XDG_CONFIG_HOME` when set and `Path.home() / ".config"` otherwise.

Each skill action uses the whole skill directory as its source and destination.
Each agent and command action uses one file. Place `.waterology-install.json`
beside the managed `skills`, `agents`, or `commands` directory and attach that
manifest path to each action. Set `source_id` to the source path relative to the
asset catalog root, with POSIX separators.

- [ ] **Step 5: Run install plan tests**

Run: `pixi run pytest tests/runtime/test_install_plan.py -v`

Expected: 3 passed.

- [ ] **Step 6: Commit install planning**

```bash
git add src/waterology/runtime/install.py tests/runtime/test_install_plan.py
git -c user.name=researcher -c user.email=researcher@example.org commit -S -m "feat: plan runtime asset installs"
```

### Task 7: Collision safe copy and link installation

**Files:**
- Modify: `src/waterology/runtime/install.py`
- Create: `tests/runtime/test_install_apply.py`

**Interfaces:**
- Consumes: `InstallPlan` from Task 6
- Produces: `preflight(plan, force=False) -> tuple[InstallConflict, ...]` and `apply_install_plan(plan, force=False) -> InstallResult`

- [ ] **Step 1: Write failing collision and ownership tests**

```python
import json
from pathlib import Path

import pytest

from waterology.runtime.assets import AssetCatalog
from waterology.runtime.install import (
    InstallConflictError,
    InstallMode,
    InstallScope,
    Runtime,
    apply_install_plan,
    build_install_plan,
)


def make_plan(tmp_path: Path, mode: InstallMode = InstallMode.COPY):
    return build_install_plan(
        Runtime.OPENCODE,
        InstallScope.PROJECT,
        tmp_path,
        mode,
        AssetCatalog.discover(),
    )


def test_copy_install_writes_manifest_and_assets(tmp_path: Path) -> None:
    result = apply_install_plan(make_plan(tmp_path))

    assert result.changed
    assert (tmp_path / ".opencode/agents/researcher.md").is_file()
    manifest = json.loads((tmp_path / ".opencode/.waterology-install.json").read_text())
    assert manifest["schema"] == 1
    assert manifest["waterology_version"] == "0.2.0"
    assert "agents/researcher.md" in manifest["assets"]


def test_unowned_destination_blocks_every_write(tmp_path: Path) -> None:
    collision = tmp_path / ".opencode/agents/researcher.md"
    collision.parent.mkdir(parents=True)
    collision.write_text("user-owned\n")

    with pytest.raises(InstallConflictError):
        apply_install_plan(make_plan(tmp_path))

    assert collision.read_text() == "user-owned\n"
    assert not (tmp_path / ".opencode/skills/project-conventions").exists()


def test_link_install_points_to_source_assets(tmp_path: Path) -> None:
    apply_install_plan(make_plan(tmp_path, InstallMode.LINK))

    installed = tmp_path / ".opencode/skills/project-conventions"
    assert installed.is_symlink()
    assert installed.resolve() == AssetCatalog.discover().path("skills/project-conventions")
```

- [ ] **Step 2: Run the focused tests and confirm apply functions are absent**

Run: `pixi run pytest tests/runtime/test_install_apply.py -v`

Expected: FAIL on missing `apply_install_plan` and related types.

- [ ] **Step 3: Implement manifest based preflight**

Use this manifest schema:

```json
{
  "schema": 1,
  "waterology_version": "0.2.0",
  "runtime": "opencode",
  "mode": "copy",
  "assets": {
    "agents/researcher.md": {
      "source": ".opencode/agents/researcher.md",
      "sha256": "hex digest",
      "kind": "file"
    }
  }
}
```

Use `kind` values `file`, `directory`, and `symlink`. A copied skill directory
uses `directory`; a linked file or directory uses `symlink`.

Preflight every action before writing. Permit a missing destination, an exact
copy already recorded in the manifest, or a symlink already recorded in the
manifest that points to the planned source. Treat every other existing path as
a conflict. `force=True` may replace a changed path only when the prior manifest
owns it. It must never replace an untracked path.

Define the result and error types before the function:

```python
@dataclass(frozen=True)
class InstallConflict:
    destination: Path
    reason: str


class InstallConflictError(RuntimeError):
    def __init__(self, conflicts: tuple[InstallConflict, ...]) -> None:
        self.conflicts = conflicts
        super().__init__("Install destinations conflict with existing files")


def preflight(plan: InstallPlan, force: bool = False) -> tuple[InstallConflict, ...]:
    conflicts: list[InstallConflict] = []
    records = _load_manifests(plan)
    for action in plan.actions:
        if not action.destination.exists() and not action.destination.is_symlink():
            continue
        key = action.destination.relative_to(action.manifest.parent).as_posix()
        prior = records.get(action.manifest, {}).get("assets", {}).get(key)
        if prior is None:
            conflicts.append(InstallConflict(action.destination, "destination is not owned"))
            continue
        unchanged_since_install = _fingerprint(action.destination) == prior["sha256"]
        if not unchanged_since_install and not force:
            conflicts.append(InstallConflict(action.destination, "owned destination was modified"))
    return tuple(conflicts)
```

`_fingerprint()` hashes one file directly. For directories, it hashes each
sorted relative file name, a null byte, and that file's bytes. For symlinks, it
hashes the resolved target path. `_load_manifests()` returns an empty record for
a missing manifest and rejects schema values other than `1`.

- [ ] **Step 4: Implement atomic application**

For copy mode, copy each file into a temporary sibling and finish with
`os.replace()`. Recursively copy skill directories into a temporary sibling
directory and finish with a rename. For link mode, create a temporary symlink
and rename it into place. Write each install manifest last through the same
temporary sibling pattern.

Return:

```python
@dataclass(frozen=True)
class InstallResult:
    changed: tuple[Path, ...]
    unchanged: tuple[Path, ...]
    manifests: tuple[Path, ...]
```

If preflight finds any conflict, raise `InstallConflictError(conflicts)` before
creating a directory or temporary file.

The top level function must start with the complete preflight:

```python
def apply_install_plan(plan: InstallPlan, force: bool = False) -> InstallResult:
    conflicts = preflight(plan, force=force)
    if conflicts:
        raise InstallConflictError(conflicts)
    changed, unchanged = _apply_actions(plan.actions)
    manifests = _write_install_manifests(plan)
    return InstallResult(tuple(changed), tuple(unchanged), tuple(manifests))
```

When replacing an owned directory, rename it to a temporary sibling, rename the
prepared directory into place, and restore the old directory if the second
rename fails. Remove the temporary backup only after the new directory is in
place.

- [ ] **Step 5: Run installation tests**

Run: `pixi run pytest tests/runtime/test_install_apply.py tests/runtime/test_install_plan.py -v`

Expected: 6 passed.

Run: `pixi run ruff check src/waterology/runtime/install.py tests/runtime/test_install_apply.py`

Expected: exit 0.

- [ ] **Step 6: Commit safe installation**

```bash
git add src/waterology/runtime/install.py tests/runtime/test_install_apply.py
git -c user.name=researcher -c user.email=researcher@example.org commit -S -m "feat: install runtime assets safely"
```

### Task 8: Install, render, and doctor commands

**Files:**
- Create: `src/waterology/runtime/doctor.py`
- Create: `tests/runtime/test_doctor.py`
- Create: `tests/test_install_cli.py`
- Modify: `src/waterology/cli.py`

**Interfaces:**
- Consumes: render, validation, and installation interfaces from Tasks 4 through 7
- Produces: `waterology render`, `waterology install`, `waterology doctor`, `Diagnostic`, and `run_diagnostics(catalog, runtime=None) -> tuple[Diagnostic, ...]`

- [ ] **Step 1: Write failing command tests**

```python
import json
from pathlib import Path

from typer.testing import CliRunner

from waterology.cli import app


runner = CliRunner()


def test_install_dry_run_json_makes_no_files(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "install",
            "opencode",
            "--target",
            str(tmp_path),
            "--dry-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["runtime"] == "opencode"
    assert payload["scope"] == "project"
    assert payload["dry_run"] is True
    assert not (tmp_path / ".opencode").exists()


def test_render_check_reports_current_generated_assets() -> None:
    result = runner.invoke(app, ["render", "--check"])
    assert result.exit_code == 0
    assert "Generated agents are current" in result.stdout


def test_doctor_json_reports_runtime_commands(monkeypatch, tmp_path: Path) -> None:
    codex = tmp_path / "bin" / "codex"
    monkeypatch.setattr("shutil.which", lambda name: str(codex) if name == "codex" else None)
    result = runner.invoke(app, ["doctor", "--json"])
    payload = json.loads(result.stdout)
    assert payload["assets"]["status"] == "pass"
    assert payload["runtimes"]["codex"]["status"] == "pass"
    assert payload["runtimes"]["claude"]["status"] == "warn"
```

- [ ] **Step 2: Run the command tests and observe missing commands**

Run: `pixi run pytest tests/test_install_cli.py tests/runtime/test_doctor.py -v`

Expected: FAIL because `install`, `render`, and `doctor` are not registered.

- [ ] **Step 3: Implement diagnostics**

```python
from dataclasses import dataclass
from shutil import which
from typing import Literal

from waterology.runtime.assets import AssetCatalog
from waterology.runtime.validate import validate_assets


@dataclass(frozen=True)
class Diagnostic:
    name: str
    status: Literal["pass", "warn", "fail"]
    message: str


def run_diagnostics(
    catalog: AssetCatalog,
    runtime: str | None = None,
) -> tuple[Diagnostic, ...]:
    diagnostics = []
    issues = validate_assets(catalog)
    diagnostics.append(
        Diagnostic(
            "assets",
            "fail" if issues else "pass",
            f"{len(issues)} asset validation issue(s)" if issues else "Assets are valid",
        )
    )
    for name in ("claude", "codex", "opencode"):
        path = which(name)
        required = runtime == name
        diagnostics.append(
            Diagnostic(
                f"runtime:{name}",
                "pass" if path else ("fail" if required else "warn"),
                path or f"{name} command was not found",
            )
        )
    return tuple(diagnostics)
```

- [ ] **Step 4: Wire exact CLI options**

Register:

```console
waterology render [--check]
waterology install <claude|codex|opencode|all> \
  [--scope project|user] [--target PATH] [--mode copy|link] \
  [--dry-run] [--force] [--json]
waterology doctor [--runtime claude|codex|opencode] [--json]
```

Default to `--scope project`, `--target .`, and `--mode copy`. Reject `--target`
with `--scope user`. `install all` must build and preflight all three plans
before applying any of them. Human output uses Rich tables. JSON output uses
`json.dumps(..., sort_keys=True)` and contains no Rich control sequences.

Exit codes:

- `0`: success, including optional missing runtimes in an unfiltered doctor run.
- `1`: validation failure, requested runtime missing, or install conflict.
- `2`: invalid CLI usage, left to Typer.

- [ ] **Step 5: Run command tests and the full Python suite**

Run: `pixi run pytest tests/test_install_cli.py tests/runtime/test_doctor.py -v`

Expected: all focused tests pass.

Run: `pixi run pytest -v`

Expected: all tests pass.

- [ ] **Step 6: Commit the commands**

```bash
git add src/waterology/cli.py src/waterology/runtime/doctor.py tests/test_install_cli.py tests/runtime/test_doctor.py
git -c user.name=researcher -c user.email=researcher@example.org commit -S -m "feat: add runtime install and doctor commands"
```

### Task 9: Canonical guidance and three-runtime documentation

**Files:**
- Create: `AGENTS.md`
- Modify: `.gitignore`
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Create: `tests/packaging/test_docs.py`

**Interfaces:**
- Consumes: the commands and paths implemented in Tasks 1 through 8
- Produces: one canonical guidance file and tested installation instructions for all three runtimes

- [ ] **Step 1: Write failing documentation contract tests**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_readme_documents_all_runtimes_and_cli() -> None:
    readme = (ROOT / "README.md").read_text()
    assert "Claude Code" in readme
    assert "Codex" in readme
    assert "OpenCode" in readme
    assert "waterology install all" in readme
    assert "waterology doctor" in readme


def test_claude_guidance_defers_to_agents() -> None:
    claude = (ROOT / "CLAUDE.md").read_text()
    assert len(claude.splitlines()) <= 20
    assert "AGENTS.md" in claude


def test_canonical_guidance_has_required_commands() -> None:
    agents = (ROOT / "AGENTS.md").read_text()
    assert "pixi run pytest" in agents
    assert "pixi run ruff check" in agents
    assert "waterology render --check" in agents
    assert "python3 constraints/check-all.py ." in agents
```

- [ ] **Step 2: Run the documentation tests and observe the Claude-only language**

Run: `pixi run pytest tests/packaging/test_docs.py -v`

Expected: FAIL because `AGENTS.md` is absent and the README describes only Claude Code.

- [ ] **Step 3: Create canonical repository guidance**

Write `AGENTS.md` with these sections and contracts:

- `Purpose`: Waterology serves Claude Code, Codex, and OpenCode.
- `Source layout`: root skills are canonical; `agent-definitions/` is canonical;
  runtime agent files are generated and must not be edited.
- `Development`: use Pixi and the four tested commands from Step 1.
- `TDD`: write a failing test before implementation.
- `Skill edits`: require `superpowers:writing-skills`, one skill at a time.
- `Attribution`: update the file header and `ATTRIBUTION.md` for adapted work.
- `Git`: signed commits, personal identity, no coauthor trailers, no push without
  permission.
- `Scope`: experiment storage, TORC, agent sessions, MCP, and dashboard belong
  to later plans.

Replace the `AGENTS.md` ignore rule with `!AGENTS.md` so the canonical root file
is tracked. Keep personal runtime state ignored.

- [ ] **Step 4: Reduce `CLAUDE.md` to a thin adapter**

Keep only a pointer to `AGENTS.md`, the Claude plugin locations
`.claude-plugin/`, `agents/`, and `commands/`, and the local Claude marketplace
verification command. Do not repeat general development or attribution rules.

- [ ] **Step 5: Rewrite the README introduction and installation section**

Lead with Waterology as a research workflow package for all three runtimes.
Document:

```console
pixi install
pixi run waterology install claude
pixi run waterology install codex
pixi run waterology install opencode
pixi run waterology install all --dry-run
pixi run waterology doctor
```

Keep the current Claude marketplace instructions under a `Claude Code plugin`
subsection. Add Codex manifest and OpenCode project directory explanations with
links to the official
[Codex plugin documentation](https://developers.openai.com/plugins/concepts/plugins),
[OpenCode skills documentation](https://opencode.ai/docs/skills), and
[OpenCode agent documentation](https://opencode.ai/v2/docs/agents).

State the Slice 1 boundary plainly: packaging and agents support all three
runtimes; command backed skill bodies become runtime neutral in the next slice.

- [ ] **Step 6: Update the roadmap and run documentation tests**

Add the approved six platform slices at the top of `ROADMAP.md`. Mark the cross
runtime foundation complete only after Task 10 passes. Retain the existing
research feature roadmap below it.

Run: `pixi run pytest tests/packaging/test_docs.py -v`

Expected: 3 passed.

Run: `python3 constraints/check-all.py .`

Expected: all repository constraints pass.

- [ ] **Step 7: Commit documentation and guidance**

```bash
git add .gitignore AGENTS.md CLAUDE.md README.md ROADMAP.md tests/packaging/test_docs.py
git -c user.name=researcher -c user.email=researcher@example.org commit -S -m "docs: describe three-runtime waterology package"
```

### Task 10: Wheel, install, and repository acceptance

**Files:**
- Create: `tests/packaging/test_wheel.py`
- Modify: `ROADMAP.md`

**Interfaces:**
- Consumes: the complete Slice 1 implementation
- Produces: a wheel containing every declared asset and evidence that each runtime receives valid files

- [ ] **Step 1: Write a failing wheel content test**

```python
import zipfile
from pathlib import Path

from build import ProjectBuilder


ROOT = Path(__file__).resolve().parents[2]


def test_wheel_contains_cross_runtime_assets(tmp_path: Path) -> None:
    wheel = Path(ProjectBuilder(ROOT).build("wheel", tmp_path))
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    required = {
        "waterology_assets/skills/project-conventions/SKILL.md",
        "waterology_assets/agents/researcher.md",
        "waterology_assets/.codex/agents/researcher.toml",
        "waterology_assets/.opencode/agents/researcher.md",
        "waterology_assets/.claude-plugin/plugin.json",
        "waterology_assets/.codex-plugin/plugin.json",
        "waterology_assets/ATTRIBUTION.md",
    }
    assert required <= names
```

- [ ] **Step 2: Run the wheel test and confirm missing or mislocated assets**

Run: `pixi run pytest tests/packaging/test_wheel.py -v`

Expected: FAIL until Hatchling includes every mapped source and generated directory.

- [ ] **Step 3: Correct wheel mappings without duplicating canonical sources**

Adjust only `[tool.hatch.build.targets.wheel.force-include]`. Keep root
`skills/` and `agent-definitions/` canonical. Do not add hand copied asset trees
under `src/`.

- [ ] **Step 4: Add isolated project install smoke tests**

```python
import json
import tomllib

import pytest
import yaml
from typer.testing import CliRunner

from waterology.cli import app


runner = CliRunner()


@pytest.mark.parametrize(
    ("runtime", "agent_path", "skill_path"),
    [
        ("claude", ".claude/agents/researcher.md", ".claude/skills/project-conventions"),
        ("codex", ".codex/agents/researcher.toml", ".agents/skills/project-conventions"),
        ("opencode", ".opencode/agents/researcher.md", ".opencode/skills/project-conventions"),
    ],
)
def test_project_install_smoke(
    tmp_path: Path,
    runtime: str,
    agent_path: str,
    skill_path: str,
) -> None:
    result = runner.invoke(app, ["install", runtime, "--target", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / skill_path / "SKILL.md").is_file()
    installed_agent = tmp_path / agent_path
    if installed_agent.suffix == ".toml":
        assert tomllib.loads(installed_agent.read_text())["name"] == "researcher"
    else:
        assert yaml.safe_load(installed_agent.read_text().split("---", 2)[1])


def test_all_runtime_dry_run_is_json_and_read_only(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["install", "all", "--target", str(tmp_path), "--dry-run", "--json"],
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout)["dry_run"] is True
    assert list(tmp_path.iterdir()) == []
```

Extend the smoke test to read each `.waterology-install.json` file and assert
that its `assets` keys cover every destination created under the same runtime
root. Also assert that Claude installs `commands/deepresearch.md`.

- [ ] **Step 5: Run complete acceptance checks**

Run: `pixi run waterology render --check`

Expected: `Generated agents are current`.

Run: `pixi run waterology doctor --json`

Expected: asset status `pass`; missing optional runtime commands may report
`warn`.

Run: `pixi run ruff check .`

Expected: exit 0.

Run: `pixi run pytest -v`

Expected: all tests pass.

Run: `python3 constraints/check-all.py .`

Expected: all repository constraints pass.

Run: `git diff --check`

Expected: no output.

- [ ] **Step 6: Mark the foundation slice complete and commit acceptance**

Mark only the cross runtime foundation complete in `ROADMAP.md`. Leave research
method migration, OpenResearch adaptation, experiment storage, TORC, sessions,
MCP, and dashboard slices open.

```bash
git add ROADMAP.md tests/packaging/test_wheel.py pyproject.toml
git -c user.name=researcher -c user.email=researcher@example.org commit -S -m "test: verify cross-runtime package"
```

## Slice 1 acceptance

The plan is complete when:

1. `waterology --version` reports `0.2.0`.
2. Claude Code continues to load its existing skills, agents, and commands.
3. Codex recognizes `.codex-plugin/plugin.json` and its generated TOML agents.
4. OpenCode receives V2 Markdown agents and Agent Skills in supported paths.
5. `waterology install` supports safe project or user copy and link modes.
6. Install preflight checks every destination before writing and never replaces unowned files.
7. `waterology render --check` detects stale generated agents.
8. `waterology doctor` reports asset and runtime status in human and JSON forms.
9. The built wheel contains the canonical skills and all runtime adapters.
10. Tests, Ruff, repository constraints, and signed commit verification pass.

The next plan will migrate command backed workflows into self contained Agent
Skills and adapt the remaining portable OpenResearch skills. It must invoke
`superpowers:writing-skills`, run a failing baseline with a fresh subagent before
each skill edit, retest that skill after the edit, and commit each verified
skill before starting the next.
