# src/api/main.py
"""
LLM Gateway POC — FastAPI Application Factory.
Registers routes, middleware, and startup/shutdown lifecycle.
"""

from dotenv import load_dotenv
load_dotenv()  # Load .env before any os.getenv() calls

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.auth import AuthMiddleware
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.routes import route as route_module
from src.api.routes import health as health_module
from src.api.routes import analytics as analytics_module
from src.gateway.router import GatewayRouter


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the GatewayRouter once on startup; share via app.state."""
    app.state.gateway = GatewayRouter()
    print("\n[OK]  LLM Gateway POC started.")
    print("[>>]  Swagger UI  -> http://localhost:8000/docs")
    print("[>>]  ReDoc       -> http://localhost:8000/redoc")
    print("[>>]  Health      -> http://localhost:8000/health")
    print("[KEY] Demo keys   -> free-key-001 | basic-key-001 | pro-key-001 | enterprise-key-001\n")
    yield
    print("[--]  LLM Gateway shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="LLM Gateway POC",
        description=(
            "Intelligent LLM routing with NFR-based model selection, "
            "semantic caching, multi-level failover, and analytics.\n\n"
            "---\n\n"
            "### Demo API Keys\n"
            "Pass as `Authorization: Bearer {key}`\n\n"
            "| Key | Tier | Models Available |\n"
            "|-----|------|------------------|\n"
            "| `free-key-001` | free | gpt-3.5-turbo, claude-3-haiku, gemini-pro, gemini-flash |\n"
            "| `basic-key-001` | basic | + gpt-4-turbo, claude-3-sonnet |\n"
            "| `pro-key-001` | pro | + gpt-4, claude-3-opus |\n"
            "| `enterprise-key-001` | enterprise | all models |\n\n"
            "### NFR Parameters\n"
            "Pass in request body `nfr` field or via headers:\n"
            "- `X-NFR-Latency`: `low` | `medium` | `high`\n"
            "- `X-NFR-Cost`: `low` | `medium` | `high`\n"
            "- `X-NFR-Accuracy`: `standard` | `high` | `critical`\n"
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS — permit all origins for local POC
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Auth — must be added AFTER CORSMiddleware
    app.add_middleware(AuthMiddleware)

    # Rate limiting — must be added AFTER AuthMiddleware (needs request.state.tier)
    app.add_middleware(RateLimitMiddleware)

    # Routers
    app.include_router(health_module.router,    tags=["health"])
    app.include_router(route_module.router,     prefix="/api/v1", tags=["gateway"])
    app.include_router(analytics_module.router, prefix="/api/v1", tags=["analytics"])

    return app


app = create_app()
