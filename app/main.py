from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.charge_management import router as charge_management_router
from app.operations import readiness


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

    @app.get("/ready", tags=["Operations"], include_in_schema=False, response_model=None)
    def ready():
        try:
            readiness.check_database_readiness()
        except readiness.DatabaseReadinessError:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "checks": {"database": "unavailable"},
                },
            )
        return {"status": "ok", "checks": {"database": "ok"}}

    web_directory = os.getenv("LEDGERFLOW_WEB_DIRECTORY", "").strip()
    if web_directory:
        resolved_web_directory = Path(web_directory).expanduser().resolve()
        if not resolved_web_directory.is_dir():
            raise RuntimeError(
                f"LEDGERFLOW_WEB_DIRECTORY is not a directory: {resolved_web_directory}"
            )
        app.mount(
            "/",
            StaticFiles(directory=resolved_web_directory, html=True),
            name="ledgerflow-web",
        )

    return app


app = create_app()
