import urllib.error
import urllib.request
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


class SessionChecker(Protocol):
    def ensure_active(self, token: str) -> None: ...


class SupabaseSessionChecker:
    """Asks Supabase Auth whether the token's session still exists.

    A signature check alone keeps accepting a token until it expires, even after
    the user logs out; Supabase rejects tokens whose session was signed out.
    """

    def __init__(self, auth_url: str, api_key: str, timeout: float = 5) -> None:
        self._user_url = f"{auth_url}/user"
        self._api_key = api_key
        self._timeout = timeout

    def ensure_active(self, token: str) -> None:
        request = urllib.request.Request(
            self._user_url,
            headers={"apikey": self._api_key, "Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout):
                return
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise InvalidTokenError(
                    f"Supabase rejected the session ({exc.code})"
                ) from exc
            raise AuthServiceUnavailableError(
                f"Supabase Auth returned {exc.code}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise AuthServiceUnavailableError(str(exc)) from exc


class TokenVerifier:
    def __init__(
        self,
        signing_keys: SigningKeySource,
        issuer: str,
        session_checker: SessionChecker,
    ) -> None:
        self._signing_keys = signing_keys
        self._issuer = issuer
        self._session_checker = session_checker

    @classmethod
    def for_supabase(cls, jwks_url: str, issuer: str, api_key: str) -> "TokenVerifier":
        return cls(
            jwt.PyJWKClient(jwks_url, cache_keys=True, timeout=5),
            issuer,
            SupabaseSessionChecker(issuer, api_key),
        )

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

        self._session_checker.ensure_active(token)
        return CurrentUser(id=claims["sub"], email=claims.get("email"))
