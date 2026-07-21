from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json
from typing import Any

from pydantic import BaseModel
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import (
    ChargeAllocationProfileRow,
    ChargeAllocationProfileVersionRow,
    ChargeBusinessDateProfileAssignmentRow,
    ChargeBusinessDateProfileRow,
    ChargeBusinessDateProfileStepRow,
    ChargeBusinessDateProfileVersionRow,
    ChargeCalculationTemplateRow,
    ChargeCalculationTemplateStepRow,
    ChargeComponentAliasRow,
    ChargeComponentRow,
    ChargeContractLineRow,
    ChargeDocumentRow,
    ChargeExportBatchRow,
    ChargeFxRateRow,
    ChargeFxRateSourceRow,
    ChargeIdSequenceRow,
    ChargeInvoiceRow,
    ChargeLineRow,
    ChargeManagementSettingsRow,
    ChargeMatchResultRow,
    ChargeQuoteCommitmentConsumptionRow,
    ChargeQuoteCommitmentRow,
    ChargeQuoteOfferRow,
    ChargeQuoteOptionLineRow,
    ChargeQuoteOptionRow,
    ChargeQuoteRequestRow,
    ChargeRateBookEntryRow,
    ChargeRateBookRow,
    ChargeRateContractRow,
)
from app.domain.models import (
    BusinessDateProfile,
    BusinessDateProfileAssignment,
    BusinessDateProfileAssignmentCreate,
    BusinessDateProfileStep,
    BusinessDateProfileVersion,
    ChargeAllocationProfile,
    ChargeAllocationProfileVersion,
    ChargeComponent,
    ChargeComponentAlias,
    ChargeDocument,
    ChargeExportResponse,
    ChargeInvoice,
    ChargeLine,
    ChargeInitializationData,
    ChargeManagementSettings,
    ChargeMatchResult,
    CalculationTemplate,
    CalculationTemplateStep,
    ContractLine,
    FxRate,
    FxRateSource,
    QuoteCommitment,
    QuoteCommitmentConsumption,
    QuoteOffer,
    QuoteOption,
    QuoteOptionLine,
    QuoteRequest,
    RateBook,
    RateBookEntry,
    RateContract,
    utcnow,
)
from app.domain.service import InMemoryChargeRepository
from app.domain.seeds import COMMON_CHARGE_ALLOCATION_PROFILES, COMMON_CHARGE_COMPONENTS, COMMON_BUSINESS_DATE_PROFILES


def _row_data(row: Any) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for column in row.__table__.columns:
        value = getattr(row, column.key)
        if isinstance(value, datetime) and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        data[column.key] = value
    return data


def _model_from_row(model_type: Any, row: Any, **extra: Any) -> Any:
    data = _row_data(row)
    data.update(extra)
    return model_type.model_validate(data)


def _normalize_model_datetimes(value: Any) -> None:
    if isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            field_value = getattr(value, field_name)
            if isinstance(field_value, datetime) and field_value.tzinfo is None:
                setattr(value, field_name, field_value.replace(tzinfo=timezone.utc))
            else:
                _normalize_model_datetimes(field_value)
    elif isinstance(value, dict):
        for item in value.values():
            _normalize_model_datetimes(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _normalize_model_datetimes(item)


def _remaining(committed: Decimal | None, consumed: Decimal) -> Decimal | None:
    if committed is None:
        return None
    return _trim_decimal(Decimal(committed) - Decimal(consumed))


def _trim_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    decimal_value = Decimal(value)
    return Decimal("0") if decimal_value == 0 else decimal_value.normalize()


def _money_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value).quantize(Decimal("0.01"))


def _charge_line_depth(lines_by_id: dict[int, ChargeLine], line: ChargeLine, cache: dict[int, int]) -> int:
    if line.id in cache:
        return cache[line.id]
    parent_id = line.parent_line_id
    if parent_id is None or parent_id not in lines_by_id:
        cache[line.id] = 0
    else:
        cache[line.id] = _charge_line_depth(lines_by_id, lines_by_id[parent_id], cache) + 1
    return cache[line.id]


def _sorted_charge_lines(lines: list[ChargeLine]) -> list[ChargeLine]:
    lines_by_id = {line.id: line for line in lines}
    cache: dict[int, int] = {}
    return sorted(
        lines,
        key=lambda line: (
            _charge_line_depth(lines_by_id, line, cache),
            line.line_number if line.line_number is not None else 0,
            line.id,
        ),
    )


def _charge_line_row(line: ChargeLine, component_id: int) -> ChargeLineRow:
    return ChargeLineRow(
        id=line.id,
        charge_document_id=line.charge_document_id,
        relationship_role=line.relationship_role,
        line_number=line.line_number,
        parent_line_id=line.parent_line_id,
        line_role=line.line_role,
        target_level=line.target_level,
        target_object_type=line.target_object_type,
        target_object_id=line.target_object_id,
        payer_party_ref=line.payer_party_ref,
        payee_party_ref=line.payee_party_ref,
        party_role_ref=line.party_role_ref,
        charge_component_id=component_id,
        description=line.description,
        charge_date=line.charge_date,
        charge_date_basis=line.charge_date_basis,
        expected_amount=line.expected_amount,
        actual_amount=line.actual_amount,
        approved_amount=line.approved_amount,
        currency=line.currency,
        quantity_uom=line.quantity_uom,
        source_currency=line.source_currency,
        source_amount=line.source_amount,
        exchange_rate=line.exchange_rate,
        exchange_rate_date=line.exchange_rate_date,
        fx_rate_id=line.fx_rate_id,
        exchange_rate_source_code=line.exchange_rate_source_code,
        exchange_rate_type=line.exchange_rate_type,
        exchange_rate_method=line.exchange_rate_method,
        allocation_profile_id=line.allocation_profile_id,
        allocation_profile_version_id=line.allocation_profile_version_id,
        pinned_allocation_snapshot_json=line.pinned_allocation_snapshot_json,
        effective_allocation_snapshot_json=line.effective_allocation_snapshot_json,
        charge_text_snapshot=line.charge_text_snapshot,
        allocation_basis=line.allocation_basis,
        allocation_ratio=line.allocation_ratio,
        allocation_driver_value=line.allocation_driver_value,
        target_reference_snapshot_json=line.target_reference_snapshot_json,
        calculation_audit_json=line.calculation_audit_json,
        basis=line.basis,
        source_quote_option_line_id=line.source_quote_option_line_id,
    )


class SqlAlchemyChargeRepository(InMemoryChargeRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._sequence_rows: dict[str, ChargeIdSequenceRow] = {}
        self._fx_sources: dict[int, FxRateSource] = {}
        self._fx_rates: dict[int, FxRate] = {}
        self._export_ids: dict[str, int] = {}
        self._ids = defaultdict(int)
        self.allocation_profiles: dict[int, ChargeAllocationProfile] = {}
        self.allocation_profile_versions: dict[int, ChargeAllocationProfileVersion] = {}
        self.business_date_profiles: dict[int, BusinessDateProfile] = {}
        self.business_date_profile_versions: dict[int, BusinessDateProfileVersion] = {}
        self.business_date_profile_assignments: dict[int, BusinessDateProfileAssignment] = {}
        self.components: dict[int, ChargeComponent] = {}
        self.components_by_code: dict[str, ChargeComponent] = {}
        self.component_aliases: dict[int, ChargeComponentAlias] = {}
        self.rate_books: dict[int, RateBook] = {}
        self.calculation_templates: dict[int, CalculationTemplate] = {}
        self.contracts: dict[int, RateContract] = {}
        self.quote_requests: dict[int, QuoteRequest] = {}
        self.quote_offers: dict[int, QuoteOffer] = {}
        self.quote_options: dict[int, QuoteOption] = {}
        self.quote_commitments: dict[int, QuoteCommitment] = {}
        self.quote_commitment_consumptions: dict[int, QuoteCommitmentConsumption] = {}
        self.documents: dict[int, ChargeDocument] = {}
        self.invoices: dict[int, ChargeInvoice] = {}
        self.match_results: dict[int, ChargeMatchResult] = {}
        self.exports: dict[str, ChargeExportResponse] = {}
        self.quotation_policy = "OPTIONAL"
        self.quote_acceptance_mode = "CUSTOMER_ACCEPTANCE"
        self.provider_cost_layer_enabled = False
        self._original_state_signature: str | None = None
        self._original_row_keys: dict[str, set[Any]] = {}
        if self._has_seed_components():
            self._load_state()
        else:
            self.reset()

    def _has_seed_components(self) -> bool:
        return self.session.scalar(select(ChargeComponentRow.id).limit(1)) is not None

    def _clear_state(self) -> None:
        self._ids.clear()
        self._sequence_rows.clear()
        self.allocation_profiles.clear()
        self.allocation_profile_versions.clear()
        self.business_date_profiles.clear()
        self.business_date_profile_versions.clear()
        self.business_date_profile_assignments.clear()
        self.components.clear()
        self.components_by_code.clear()
        self.component_aliases.clear()
        self.rate_books.clear()
        self.calculation_templates.clear()
        self.contracts.clear()
        self.quote_requests.clear()
        self.quote_offers.clear()
        self.quote_options.clear()
        self.quote_commitments.clear()
        self.quote_commitment_consumptions.clear()
        self.documents.clear()
        self.invoices.clear()
        self.match_results.clear()
        self.exports.clear()
        self._export_ids.clear()
        self._fx_sources.clear()
        self._fx_rates.clear()
        self.quotation_policy = "OPTIONAL"
        self.quote_acceptance_mode = "CUSTOMER_ACCEPTANCE"
        self.provider_cost_layer_enabled = False

    def _delete_all_rows(self) -> None:
        # Break the profile/version cycles before deleting either side. PostgreSQL
        # enforces these foreign keys during the statement, unlike default SQLite.
        self.session.execute(update(ChargeBusinessDateProfileRow).values(published_version_id=None))
        self.session.execute(update(ChargeAllocationProfileRow).values(published_version_id=None))
        self.session.flush()
        for table in (
            ChargeMatchResultRow,
            ChargeExportBatchRow,
            ChargeInvoiceRow,
            ChargeQuoteCommitmentConsumptionRow,
            ChargeQuoteCommitmentRow,
            ChargeLineRow,
            ChargeDocumentRow,
            ChargeQuoteOptionLineRow,
            ChargeQuoteOptionRow,
            ChargeQuoteOfferRow,
            ChargeQuoteRequestRow,
            ChargeContractLineRow,
            ChargeRateContractRow,
            ChargeCalculationTemplateStepRow,
            ChargeCalculationTemplateRow,
            ChargeRateBookEntryRow,
            ChargeRateBookRow,
            ChargeComponentAliasRow,
            ChargeComponentRow,
            ChargeBusinessDateProfileAssignmentRow,
            ChargeBusinessDateProfileStepRow,
            ChargeBusinessDateProfileVersionRow,
            ChargeBusinessDateProfileRow,
            ChargeAllocationProfileVersionRow,
            ChargeAllocationProfileRow,
            ChargeFxRateRow,
            ChargeFxRateSourceRow,
            ChargeManagementSettingsRow,
            ChargeIdSequenceRow,
        ):
            self.session.execute(delete(table))
        self.session.flush()

    def reset(self) -> None:
        self._delete_all_rows()
        self._clear_state()
        self._original_row_keys = {}
        self.seed_business_date_profiles()
        self.seed_allocation_profiles()
        self.seed_components()
        self.flush()

    def next_id(self, bucket: str) -> int:
        row = self.session.scalar(
            select(ChargeIdSequenceRow)
            .where(ChargeIdSequenceRow.bucket == bucket)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if row is None:
            row = ChargeIdSequenceRow(bucket=bucket, last_value=0)
            self.session.add(row)
        self._sequence_rows[bucket] = row
        row.last_value = int(row.last_value) + 1
        self._ids[bucket] = int(row.last_value)
        self.session.flush()
        return self._ids[bucket]

    def flush(self) -> None:
        self._sync_settings_row()
        self._sync_sequence_rows()
        current_signature = self._state_signature()
        if current_signature == self._original_state_signature:
            return
        self._delete_removed_rows()
        self._persist_settings()
        self._persist_sequences()
        self._persist_allocation_profiles()
        self._persist_business_date_profiles()
        self._persist_components()
        self._persist_rate_books()
        self._persist_calculation_templates()
        self._persist_contracts()
        self._persist_quote_requests()
        self._persist_documents()
        self._persist_quote_commitments()
        self._persist_invoices()
        self._persist_match_results()
        self._persist_exports()
        self.session.flush()
        self._original_state_signature = self._state_signature()
        self._original_row_keys = self._state_row_keys()

    def _state_row_keys(self) -> dict[str, set[Any]]:
        return {
            "business_date_profile_assignment": set(self.business_date_profile_assignments),
            "business_date_profile_step": {
                step.id
                for version in self.business_date_profile_versions.values()
                for step in version.steps
            },
            "rate_book_entry": {
                entry.id for book in self.rate_books.values() for entry in book.entries
            },
            "calculation_template_step": {
                step.id for template in self.calculation_templates.values() for step in template.steps
            },
            "contract_line": {
                line.id for contract in self.contracts.values() for line in contract.lines
            },
            "quote_option": set(self.quote_options),
            "quote_option_line": {
                line.id for option in self.quote_options.values() for line in option.lines
            },
            "charge_document": set(self.documents),
            "charge_line": {
                line.id for document in self.documents.values() for line in document.lines
            },
            "match_result": set(self.match_results),
        }

    def _delete_removed_rows(self) -> None:
        current = self._state_row_keys()
        specs = (
            ("match_result", ChargeMatchResultRow, ChargeMatchResultRow.id),
            ("charge_line", ChargeLineRow, ChargeLineRow.id),
            ("charge_document", ChargeDocumentRow, ChargeDocumentRow.id),
            ("quote_option_line", ChargeQuoteOptionLineRow, ChargeQuoteOptionLineRow.id),
            ("quote_option", ChargeQuoteOptionRow, ChargeQuoteOptionRow.id),
            ("contract_line", ChargeContractLineRow, ChargeContractLineRow.id),
            (
                "calculation_template_step",
                ChargeCalculationTemplateStepRow,
                ChargeCalculationTemplateStepRow.id,
            ),
            ("rate_book_entry", ChargeRateBookEntryRow, ChargeRateBookEntryRow.id),
            (
                "business_date_profile_assignment",
                ChargeBusinessDateProfileAssignmentRow,
                ChargeBusinessDateProfileAssignmentRow.id,
            ),
            (
                "business_date_profile_step",
                ChargeBusinessDateProfileStepRow,
                ChargeBusinessDateProfileStepRow.id,
            ),
        )
        for name, row_type, key_column in specs:
            removed = self._original_row_keys.get(name, set()) - current[name]
            if removed:
                self.session.execute(delete(row_type).where(key_column.in_(removed)))
        self.session.flush()

    def _state_signature(self) -> str:
        collections = (
            "allocation_profiles",
            "allocation_profile_versions",
            "business_date_profiles",
            "business_date_profile_versions",
            "business_date_profile_assignments",
            "components",
            "component_aliases",
            "rate_books",
            "calculation_templates",
            "contracts",
            "quote_requests",
            "quote_offers",
            "quote_options",
            "quote_commitments",
            "quote_commitment_consumptions",
            "documents",
            "invoices",
            "match_results",
            "exports",
            "_fx_sources",
            "_fx_rates",
        )
        payload: dict[str, Any] = {
            "ids": dict(self._ids),
            "settings": self._settings_model().model_dump(mode="json"),
        }
        for name in collections:
            values = getattr(self, name)
            payload[name] = {
                str(key): value.model_dump(mode="json")
                for key, value in sorted(values.items(), key=lambda item: str(item[0]))
            }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def _sync_settings_row(self) -> None:
        self._settings_row = ChargeManagementSettingsRow(
            id=1,
            quotation_policy=self.quotation_policy,
            quote_acceptance_mode=self.quote_acceptance_mode,
            provider_cost_layer_enabled=self.provider_cost_layer_enabled,
            settings_json=self._settings_model().model_dump(),
        )

    def _sync_sequence_rows(self) -> None:
        for bucket in set(self._ids):
            if bucket not in self._sequence_rows:
                self._sequence_rows[bucket] = ChargeIdSequenceRow(bucket=bucket, last_value=0)
            self._sequence_rows[bucket].last_value = int(self._ids[bucket])

    def _settings_model(self) -> ChargeManagementSettings:
        return ChargeManagementSettings(
            quotation_policy=self.quotation_policy,
            quote_acceptance_mode=self.quote_acceptance_mode,
            provider_cost_layer_enabled=self.provider_cost_layer_enabled,
        )

    def _load_state(self) -> None:
        self._clear_state()
        self._load_settings()
        self._load_sequence_rows()
        self._load_allocation_profiles()
        self._load_business_date_profiles()
        self._load_components()
        self._load_rate_books()
        self._load_calculation_templates()
        self._load_contracts()
        self._load_quote_requests()
        self._load_documents()
        self._load_quote_commitments()
        self._load_invoices()
        self._load_match_results()
        self._load_exports()
        for collection in (
            self.allocation_profiles,
            self.allocation_profile_versions,
            self.business_date_profiles,
            self.business_date_profile_versions,
            self.business_date_profile_assignments,
            self.components,
            self.component_aliases,
            self.rate_books,
            self.calculation_templates,
            self.contracts,
            self.quote_requests,
            self.quote_offers,
            self.quote_options,
            self.quote_commitments,
            self.quote_commitment_consumptions,
            self.documents,
            self.invoices,
            self.match_results,
            self.exports,
            self._fx_sources,
            self._fx_rates,
        ):
            _normalize_model_datetimes(collection)
        self._original_state_signature = self._state_signature()
        self._original_row_keys = self._state_row_keys()

    def _load_settings(self) -> None:
        row = self.session.scalar(select(ChargeManagementSettingsRow).order_by(ChargeManagementSettingsRow.id))
        if row is None:
            return
        self.quotation_policy = row.quotation_policy
        self.quote_acceptance_mode = row.quote_acceptance_mode
        self.provider_cost_layer_enabled = bool(row.provider_cost_layer_enabled)

    def _load_sequence_rows(self) -> None:
        rows = self.session.scalars(select(ChargeIdSequenceRow)).all()
        for row in rows:
            self._sequence_rows[row.bucket] = row
            self._ids[row.bucket] = max(self._ids[row.bucket], int(row.last_value))

    def _load_allocation_profiles(self) -> None:
        profile_rows = self.session.scalars(
            select(ChargeAllocationProfileRow).order_by(ChargeAllocationProfileRow.profile_code, ChargeAllocationProfileRow.id)
        ).all()
        version_rows = self.session.scalars(
            select(ChargeAllocationProfileVersionRow).order_by(
                ChargeAllocationProfileVersionRow.profile_id,
                ChargeAllocationProfileVersionRow.version_number,
                ChargeAllocationProfileVersionRow.id,
            )
        ).all()
        versions_by_profile: dict[int, list[ChargeAllocationProfileVersion]] = defaultdict(list)
        for row in version_rows:
            version = _model_from_row(
                ChargeAllocationProfileVersion,
                row,
                settings_json=dict(row.settings_json or {}),
            )
            versions_by_profile[version.profile_id].append(version)
            self._ids["allocation_profile_version"] = max(self._ids["allocation_profile_version"], version.id)
        for row in profile_rows:
            profile = ChargeAllocationProfile(
                id=row.id,
                profile_code=row.profile_code,
                profile_name=row.profile_name,
                published_version_id=row.published_version_id,
                published_version_number=next(
                    (
                        version.version_number
                        for version in versions_by_profile.get(row.id, [])
                        if version.id == row.published_version_id
                    ),
                    None,
                ),
                versions=sorted(versions_by_profile.get(row.id, []), key=lambda item: (item.version_number, item.id)),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            self.allocation_profiles[profile.id] = profile
            self._ids["allocation_profile"] = max(self._ids["allocation_profile"], profile.id)
        for profile in self.allocation_profiles.values():
            for version in profile.versions:
                self.allocation_profile_versions[version.id] = version

    def _load_business_date_profiles(self) -> None:
        profile_rows = self.session.scalars(
            select(ChargeBusinessDateProfileRow).order_by(
                ChargeBusinessDateProfileRow.profile_code,
                ChargeBusinessDateProfileRow.id,
            )
        ).all()
        version_rows = self.session.scalars(
            select(ChargeBusinessDateProfileVersionRow).order_by(
                ChargeBusinessDateProfileVersionRow.profile_id,
                ChargeBusinessDateProfileVersionRow.version_number,
                ChargeBusinessDateProfileVersionRow.id,
            )
        ).all()
        step_rows = self.session.scalars(
            select(ChargeBusinessDateProfileStepRow).order_by(
                ChargeBusinessDateProfileStepRow.version_id,
                ChargeBusinessDateProfileStepRow.step_number,
                ChargeBusinessDateProfileStepRow.id,
            )
        ).all()
        assignment_rows = self.session.scalars(
            select(ChargeBusinessDateProfileAssignmentRow).order_by(
                ChargeBusinessDateProfileAssignmentRow.profile_id,
                ChargeBusinessDateProfileAssignmentRow.priority,
                ChargeBusinessDateProfileAssignmentRow.id,
            )
        ).all()
        steps_by_version: dict[int, list[BusinessDateProfileStep]] = defaultdict(list)
        for row in step_rows:
            step = _model_from_row(BusinessDateProfileStep, row)
            steps_by_version[step.version_id].append(step)
            self._ids["business_date_profile_step"] = max(self._ids["business_date_profile_step"], step.id)
        versions_by_profile: dict[int, list[BusinessDateProfileVersion]] = defaultdict(list)
        for row in version_rows:
            version = BusinessDateProfileVersion(
                id=row.id,
                profile_id=row.profile_id,
                version_number=row.version_number,
                status=row.status,
                notes=row.notes,
                published_at=row.published_at,
                created_at=row.created_at,
                updated_at=row.updated_at,
                steps=sorted(steps_by_version.get(row.id, []), key=lambda item: (item.step_number, item.id)),
            )
            versions_by_profile[version.profile_id].append(version)
            self._ids["business_date_profile_version"] = max(self._ids["business_date_profile_version"], version.id)
        for row in profile_rows:
            profile = BusinessDateProfile(
                id=row.id,
                profile_code=row.profile_code,
                profile_name=row.profile_name,
                description=row.description,
                published_version_id=row.published_version_id,
                published_version_number=next(
                    (
                        version.version_number
                        for version in versions_by_profile.get(row.id, [])
                        if version.id == row.published_version_id
                    ),
                    None,
                ),
                versions=sorted(versions_by_profile.get(row.id, []), key=lambda item: (item.version_number, item.id)),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            self.business_date_profiles[profile.id] = profile
            self._ids["business_date_profile"] = max(self._ids["business_date_profile"], profile.id)
        for profile in self.business_date_profiles.values():
            for version in profile.versions:
                self.business_date_profile_versions[version.id] = version
        for row in assignment_rows:
            assignment = _model_from_row(BusinessDateProfileAssignment, row)
            self.business_date_profile_assignments[assignment.id] = assignment
            self._ids["business_date_profile_assignment"] = max(self._ids["business_date_profile_assignment"], assignment.id)

    def _load_fx_sources(self) -> None:
        self._fx_sources = {}
        self._fx_rates = {}
        source_rows = self.session.scalars(
            select(ChargeFxRateSourceRow).order_by(ChargeFxRateSourceRow.priority, ChargeFxRateSourceRow.source_code)
        ).all()
        rate_rows = self.session.scalars(
            select(ChargeFxRateRow).order_by(ChargeFxRateRow.rate_date.desc(), ChargeFxRateRow.id.desc())
        ).all()
        sources_by_id: dict[int, FxRateSource] = {}
        for row in source_rows:
            source = _model_from_row(FxRateSource, row, metadata_json=dict(row.metadata_json or {}))
            self._ids["fx_rate_source"] = max(self._ids["fx_rate_source"], source.id)
            sources_by_id[source.id] = source
            self._fx_sources[source.id] = source
        for row in rate_rows:
            source = sources_by_id.get(row.source_id)
            if source is None:
                source_row = self.session.get(ChargeFxRateSourceRow, row.source_id)
                if source_row is None:
                    continue
                source = _model_from_row(FxRateSource, source_row, metadata_json=dict(source_row.metadata_json or {}))
                sources_by_id[source.id] = source
            rate = _model_from_row(
                FxRate,
                row,
                source_code=source.source_code,
                source_name=source.source_name,
                metadata_json=dict(row.metadata_json or {}),
            )
            self._ids["fx_rate"] = max(self._ids["fx_rate"], rate.id)
            self._fx_rates[rate.id] = rate

    def _load_components(self) -> None:
        component_rows = self.session.scalars(
            select(ChargeComponentRow).order_by(
                ChargeComponentRow.category,
                ChargeComponentRow.component_name,
                ChargeComponentRow.component_code,
                ChargeComponentRow.id,
            )
        ).all()
        components_by_id: dict[int, ChargeComponent] = {}
        for row in component_rows:
            component = _model_from_row(ChargeComponent, row)
            self.components[component.id] = component
            self.components_by_code[component.component_code] = component
            components_by_id[component.id] = component
            self._ids["component"] = max(self._ids["component"], component.id)
        alias_rows = self.session.scalars(
            select(ChargeComponentAliasRow).order_by(
                ChargeComponentAliasRow.document_kind,
                ChargeComponentAliasRow.template_key,
                ChargeComponentAliasRow.normalized_label,
                ChargeComponentAliasRow.id,
            )
        ).all()
        for row in alias_rows:
            component = components_by_id.get(row.charge_component_id)
            if component is None:
                continue
            alias = _model_from_row(
                ChargeComponentAlias,
                row,
                component_code=component.component_code,
                component_name=component.component_name,
            )
            self.component_aliases[alias.id] = alias
            self._ids["component_alias"] = max(self._ids["component_alias"], alias.id)

    def _load_rate_books(self) -> None:
        books = self.session.scalars(
            select(ChargeRateBookRow).order_by(ChargeRateBookRow.rate_book_code, ChargeRateBookRow.id)
        ).all()
        entries = self.session.scalars(
            select(ChargeRateBookEntryRow).order_by(ChargeRateBookEntryRow.rate_book_id, ChargeRateBookEntryRow.id)
        ).all()
        entries_by_book: dict[int, list[RateBookEntry]] = defaultdict(list)
        for row in entries:
            component = self.components.get(row.charge_component_id)
            if component is None:
                continue
            entry = _model_from_row(RateBookEntry, row, charge_component_code=component.component_code)
            entries_by_book[entry.rate_book_id].append(entry)
            self._ids["rate_book_entry"] = max(self._ids["rate_book_entry"], entry.id)
        for row in books:
            book = RateBook(
                id=row.id,
                rate_book_code=row.rate_book_code,
                rate_book_name=row.rate_book_name,
                currency=row.currency,
                entries=sorted(entries_by_book.get(row.id, []), key=lambda item: item.id),
                is_active=row.is_active,
            )
            self.rate_books[book.id] = book
            self._ids["rate_book"] = max(self._ids["rate_book"], book.id)

    def _load_calculation_templates(self) -> None:
        templates = self.session.scalars(
            select(ChargeCalculationTemplateRow).order_by(
                ChargeCalculationTemplateRow.template_code,
                ChargeCalculationTemplateRow.id,
            )
        ).all()
        steps = self.session.scalars(
            select(ChargeCalculationTemplateStepRow).order_by(
                ChargeCalculationTemplateStepRow.template_id,
                ChargeCalculationTemplateStepRow.sequence_no,
                ChargeCalculationTemplateStepRow.id,
            )
        ).all()
        steps_by_template: dict[int, list[CalculationTemplateStep]] = defaultdict(list)
        for row in steps:
            component = self.components.get(row.charge_component_id)
            if component is None:
                continue
            rate_book = self.rate_books.get(row.rate_book_id) if row.rate_book_id is not None else None
            step = _model_from_row(
                CalculationTemplateStep,
                row,
                step_number=row.sequence_no,
                charge_component_code=component.component_code,
                relationship_role=row.relationship_role,
                subtotal_key=row.subtotal_group,
                precondition_key=(row.precondition_json or {}).get("precondition_key"),
                rate_book_code=rate_book.rate_book_code if rate_book else None,
                rate_book_name=rate_book.rate_book_name if rate_book else None,
            )
            steps_by_template[step.template_id].append(step)
            self._ids["calculation_template_step"] = max(self._ids["calculation_template_step"], step.id)
        for row in templates:
            template = CalculationTemplate(
                id=row.id,
                template_code=row.template_code,
                template_name=row.template_name,
                description=row.description,
                status=row.status,
                is_active=row.is_active,
                steps=sorted(steps_by_template.get(row.id, []), key=lambda item: (item.step_number, item.id)),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            self.calculation_templates[template.id] = template
            self._ids["calculation_template"] = max(self._ids["calculation_template"], template.id)

    def _load_contracts(self) -> None:
        contracts = self.session.scalars(
            select(ChargeRateContractRow).order_by(ChargeRateContractRow.contract_number, ChargeRateContractRow.id)
        ).all()
        lines = self.session.scalars(
            select(ChargeContractLineRow).order_by(ChargeContractLineRow.contract_id, ChargeContractLineRow.id)
        ).all()
        lines_by_contract: dict[int, list[ContractLine]] = defaultdict(list)
        for row in lines:
            component = self.components.get(row.charge_component_id)
            if component is None:
                continue
            line = _model_from_row(ContractLine, row, charge_component_code=component.component_code)
            lines_by_contract[line.contract_id].append(line)
            self._ids["contract_line"] = max(self._ids["contract_line"], line.id)
        for row in contracts:
            contract = RateContract(
                id=row.id,
                contract_number=row.contract_number,
                contract_name=row.contract_name,
                contract_role=row.contract_role,
                payer_party_ref=row.payer_party_ref,
                payee_party_ref=row.payee_party_ref,
                party_role_ref=row.party_role_ref,
                status=row.status,
                partner_id=row.partner_id,
                customer_id=row.customer_id,
                vendor_id=row.vendor_id,
                forwarder_id=row.forwarder_id,
                carrier_id=row.carrier_id,
                company_id=row.company_id,
                currency=row.currency,
                valid_from=row.valid_from,
                valid_to=row.valid_to,
                default_rate_book_id=row.default_rate_book_id,
                default_calculation_template_id=row.default_calculation_template_id,
                lines=sorted(lines_by_contract.get(row.id, []), key=lambda item: item.id),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            self.contracts[contract.id] = contract
            self._ids["contract"] = max(self._ids["contract"], contract.id)

    def _load_quote_requests(self) -> None:
        requests = self.session.scalars(
            select(ChargeQuoteRequestRow).order_by(ChargeQuoteRequestRow.id)
        ).all()
        offers = self.session.scalars(select(ChargeQuoteOfferRow).order_by(ChargeQuoteOfferRow.id)).all()
        options = self.session.scalars(select(ChargeQuoteOptionRow).order_by(ChargeQuoteOptionRow.id)).all()
        option_lines = self.session.scalars(select(ChargeQuoteOptionLineRow).order_by(ChargeQuoteOptionLineRow.id)).all()
        offers_by_request: dict[int, list[QuoteOffer]] = defaultdict(list)
        options_by_request: dict[int, list[QuoteOption]] = defaultdict(list)
        option_lines_by_option: dict[int, list[QuoteOptionLine]] = defaultdict(list)
        for row in option_lines:
            component = self.components.get(row.charge_component_id)
            if component is None:
                continue
            option_line = _model_from_row(
                QuoteOptionLine,
                row,
                charge_component_code=component.component_code,
                amount=_money_decimal(row.amount),
            )
            option_lines_by_option[option_line.quote_option_id].append(option_line)
            self._ids["quote_option_line"] = max(self._ids["quote_option_line"], option_line.id)
        for row in offers:
            offer = _model_from_row(
                QuoteOffer,
                row,
                amount=_money_decimal(row.amount),
                performance_score=_trim_decimal(row.performance_score),
            )
            offers_by_request[offer.quote_request_id].append(offer)
            self._ids["quote_offer"] = max(self._ids["quote_offer"], offer.id)
        for row in options:
            option = QuoteOption(
                id=row.id,
                quote_request_id=row.quote_request_id,
                option_name=row.option_name,
                source_offer_id=row.source_offer_id,
                payer_contract_id=row.payer_contract_id,
                payee_contract_id=row.payee_contract_id,
                payer_total_amount=_money_decimal(row.payer_total_amount),
                payee_total_amount=_money_decimal(row.payee_total_amount),
                margin_amount=_money_decimal(row.margin_amount),
                margin_percent=_trim_decimal(row.margin_percent),
                transit_time_days=row.transit_time_days,
                service_level_score=_trim_decimal(row.service_level_score),
                policy_compliant=row.policy_compliant,
                rank=row.rank,
                score=_trim_decimal(row.score),
                expires_at=row.expires_at,
                lines=sorted(option_lines_by_option.get(row.id, []), key=lambda item: item.id),
            )
            options_by_request[option.quote_request_id].append(option)
            self._ids["quote_option"] = max(self._ids["quote_option"], option.id)
        for row in requests:
            request = QuoteRequest(
                id=row.id,
                source_object_type=row.source_object_type,
                source_object_id=row.source_object_id,
                company_id=row.company_id,
                customer_id=row.customer_id,
                vendor_id=row.vendor_id,
                forwarder_id=row.forwarder_id,
                carrier_id=row.carrier_id,
                origin_code=row.origin_code,
                destination_code=row.destination_code,
                mode=row.mode,
                equipment_type=row.equipment_type,
                commodity_code=row.commodity_code,
                service_level=row.service_level,
                currency=row.currency,
                quantity=_trim_decimal(row.quantity),
                gross_weight=_trim_decimal(row.gross_weight),
                gross_volume_cbm=_trim_decimal(row.gross_volume_cbm),
                container_count=_trim_decimal(row.container_count),
                package_count=_trim_decimal(row.package_count),
                package_type=row.package_type,
                requested_service_date=row.requested_service_date,
                valid_from=row.valid_from,
                valid_to=row.valid_to,
                expires_at=row.expires_at,
                margin_rules=dict(row.margin_rules_json or {}),
                context=dict(row.context_json or {}),
                status=row.status,
                quotation_policy_snapshot=row.quotation_policy_snapshot,
                awarded_option_id=row.awarded_option_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            self.quote_requests[request.id] = request
            self._ids["quote_request"] = max(self._ids["quote_request"], request.id)
        self.quote_offers = {offer.id: offer for values in offers_by_request.values() for offer in values}
        self.quote_options = {option.id: option for values in options_by_request.values() for option in values}

    def _load_documents(self) -> None:
        documents = self.session.scalars(
            select(ChargeDocumentRow).order_by(ChargeDocumentRow.id)
        ).all()
        lines = self.session.scalars(select(ChargeLineRow).order_by(ChargeLineRow.id)).all()
        lines_by_document: dict[int, list[ChargeLine]] = defaultdict(list)
        for row in lines:
            component = self.components.get(row.charge_component_id)
            if component is None:
                continue
            line = _model_from_row(
                ChargeLine,
                row,
                charge_component_code=component.component_code,
                expected_amount=_money_decimal(row.expected_amount),
                actual_amount=_money_decimal(row.actual_amount),
                approved_amount=_money_decimal(row.approved_amount),
                source_amount=_money_decimal(row.source_amount),
                exchange_rate=_trim_decimal(row.exchange_rate),
                allocation_ratio=_trim_decimal(row.allocation_ratio),
                allocation_driver_value=_trim_decimal(row.allocation_driver_value),
            )
            lines_by_document[line.charge_document_id].append(line)
            self._ids["charge_line"] = max(self._ids["charge_line"], line.id)
        for row in documents:
            document = ChargeDocument(
                id=row.id,
                document_number=row.document_number,
                quote_request_id=row.quote_request_id,
                quote_option_id=row.quote_option_id,
                quotation_policy_snapshot=row.quotation_policy_snapshot,
                source_object_type=row.source_object_type,
                source_object_id=row.source_object_id,
                document_scope_level=row.document_scope_level,
                shipment_scope=row.shipment_scope,
                document_date=row.document_date,
                source_reference_snapshot_json=dict(row.source_reference_snapshot_json or {}),
                company_id=row.company_id,
                customer_id=row.customer_id,
                vendor_id=row.vendor_id,
                forwarder_id=row.forwarder_id,
                carrier_id=row.carrier_id,
                status=row.status,
                currency=row.currency,
                payer_total_amount=_money_decimal(row.payer_total_amount),
                payee_total_amount=_money_decimal(row.payee_total_amount),
                margin_amount=_money_decimal(row.margin_amount),
                lines=_sorted_charge_lines(lines_by_document.get(row.id, [])),
                created_at=row.created_at,
                approved_at=row.approved_at,
                exported_at=row.exported_at,
                reversed_at=row.reversed_at,
                reversal_reason=row.reversal_reason,
            )
            self.documents[document.id] = document
            self._ids["document"] = max(self._ids["document"], document.id)

    def _load_quote_commitments(self) -> None:
        commitments = self.session.scalars(
            select(ChargeQuoteCommitmentRow).order_by(ChargeQuoteCommitmentRow.id)
        ).all()
        consumptions = self.session.scalars(
            select(ChargeQuoteCommitmentConsumptionRow).order_by(ChargeQuoteCommitmentConsumptionRow.id)
        ).all()
        consumptions_by_commitment: dict[int, list[QuoteCommitmentConsumption]] = defaultdict(list)
        for row in consumptions:
            consumption = _model_from_row(
                QuoteCommitmentConsumption,
                row,
                container_count=_trim_decimal(row.container_count),
                package_count=_trim_decimal(row.package_count),
                chargeable_weight=_trim_decimal(row.chargeable_weight),
                quantity=_trim_decimal(row.quantity),
                amount=_money_decimal(row.amount),
            )
            consumptions_by_commitment[consumption.commitment_id].append(consumption)
            self.quote_commitment_consumptions[consumption.id] = consumption
            self._ids["quote_commitment_consumption"] = max(self._ids["quote_commitment_consumption"], consumption.id)
        for row in commitments:
            commitment = QuoteCommitment(
                id=row.id,
                commitment_number=row.commitment_number,
                quote_request_id=row.quote_request_id,
                quote_option_id=row.quote_option_id,
                charge_document_id=row.charge_document_id,
                company_id=row.company_id,
                customer_id=row.customer_id,
                vendor_id=row.vendor_id,
                forwarder_id=row.forwarder_id,
                carrier_id=row.carrier_id,
                origin_code=row.origin_code,
                destination_code=row.destination_code,
                mode=row.mode,
                equipment_type=row.equipment_type,
                commodity_code=row.commodity_code,
                service_level=row.service_level,
                package_type=row.package_type,
                requested_service_date=row.requested_service_date,
                valid_from=row.valid_from,
                valid_to=row.valid_to,
                committed_container_count=_trim_decimal(row.committed_container_count),
                consumed_container_count=_trim_decimal(row.consumed_container_count),
                remaining_container_count=_remaining(row.committed_container_count, row.consumed_container_count),
                committed_package_count=_trim_decimal(row.committed_package_count),
                consumed_package_count=_trim_decimal(row.consumed_package_count),
                remaining_package_count=_remaining(row.committed_package_count, row.consumed_package_count),
                committed_chargeable_weight=_trim_decimal(row.committed_chargeable_weight),
                consumed_chargeable_weight=_trim_decimal(row.consumed_chargeable_weight),
                remaining_chargeable_weight=_remaining(
                    row.committed_chargeable_weight,
                    row.consumed_chargeable_weight,
                ),
                committed_quantity=_trim_decimal(row.committed_quantity),
                consumed_quantity=_trim_decimal(row.consumed_quantity),
                remaining_quantity=_remaining(row.committed_quantity, row.consumed_quantity),
                committed_amount=_money_decimal(row.committed_amount),
                consumed_amount=_money_decimal(row.consumed_amount),
                remaining_amount=_money_decimal(Decimal(row.committed_amount) - Decimal(row.consumed_amount)),
                currency=row.currency,
                status=row.status,
                consumptions=sorted(consumptions_by_commitment.get(row.id, []), key=lambda item: item.id),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            self.quote_commitments[commitment.id] = commitment
            self._ids["quote_commitment"] = max(self._ids["quote_commitment"], commitment.id)

    def _load_invoices(self) -> None:
        invoices = self.session.scalars(select(ChargeInvoiceRow).order_by(ChargeInvoiceRow.id)).all()
        for row in invoices:
            document = self.documents.get(row.charge_document_id)
            invoice = ChargeInvoice(
                id=row.id,
                charge_document_id=row.charge_document_id,
                invoice_number=row.invoice_number,
                invoice_type=row.invoice_type,
                invoice_date=row.invoice_date,
                currency=row.currency,
                lines=list(row.lines_json or []),
                charge_document_number=document.document_number if document else None,
                charge_document_status=document.status if document else None,
                status=row.status,
                total_amount=_money_decimal(row.total_amount),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            self.invoices[invoice.id] = invoice
            self._ids["invoice"] = max(self._ids["invoice"], invoice.id)

    def _load_match_results(self) -> None:
        results = self.session.scalars(select(ChargeMatchResultRow).order_by(ChargeMatchResultRow.id)).all()
        for row in results:
            component = self.components.get(row.charge_component_id) if row.charge_component_id is not None else None
            result = ChargeMatchResult(
                id=row.id,
                invoice_id=row.invoice_id,
                charge_document_id=row.charge_document_id,
                charge_line_id=row.charge_line_id,
                charge_component_code=component.component_code if component else "",
                expected_amount=_money_decimal(row.expected_amount),
                invoice_amount=_money_decimal(row.invoice_amount),
                variance_amount=_money_decimal(row.variance_amount),
                variance_percent=_trim_decimal(row.variance_percent),
                match_status=row.match_status,
                notes=row.notes,
            )
            self.match_results[result.id] = result
            self._ids["match_result"] = max(self._ids["match_result"], result.id)

    def _load_exports(self) -> None:
        exports = self.session.scalars(select(ChargeExportBatchRow).order_by(ChargeExportBatchRow.id)).all()
        for row in exports:
            document = self.documents.get(row.charge_document_id)
            if document is None:
                continue
            response = ChargeExportResponse(
                document=document,
                export_number=row.export_number,
                target_system=row.target_system,
                status=row.status,
                payload_json=dict(row.payload_json or {}),
            )
            self.exports[response.export_number] = response
            self._export_ids[response.export_number] = int(row.id)
            self._ids["export"] = max(self._ids["export"], int(row.id))

    def _persist_settings(self) -> None:
        self.session.merge(
            ChargeManagementSettingsRow(
                id=1,
                quotation_policy=self.quotation_policy,
                quote_acceptance_mode=self.quote_acceptance_mode,
                provider_cost_layer_enabled=self.provider_cost_layer_enabled,
                settings_json=self._settings_model().model_dump(),
            )
        )

    def _persist_sequences(self) -> None:
        for bucket, value in self._ids.items():
            self.session.merge(ChargeIdSequenceRow(bucket=bucket, last_value=int(value)))

    def _persist_allocation_profiles(self) -> None:
        for profile in sorted(self.allocation_profiles.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeAllocationProfileRow(
                    id=profile.id,
                    profile_code=profile.profile_code,
                    profile_name=profile.profile_name,
                    published_version_id=None,
                    created_at=profile.created_at,
                    updated_at=profile.updated_at,
                )
            )
        self.session.flush()
        for version in sorted(self.allocation_profile_versions.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeAllocationProfileVersionRow(
                    id=version.id,
                    profile_id=version.profile_id,
                    version_number=version.version_number,
                    status=version.status,
                    source_level=version.source_level,
                    source_to_house_driver=version.source_to_house_driver,
                    house_to_item_driver=version.house_to_item_driver,
                    final_posting_level=version.final_posting_level,
                    default_quantity_uom=version.default_quantity_uom,
                    settings_json=dict(version.settings_json or {}),
                    notes=version.notes,
                    published_at=version.published_at,
                    created_at=version.created_at,
                    updated_at=version.updated_at,
                )
            )
        self.session.flush()
        for profile in self.allocation_profiles.values():
            if profile.published_version_id is not None:
                self.session.execute(
                    update(ChargeAllocationProfileRow)
                    .where(ChargeAllocationProfileRow.id == profile.id)
                    .values(published_version_id=profile.published_version_id)
                )
        self.session.flush()

    def _persist_business_date_profiles(self) -> None:
        for profile in sorted(self.business_date_profiles.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeBusinessDateProfileRow(
                    id=profile.id,
                    profile_code=profile.profile_code,
                    profile_name=profile.profile_name,
                    description=profile.description,
                    published_version_id=None,
                    created_at=profile.created_at,
                    updated_at=profile.updated_at,
                )
            )
        self.session.flush()
        for version in sorted(self.business_date_profile_versions.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeBusinessDateProfileVersionRow(
                    id=version.id,
                    profile_id=version.profile_id,
                    version_number=version.version_number,
                    status=version.status,
                    notes=version.notes,
                    published_at=version.published_at,
                    created_at=version.created_at,
                    updated_at=version.updated_at,
                )
            )
        self.session.flush()
        for profile in self.business_date_profiles.values():
            if profile.published_version_id is not None:
                self.session.execute(
                    update(ChargeBusinessDateProfileRow)
                    .where(ChargeBusinessDateProfileRow.id == profile.id)
                    .values(published_version_id=profile.published_version_id)
                )
        self.session.flush()
        steps = sorted(
            (step for version in self.business_date_profile_versions.values() for step in version.steps),
            key=lambda item: item.id,
        )
        for step in steps:
            self.session.merge(
                ChargeBusinessDateProfileStepRow(
                    id=step.id,
                    version_id=step.version_id,
                    step_number=step.step_number,
                    date_key=step.date_key,
                    notes=step.notes,
                )
            )
        self.session.flush()
        for assignment in sorted(self.business_date_profile_assignments.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeBusinessDateProfileAssignmentRow(
                    id=assignment.id,
                    profile_id=assignment.profile_id,
                    scope_type=assignment.scope_type,
                    scope_id=assignment.scope_id,
                    owner_scope_key=assignment.owner_scope_key,
                    shipment_scope=assignment.shipment_scope,
                    business_purpose=assignment.business_purpose,
                    priority=assignment.priority,
                    is_active=assignment.is_active,
                    created_at=assignment.created_at,
                    updated_at=assignment.updated_at,
                )
            )
        self.session.flush()

    def _persist_components(self) -> None:
        for component in sorted(self.components.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeComponentRow(
                    id=component.id,
                    component_code=component.component_code,
                    component_name=component.component_name,
                    category=component.category,
                    default_party_role=component.default_party_role,
                    charge_context=component.charge_context,
                    calculation_basis=component.calculation_basis,
                    charge_date_basis=component.charge_date_basis,
                    business_date_policy_mode=component.business_date_policy_mode,
                    business_date_profile_id=component.business_date_profile_id,
                    allocation_profile_id=component.allocation_profile_id,
                    allocation_profile_version_id=component.allocation_profile_version_id,
                    is_tax=component.is_tax,
                    is_active=component.is_active,
                )
            )
        self.session.flush()
        for alias in sorted(self.component_aliases.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeComponentAliasRow(
                    id=alias.id,
                    document_kind=alias.document_kind,
                    template_key=alias.template_key,
                    source_section=alias.source_section,
                    customer_id=alias.customer_id,
                    forwarder_id=alias.forwarder_id,
                    transport_mode=alias.transport_mode,
                    raw_label=alias.raw_label,
                    normalized_label=alias.normalized_label,
                    charge_component_id=alias.charge_component_id,
                    default_calculation_basis=alias.default_calculation_basis,
                    default_charge_level=alias.default_charge_level,
                    default_allocation_basis=alias.default_allocation_basis,
                    container_house_allocation_basis=alias.container_house_allocation_basis,
                    house_item_allocation_basis=alias.house_item_allocation_basis,
                    final_posting_level=alias.final_posting_level,
                    default_quantity_uom=alias.default_quantity_uom,
                    allocation_override_mode=alias.allocation_override_mode,
                    override_allocation_profile_id=alias.override_allocation_profile_id,
                    override_allocation_profile_version_id=alias.override_allocation_profile_version_id,
                    override_charge_level=alias.override_charge_level,
                    override_allocation_basis=alias.override_allocation_basis,
                    override_container_house_allocation_basis=alias.override_container_house_allocation_basis,
                    override_house_item_allocation_basis=alias.override_house_item_allocation_basis,
                    override_final_posting_level=alias.override_final_posting_level,
                    override_quantity_uom=alias.override_quantity_uom,
                    priority=alias.priority,
                    is_active=alias.is_active,
                    created_at=alias.created_at,
                    updated_at=alias.updated_at,
                )
            )
        self.session.flush()

    def _persist_fx_sources(self) -> None:
        fx_sources = getattr(self, "_fx_sources", {})
        for source in sorted(fx_sources.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeFxRateSourceRow(
                    id=source.id,
                    source_code=source.source_code,
                    source_name=source.source_name,
                    provider_url=source.provider_url,
                    timezone=source.timezone,
                    priority=source.priority,
                    is_active=source.is_active,
                    metadata_json=dict(source.metadata_json or {}),
                    created_at=source.created_at,
                    updated_at=source.updated_at,
                )
            )
        self.session.flush()
        fx_rates = getattr(self, "_fx_rates", {})
        for rate in sorted(fx_rates.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeFxRateRow(
                    id=rate.id,
                    source_id=rate.source_id,
                    source_currency=rate.source_currency,
                    target_currency=rate.target_currency,
                    rate_date=rate.rate_date,
                    rate=rate.rate,
                    rate_type=rate.rate_type,
                    conversion_method=rate.conversion_method,
                    is_active=rate.is_active,
                    metadata_json=dict(rate.metadata_json or {}),
                    created_at=rate.created_at,
                    updated_at=rate.updated_at,
                )
            )
        self.session.flush()

    def _persist_rate_books(self) -> None:
        for book in sorted(self.rate_books.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeRateBookRow(
                    id=book.id,
                    rate_book_code=book.rate_book_code,
                    rate_book_name=book.rate_book_name,
                    currency=book.currency,
                    is_active=book.is_active,
                )
            )
        self.session.flush()
        for entry in sorted((entry for book in self.rate_books.values() for entry in book.entries), key=lambda item: item.id):
            component = self.components_by_code.get(entry.charge_component_code)
            if component is None:
                continue
            self.session.merge(
                ChargeRateBookEntryRow(
                    id=entry.id,
                    rate_book_id=entry.rate_book_id,
                    charge_component_id=component.id,
                    rate_amount=entry.rate_amount,
                    basis=entry.basis,
                    currency=entry.currency,
                    allocation_profile_id=entry.allocation_profile_id,
                    allocation_profile_version_id=entry.allocation_profile_version_id,
                    origin_code=entry.origin_code,
                    destination_code=entry.destination_code,
                    mode=entry.mode,
                    equipment_type=entry.equipment_type,
                    commodity_code=entry.commodity_code,
                    service_level=entry.service_level,
                    scale_from=entry.scale_from,
                    scale_to=entry.scale_to,
                    minimum_amount=entry.minimum_amount,
                    maximum_amount=entry.maximum_amount,
                    validity_from=entry.validity_from,
                    validity_to=entry.validity_to,
                )
            )
        self.session.flush()

    def _persist_calculation_templates(self) -> None:
        for template in sorted(self.calculation_templates.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeCalculationTemplateRow(
                    id=template.id,
                    template_code=template.template_code,
                    template_name=template.template_name,
                    description=template.description,
                    status=template.status,
                    is_active=template.is_active,
                    created_at=template.created_at,
                    updated_at=template.updated_at,
                )
            )
        self.session.flush()
        for step in sorted((step for template in self.calculation_templates.values() for step in template.steps), key=lambda item: item.id):
            component = self.components_by_code.get(step.charge_component_code)
            if component is None:
                continue
            self.session.merge(
                ChargeCalculationTemplateStepRow(
                    id=step.id,
                    template_id=step.template_id,
                    sequence_no=step.step_number,
                    charge_component_id=component.id,
                    relationship_role=step.relationship_role,
                    rate_book_id=step.rate_book_id,
                    precondition_json=None if step.precondition_key is None else {"precondition_key": step.precondition_key},
                    subtotal_group=step.subtotal_key,
                    is_statistical=step.is_statistical,
                )
            )
        self.session.flush()

    def _persist_contracts(self) -> None:
        for contract in sorted(self.contracts.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeRateContractRow(
                    id=contract.id,
                    contract_number=contract.contract_number,
                    contract_name=contract.contract_name,
                    contract_role=contract.contract_role,
                    payer_party_ref=contract.payer_party_ref,
                    payee_party_ref=contract.payee_party_ref,
                    party_role_ref=contract.party_role_ref,
                    status=contract.status,
                    partner_id=contract.partner_id,
                    customer_id=contract.customer_id,
                    vendor_id=contract.vendor_id,
                    forwarder_id=contract.forwarder_id,
                    carrier_id=contract.carrier_id,
                    company_id=contract.company_id,
                    currency=contract.currency,
                    valid_from=contract.valid_from,
                    valid_to=contract.valid_to,
                    default_rate_book_id=contract.default_rate_book_id,
                    default_calculation_template_id=contract.default_calculation_template_id,
                    created_at=contract.created_at,
                    updated_at=contract.updated_at,
                )
            )
        self.session.flush()
        for line in sorted((line for contract in self.contracts.values() for line in contract.lines), key=lambda item: item.id):
            component = self.components_by_code.get(line.charge_component_code)
            if component is None:
                continue
            self.session.merge(
                ChargeContractLineRow(
                    id=line.id,
                    contract_id=line.contract_id,
                    charge_component_id=component.id,
                    rate_book_id=line.rate_book_id,
                    calculation_template_id=line.calculation_template_id,
                    allocation_profile_id=line.allocation_profile_id,
                    allocation_profile_version_id=line.allocation_profile_version_id,
                    origin_code=line.origin_code,
                    destination_code=line.destination_code,
                    mode=line.mode,
                    equipment_type=line.equipment_type,
                    commodity_code=line.commodity_code,
                    service_level=line.service_level,
                    valid_from=line.valid_from,
                    valid_to=line.valid_to,
                )
            )
        self.session.flush()

    def _persist_quote_requests(self) -> None:
        for request in sorted(self.quote_requests.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeQuoteRequestRow(
                    id=request.id,
                    source_object_type=request.source_object_type,
                    source_object_id=request.source_object_id,
                    company_id=request.company_id,
                    customer_id=request.customer_id,
                    vendor_id=request.vendor_id,
                    forwarder_id=request.forwarder_id,
                    carrier_id=request.carrier_id,
                    origin_code=request.origin_code,
                    destination_code=request.destination_code,
                    mode=request.mode,
                    equipment_type=request.equipment_type,
                    commodity_code=request.commodity_code,
                    service_level=request.service_level,
                    currency=request.currency,
                    quantity=request.quantity,
                    gross_weight=request.gross_weight,
                    gross_volume_cbm=request.gross_volume_cbm,
                    container_count=request.container_count,
                    package_count=request.package_count,
                    package_type=request.package_type,
                    requested_service_date=request.requested_service_date,
                    valid_from=request.valid_from,
                    valid_to=request.valid_to,
                    expires_at=request.expires_at,
                    status=request.status,
                    quotation_policy_snapshot=request.quotation_policy_snapshot,
                    awarded_option_id=request.awarded_option_id,
                    margin_rules_json=dict(request.margin_rules),
                    context_json=dict(request.context),
                    created_at=request.created_at,
                    updated_at=request.updated_at,
                )
            )
        self.session.flush()
        for offer in sorted(self.quote_offers.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeQuoteOfferRow(
                    id=offer.id,
                    quote_request_id=offer.quote_request_id,
                    provider_party_ref=offer.provider_party_ref,
                    provider_role_ref=offer.provider_role_ref,
                    offer_number=offer.offer_number,
                    source=offer.source,
                    amount=offer.amount,
                    currency=offer.currency,
                    is_sealed=offer.is_sealed,
                    transit_time_days=offer.transit_time_days,
                    service_level=offer.service_level,
                    performance_score=offer.performance_score,
                    expires_at=offer.expires_at,
                    status=offer.status,
                    notes=offer.notes,
                    created_at=offer.created_at,
                    updated_at=offer.updated_at,
                )
            )
        self.session.flush()
        for option in sorted(self.quote_options.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeQuoteOptionRow(
                    id=option.id,
                    quote_request_id=option.quote_request_id,
                    option_name=option.option_name,
                    source_offer_id=option.source_offer_id,
                    payer_contract_id=option.payer_contract_id,
                    payee_contract_id=option.payee_contract_id,
                    payer_total_amount=option.payer_total_amount,
                    payee_total_amount=option.payee_total_amount,
                    margin_amount=option.margin_amount,
                    margin_percent=option.margin_percent,
                    transit_time_days=option.transit_time_days,
                    service_level_score=option.service_level_score,
                    policy_compliant=option.policy_compliant,
                    rank=option.rank,
                    score=option.score,
                    expires_at=option.expires_at,
                )
            )
        self.session.flush()
        for option in sorted(self.quote_options.values(), key=lambda item: item.id):
            for line in sorted(option.lines, key=lambda item: item.id):
                component = self.components_by_code.get(line.charge_component_code)
                if component is None:
                    continue
                self.session.merge(
                    ChargeQuoteOptionLineRow(
                        id=line.id,
                        quote_option_id=line.quote_option_id,
                        relationship_role=line.relationship_role,
                        payer_party_ref=line.payer_party_ref,
                        payee_party_ref=line.payee_party_ref,
                        party_role_ref=line.party_role_ref,
                        charge_component_id=component.id,
                        description=line.description,
                        amount=line.amount,
                        currency=line.currency,
                        basis=line.basis,
                        quantity_uom=line.quantity_uom,
                        allocation_basis=line.allocation_basis,
                        allocation_profile_id=line.allocation_profile_id,
                        allocation_profile_version_id=line.allocation_profile_version_id,
                        pinned_allocation_snapshot_json=dict(line.pinned_allocation_snapshot_json or {}),
                        effective_allocation_snapshot_json=dict(line.effective_allocation_snapshot_json or {}),
                        source_contract_id=line.source_contract_id,
                        source_rate_book_id=line.source_rate_book_id,
                        is_margin_line=line.is_margin_line,
                    )
                )
        self.session.flush()

    def _persist_documents(self) -> None:
        for document in sorted(self.documents.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeDocumentRow(
                    id=document.id,
                    document_number=document.document_number,
                    quote_request_id=document.quote_request_id,
                    quote_option_id=document.quote_option_id,
                    quotation_policy_snapshot=document.quotation_policy_snapshot,
                    source_object_type=document.source_object_type,
                    source_object_id=document.source_object_id,
                    document_scope_level=document.document_scope_level,
                    shipment_scope=document.shipment_scope,
                    document_date=document.document_date,
                    source_reference_snapshot_json=dict(document.source_reference_snapshot_json or {}),
                    company_id=document.company_id,
                    customer_id=document.customer_id,
                    vendor_id=document.vendor_id,
                    forwarder_id=document.forwarder_id,
                    carrier_id=document.carrier_id,
                    status=document.status,
                    currency=document.currency,
                    payer_total_amount=document.payer_total_amount,
                    payee_total_amount=document.payee_total_amount,
                    margin_amount=document.margin_amount,
                    approved_at=document.approved_at,
                    exported_at=document.exported_at,
                    reversed_at=document.reversed_at,
                    reversal_reason=document.reversal_reason,
                    created_at=document.created_at,
                )
            )
        self.session.flush()
        for document in sorted(self.documents.values(), key=lambda item: item.id):
            for line in _sorted_charge_lines(document.lines):
                component = self.components_by_code.get(line.charge_component_code)
                if component is None:
                    continue
                self.session.merge(_charge_line_row(line, component.id))
        self.session.flush()

    def _persist_quote_commitments(self) -> None:
        for commitment in sorted(self.quote_commitments.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeQuoteCommitmentRow(
                    id=commitment.id,
                    commitment_number=commitment.commitment_number,
                    quote_request_id=commitment.quote_request_id,
                    quote_option_id=commitment.quote_option_id,
                    charge_document_id=commitment.charge_document_id,
                    company_id=commitment.company_id,
                    customer_id=commitment.customer_id,
                    vendor_id=commitment.vendor_id,
                    forwarder_id=commitment.forwarder_id,
                    carrier_id=commitment.carrier_id,
                    origin_code=commitment.origin_code,
                    destination_code=commitment.destination_code,
                    mode=commitment.mode,
                    equipment_type=commitment.equipment_type,
                    commodity_code=commitment.commodity_code,
                    service_level=commitment.service_level,
                    package_type=commitment.package_type,
                    requested_service_date=commitment.requested_service_date,
                    valid_from=commitment.valid_from,
                    valid_to=commitment.valid_to,
                    committed_container_count=commitment.committed_container_count,
                    consumed_container_count=commitment.consumed_container_count,
                    committed_package_count=commitment.committed_package_count,
                    consumed_package_count=commitment.consumed_package_count,
                    committed_chargeable_weight=commitment.committed_chargeable_weight,
                    consumed_chargeable_weight=commitment.consumed_chargeable_weight,
                    committed_quantity=commitment.committed_quantity,
                    consumed_quantity=commitment.consumed_quantity,
                    committed_amount=commitment.committed_amount,
                    consumed_amount=commitment.consumed_amount,
                    currency=commitment.currency,
                    status=commitment.status,
                    created_at=commitment.created_at,
                    updated_at=commitment.updated_at,
                )
            )
        self.session.flush()
        for consumption in sorted(self.quote_commitment_consumptions.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeQuoteCommitmentConsumptionRow(
                    id=consumption.id,
                    commitment_id=consumption.commitment_id,
                    source_object_type=consumption.source_object_type,
                    source_object_id=consumption.source_object_id,
                    reference_number=consumption.reference_number,
                    container_count=consumption.container_count,
                    package_count=consumption.package_count,
                    chargeable_weight=consumption.chargeable_weight,
                    quantity=consumption.quantity,
                    amount=consumption.amount,
                    consumed_at=consumption.consumed_at,
                    status=consumption.status,
                    reversed_at=consumption.reversed_at,
                    reversal_reason=consumption.reversal_reason,
                )
            )
        self.session.flush()

    def _persist_invoices(self) -> None:
        for invoice in sorted(self.invoices.values(), key=lambda item: item.id):
            self.session.merge(
                ChargeInvoiceRow(
                    id=invoice.id,
                    charge_document_id=invoice.charge_document_id,
                    invoice_number=invoice.invoice_number,
                    invoice_type=invoice.invoice_type,
                    invoice_date=invoice.invoice_date,
                    currency=invoice.currency,
                    total_amount=invoice.total_amount,
                    status=invoice.status,
                    lines_json=list(invoice.lines),
                    created_at=invoice.created_at,
                    updated_at=invoice.updated_at,
                )
            )
        self.session.flush()

    def _persist_match_results(self) -> None:
        for result in sorted(self.match_results.values(), key=lambda item: item.id):
            component = self.components_by_code.get(result.charge_component_code)
            self.session.merge(
                ChargeMatchResultRow(
                    id=result.id,
                    invoice_id=result.invoice_id,
                    charge_document_id=result.charge_document_id,
                    charge_line_id=result.charge_line_id,
                    charge_component_id=component.id if component else None,
                    expected_amount=result.expected_amount,
                    invoice_amount=result.invoice_amount,
                    variance_amount=result.variance_amount,
                    variance_percent=result.variance_percent,
                    match_status=result.match_status,
                    notes=result.notes,
                )
            )
        self.session.flush()

    def _persist_exports(self) -> None:
        for export_number, response in sorted(self.exports.items(), key=lambda item: item[0]):
            export_id = self._export_ids.get(export_number)
            if export_id is None:
                export_id = int(export_number.rsplit("-", 1)[-1])
                self._export_ids[export_number] = export_id
            self.session.merge(
                ChargeExportBatchRow(
                    id=export_id,
                    export_number=export_number,
                    charge_document_id=response.document.id,
                    target_system=response.target_system,
                    status=response.status,
                    payload_json=dict(response.payload_json or {}),
                )
            )
        self.session.flush()


@dataclass
class DatabaseRepositoryControl:
    session_factory: sessionmaker[Session]

    def reset(self) -> None:
        with self.session_factory() as session:
            Base.metadata.create_all(session.get_bind())
            repository = SqlAlchemyChargeRepository(session)
            repository.reset()
            session.commit()

    def _read_setting(self, name: str) -> Any:
        with self.session_factory() as session:
            repository = SqlAlchemyChargeRepository(session)
            return getattr(repository, name)

    def _write_setting(self, name: str, value: Any) -> None:
        with self.session_factory() as session:
            repository = SqlAlchemyChargeRepository(session)
            setattr(repository, name, value)
            repository.flush()
            session.commit()

    @property
    def quotation_policy(self) -> str:
        return self._read_setting("quotation_policy")

    @quotation_policy.setter
    def quotation_policy(self, value: str) -> None:
        self._write_setting("quotation_policy", value)

    @property
    def quote_acceptance_mode(self) -> str:
        return self._read_setting("quote_acceptance_mode")

    @quote_acceptance_mode.setter
    def quote_acceptance_mode(self, value: str) -> None:
        self._write_setting("quote_acceptance_mode", value)

    @property
    def provider_cost_layer_enabled(self) -> bool:
        return bool(self._read_setting("provider_cost_layer_enabled"))

    @provider_cost_layer_enabled.setter
    def provider_cost_layer_enabled(self, value: bool) -> None:
        self._write_setting("provider_cost_layer_enabled", bool(value))

    @property
    def persisted_settings(self) -> ChargeManagementSettings:
        with self.session_factory() as session:
            return SqlAlchemyChargeRepository(session)._settings_model()

    @persisted_settings.setter
    def persisted_settings(self, value: ChargeManagementSettings) -> None:
        with self.session_factory() as session:
            repository = SqlAlchemyChargeRepository(session)
            repository.quotation_policy = value.quotation_policy
            repository.quote_acceptance_mode = value.quote_acceptance_mode
            repository.provider_cost_layer_enabled = value.provider_cost_layer_enabled
            repository.flush()
            session.commit()
