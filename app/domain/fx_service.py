from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ChargeFxRateRow, ChargeFxRateSourceRow
from app.domain.models import (
    FxRate,
    FxRateListResponse,
    FxRatePayload,
    FxRateResolution,
    FxRateResolveRequest,
    FxRateSource,
    FxRateSourceListResponse,
    FxRateSourcePayload,
)


class FxRateService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_sources(
        self,
        *,
        search: str | None = None,
        active_only: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> FxRateSourceListResponse:
        statement = select(ChargeFxRateSourceRow)
        if active_only is not None:
            statement = statement.where(ChargeFxRateSourceRow.is_active.is_(active_only))
        if search:
            term = f"%{search.strip().lower()}%"
            statement = statement.where(
                func.lower(ChargeFxRateSourceRow.source_code).like(term)
                | func.lower(ChargeFxRateSourceRow.source_name).like(term)
            )
        total = self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        rows = self.db.scalars(
            statement.order_by(
                ChargeFxRateSourceRow.priority,
                ChargeFxRateSourceRow.source_code,
            ).offset(offset).limit(limit)
        ).all()
        return FxRateSourceListResponse(
            items=[self._source_model(row) for row in rows],
            total=int(total),
            limit=limit,
            offset=offset,
        )

    def create_source(self, payload: FxRateSourcePayload) -> FxRateSource:
        values = self._source_values(payload)
        duplicate = self.db.scalar(
            select(ChargeFxRateSourceRow).where(
                func.upper(ChargeFxRateSourceRow.source_code) == values["source_code"]
            )
        )
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="FX rate source_code already exists.")
        row = ChargeFxRateSourceRow(**values)
        self.db.add(row)
        self.db.flush()
        return self._source_model(row)

    def get_source(self, source_id: int) -> FxRateSource:
        return self._source_model(self._require_source(source_id))

    def update_source(self, source_id: int, payload: FxRateSourcePayload) -> FxRateSource:
        row = self._require_source(source_id)
        values = self._source_values(payload)
        duplicate = self.db.scalar(
            select(ChargeFxRateSourceRow).where(
                func.upper(ChargeFxRateSourceRow.source_code) == values["source_code"],
                ChargeFxRateSourceRow.id != source_id,
            )
        )
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="FX rate source_code already exists.")
        for key, value in values.items():
            setattr(row, key, value)
        self.db.flush()
        return self._source_model(row)

    def deactivate_source(self, source_id: int) -> FxRateSource:
        row = self._require_source(source_id)
        row.is_active = False
        self.db.flush()
        return self._source_model(row)

    def list_rates(
        self,
        *,
        source_id: int | None = None,
        source_currency: str | None = None,
        target_currency: str | None = None,
        rate_date_from: object | None = None,
        rate_date_to: object | None = None,
        rate_type: str | None = None,
        conversion_method: str | None = None,
        active_only: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> FxRateListResponse:
        statement = select(ChargeFxRateRow).join(ChargeFxRateSourceRow)
        if source_id is not None:
            statement = statement.where(ChargeFxRateRow.source_id == source_id)
        if source_currency:
            statement = statement.where(ChargeFxRateRow.source_currency == self._currency(source_currency))
        if target_currency:
            statement = statement.where(ChargeFxRateRow.target_currency == self._currency(target_currency))
        if rate_date_from is not None:
            statement = statement.where(ChargeFxRateRow.rate_date >= rate_date_from)
        if rate_date_to is not None:
            statement = statement.where(ChargeFxRateRow.rate_date <= rate_date_to)
        if rate_type:
            statement = statement.where(ChargeFxRateRow.rate_type == self._rate_type(rate_type))
        if conversion_method:
            statement = statement.where(ChargeFxRateRow.conversion_method == self._method(conversion_method))
        if active_only is not None:
            statement = statement.where(ChargeFxRateRow.is_active.is_(active_only))
            if active_only:
                statement = statement.where(ChargeFxRateSourceRow.is_active.is_(True))
        total = self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        rows = self.db.scalars(
            statement.order_by(
                ChargeFxRateRow.rate_date.desc(),
                ChargeFxRateSourceRow.priority,
                ChargeFxRateRow.id.desc(),
            ).offset(offset).limit(limit)
        ).all()
        return FxRateListResponse(
            items=[self._rate_model(row) for row in rows],
            total=int(total),
            limit=limit,
            offset=offset,
        )

    def create_rate(self, payload: FxRatePayload) -> FxRate:
        source = self._require_source(payload.source_id)
        if not source.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="FX rate source is inactive.")
        values = self._rate_values(payload)
        self._assert_unique_rate(values)
        row = ChargeFxRateRow(**values)
        self.db.add(row)
        self.db.flush()
        return self._rate_model(row, source=source)

    def get_rate(self, rate_id: int) -> FxRate:
        return self._rate_model(self._require_rate(rate_id))

    def update_rate(self, rate_id: int, payload: FxRatePayload) -> FxRate:
        row = self._require_rate(rate_id)
        source = self._require_source(payload.source_id)
        if not source.is_active and payload.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="FX rate source is inactive.")
        values = self._rate_values(payload)
        self._assert_unique_rate(values, exclude_id=rate_id)
        for key, value in values.items():
            setattr(row, key, value)
        self.db.flush()
        return self._rate_model(row, source=source)

    def deactivate_rate(self, rate_id: int) -> FxRate:
        row = self._require_rate(rate_id)
        row.is_active = False
        self.db.flush()
        return self._rate_model(row)

    def resolve(self, payload: FxRateResolveRequest) -> FxRateResolution:
        source_currency = self._currency(payload.source_currency)
        target_currency = self._currency(payload.target_currency)
        if source_currency == target_currency:
            return FxRateResolution(
                effective_rate=Decimal("1"),
                converted_amount=payload.amount,
                requested_rate_date=payload.rate_date,
                selected_rate_date=payload.rate_date,
            )

        source_id = payload.source_id
        if payload.source_code:
            source = self.db.scalar(
                select(ChargeFxRateSourceRow).where(
                    func.upper(ChargeFxRateSourceRow.source_code) == payload.source_code.strip().upper()
                )
            )
            if source is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FX rate source was not found.")
            if source_id is not None and source_id != source.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="source_id and source_code identify different FX rate sources.",
                )
            source_id = source.id

        direct = self._resolve_row(
            source_currency=source_currency,
            target_currency=target_currency,
            payload=payload,
            source_id=source_id,
        )
        inverse_applied = False
        selected = direct
        if selected is None and payload.allow_inverse:
            selected = self._resolve_row(
                source_currency=target_currency,
                target_currency=source_currency,
                payload=payload,
                source_id=source_id,
            )
            inverse_applied = selected is not None
        if selected is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active FX rate matched the requested currency pair and date.",
            )

        stored_rate = Decimal(str(selected.rate))
        effective_rate = Decimal("1") / stored_rate if inverse_applied else stored_rate
        return FxRateResolution(
            rate=self._rate_model(selected),
            effective_rate=effective_rate,
            converted_amount=payload.amount * effective_rate,
            requested_rate_date=payload.rate_date,
            selected_rate_date=selected.rate_date,
            inverse_applied=inverse_applied,
        )

    def _resolve_row(
        self,
        *,
        source_currency: str,
        target_currency: str,
        payload: FxRateResolveRequest,
        source_id: int | None,
    ) -> ChargeFxRateRow | None:
        statement = (
            select(ChargeFxRateRow)
            .join(ChargeFxRateSourceRow)
            .where(
                ChargeFxRateRow.source_currency == source_currency,
                ChargeFxRateRow.target_currency == target_currency,
                ChargeFxRateRow.rate_type == payload.rate_type,
                ChargeFxRateRow.is_active.is_(True),
                ChargeFxRateSourceRow.is_active.is_(True),
            )
        )
        if payload.allow_prior_date:
            statement = statement.where(ChargeFxRateRow.rate_date <= payload.rate_date)
        else:
            statement = statement.where(ChargeFxRateRow.rate_date == payload.rate_date)
        if source_id is not None:
            statement = statement.where(ChargeFxRateRow.source_id == source_id)
        if payload.conversion_method:
            statement = statement.where(
                ChargeFxRateRow.conversion_method == self._method(payload.conversion_method)
            )
        return self.db.scalar(
            statement.order_by(
                ChargeFxRateRow.rate_date.desc(),
                ChargeFxRateSourceRow.priority,
                ChargeFxRateRow.id.desc(),
            ).limit(1)
        )

    def _assert_unique_rate(self, values: dict[str, object], *, exclude_id: int | None = None) -> None:
        statement = select(ChargeFxRateRow).where(
            ChargeFxRateRow.source_id == values["source_id"],
            ChargeFxRateRow.source_currency == values["source_currency"],
            ChargeFxRateRow.target_currency == values["target_currency"],
            ChargeFxRateRow.rate_date == values["rate_date"],
            ChargeFxRateRow.rate_type == values["rate_type"],
            ChargeFxRateRow.conversion_method == values["conversion_method"],
        )
        if exclude_id is not None:
            statement = statement.where(ChargeFxRateRow.id != exclude_id)
        if self.db.scalar(statement) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An FX rate already exists for this source, pair, date, type, and method.",
            )

    def _require_source(self, source_id: int) -> ChargeFxRateSourceRow:
        row = self.db.get(ChargeFxRateSourceRow, source_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FX rate source was not found.")
        return row

    def _require_rate(self, rate_id: int) -> ChargeFxRateRow:
        row = self.db.get(ChargeFxRateRow, rate_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FX rate was not found.")
        return row

    @staticmethod
    def _source_values(payload: FxRateSourcePayload) -> dict[str, object]:
        code = payload.source_code.strip().upper()
        name = payload.source_name.strip()
        timezone = payload.timezone.strip()
        if not code or not name or not timezone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_code, source_name, and timezone are required.",
            )
        if payload.priority < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="priority cannot be negative.")
        return {
            "source_code": code,
            "source_name": name,
            "provider_url": payload.provider_url.strip() if payload.provider_url else None,
            "timezone": timezone,
            "priority": payload.priority,
            "is_active": payload.is_active,
            "metadata_json": dict(payload.metadata_json),
        }

    def _rate_values(self, payload: FxRatePayload) -> dict[str, object]:
        source_currency = self._currency(payload.source_currency)
        target_currency = self._currency(payload.target_currency)
        if source_currency == target_currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FX source_currency and target_currency must differ.",
            )
        if payload.rate <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="FX rate must be positive.")
        return {
            "source_id": payload.source_id,
            "source_currency": source_currency,
            "target_currency": target_currency,
            "rate_date": payload.rate_date,
            "rate": payload.rate,
            "rate_type": self._rate_type(payload.rate_type),
            "conversion_method": self._method(payload.conversion_method),
            "is_active": payload.is_active,
            "metadata_json": dict(payload.metadata_json),
        }

    @staticmethod
    def _currency(value: str) -> str:
        currency = value.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Currencies must be three-letter alphabetic codes.",
            )
        return currency

    @staticmethod
    def _rate_type(value: str) -> str:
        rate_type = value.strip().upper()
        if rate_type not in {"MID", "BUY", "SELL", "CUSTOM"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported FX rate_type.")
        return rate_type

    @staticmethod
    def _method(value: str) -> str:
        method = value.strip().upper()
        if not method:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="conversion_method is required.")
        return method

    @staticmethod
    def _source_model(row: ChargeFxRateSourceRow) -> FxRateSource:
        return FxRateSource(
            id=row.id,
            source_code=row.source_code,
            source_name=row.source_name,
            provider_url=row.provider_url,
            timezone=row.timezone,
            priority=row.priority,
            is_active=row.is_active,
            metadata_json=dict(row.metadata_json or {}),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _rate_model(
        self,
        row: ChargeFxRateRow,
        *,
        source: ChargeFxRateSourceRow | None = None,
    ) -> FxRate:
        source = source or row.source
        return FxRate(
            id=row.id,
            source_id=row.source_id,
            source_code=source.source_code,
            source_name=source.source_name,
            source_currency=row.source_currency,
            target_currency=row.target_currency,
            rate_date=row.rate_date,
            rate=row.rate,
            rate_type=row.rate_type,
            conversion_method=row.conversion_method,
            is_active=row.is_active,
            metadata_json=dict(row.metadata_json or {}),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
