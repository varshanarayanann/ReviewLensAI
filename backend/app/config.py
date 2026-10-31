from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class ConfigurationError(RuntimeError):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["local", "test", "production"] = "local"
    database_url: SecretStr = Field(min_length=1)
    cors_origins: Annotated[list[str], NoDecode] = Field(min_length=1)
    supabase_url: str = Field(pattern=r"^https?://[^\s/]+")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("supabase_url", mode="before")
    @classmethod
    def strip_trailing_slash(cls, value: object) -> object:
        return value.strip().rstrip("/") if isinstance(value, str) else value

    @property
    def supabase_auth_issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1"

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_auth_issuer}/.well-known/jwks.json"


def load_settings(**overrides: object) -> Settings:
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        fields = ", ".join(
            str(error["loc"][0]).upper() for error in exc.errors() if error["loc"]
        )
        raise ConfigurationError(
            f"Missing or invalid configuration: {fields}. "
            "Copy backend/.env.example to backend/.env and fill in the values."
        ) from None


@lru_cache
def get_settings() -> Settings:
    return load_settings()
