"""Tenant-scoped preview/confirm API for historical TOS and PL.03 sources."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Literal
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .database import audit, get_db, now_iso
from .historical import (
    HistoricalAuthorizationError, HistoricalTenantError, validate_import_actor,
    validate_reviewer, validate_vessel_link_tenant,
)
from .historical_tos_parser import (
    HistoricalWorkbookError, ParsedWorkbook, TRANSFORM_VERSION, json_dumps,
    normalize_vessel_name, parse_workbook,
)
from .models import (
    HistoricalCargoRow, HistoricalPortCall, HistoricalReportImport,
    HistoricalReportMetric, HistoricalReportRow, HistoricalVesselLink,
    ReportingUnitVessel, Vessel,
)
from .tenant import Scope, require_port_scope


router = APIRouter(prefix="/api/historical-imports", tags=["historical-imports"])
MAX_SOURCE_BYTES = 12 * 1024 * 1024
ACTIVE_IMPORT_STATUSES = ("COMMITTED", "REVIEW")
ROOT = Path(__file__).resolve().parents[1]
SOURCE_ARCHIVE_ROOT = Path(os.environ.get("HISTORICAL_SOURCE_DIR", ROOT / "data" / "historical_sources"))


class ConfirmHistoricalImport(BaseModel):
    conflict_action: Literal["KEEP_EXISTING", "ACTIVATE_NEW_REVISION"] | None = None
    reason: str = Field(default="", max_length=500)
    supersedes_import_id: int | None = None


class ResolveVesselLink(BaseModel):
    decision: Literal["ACCEPT", "REJECT"]
    candidate_vessel_id: int | None = None
    reason: str = Field(default="", max_length=500)


class CancelHistoricalImport(BaseModel):
    reason: str = Field(default="Người dùng hủy sau khi xem preview.", max_length=500)


def _authorize(db: Session, scope: Scope, *, reviewer: bool = False) -> None:
    try:
        validator = validate_reviewer if reviewer else validate_import_actor
        key = "reviewer" if reviewer else "user"
        validator(
            db, reporting_unit_id=scope.reporting_unit_id,
            platform_context=scope.user.role == "PLATFORM_ADMIN", **{key: scope.user},
        )
    except HistoricalAuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _source_filename(value: str | None) -> str:
    if not value:
        return "uploaded.xlsx"
    cleaned = Path(unquote(value).replace("\\", "/")).name.strip()
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", cleaned)[:255]
    return cleaned or "uploaded.xlsx"


def _archive_source(reporting_unit_id: int, checksum: str, content: bytes) -> str:
    directory = SOURCE_ARCHIVE_ROOT / str(reporting_unit_id)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{checksum}.xlsx"
    if not target.exists():
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(content)
        os.replace(temporary, target)
    return str(target.relative_to(SOURCE_ARCHIVE_ROOT)).replace("\\", "/")


def _import_json(item: HistoricalReportImport, *, conflicts: list[int] | None = None) -> dict[str, Any]:
    return {
        "id": item.id, "reportingUnitId": item.reporting_unit_id,
        "sourceKind": item.source_kind, "appendixKind": item.appendix_kind,
        "mappingVersion": item.mapping_version, "reportingPeriod": item.reporting_period,
        "sourceFilename": item.source_filename, "checksum": item.source_checksum,
        "sourceSizeBytes": item.source_size_bytes, "status": item.status,
        "revisionNo": item.revision_no, "supersededByImportId": item.superseded_by_import_id,
        "accepted": item.accepted_count, "review": item.review_count,
        "rejected": item.rejected_count, "createdAt": item.created_at,
        "conflictingImportIds": conflicts or [],
    }


def _registered_vessels(db: Session, unit_id: int) -> list[Vessel]:
    return (
        db.query(Vessel).join(ReportingUnitVessel, ReportingUnitVessel.vessel_id == Vessel.id)
        .filter(ReportingUnitVessel.reporting_unit_id == unit_id).all()
    )


def _candidate_link(vessels: list[Vessel], vessel_name: str) -> tuple[Vessel | None, str, str, str]:
    exact = [item for item in vessels if item.name.strip() == vessel_name.strip()]
    if len(exact) == 1:
        return exact[0], "EXACT", "HIGH", ""
    normalized = normalize_vessel_name(vessel_name)
    candidates = [item for item in vessels if normalize_vessel_name(item.name) == normalized]
    if len(candidates) == 1:
        return candidates[0], "NORMALIZED", "MEDIUM", "REVIEW_NORMALIZED_VESSEL_LINK"
    if not candidates:
        return None, "", "LOW", "UNMATCHED_VESSEL"
    return None, "", "LOW", "AMBIGUOUS_VESSEL"


def _active_calls_by_key(
    db: Session, unit_id: int, keys: set[str],
) -> dict[str, list[HistoricalPortCall]]:
    """Load calls in bounded chunks; never perform one lookup per source row."""
    result: dict[str, list[HistoricalPortCall]] = {key: [] for key in keys if key}
    ordered = sorted(result)
    for offset in range(0, len(ordered), 500):
        rows = (
            db.query(HistoricalPortCall)
            .join(HistoricalReportImport, HistoricalReportImport.id == HistoricalPortCall.import_id)
            .filter(
                HistoricalPortCall.reporting_unit_id == unit_id,
                HistoricalPortCall.call_key_normalized.in_(ordered[offset:offset + 500]),
                HistoricalReportImport.reporting_unit_id == unit_id,
                HistoricalReportImport.status.in_(ACTIVE_IMPORT_STATUSES),
            ).all()
        )
        for row in rows:
            result.setdefault(row.call_key_normalized, []).append(row)
    return result


def _stage_berth(db: Session, item: HistoricalReportImport, parsed: ParsedWorkbook) -> None:
    vessels = _registered_vessels(db, item.reporting_unit_id)
    for source in parsed.rows:
        status = source["validation_status"]
        ambiguity = source["ambiguity_status"]
        candidate, method, confidence, link_warning = _candidate_link(
            vessels, source["vessel_name_raw"]
        )
        warnings = list(source["warnings"])
        if link_warning:
            warnings.append(link_warning)
            status = "REVIEW" if status != "REJECTED" else status
            if link_warning == "UNMATCHED_VESSEL":
                ambiguity = "UNMATCHED"
            elif link_warning == "AMBIGUOUS_VESSEL":
                ambiguity = "AMBIGUOUS"
        call = HistoricalPortCall(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id,
            source_sheet=source["source_sheet"], source_row=source["source_row"],
            mapping_version=item.mapping_version,
            vessel_name_raw=source["vessel_name_raw"],
            vessel_name_normalized=source["vessel_name_normalized"],
            call_year_raw=source["call_year_raw"], voyage_number_raw=source["voyage_number_raw"],
            call_key_normalized=source["call_key_normalized"],
            source_berth_raw=source["source_berth_raw"], arrival_berth=source["arrival_berth"],
            departure_berth=source["departure_berth"], berth_correction_json="{}",
            actual_berthing_at_raw=source["actual_berthing_at_raw"],
            actual_berthing_at=source["actual_berthing_at"],
            actual_departure_at_raw=source["actual_departure_at_raw"],
            actual_departure_at=source["actual_departure_at"],
            reporting_month=source["reporting_month"], validation_status=status,
            ambiguity_status=ambiguity, reconciliation_status="NONE",
            provenance_json=json_dumps({**source["provenance"], "warnings": warnings}),
            created_at=now_iso(),
        )
        db.add(call)
        db.flush()
        db.add(HistoricalVesselLink(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id, port_call_id=call.id,
            raw_vessel_name=source["vessel_name_raw"],
            normalized_vessel_name=source["vessel_name_normalized"],
            candidate_vessel_id=candidate.id if candidate else None,
            match_method=method, confidence=confidence, link_status="PENDING",
            reason=link_warning, created_at=now_iso(),
        ))


def _stage_cargo(db: Session, item: HistoricalReportImport, parsed: ParsedWorkbook) -> None:
    periods: set[str] = set()
    calls_by_key = _active_calls_by_key(
        db, item.reporting_unit_id,
        {source["call_key_normalized"] for source in parsed.rows if source["call_key_normalized"]},
    )
    for source in parsed.rows:
        calls = calls_by_key.get(source["call_key_normalized"], [])
        status = source["validation_status"]
        if len(calls) == 1:
            call = calls[0]
            match_status = "MATCHED"
            if call.reporting_month:
                periods.add(call.reporting_month)
        elif not calls:
            call, match_status = None, "UNMATCHED"
            status = "REVIEW" if status != "REJECTED" else status
        else:
            call, match_status = None, "AMBIGUOUS"
            status = "REVIEW" if status != "REJECTED" else status
        db.add(HistoricalCargoRow(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id,
            source_sheet=source["source_sheet"], source_row=source["source_row"],
            port_call_id=call.id if call else None,
            source_call_key_raw=source["source_call_key_raw"],
            call_key_normalized=source["call_key_normalized"],
            container_size_code_raw=source["container_size_code_raw"],
            teu_factor=source["teu_factor"], full_empty_code_raw=source["full_empty_code_raw"],
            trade_scope_raw=source["trade_scope_raw"], movement_method_raw=source["movement_method_raw"],
            derived_direction=source["derived_direction"], weight_raw=source["weight_raw"],
            weight_tonnes=source["weight_tonnes"], weight_state=source["weight_state"],
            transform_version=TRANSFORM_VERSION, match_status=match_status,
            validation_status=status,
            provenance_json=json_dumps({**source["provenance"], "warnings": source["warnings"]}),
            created_at=now_iso(),
        ))
    if len(periods) == 1:
        item.reporting_period = next(iter(periods))


def _stage_pl03(db: Session, item: HistoricalReportImport, parsed: ParsedWorkbook) -> None:
    for source in parsed.rows:
        row = HistoricalReportRow(
            reporting_unit_id=item.reporting_unit_id, import_id=item.id,
            source_sheet=source["source_sheet"], source_row=source["source_row"],
            appendix_row_no=source["appendix_row_no"],
            normalized_registration=normalize_vessel_name(source["registration_raw"]),
            raw_payload_json=json_dumps(source["raw_payload"]),
            mapped_dimensions_json=json_dumps({
                "vesselNameRaw": source["vessel_name_raw"],
                "registrationRaw": source["registration_raw"],
            }), validation_status=source["validation_status"],
            warning_json=json_dumps(source["warnings"]),
            provenance_json=json_dumps(source["provenance"]), created_at=now_iso(),
        )
        db.add(row)
        db.flush()
        for metric in source["metrics"]:
            code = metric["metric_code"]
            db.add(HistoricalReportMetric(
                reporting_unit_id=item.reporting_unit_id, import_id=item.id, row_id=row.id,
                metric_code=code, direction="", category="", unit="tonne" if "tons" in code else "teu",
                value_class="REPORTED_TOTAL", numeric_value=metric["numeric_value"],
                text_value=metric["text_value"], value_state=metric["value_state"],
                source_cell=metric["source_cell"], source_header_raw="",
                mapping_version=item.mapping_version,
                reconciliation_status="REVIEW" if metric["invalid"] else "NONE",
                created_at=now_iso(),
            ))


def _refresh_counts(db: Session, item: HistoricalReportImport) -> None:
    model = {
        "tos_berth_call": HistoricalPortCall,
        "tos_cargo_detail": HistoricalCargoRow,
        "reported_pl03": HistoricalReportRow,
    }[item.source_kind]
    counts = dict(
        db.query(model.validation_status, func.count(model.id))
        .filter(model.import_id == item.id, model.reporting_unit_id == item.reporting_unit_id)
        .group_by(model.validation_status).all()
    )
    item.accepted_count = counts.get("VALID", 0)
    item.review_count = counts.get("REVIEW", 0)
    item.rejected_count = counts.get("REJECTED", 0)
    item.updated_at = now_iso()


def _reconcile_active_cargo_links(db: Session, unit_id: int, actor_user_id: int) -> None:
    """Re-link active cargo after a Berth revision becomes authoritative.

    A corrected Berth file supersedes its former calls.  Cargo facts remain tied
    to their own immutable source import, but their tenant-safe call reference
    must follow the single active call for the audited normalized key.
    """
    cargo_imports = (
        db.query(HistoricalReportImport).filter(
            HistoricalReportImport.reporting_unit_id == unit_id,
            HistoricalReportImport.source_kind == "tos_cargo_detail",
            HistoricalReportImport.status.in_(("PREVIEWED", "COMMITTED", "REVIEW")),
        ).all()
    )
    for cargo_import in cargo_imports:
        periods: set[str] = set()
        rows = db.query(HistoricalCargoRow).filter_by(
            reporting_unit_id=unit_id, import_id=cargo_import.id,
        ).all()
        calls_by_key = _active_calls_by_key(
            db, unit_id, {row.call_key_normalized for row in rows if row.call_key_normalized},
        )
        for row in rows:
            calls = calls_by_key.get(row.call_key_normalized, [])
            if len(calls) == 1:
                row.port_call_id = calls[0].id
                row.match_status = "MATCHED"
                if calls[0].reporting_month:
                    periods.add(calls[0].reporting_month)
                if row.validation_status != "REJECTED":
                    warnings = json.loads(row.provenance_json or "{}").get("warnings", [])
                    row.validation_status = "REVIEW" if warnings else "VALID"
            else:
                row.port_call_id = None
                row.match_status = "UNMATCHED" if not calls else "AMBIGUOUS"
                if row.validation_status != "REJECTED":
                    row.validation_status = "REVIEW"
        cargo_import.reporting_period = next(iter(periods)) if len(periods) == 1 else None
        db.flush()
        _refresh_counts(db, cargo_import)
        if cargo_import.status == "REVIEW" and cargo_import.review_count == 0:
            cargo_import.status = "COMMITTED"
        audit(
            db, "historical_report_import", cargo_import.id, "CARGO_CALLS_RECONCILED",
            f"{cargo_import.accepted_count} valid, {cargo_import.review_count} review",
            actor_user_id=actor_user_id, reporting_unit_id=unit_id,
        )


def _conflicts(db: Session, item: HistoricalReportImport) -> list[HistoricalReportImport]:
    query = db.query(HistoricalReportImport).filter(
        HistoricalReportImport.reporting_unit_id == item.reporting_unit_id,
        HistoricalReportImport.source_kind == item.source_kind,
        HistoricalReportImport.id != item.id,
        HistoricalReportImport.status.in_(("COMMITTED", "REVIEW")),
    )
    # A parser/mapping correction intentionally creates a new receipt for the
    # same immutable source checksum.  Treat the active older mapping as a
    # conflict even when a legacy report has no reliable reporting period, so
    # confirmation supersedes it instead of leaving two apparently active rows.
    same_source = query.filter(
        HistoricalReportImport.source_checksum == item.source_checksum,
    ).all()
    if same_source:
        return same_source
    if item.reporting_period:
        return query.filter(HistoricalReportImport.reporting_period == item.reporting_period).all()
    if item.source_kind == "tos_cargo_detail":
        ids = [row[0] for row in db.query(HistoricalCargoRow.import_id)
               .filter(HistoricalCargoRow.import_id != item.id,
                       HistoricalCargoRow.reporting_unit_id == item.reporting_unit_id,
                       HistoricalCargoRow.call_key_normalized.in_(
                           db.query(HistoricalCargoRow.call_key_normalized).filter(
                               HistoricalCargoRow.import_id == item.id,
                               HistoricalCargoRow.reporting_unit_id == item.reporting_unit_id,
                           )
                       )).distinct().all()]
        return query.filter(HistoricalReportImport.id.in_(ids)).all() if ids else []
    return []


@router.post("/preview")
async def preview_historical_import(
    request: Request,
    x_source_filename: str | None = Header(default=None, alias="X-Source-Filename"),
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="File trống.")
    if len(content) > MAX_SOURCE_BYTES:
        raise HTTPException(status_code=413, detail="File vượt quá giới hạn 12 MB.")
    if not content.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=400, detail="File không đúng định dạng XLSX.")
    try:
        parsed = parse_workbook(content)
    except HistoricalWorkbookError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    checksum = hashlib.sha256(content).hexdigest()
    prior = db.query(HistoricalReportImport).filter_by(
        reporting_unit_id=scope.reporting_unit_id, source_kind=parsed.source_kind,
        source_checksum=checksum, mapping_version=parsed.mapping_version,
    ).first()
    if prior:
        _archive_source(scope.reporting_unit_id, checksum, content)
        return {**_import_json(prior, conflicts=[i.id for i in _conflicts(db, prior)]), "idempotent": True}
    archive_key = _archive_source(scope.reporting_unit_id, checksum, content)
    receipt = dict(parsed.receipt)
    receipt.update({"sourceArchiveKey": archive_key, "checksumAlgorithm": "sha256"})
    item = HistoricalReportImport(
        reporting_unit_id=scope.reporting_unit_id, source_kind=parsed.source_kind,
        appendix_kind=parsed.appendix_kind, mapping_version=parsed.mapping_version,
        reporting_period=parsed.reporting_period, source_filename=_source_filename(x_source_filename),
        source_checksum=checksum, source_size_bytes=len(content),
        source_sheets_json=json_dumps([parsed.sheet_name]), status="PREVIEWED",
        revision_no=1, accepted_count=0, rejected_count=0, review_count=0,
        mapping_receipt_json=json_dumps(receipt), created_by_user_id=scope.user.id,
        created_at=now_iso(), updated_at=now_iso(),
    )
    db.add(item)
    db.flush()
    if parsed.source_kind == "tos_berth_call":
        _stage_berth(db, item, parsed)
    elif parsed.source_kind == "tos_cargo_detail":
        _stage_cargo(db, item, parsed)
    else:
        _stage_pl03(db, item, parsed)
    db.flush()
    _refresh_counts(db, item)
    audit(db, "historical_report_import", item.id, "IMPORT_PREVIEWED",
          f"{item.source_kind} / {item.source_checksum[:12]}", actor_user_id=scope.user.id,
          reporting_unit_id=scope.reporting_unit_id)
    db.commit()
    db.refresh(item)
    return {**_import_json(item, conflicts=[i.id for i in _conflicts(db, item)]), "idempotent": False,
            "mappingReceipt": receipt}


@router.get("")
def list_historical_imports(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    query = db.query(HistoricalReportImport).filter_by(reporting_unit_id=scope.reporting_unit_id)
    total = query.count()
    items = query.order_by(HistoricalReportImport.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [_import_json(item) for item in items], "page": page, "pageSize": page_size, "total": total}


@router.get("/{import_id}")
def historical_import_detail(
    import_id: int, db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    item = db.query(HistoricalReportImport).filter_by(
        id=import_id, reporting_unit_id=scope.reporting_unit_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt import.")
    return {
        **_import_json(item, conflicts=[entry.id for entry in _conflicts(db, item)]),
        "mappingReceipt": json.loads(item.mapping_receipt_json or "{}"),
        "sourceSheets": json.loads(item.source_sheets_json or "[]"),
        "supersedeReason": item.supersede_reason,
    }


@router.get("/{import_id}/rows")
def historical_import_rows(
    import_id: int, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    status_filter: Literal["VALID", "REVIEW", "REJECTED"] | None = Query(
        default=None, alias="status"
    ),
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    item = db.query(HistoricalReportImport).filter_by(id=import_id, reporting_unit_id=scope.reporting_unit_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt import.")
    model = {"tos_berth_call": HistoricalPortCall, "tos_cargo_detail": HistoricalCargoRow,
             "reported_pl03": HistoricalReportRow}[item.source_kind]
    query = db.query(model).filter_by(import_id=item.id, reporting_unit_id=scope.reporting_unit_id)
    if status_filter:
        query = query.filter(model.validation_status == status_filter)
    total = query.count()
    rows = query.order_by(model.source_row).offset((page - 1) * page_size).limit(page_size).all()
    if model is HistoricalPortCall:
        payload = [{"id": row.id, "sourceRow": row.source_row, "vesselName": row.vessel_name_raw,
                    "year": row.call_year_raw, "voyage": row.voyage_number_raw,
                    "berth": row.source_berth_raw, "atb": row.actual_berthing_at_raw,
                    "atd": row.actual_departure_at_raw, "reportingMonth": row.reporting_month,
                    "validationStatus": row.validation_status, "ambiguityStatus": row.ambiguity_status,
                    "warnings": json.loads(row.provenance_json or "{}").get("warnings", []),
                    "provenance": json.loads(row.provenance_json)} for row in rows]
    elif model is HistoricalCargoRow:
        payload = [{"id": row.id, "sourceRow": row.source_row, "sourceCallKey": row.source_call_key_raw,
                    "size": row.container_size_code_raw, "teuFactor": row.teu_factor,
                    "fullEmpty": row.full_empty_code_raw, "trade": row.trade_scope_raw,
                    "method": row.movement_method_raw, "direction": row.derived_direction,
                    "weightTonnes": row.weight_tonnes, "weightState": row.weight_state,
                    "matchStatus": row.match_status, "validationStatus": row.validation_status,
                    "warnings": json.loads(row.provenance_json or "{}").get("warnings", []),
                    "provenance": json.loads(row.provenance_json)} for row in rows]
    else:
        payload = [{"id": row.id, "sourceRow": row.source_row, "appendixRowNo": row.appendix_row_no,
                    "dimensions": json.loads(row.mapped_dimensions_json),
                    "validationStatus": row.validation_status, "warnings": json.loads(row.warning_json),
                    "provenance": json.loads(row.provenance_json)} for row in rows]
    return {"items": payload, "page": page, "pageSize": page_size, "total": total,
            "status": status_filter}


@router.get("/{import_id}/vessel-links")
def historical_vessel_links(
    import_id: int, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    status_filter: Literal["PENDING", "ACCEPTED", "REJECTED"] | None = Query(
        default=None, alias="status"
    ),
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    item = db.query(HistoricalReportImport).filter_by(
        id=import_id, reporting_unit_id=scope.reporting_unit_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt import.")
    query = db.query(HistoricalVesselLink).filter_by(
        import_id=import_id, reporting_unit_id=scope.reporting_unit_id,
    )
    if status_filter:
        query = query.filter(HistoricalVesselLink.link_status == status_filter)
    total = query.count()
    links = query.order_by(HistoricalVesselLink.id).offset((page - 1) * page_size).limit(page_size).all()
    candidates = {
        vessel.id: vessel for vessel in db.query(Vessel).filter(
            Vessel.id.in_([link.candidate_vessel_id for link in links if link.candidate_vessel_id])
        ).all()
    }
    return {
        "items": [{
            "id": link.id, "portCallId": link.port_call_id,
            "rawVesselName": link.raw_vessel_name,
            "normalizedVesselName": link.normalized_vessel_name,
            "rawRegistration": link.raw_registration,
            "candidateVesselId": link.candidate_vessel_id,
            "candidateVesselName": candidates.get(link.candidate_vessel_id).name
                if candidates.get(link.candidate_vessel_id) else None,
            "candidateRegistration": candidates.get(link.candidate_vessel_id).registration_no
                if candidates.get(link.candidate_vessel_id) else None,
            "matchMethod": link.match_method, "confidence": link.confidence,
            "status": link.link_status, "reason": link.reason,
        } for link in links],
        "page": page, "pageSize": page_size, "total": total,
    }


@router.post("/{import_id}/cancel")
def cancel_historical_import(
    import_id: int, body: CancelHistoricalImport,
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    item = db.query(HistoricalReportImport).filter_by(
        id=import_id, reporting_unit_id=scope.reporting_unit_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt import.")
    if item.status == "REJECTED":
        return {**_import_json(item), "idempotent": True}
    if item.status != "PREVIEWED":
        raise HTTPException(status_code=409, detail="Chỉ có thể hủy lượt import đang ở bước preview.")
    item.status = "REJECTED"
    item.supersede_reason = body.reason.strip() or "Người dùng hủy sau khi xem preview."
    item.updated_at = now_iso()
    audit(db, "historical_report_import", item.id, "IMPORT_PREVIEW_CANCELLED",
          item.supersede_reason, actor_user_id=scope.user.id,
          reporting_unit_id=scope.reporting_unit_id)
    db.commit()
    return _import_json(item)


@router.post("/{import_id}/confirm")
def confirm_historical_import(
    import_id: int, body: ConfirmHistoricalImport,
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope)
    item = db.query(HistoricalReportImport).filter_by(id=import_id, reporting_unit_id=scope.reporting_unit_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt import.")
    if item.status != "PREVIEWED":
        return {**_import_json(item), "idempotent": True}
    conflicts = _conflicts(db, item)
    if body.supersedes_import_id is not None:
        conflicts = [entry for entry in conflicts if entry.id == body.supersedes_import_id]
        if not conflicts:
            raise HTTPException(status_code=409, detail="Bản được chọn không phải xung đột cùng đơn vị/nguồn/kỳ.")
    if conflicts and body.conflict_action is None:
        raise HTTPException(status_code=409, detail={
            "message": "Dữ liệu trùng phạm vi đã lưu; cần chọn giữ bản cũ hoặc kích hoạt revision mới.",
            "conflictingImportIds": [entry.id for entry in conflicts],
        })
    if conflicts and body.conflict_action == "KEEP_EXISTING":
        item.status = "REJECTED"
        item.supersede_reason = body.reason or "Giữ dữ liệu hiện có theo xác nhận người dùng."
        item.updated_at = now_iso()
        audit(db, "historical_report_import", item.id, "IMPORT_CONFLICT_KEEP_EXISTING",
              item.supersede_reason, actor_user_id=scope.user.id, reporting_unit_id=scope.reporting_unit_id)
        db.commit()
        return _import_json(item, conflicts=[entry.id for entry in conflicts])
    if conflicts:
        if not body.reason.strip():
            raise HTTPException(status_code=422, detail="Cần ghi lý do khi kích hoạt revision mới.")
        item.revision_no = max(entry.revision_no for entry in conflicts) + 1
        for prior in conflicts:
            prior.status = "SUPERSEDED"
            prior.superseded_by_import_id = item.id
            prior.supersede_reason = body.reason.strip()
            prior.updated_at = now_iso()
    item.status = "REVIEW" if item.review_count else "COMMITTED"
    item.supersede_reason = body.reason.strip()
    item.updated_at = now_iso()
    audit(db, "historical_report_import", item.id, "IMPORT_CONFIRMED",
          f"{item.source_kind} revision {item.revision_no}; {item.accepted_count} valid, "
          f"{item.review_count} review, {item.rejected_count} rejected",
          actor_user_id=scope.user.id, reporting_unit_id=scope.reporting_unit_id)
    db.flush()
    if item.source_kind == "tos_berth_call":
        _reconcile_active_cargo_links(db, scope.reporting_unit_id, scope.user.id)
    db.commit()
    db.refresh(item)
    return _import_json(item, conflicts=[entry.id for entry in conflicts])


@router.post("/{import_id}/vessel-links/{link_id}/resolve")
def resolve_historical_vessel_link(
    import_id: int, link_id: int, body: ResolveVesselLink,
    db: Session = Depends(get_db), scope: Scope = Depends(require_port_scope),
):
    _authorize(db, scope, reviewer=True)
    link = db.query(HistoricalVesselLink).filter_by(
        id=link_id, import_id=import_id, reporting_unit_id=scope.reporting_unit_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Không tìm thấy liên kết phương tiện.")
    item = db.query(HistoricalReportImport).filter_by(
        id=import_id, reporting_unit_id=scope.reporting_unit_id,
    ).one()
    if item.status in {"REJECTED", "SUPERSEDED"}:
        raise HTTPException(
            status_code=409,
            detail="Không thể xử lý liên kết của lượt import đã hủy hoặc đã được thay thế.",
        )
    if body.decision == "ACCEPT":
        candidate_id = body.candidate_vessel_id or link.candidate_vessel_id
        if candidate_id is None:
            raise HTTPException(status_code=422, detail="Cần chọn phương tiện để chấp nhận liên kết.")
        try:
            validate_vessel_link_tenant(
                db, reporting_unit_id=scope.reporting_unit_id, candidate_vessel_id=candidate_id,
            )
        except HistoricalTenantError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        previous_candidate_id = link.candidate_vessel_id
        link.candidate_vessel_id = candidate_id
        link.link_status = "ACCEPTED"
        link.match_method = "MANUAL" if candidate_id != previous_candidate_id else link.match_method
        if link.port_call_id:
            call = db.query(HistoricalPortCall).filter_by(
                id=link.port_call_id, reporting_unit_id=scope.reporting_unit_id,
            ).first()
            if call:
                call.vessel_id = candidate_id
                if call.ambiguity_status in {"UNMATCHED", "AMBIGUOUS"}:
                    call.ambiguity_status = "NONE"
                original_warnings = json.loads(call.provenance_json or "{}").get("warnings", [])
                link_warnings = {
                    "REVIEW_NORMALIZED_VESSEL_LINK", "UNMATCHED_VESSEL", "AMBIGUOUS_VESSEL",
                }
                if call.validation_status != "REJECTED" and not any(
                    warning not in link_warnings for warning in original_warnings
                ):
                    call.validation_status = "VALID"
    else:
        link.link_status = "REJECTED"
    link.reason = body.reason.strip()
    link.reviewed_by_user_id = scope.user.id
    link.reviewed_at = now_iso()
    audit(db, "historical_vessel_link", link.id, f"LINK_{link.link_status}",
          link.reason or link.raw_vessel_name, actor_user_id=scope.user.id,
          reporting_unit_id=scope.reporting_unit_id)
    db.flush()
    _refresh_counts(db, item)
    if item.status == "REVIEW" and item.review_count == 0:
        item.status = "COMMITTED"
    db.commit()
    return {"id": link.id, "status": link.link_status, "candidateVesselId": link.candidate_vessel_id}
