import json
import time
from collections.abc import Callable

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.auth.tokens import (
    AuthServiceUnavailableError,
    InvalidTokenError,
    TokenVerifier,
)
from app.config import Settings, load_settings
from app.main import create_app

SUPABASE_URL = "https://test-project.supabase.co"
ISSUER = f"{SUPABASE_URL}/auth/v1"
KEY_ID = "test-signing-key"
USER_A_ID = "11111111-1111-4111-8111-111111111111"
USER_A_EMAIL = "user.a@example.com"

TokenFactory = Callable[..., str]


class FakeSessionChecker:
    def __init__(self) -> None:
        self.revoked_tokens: set[str] = set()
        self.unavailable = False
        self.checked_tokens: list[str] = []

    def ensure_active(self, token: str) -> None:
        self.checked_tokens.append(token)
        if self.unavailable:
            raise AuthServiceUnavailableError("supabase auth timed out")
        if token in self.revoked_tokens:
            raise InvalidTokenError("session_not_found")


class StaticJWKClient(jwt.PyJWKClient):
    def __init__(self, jwks: dict) -> None:
        super().__init__("https://jwks.invalid/.well-known/jwks.json")
        self._jwks = jwks

    def fetch_data(self) -> dict:
        return self._jwks


def public_jwks(private_key: ec.EllipticCurvePrivateKey, kid: str = KEY_ID) -> dict:
    jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(private_key.public_key()))
    jwk.update(kid=kid, alg="ES256", use="sig")
    return {"keys": [jwk]}


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "ENVIRONMENT",
        "DATABASE_URL",
        "CORS_ORIGINS",
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(scope="session")
def signing_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def make_token(signing_key: ec.EllipticCurvePrivateKey) -> TokenFactory:
    def factory(
        private_key: ec.EllipticCurvePrivateKey | None = None,
        kid: str = KEY_ID,
        **claim_overrides: object,
    ) -> str:
        now = int(time.time())
        claims: dict[str, object] = {
            "sub": USER_A_ID,
            "email": USER_A_EMAIL,
            "aud": "authenticated",
            "role": "authenticated",
            "iss": ISSUER,
            "iat": now,
            "exp": now + 3600,
        }
        claims.update(claim_overrides)
        claims = {key: value for key, value in claims.items() if value is not None}
        return jwt.encode(
            claims,
            private_key or signing_key,
            algorithm="ES256",
            headers={"kid": kid},
        )

    return factory


@pytest.fixture
def settings() -> Settings:
    return load_settings(
        _env_file=None,
        environment="test",
        database_url="postgresql://user:pass@localhost:5432/reviewlens_test",
        cors_origins="http://localhost:5173",
        supabase_url=SUPABASE_URL,
        supabase_publishable_key="sb_publishable_test_key",
    )


@pytest.fixture
def session_checker() -> FakeSessionChecker:
    return FakeSessionChecker()


@pytest.fixture
def token_verifier(
    signing_key: ec.EllipticCurvePrivateKey, session_checker: FakeSessionChecker
) -> TokenVerifier:
    return TokenVerifier(
        StaticJWKClient(public_jwks(signing_key)), ISSUER, session_checker
    )


@pytest.fixture
def client(settings: Settings, token_verifier: TokenVerifier) -> TestClient:
    return TestClient(create_app(settings, token_verifier=token_verifier))
