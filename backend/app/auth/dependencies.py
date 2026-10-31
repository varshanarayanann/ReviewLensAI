import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.tokens import (
    AuthServiceUnavailableError,
    CurrentUser,
    InvalidTokenError,
    TokenVerifier,
)

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


def get_token_verifier(request: Request) -> TokenVerifier:
    return request.app.state.token_verifier


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    verifier: TokenVerifier = Depends(get_token_verifier),
) -> CurrentUser:
    if credentials is None:
        raise _unauthenticated()

    try:
        return verifier.verify(credentials.credentials)
    except InvalidTokenError as exc:
        logger.info("Rejected access token: %s", exc)
        raise _unauthenticated() from None
    except AuthServiceUnavailableError:
        logger.exception("Could not fetch Supabase signing keys")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is unavailable. Try again shortly.",
        ) from None


def _unauthenticated() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
