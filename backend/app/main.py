import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, me
from app.auth.tokens import TokenVerifier
from app.config import Settings, get_settings


def create_app(
    settings: Settings | None = None, token_verifier: TokenVerifier | None = None
) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO)

    app = FastAPI(
        title="ReviewLens AI API",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.token_verifier = token_verifier or TokenVerifier.for_supabase(
        settings.supabase_jwks_url, settings.supabase_auth_issuer
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(me.router)
    return app
