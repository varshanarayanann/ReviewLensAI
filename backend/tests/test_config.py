import pytest

from app.config import ConfigurationError, load_settings
from app.db import to_sqlalchemy_url

REQUIRED = {
    "database_url": "postgresql://localhost/db",
    "cors_origins": "http://localhost:5173",
    "supabase_url": "https://test-project.supabase.co",
    "supabase_publishable_key": "sb_publishable_test_key",
}


def settings_with(**overrides: object):
    return load_settings(_env_file=None, **{**REQUIRED, **overrides})


def test_settings_parse_comma_separated_cors_origins() -> None:
    settings = settings_with(
        cors_origins="http://localhost:5173, https://reviewlens.netlify.app"
    )

    assert settings.cors_origins == [
        "http://localhost:5173",
        "https://reviewlens.netlify.app",
    ]
    assert settings.environment == "local"


def test_settings_read_values_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://env-host/db")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("SUPABASE_URL", "https://env-project.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_env_key")

    settings = load_settings(_env_file=None)

    assert settings.database_url.get_secret_value() == "postgresql://env-host/db"
    assert settings.supabase_url == "https://env-project.supabase.co"


def test_database_url_is_hidden_when_settings_are_printed() -> None:
    settings = settings_with(
        database_url="postgresql://app:sup3r-s3cret@db.example.com:5432/postgres"
    )

    for rendered in (str(settings), repr(settings), str(settings.model_dump())):
        assert "sup3r-s3cret" not in rendered
    assert "sup3r-s3cret" in settings.database_url.get_secret_value()


def test_empty_database_url_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        settings_with(database_url="")


def test_missing_required_settings_fail_with_clear_message() -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        load_settings(_env_file=None)

    message = str(exc_info.value)
    for name in (
        "DATABASE_URL",
        "CORS_ORIGINS",
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
    ):
        assert name in message
    assert "backend/.env.example" in message


def test_invalid_environment_name_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="ENVIRONMENT"):
        settings_with(environment="staging")


@pytest.mark.parametrize("value", ["", "test-project.supabase.co", "ftp://x.co"])
def test_invalid_supabase_url_is_rejected(value: str) -> None:
    with pytest.raises(ConfigurationError, match="SUPABASE_URL"):
        settings_with(supabase_url=value)


def test_supabase_secret_key_is_rejected_as_publishable_key() -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        settings_with(supabase_publishable_key="sb_secret_do-not-use")

    assert "SUPABASE_PUBLISHABLE_KEY" in str(exc_info.value)
    assert "do-not-use" not in str(exc_info.value)


def test_supabase_auth_urls_are_derived_from_project_url() -> None:
    settings = settings_with(supabase_url="https://abc.supabase.co/")

    assert settings.supabase_auth_issuer == "https://abc.supabase.co/auth/v1"
    assert (
        settings.supabase_jwks_url
        == "https://abc.supabase.co/auth/v1/.well-known/jwks.json"
    )


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("postgresql://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ],
)
def test_database_url_uses_psycopg_driver(url: str, expected: str) -> None:
    assert to_sqlalchemy_url(url) == expected
