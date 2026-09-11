"""Optional personal settings, kept outside distributable runtime assets."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IdentitySettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = ""
    email: str = ""
    git_name: str = ""
    orcid: str = ""


class GuidanceSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    files: tuple[str, ...] = ()

    @field_validator("files")
    @classmethod
    def valid_files(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() or "\x00" in value for value in values):
            raise ValueError("Guidance paths must be nonempty")
        return values


class WritingSettings(GuidanceSettings):
    papers: tuple[str, ...] = ()


class DashboardSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    profile: str = ""
    host: str = "127.0.0.1"
    llm_provider: str = ""
    openai_base_url: str = ""
    openai_model: str = ""
    api_key_env: str = ""
    torc_password_keychain_service: str = ""


class UserSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    identity: IdentitySettings = Field(default_factory=IdentitySettings)
    preferences: GuidanceSettings = Field(default_factory=GuidanceSettings)
    writing: WritingSettings = Field(default_factory=WritingSettings)
    guidance: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    dashboard: DashboardSettings = Field(default_factory=DashboardSettings)

    @field_validator("guidance")
    @classmethod
    def valid_guidance(cls, values: dict[str, tuple[str, ...]]) -> dict[str, tuple[str, ...]]:
        for paths in values.values():
            GuidanceSettings(files=paths)
        return values
