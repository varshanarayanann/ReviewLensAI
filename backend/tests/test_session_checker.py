import io
import urllib.error
import urllib.request

import pytest

from app.auth.tokens import (
    AuthServiceUnavailableError,
    InvalidTokenError,
    SupabaseSessionChecker,
)

AUTH_URL = "https://test-project.supabase.co/auth/v1"


@pytest.fixture
def checker() -> SupabaseSessionChecker:
    return SupabaseSessionChecker(AUTH_URL, "sb_publishable_test_key")


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        f"{AUTH_URL}/user", code, "error", {}, io.BytesIO(b"{}")
    )


def test_active_session_passes_and_sends_key_and_token(
    monkeypatch: pytest.MonkeyPatch, checker: SupabaseSessionChecker
) -> None:
    sent: list[urllib.request.Request] = []

    def fake_urlopen(request, timeout):
        sent.append(request)
        return io.BytesIO(b'{"id": "user-a"}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    checker.ensure_active("access-token")

    assert sent[0].full_url == f"{AUTH_URL}/user"
    assert sent[0].get_header("Apikey") == "sb_publishable_test_key"
    assert sent[0].get_header("Authorization") == "Bearer access-token"


@pytest.mark.parametrize("code", [401, 403])
def test_rejected_session_is_an_invalid_token(
    monkeypatch: pytest.MonkeyPatch, checker: SupabaseSessionChecker, code: int
) -> None:
    def fake_urlopen(request, timeout):
        raise http_error(code)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(InvalidTokenError):
        checker.ensure_active("access-token")


@pytest.mark.parametrize(
    "failure",
    [http_error(500), urllib.error.URLError("dns failure"), TimeoutError()],
    ids=["server-error", "unreachable", "timeout"],
)
def test_supabase_outage_is_reported_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    checker: SupabaseSessionChecker,
    failure: Exception,
) -> None:
    def fake_urlopen(request, timeout):
        raise failure

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(AuthServiceUnavailableError):
        checker.ensure_active("access-token")
