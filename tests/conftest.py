import pytest


@pytest.fixture(autouse=True)
def isolated_machine_config(tmp_path_factory, monkeypatch):
    """Keep tests away from the user's machine config and credentials file."""
    config = tmp_path_factory.mktemp("machine-config") / "config.toml"
    config.write_text('[credentials]\nfile = ""\n')
    monkeypatch.setenv("WATEROLOGY_CONFIG", str(config))
