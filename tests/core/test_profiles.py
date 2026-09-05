from pathlib import Path

import pytest
from pydantic import ValidationError

from waterology.core.profiles import (
    ComputeProfile,
    MachineConfig,
    MachineConfigError,
    load_machine_config,
    machine_config_path,
    trust_profile,
)


def test_machine_config_path_prefers_explicit_then_xdg(tmp_path: Path) -> None:
    explicit = tmp_path / "explicit.toml"
    xdg = tmp_path / "xdg"

    assert machine_config_path({"WATEROLOGY_CONFIG": str(explicit)}) == explicit
    assert machine_config_path({"XDG_CONFIG_HOME": str(xdg)}) == (
        xdg / "waterology" / "config.toml"
    )


def test_load_machine_config_parses_torc_profiles(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """\
trusted_profiles = ["cluster"]

[profiles.local]
provider = "torc"
mode = "local"
api_url = "http://localhost:8080/torc-service/v1"

[profiles.cluster]
provider = "torc"
mode = "slurm"
api_url = "http://control.example:8085/torc-service/v1"
torc_profile = "cluster"
slurm_account = "project-123"
dashboard_url = "http://localhost:8085/dashboard"

[profiles.worker]
provider = "torc"
mode = "remote"
api_url = "http://control.example:8085/torc-service/v1"
ssh_alias = "worker"
access_group_id = 2
""",
        encoding="utf-8",
    )

    config = load_machine_config(path)

    assert config.profile("local").mode == "local"
    assert config.profile("cluster").trusted is True
    assert config.profile("cluster").slurm_account == "project-123"
    assert config.profile("worker").access_group_id == 2
    assert config.profile("cluster").dashboard_url == "http://localhost:8085/dashboard"


def test_remote_profile_requires_ssh_alias() -> None:
    with pytest.raises(ValidationError, match="ssh_alias"):
        ComputeProfile(mode="remote", api_url="http://localhost:8080")


def test_access_group_is_only_supported_for_remote_profiles() -> None:
    with pytest.raises(ValidationError, match="only supported for remote profiles"):
        ComputeProfile(mode="local", api_url="http://localhost:8080", access_group_id=2)


@pytest.mark.parametrize(
    "api_url",
    [
        "http://localhost:8080/torc-service/v1",
        "http://127.0.0.1:8080/torc-service/v1",
        "http://[::1]:8080/torc-service/v1",
    ],
)
def test_remote_profile_rejects_loopback_api_url(api_url: str) -> None:
    with pytest.raises(ValidationError, match="routable TORC API URL"):
        ComputeProfile(mode="remote", api_url=api_url, ssh_alias="worker-a")


def test_slurm_profile_rejects_loopback_api_url() -> None:
    with pytest.raises(ValidationError, match="routable TORC API URL"):
        ComputeProfile(
            mode="slurm",
            api_url="http://localhost:8080/torc-service/v1",
            slurm_account="project-123",
        )


def test_slurm_profile_requires_account() -> None:
    with pytest.raises(ValidationError, match="slurm_account"):
        ComputeProfile(mode="slurm", api_url="http://localhost:8080")


def test_machine_config_rejects_credentials() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        MachineConfig.model_validate(
            {
                "profiles": {
                    "bad": {
                        "provider": "torc",
                        "mode": "local",
                        "api_url": "http://localhost:8080",
                        "token": "secret",
                    }
                }
            }
        )


@pytest.mark.parametrize(
    "api_url",
    [
        "https://host/torc-service/v1?token=secret",
        "https://host/torc-service/v1#secret",
        "https://host/torc service/v1",
    ],
)
def test_machine_config_rejects_credential_bearing_or_unsafe_urls(api_url: str) -> None:
    with pytest.raises(ValidationError):
        ComputeProfile(mode="local", api_url=api_url)


def test_machine_config_rejects_unsafe_profile_name() -> None:
    with pytest.raises(ValidationError, match="invalid compute profile names"):
        MachineConfig.model_validate(
            {
                "profiles": {
                    "../cluster": {
                        "provider": "torc",
                        "mode": "slurm",
                        "api_url": "http://control.example:8080",
                        "slurm_account": "project-123",
                    }
                }
            }
        )


def test_trust_profile_is_atomic_and_preserves_profiles(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """\
[profiles.cluster]
provider = "torc"
mode = "slurm"
api_url = "http://control.example:8085/torc-service/v1"
torc_profile = "cluster"
slurm_account = "project-123"
""",
        encoding="utf-8",
    )

    trusted = trust_profile(path, "cluster")

    assert trusted.profile("cluster").trusted is True
    assert load_machine_config(path).profiles["cluster"].torc_profile == "cluster"
    assert load_machine_config(path).profiles["cluster"].slurm_account == "project-123"
    assert not (tmp_path / ".config.toml.tmp").exists()


def test_trust_profile_does_not_follow_predictable_temporary_symlink(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    victim = tmp_path / "victim.txt"
    victim.write_text("keep\n", encoding="utf-8")
    path.write_text(
        '[profiles.local]\nmode = "local"\napi_url = "http://localhost:8080"\n',
        encoding="utf-8",
    )
    (tmp_path / ".config.toml.tmp").symlink_to(victim)

    trust_profile(path, "local")

    assert victim.read_text(encoding="utf-8") == "keep\n"


def test_machine_config_normalizes_relative_output_root(tmp_path: Path) -> None:
    path = tmp_path / "machine" / "config.toml"
    path.parent.mkdir()
    path.write_text(
        """\
[profiles.local]
mode = "local"
api_url = "http://localhost:8080"
local_output_root = "outputs"
""",
        encoding="utf-8",
    )

    profile = load_machine_config(path).profile("local")

    assert profile.local_output_root == str((path.parent / "outputs").absolute())


def test_missing_machine_config_or_profile_has_stable_error(tmp_path: Path) -> None:
    assert load_machine_config(tmp_path / "missing.toml") == MachineConfig()
    with pytest.raises(MachineConfigError, match="does not exist"):
        MachineConfig().profile("missing")
