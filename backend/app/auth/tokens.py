from dataclasses import dataclass
from typing import Protocol

import jwt

SUPABASE_AUDIENCE = "authenticated"
ALLOWED_ALGORITHMS = ["ES256", "RS256"]


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None


class InvalidTokenError(Exception):
    pass


class AuthServiceUnavailableError(Exception):
    pass


class SigningKeySource(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK: ...


class TokenVerifier:
    def __init__(self, signing_keys: SigningKeySource, issuer: str) -> None:
        self._signing_keys = signing_keys
        self._issuer = issuer

    @classmethod
    def for_supabase(cls, jwks_url: str, issuer: str) -> "TokenVerifier":
        return cls(jwt.PyJWKClient(jwks_url, cache_keys=True, timeout=5), issuer)

    def verify(self, token: str) -> CurrentUser:
        try:
            signing_key = self._signing_keys.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=ALLOWED_ALGORITHMS,
                audience=SUPABASE_AUDIENCE,
                issuer=self._issuer,
                options={"require": ["exp", "sub", "aud", "iss"]},
            )
        except jwt.PyJWKClientConnectionError as exc:
            raise AuthServiceUnavailableError(str(exc)) from exc
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc

        return CurrentUser(id=claims["sub"], email=claims.get("email"))
