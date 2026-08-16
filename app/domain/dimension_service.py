from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    ChargeCallerMappingProfileRow,
    ChargePricingDimensionRow,
    ChargeQuoteRequestRow,
    ChargeRateBookRow,
)
from app.domain.models import (
    CallerAttributeMapping,
    CallerMappingPreviewResponse,
    CallerMappingProfile,
    CallerMappingProfileListResponse,
    CallerMappingProfilePayload,
    PricingDimension,
    PricingDimensionListResponse,
    PricingDimensionPayload,
    QuoteRequestCreate,
    QuoteRequestWorkspaceUpdate,
    RateBookEntryPayload,
    RateBookPayload,
)


BUILT_IN_DIMENSIONS = (
    (1, "ORIGIN_CODE", "Origin", "origin_code"),
    (2, "DESTINATION_CODE", "Destination", "destination_code"),
    (3, "TRANSPORT_MODE", "Transport mode", "mode"),
    (4, "EQUIPMENT_TYPE", "Equipment type", "equipment_type"),
    (5, "COMMODITY_CODE", "Commodity", "commodity_code"),
    (6, "SERVICE_LEVEL", "Service level", "service_level"),
    (7, "CHARGE_CONTEXT", "Charge context", "charge_context"),
)
BUILT_IN_CODE_BY_FIELD = {field: code for _, code, _, field in BUILT_IN_DIMENSIONS}


def seed_system_dimensions(db: Session) -> None:
    existing = {
        code
        for code in db.scalars(select(ChargePricingDimensionRow.dimension_code)).all()
    }
    for row_id, code, name, field in BUILT_IN_DIMENSIONS:
        if code in existing:
            continue
        db.add(
            ChargePricingDimensionRow(
                id=row_id,
                dimension_code=code,
                dimension_name=name,
                description=f"Built-in LedgerFlow applicability dimension mapped to {field}.",
                data_type="STRING",
                built_in_field=field,
                allowed_values_json=[],
                case_sensitive=False,
                is_system=True,
                is_active=True,
            )
        )
    db.flush()


class PricingDimensionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_dimensions(
        self,
        *,
        search: str | None = None,
        active_only: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> PricingDimensionListResponse:
        statement = select(ChargePricingDimensionRow)
        if active_only is not None:
            statement = statement.where(ChargePricingDimensionRow.is_active.is_(active_only))
        if search:
            term = f"%{search.strip().lower()}%"
            statement = statement.where(
                func.lower(ChargePricingDimensionRow.dimension_code).like(term)
                | func.lower(ChargePricingDimensionRow.dimension_name).like(term)
            )
        total = self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        rows = self.db.scalars(
            statement.order_by(
                ChargePricingDimensionRow.is_system.desc(),
                ChargePricingDimensionRow.dimension_code,
            ).offset(offset).limit(limit)
        ).all()
        return PricingDimensionListResponse(
            items=[self._dimension_model(row) for row in rows],
            total=int(total),
            limit=limit,
            offset=offset,
        )

    def create_dimension(self, payload: PricingDimensionPayload) -> PricingDimension:
        values = self._dimension_values(payload)
        duplicate = self.db.scalar(
            select(ChargePricingDimensionRow).where(
                func.upper(ChargePricingDimensionRow.dimension_code) == values["dimension_code"]
            )
        )
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Dimension code already exists.")
        row = ChargePricingDimensionRow(
            **values,
            built_in_field=None,
            is_system=False,
        )
        self.db.add(row)
        self._flush_unique("Dimension code already exists.")
        return self._dimension_model(row)

    def update_dimension(self, dimension_id: int, payload: PricingDimensionPayload) -> PricingDimension:
        row = self._require_dimension(dimension_id)
        values = self._dimension_values(payload)
        if row.is_system and values["dimension_code"] != row.dimension_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="System dimension codes are immutable.",
            )
        if row.is_system and values["data_type"] != row.data_type:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="System dimension data types are immutable.",
            )
        in_use = self._dimension_in_use(row.dimension_code)
        structural_change = (
            values["dimension_code"] != row.dimension_code
            or values["data_type"] != row.data_type
            or values["allowed_values_json"] != list(row.allowed_values_json or [])
            or values["case_sensitive"] != row.case_sensitive
            or not values["is_active"]
        )
        if in_use and structural_change:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A dimension used by a rate book or caller mapping can only change its name or description.",
            )
        duplicate = self.db.scalar(
            select(ChargePricingDimensionRow).where(
                func.upper(ChargePricingDimensionRow.dimension_code) == values["dimension_code"],
                ChargePricingDimensionRow.id != dimension_id,
            )
        )
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Dimension code already exists.")
        for key, value in values.items():
            setattr(row, key, value)
        self._flush_unique("Dimension code already exists.")
        return self._dimension_model(row)

    def deactivate_dimension(self, dimension_id: int) -> PricingDimension:
        row = self._require_dimension(dimension_id)
        if row.is_system:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Built-in dimensions cannot be deactivated.",
            )
        if self._dimension_in_use(row.dimension_code):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Dimension is used by a rate book or active caller mapping profile.",
            )
        row.is_active = False
        self.db.flush()
        return self._dimension_model(row)

    def list_profiles(
        self,
        *,
        caller_system_code: str | None = None,
        schema_version: str | None = None,
        active_only: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> CallerMappingProfileListResponse:
        statement = select(ChargeCallerMappingProfileRow)
        if caller_system_code:
            statement = statement.where(
                ChargeCallerMappingProfileRow.caller_system_code
                == caller_system_code.strip().upper()
            )
        if schema_version:
            statement = statement.where(
                ChargeCallerMappingProfileRow.schema_version == schema_version.strip()
            )
        if active_only is not None:
            statement = statement.where(ChargeCallerMappingProfileRow.is_active.is_(active_only))
        total = self.db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        rows = self.db.scalars(
            statement.order_by(
                ChargeCallerMappingProfileRow.caller_system_code,
                ChargeCallerMappingProfileRow.schema_version,
                ChargeCallerMappingProfileRow.profile_code,
            ).offset(offset).limit(limit)
        ).all()
        return CallerMappingProfileListResponse(
            items=[self._profile_model(row) for row in rows],
            total=int(total),
            limit=limit,
            offset=offset,
        )

    def create_profile(self, payload: CallerMappingProfilePayload) -> CallerMappingProfile:
        values = self._profile_values(payload)
        duplicate = self.db.scalar(
            select(ChargeCallerMappingProfileRow).where(
                func.upper(ChargeCallerMappingProfileRow.profile_code) == values["profile_code"]
            )
        )
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mapping profile code already exists.")
        row = ChargeCallerMappingProfileRow(**values)
        self.db.add(row)
        self._flush_unique("Mapping profile code already exists.")
        return self._profile_model(row)

    def update_profile(
        self,
        profile_id: int,
        payload: CallerMappingProfilePayload,
    ) -> CallerMappingProfile:
        row = self._require_profile(profile_id)
        values = self._profile_values(payload)
        if self._profile_in_use(row.profile_code) and any(
            values[field] != getattr(row, field)
            for field in (
                "profile_code",
                "caller_system_code",
                "schema_version",
                "mappings_json",
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A mapping profile used by a quote is immutable; create a new "
                    "profile code for the new caller schema."
                ),
            )
        duplicate = self.db.scalar(
            select(ChargeCallerMappingProfileRow).where(
                func.upper(ChargeCallerMappingProfileRow.profile_code) == values["profile_code"],
                ChargeCallerMappingProfileRow.id != profile_id,
            )
        )
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Mapping profile code already exists.")
        for key, value in values.items():
            setattr(row, key, value)
        self._flush_unique("Mapping profile code already exists.")
        return self._profile_model(row)

    def deactivate_profile(self, profile_id: int) -> CallerMappingProfile:
        row = self._require_profile(profile_id)
        row.is_active = False
        self.db.flush()
        return self._profile_model(row)

    def preview_profile(
        self,
        profile_id: int,
        caller_attributes: dict[str, Any],
    ) -> CallerMappingPreviewResponse:
        profile = self._require_profile(profile_id)
        dimensions = self._dimension_rows_by_code(active_only=True)
        values = self._apply_profile(profile, caller_attributes, dimensions)
        standard_fields = {
            dimensions[code].built_in_field: value
            for code, value in values.items()
            if dimensions[code].built_in_field is not None
        }
        return CallerMappingPreviewResponse(
            profile_code=profile.profile_code,
            caller_system_code=profile.caller_system_code,
            schema_version=profile.schema_version,
            dimension_values=values,
            standard_fields=standard_fields,
        )

    def normalize_quote_payload(
        self,
        payload: QuoteRequestCreate | QuoteRequestWorkspaceUpdate,
        *,
        quote_request_id: int | None = None,
    ) -> QuoteRequestCreate | QuoteRequestWorkspaceUpdate:
        dimension_input_fields = {
            "caller_system_code",
            "caller_schema_version",
            "caller_mapping_profile_code",
            "caller_attributes",
            "dimension_values",
            *BUILT_IN_CODE_BY_FIELD.keys(),
        }
        if isinstance(payload, QuoteRequestWorkspaceUpdate) and not (
            payload.model_fields_set & dimension_input_fields
        ):
            return payload
        existing = self.db.get(ChargeQuoteRequestRow, quote_request_id) if quote_request_id else None
        updates: dict[str, Any] = {}
        dimensions = self._dimension_rows_by_code(active_only=True)
        canonical_values = dict(existing.dimension_values_json or {}) if existing is not None else {}
        if "dimension_values" in payload.model_fields_set:
            for raw_code, raw_value in (payload.dimension_values or {}).items():
                code = str(raw_code).strip().upper()
                if raw_value is None:
                    canonical_values.pop(code, None)
                    continue
                canonical_values.update(
                    self._normalize_dimension_values({code: raw_value}, dimensions)
                )
        profile: ChargeCallerMappingProfileRow | None = None
        profile_value = payload.caller_mapping_profile_code
        if "caller_mapping_profile_code" not in payload.model_fields_set and existing is not None:
            profile_value = existing.caller_mapping_profile_code
        profile_code = (profile_value or "").strip().upper()
        caller_attributes = (
            payload.caller_attributes
            if "caller_attributes" in payload.model_fields_set
            else (dict(existing.caller_attributes_json or {}) if existing is not None else {})
        ) or {}
        if profile_code:
            profile = self.db.scalar(
                select(ChargeCallerMappingProfileRow).where(
                    func.upper(ChargeCallerMappingProfileRow.profile_code) == profile_code
                )
            )
            if profile is None:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Caller mapping profile was not found.")
            if not profile.is_active:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Caller mapping profile is inactive.")
            caller_system = payload.caller_system_code
            if "caller_system_code" not in payload.model_fields_set and existing is not None:
                caller_system = existing.caller_system_code
            caller_schema = payload.caller_schema_version
            if "caller_schema_version" not in payload.model_fields_set and existing is not None:
                caller_schema = existing.caller_schema_version
            if caller_system and caller_system.strip().upper() != profile.caller_system_code:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="caller_system_code does not match the mapping profile.")
            if caller_schema and caller_schema.strip() != profile.schema_version:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="caller_schema_version does not match the mapping profile.")
            mapped_values = self._apply_profile(profile, caller_attributes, dimensions)
            for code, value in mapped_values.items():
                if code in canonical_values and canonical_values[code] != value:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Mapped and explicit values conflict for dimension {code}.",
                    )
                canonical_values[code] = value
            updates.update(
                caller_mapping_profile_code=profile.profile_code,
                caller_system_code=profile.caller_system_code,
                caller_schema_version=profile.schema_version,
            )
        elif "caller_attributes" in payload.model_fields_set and caller_attributes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="caller_mapping_profile_code is required when caller_attributes are supplied.",
            )
        else:
            caller_system = payload.caller_system_code
            if "caller_system_code" not in payload.model_fields_set and existing is not None:
                caller_system = existing.caller_system_code
            caller_schema = payload.caller_schema_version
            if "caller_schema_version" not in payload.model_fields_set and existing is not None:
                caller_schema = existing.caller_schema_version
            normalized_system = (caller_system or "").strip().upper()
            normalized_schema = (caller_schema or "").strip()
            if bool(normalized_system) != bool(normalized_schema):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="caller_system_code and caller_schema_version must be supplied together.",
                )
            if normalized_system:
                updates["caller_system_code"] = normalized_system
                updates["caller_schema_version"] = normalized_schema

        for code, dimension in dimensions.items():
            field = dimension.built_in_field
            if field is None:
                continue
            explicit = field in payload.model_fields_set
            current = getattr(payload, field, None)
            if not explicit and existing is not None:
                current = getattr(existing, field, None)
            if explicit and current in (None, ""):
                canonical_values.pop(code, None)
                updates[field] = None
                continue
            if code in canonical_values:
                if explicit and current not in (None, ""):
                    normalized_current = self._normalize_value(dimension, current)
                    if normalized_current != canonical_values[code]:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Explicit {field} conflicts with dimension {code}.",
                        )
                updates[field] = canonical_values[code]
            elif current not in (None, ""):
                canonical_values[code] = self._normalize_value(dimension, current)
                updates[field] = canonical_values[code]

        updates["dimension_values"] = canonical_values
        if "caller_attributes" in payload.model_fields_set or profile is not None:
            updates["caller_attributes"] = dict(caller_attributes)
        return payload.model_copy(update=updates)

    def _dimension_in_use(self, dimension_code: str) -> bool:
        code = dimension_code.strip().upper()
        for book in self.db.scalars(select(ChargeRateBookRow)).all():
            if code in {str(item).strip().upper() for item in list(book.dimension_codes_json or [])}:
                return True
        for profile in self.db.scalars(
            select(ChargeCallerMappingProfileRow).where(
                ChargeCallerMappingProfileRow.is_active.is_(True)
            )
        ).all():
            if any(
                str(mapping.get("dimension_code", "")).strip().upper() == code
                for mapping in list(profile.mappings_json or [])
            ):
                return True
        return False

    def _profile_in_use(self, profile_code: str) -> bool:
        return self.db.scalar(
            select(ChargeQuoteRequestRow.id).where(
                func.upper(ChargeQuoteRequestRow.caller_mapping_profile_code)
                == profile_code.strip().upper()
            ).limit(1)
        ) is not None

    def normalize_rate_book_payload(self, payload: RateBookPayload) -> RateBookPayload:
        dimensions = self._dimension_rows_by_code(active_only=True)
        dimension_codes = list(payload.dimension_codes)
        for code in dimension_codes:
            dimension = dimensions.get(code)
            if dimension is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown or inactive pricing dimension: {code}.",
                )
            if dimension.built_in_field:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Built-in dimension {code} must use row_attribute_keys field "
                        f"{dimension.built_in_field}."
                    ),
                )

        entries: list[RateBookEntryPayload] = []
        for entry in payload.entries:
            values = self._normalize_dimension_values(entry.dimension_values, dimensions)
            outside = sorted(set(values) - set(dimension_codes))
            if outside:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Rate-row dimensions are not selected on the rate book: " + ", ".join(outside),
                )
            entries.append(entry.model_copy(update={"dimension_values": values}))
        return payload.model_copy(
            update={
                "dimension_codes": dimension_codes,
                "entries": entries,
            }
        )

    def _profile_values(self, payload: CallerMappingProfilePayload) -> dict[str, Any]:
        profile_code = payload.profile_code.strip().upper()
        profile_name = payload.profile_name.strip()
        caller_system_code = payload.caller_system_code.strip().upper()
        schema_version = payload.schema_version.strip()
        if not profile_code or not profile_name or not caller_system_code or not schema_version:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Profile code, name, caller system, and schema version are required.",
            )
        if not all(character.isalnum() or character in {"_", "-"} for character in profile_code):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Profile code must use letters, numbers, underscores, and hyphens.",
            )
        if payload.is_active and not payload.mappings:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="An active caller mapping profile requires at least one mapping.",
            )
        dimensions = self._dimension_rows_by_code(active_only=True)
        normalized_mappings: list[dict[str, Any]] = []
        sources: set[str] = set()
        targets: set[str] = set()
        for item in payload.mappings:
            source_attribute = item.source_attribute.strip()
            dimension_code = item.dimension_code.strip().upper()
            if not source_attribute:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Mapping source_attribute must not be blank.")
            if dimension_code not in dimensions:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unknown or inactive pricing dimension: {dimension_code}.")
            if source_attribute in sources:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Duplicate source attribute: {source_attribute}.")
            if dimension_code in targets:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Duplicate target dimension: {dimension_code}.")
            sources.add(source_attribute)
            targets.add(dimension_code)
            dimension = dimensions[dimension_code]
            default_value = (
                self._normalize_value(dimension, item.default_value)
                if item.default_value is not None
                else None
            )
            value_map = {
                str(source): self._normalize_value(dimension, target)
                for source, target in item.value_map.items()
            }
            normalized_mappings.append(
                CallerAttributeMapping(
                    source_attribute=source_attribute,
                    dimension_code=dimension_code,
                    required=item.required,
                    default_value=default_value,
                    value_map=value_map,
                ).model_dump(mode="json")
            )
        return {
            "profile_code": profile_code,
            "profile_name": profile_name,
            "caller_system_code": caller_system_code,
            "schema_version": schema_version,
            "description": payload.description.strip() if payload.description else None,
            "mappings_json": normalized_mappings,
            "is_active": payload.is_active,
        }

    def _apply_profile(
        self,
        profile: ChargeCallerMappingProfileRow,
        caller_attributes: dict[str, Any],
        dimensions: dict[str, ChargePricingDimensionRow],
    ) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for raw_mapping in list(profile.mappings_json or []):
            mapping = CallerAttributeMapping.model_validate(raw_mapping)
            dimension_code = mapping.dimension_code.strip().upper()
            dimension = dimensions.get(dimension_code)
            if dimension is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Mapping profile references unknown or inactive dimension {dimension_code}.",
                )
            found, raw_value = self._path_value(caller_attributes, mapping.source_attribute)
            if not found or raw_value is None or raw_value == "":
                if mapping.default_value is not None:
                    raw_value = mapping.default_value
                elif mapping.required:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Required caller attribute is missing: {mapping.source_attribute}.",
                    )
                else:
                    continue
            mapped_value = mapping.value_map.get(str(raw_value))
            if mapped_value is None and isinstance(raw_value, str):
                mapped_value = next(
                    (
                        target
                        for source, target in mapping.value_map.items()
                        if source.casefold() == raw_value.casefold()
                    ),
                    None,
                )
            if mapped_value is None:
                mapped_value = raw_value
            values[dimension_code] = self._normalize_value(dimension, mapped_value)
        return values

    def _normalize_dimension_values(
        self,
        raw_values: dict[str, Any],
        dimensions: dict[str, ChargePricingDimensionRow],
    ) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for raw_code, value in raw_values.items():
            code = str(raw_code).strip().upper()
            dimension = dimensions.get(code)
            if dimension is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unknown or inactive pricing dimension: {code}.",
                )
            values[code] = self._normalize_value(dimension, value)
        return values

    @staticmethod
    def _normalize_value(dimension: ChargePricingDimensionRow, value: Any) -> Any:
        try:
            if dimension.data_type == "STRING":
                normalized: Any = str(value).strip()
                if not normalized:
                    raise ValueError("blank string")
                if not dimension.case_sensitive:
                    normalized = normalized.upper()
            elif dimension.data_type == "DECIMAL":
                normalized = str(Decimal(str(value)).normalize())
            elif dimension.data_type == "INTEGER":
                if isinstance(value, bool):
                    raise ValueError("boolean is not an integer")
                decimal_value = Decimal(str(value))
                if decimal_value != decimal_value.to_integral_value():
                    raise ValueError("not an integer")
                normalized = int(decimal_value)
            elif dimension.data_type == "BOOLEAN":
                if isinstance(value, bool):
                    normalized = value
                elif str(value).strip().upper() in {"TRUE", "1", "YES", "Y", "ON"}:
                    normalized = True
                elif str(value).strip().upper() in {"FALSE", "0", "NO", "N", "OFF"}:
                    normalized = False
                else:
                    raise ValueError("not a boolean")
            elif dimension.data_type == "DATE":
                normalized = value.isoformat() if isinstance(value, date) else date.fromisoformat(str(value)).isoformat()
            else:
                raise ValueError("unsupported data type")
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid {dimension.data_type.lower()} value for dimension {dimension.dimension_code}.",
            ) from exc
        allowed = list(dimension.allowed_values_json or [])
        if allowed:
            normalized_allowed = [
                item if dimension.case_sensitive else str(item).upper()
                for item in allowed
            ]
            if normalized not in normalized_allowed:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Value for dimension {dimension.dimension_code} is outside allowed_values.",
                )
        return normalized

    @staticmethod
    def _path_value(payload: dict[str, Any], path: str) -> tuple[bool, Any]:
        current: Any = payload
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return False, None
            current = current[part]
        return True, current

    def _dimension_rows_by_code(self, *, active_only: bool) -> dict[str, ChargePricingDimensionRow]:
        statement = select(ChargePricingDimensionRow)
        if active_only:
            statement = statement.where(ChargePricingDimensionRow.is_active.is_(True))
        return {
            row.dimension_code: row
            for row in self.db.scalars(statement).all()
        }

    def _require_dimension(self, dimension_id: int) -> ChargePricingDimensionRow:
        row = self.db.get(ChargePricingDimensionRow, dimension_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pricing dimension was not found.")
        return row

    def _require_profile(self, profile_id: int) -> ChargeCallerMappingProfileRow:
        row = self.db.get(ChargeCallerMappingProfileRow, profile_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caller mapping profile was not found.")
        return row

    @staticmethod
    def _dimension_values(payload: PricingDimensionPayload) -> dict[str, Any]:
        code = payload.dimension_code.strip().upper()
        name = payload.dimension_name.strip()
        if not code or not name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dimension code and name are required.")
        if not all(character.isalnum() or character == "_" for character in code):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Dimension code must use letters, numbers, and underscores.")
        allowed_values = []
        for raw_value in payload.allowed_values:
            value = raw_value.strip()
            if not value:
                continue
            normalized = value if payload.case_sensitive else value.upper()
            if normalized not in allowed_values:
                allowed_values.append(normalized)
        if payload.data_type != "STRING" and allowed_values:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="allowed_values are supported only for STRING dimensions.")
        return {
            "dimension_code": code,
            "dimension_name": name,
            "description": payload.description.strip() if payload.description else None,
            "data_type": payload.data_type,
            "allowed_values_json": allowed_values,
            "case_sensitive": payload.case_sensitive,
            "is_active": payload.is_active,
        }

    @staticmethod
    def _dimension_model(row: ChargePricingDimensionRow) -> PricingDimension:
        return PricingDimension(
            id=row.id,
            dimension_code=row.dimension_code,
            dimension_name=row.dimension_name,
            description=row.description,
            data_type=row.data_type,
            built_in_field=row.built_in_field,
            allowed_values=list(row.allowed_values_json or []),
            case_sensitive=row.case_sensitive,
            is_system=row.is_system,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _profile_model(row: ChargeCallerMappingProfileRow) -> CallerMappingProfile:
        mappings = [CallerAttributeMapping.model_validate(item) for item in list(row.mappings_json or [])]
        return CallerMappingProfile(
            id=row.id,
            profile_code=row.profile_code,
            profile_name=row.profile_name,
            caller_system_code=row.caller_system_code,
            schema_version=row.schema_version,
            description=row.description,
            mappings=mappings,
            canonical_dimension_codes=[mapping.dimension_code for mapping in mappings],
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _flush_unique(self, detail: str) -> None:
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
