import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.auth.tokens import TokenVerifier
from app.main import create_app
from tests.conftest import (
    ISSUER,
    USER_A_EMAIL,
    USER_A_ID,
    FakeSessionChecker,
    StaticJWKClient,
    TokenFactory,
)


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def assert_unauthenticated(response) -> None:
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Authentication required."}
    assert USER_A_ID not in response.text
    assert USER_A_EMAIL not in response.text


def test_valid_token_returns_the_supabase_user(
    client: TestClient, make_token: TokenFactory
) -> None:
    response = client.get("/api/me", headers=auth_header(make_token()))

    assert response.status_code == 200
    assert response.json() == {"id": USER_A_ID, "email": USER_A_EMAIL}


def test_missing_authorization_header_is_rejected(client: TestClient) -> None:
    assert_unauthenticated(client.get("/api/me"))


def test_non_bearer_authorization_is_rejected(client: TestClient) -> None:
    response = client.get("/api/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})

    assert_unauthenticated(response)


def test_malformed_token_is_rejected(client: TestClient) -> None:
    assert_unauthenticated(client.get("/api/me", headers=auth_header("not-a-jwt")))


def test_expired_token_is_rejected(
    client: TestClient, make_token: TokenFactory
) -> None:
    token = make_token(exp=int(time.time()) - 60)

    assert_unauthenticated(client.get("/api/me", headers=auth_header(token)))


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "anon"},
        {"iss": "https://another-project.supabase.co/auth/v1"},
        {"sub": None},
    ],
    ids=["anon-audience", "other-project-issuer", "missing-subject"],
)
def test_tokens_with_wrong_claims_are_rejected(
    client: TestClient, make_token: TokenFactory, overrides: dict
) -> None:
    token = make_token(**overrides)

    assert_unauthenticated(client.get("/api/me", headers=auth_header(token)))


def test_token_signed_by_another_key_is_rejected(
    client: TestClient, make_token: TokenFactory
) -> None:
    attacker_key = ec.generate_private_key(ec.SECP256R1())
    token = make_token(private_key=attacker_key)

    assert_unauthenticated(client.get("/api/me", headers=auth_header(token)))


def test_token_with_unknown_key_id_is_rejected(
    client: TestClient, make_token: TokenFactory
) -> None:
    token = make_token(kid="unknown-key")

    assert_unauthenticated(client.get("/api/me", headers=auth_header(token)))


def test_symmetric_hs256_token_is_rejected(client: TestClient) -> None:
    token = jwt.encode(
        {
            "sub": USER_A_ID,
            "aud": "authenticated",
            "iss": ISSUER,
            "exp": int(time.time()) + 3600,
        },
        "guessed-shared-secret-value-of-sufficient-length",
        algorithm="HS256",
        headers={"kid": "test-signing-key"},
    )

    assert_unauthenticated(client.get("/api/me", headers=auth_header(token)))


def test_client_supplied_user_id_is_ignored(
    client: TestClient, make_token: TokenFactory
) -> None:
    other_user = "22222222-2222-4222-8222-222222222222"

    response = client.get(
        f"/api/me?user_id={other_user}",
        headers={**auth_header(make_token()), "X-User-Id": other_user},
    )

    assert response.status_code == 200
    assert response.json()["id"] == USER_A_ID


def test_unreachable_signing_keys_return_503_without_details(
    settings, make_token: TokenFactory
) -> None:
    class UnreachableJWKClient(StaticJWKClient):
        def fetch_data(self) -> dict:
            raise jwt.PyJWKClientConnectionError("connection refused to jwks host")

    verifier = TokenVerifier(UnreachableJWKClient({}), ISSUER, FakeSessionChecker())
    client = TestClient(create_app(settings, token_verifier=verifier))

    response = client.get("/api/me", headers=auth_header(make_token()))

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Authentication service is unavailable. Try again shortly."
    }
    assert "jwks" not in response.text


def test_token_from_a_logged_out_session_is_rejected(
    client: TestClient,
    make_token: TokenFactory,
    session_checker: FakeSessionChecker,
) -> None:
    token = make_token()
    assert client.get("/api/me", headers=auth_header(token)).status_code == 200

    session_checker.revoked_tokens.add(token)

    assert_unauthenticated(client.get("/api/me", headers=auth_header(token)))


def test_session_check_outage_returns_503_without_details(
    client: TestClient,
    make_token: TokenFactory,
    session_checker: FakeSessionChecker,
) -> None:
    session_checker.unavailable = True

    response = client.get("/api/me", headers=auth_header(make_token()))

    assert response.status_code == 503
    assert "timed out" not in response.text
    assert USER_A_EMAIL not in response.text


def test_invalid_tokens_are_rejected_before_contacting_supabase(
    client: TestClient,
    make_token: TokenFactory,
    session_checker: FakeSessionChecker,
) -> None:
    expired = make_token(exp=int(time.time()) - 60)

    client.get("/api/me", headers=auth_header(expired))
    client.get("/api/me", headers=auth_header("not-a-jwt"))

    assert session_checker.checked_tokens == []


def test_health_endpoint_stays_public(client: TestClient) -> None:
    assert client.get("/api/health").status_code == 200
