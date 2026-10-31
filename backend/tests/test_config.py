import pytest

from app.config import ConfigurationError, load_settings
from app.db import to_sqlalchemy_url


def test_settings_parse_comma_separated_cors_origins() -> None:
    settings = load_settings(
        _env_file=None,
        database_url="postgresql://localhost/db",
        cors_origins="http://localhost:5173, https://reviewlens.netlify.app",
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

    settings = load_settings(_env_file=None)

    assert settings.database_url.get_secret_value() == "postgresql://env-host/db"


def test_database_url_is_hidden_when_settings_are_printed() -> None:
    settings = load_settings(
        _env_file=None,
        database_url="postgresql://app:sup3r-s3cret@db.example.com:5432/postgres",
        cors_origins="http://localhost:5173",
    )

    for rendered in (str(settings), repr(settings), str(settings.model_dump())):
        assert "sup3r-s3cret" not in rendered
    assert "sup3r-s3cret" in settings.database_url.get_secret_value()


def test_empty_database_url_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="DATABASE_URL"):
        load_settings(
            _env_file=None, database_url="", cors_origins="http://localhost:5173"
        )


def test_missing_required_settings_fail_with_clear_message() -> None:
    with pytest.raises(ConfigurationError) as exc_info:
        load_settings(_env_file=None)

    message = str(exc_info.value)
    assert "DATABASE_URL" in message
    assert "CORS_ORIGINS" in message
    assert "backend/.env.example" in message


def test_invalid_environment_name_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="ENVIRONMENT"):
        load_settings(
            _env_file=None,
            environment="staging",
            database_url="postgresql://localhost/db",
            cors_origins="http://localhost:5173",
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
