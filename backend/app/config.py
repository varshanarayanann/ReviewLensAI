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

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


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
