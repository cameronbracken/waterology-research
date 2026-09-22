import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from waterology.cli import app
from waterology.runtime.install import Runtime
from waterology.runtime.mcp import registration_command, runtime_mcp_config

ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def test_claude_and_codex_plugins_share_stdio_registration() -> None:
    registration = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    codex = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    codex_project = (ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")

    assert registration == {"mcpServers": {"waterology": {"command": "waterology-mcp"}}}
    assert codex["mcpServers"] == "./.mcp.json"
    assert codex_project == '[mcp_servers.waterology]\ncommand = "waterology-mcp"\n'


def test_opencode_project_config_uses_current_v2_shape() -> None:
    config = json.loads((ROOT / "opencode.json").read_text(encoding="utf-8"))

    assert config["mcp"]["waterology"] == {
        "type": "local",
        "command": ["waterology-mcp"],
        "cwd": ".",
        "enabled": True,
    }


def test_runtime_config_snippets_contain_no_machine_paths_or_environment() -> None:
    for runtime in (Runtime.CLAUDE, Runtime.CODEX, Runtime.OPENCODE):
        config = runtime_mcp_config(runtime)
        serialized = json.dumps(config, sort_keys=True)
        assert "waterology-mcp" in serialized
        assert str(Path.home()) not in serialized
        assert "environment" not in serialized


def test_pi_mcp_registration_is_explicitly_unsupported() -> None:
    with pytest.raises(ValueError, match="no built-in MCP"):
        runtime_mcp_config(Runtime.PI)

    result = runner.invoke(app, ["mcp", "config", "pi", "--json"])

    assert result.exit_code == 2
    assert "no built-in MCP" in result.output


def test_registration_commands_use_supported_runtime_interfaces() -> None:
    assert registration_command(Runtime.CLAUDE) == (
        "claude",
        "mcp",
        "add",
        "--transport",
        "stdio",
        "--scope",
        "project",
        "waterology",
        "--",
        "waterology-mcp",
    )
    assert registration_command(Runtime.CODEX) is None
    assert registration_command(Runtime.OPENCODE) is None
    assert registration_command(Runtime.PI) is None


def test_mcp_config_cli_prints_machine_neutral_runtime_snippet() -> None:
    result = runner.invoke(app, ["mcp", "config", "opencode", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["runtime"] == "opencode"
    assert payload["config"]["mcp"]["waterology"]["cwd"] == "."
    assert payload["command"] is None
