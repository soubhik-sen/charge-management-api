from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.charge_management import router as charge_management_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Charge Management API",
        version="0.2.0",
        description=(
            "Adapter-neutral Charge Management API for rate books, contracts, "
            "quote ranking, allocation/date profiles, FX rates, charge documents, "
            "invoice matching, and export readiness."
        ),
    )
    allowed_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(
        charge_management_router,
        prefix="/api/v1/charge-management",
        tags=["Charge Management"],
    )

    @app.get("/health", tags=["Operations"], include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
