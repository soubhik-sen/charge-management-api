from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.charge_management import router as charge_management_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Charge Management API",
        version="0.1.0",
        description=(
            "Adapter-neutral Charge Management API for rate books, contracts, "
            "quote ranking, charge documents, invoice matching, and export readiness."
        ),
    )
    app.include_router(
        charge_management_router,
        prefix="/api/v1/charge-management",
        tags=["Charge Management"],
    )
    return app


app = create_app()
