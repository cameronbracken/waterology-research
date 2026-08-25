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
    assert all("Task tool" not in agent.body for agent in agents)
    assert all("`Bash`" not in agent.body for agent in agents)
    assert all(chr(0x2014) not in agent.body for agent in agents)
