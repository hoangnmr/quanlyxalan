"""
Quản Lý Xalan FastAPI backend — T0 Baseline Recovery
WO-KBCV-T0-20260711

Entry point: python -m uvicorn backend.app:app --host 127.0.0.1 --port 8080
"""
from __future__ import annotations

import json
import hashlib
import logging
import os
import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, status
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import desc, func, or_, text
from sqlalchemy import false as sql_false
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import create_access_token, get_current_user, get_password_hash, verify_password
from .integrations import maritime_authority_adapter, registry_adapter
from .logging_config import configure_local_logging
from .mailer import (
    SMTP_SETTING_KEY, get_smtp_config, mailer_enabled as email_notifications_enabled, send_email,
)
from .notifications import notify_cancel_requested, notify_declaration_submitted, notify_declaration_workflow
from .rbac import require_roles
from .tenant import (
    resolve_scope, require_port_scope, Scope, register_vessel_ids,
    scope_allows_vessel, require_vessel_in_scope,
)
from .storage import ScannerNotConfigured, get_attachment_storage
from .database import (
    SQLALCHEMY_DATABASE_URL, SessionLocal, audit, cargo, correlation_id, engine, now_iso,
)
from .models import (
    AppSetting, Attachment, AuditEvent, Base, CrewMember, Declaration,
    DeclarationCrew, DeclarationEvent, ImportJob, IntegrationConnector, Organization,
    ReportAdjustment, SyncJob, User, Vessel, VesselOperatingProfile,
    ReportingUnit, ReportingUnitOrganization, ReportingUnitUser, ReportingUnitVessel,
    HistoricalCargoRow, HistoricalPortCall, HistoricalReportImport,
)
from .xlsx_io import (
    crew_rows, declaration_row, excel_date, import_match_key, make_report_xlsx,
    make_xlsx, read_workbook, vessel_rows,
)
from .historical_api import router as historical_import_router
from scripts.backup_local import (
    BACKUP_GLOB,
    BACKUP_SUFFIX,
    backup as create_local_backup,
    prune as prune_local_backups,
)

IMPORT_MAPPING_VERSION = "KBCV-IMPORT-1.5"
DEMO_ORGANIZATION_TAX_CODE = "DEMO-TANTHUAN-2026"
CREW_ROLES = ("Thuyền trưởng", "Máy trưởng", "Thuyền viên", "Thuyền phó")
CREW_ROLE_CANONICAL = {import_match_key(role): role for role in CREW_ROLES}

ROOT = Path(__file__).resolve().parents[1]
access_logger = configure_local_logging(ROOT)
ATTACHMENT_DIR = ROOT / "data" / "attachments"
ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR = ROOT / "data" / "backups"
attachment_storage = get_attachment_storage(ATTACHMENT_DIR / "quarantine")
attachment_scanner = ScannerNotConfigured()

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Quản Lý Xalan API", version="1.0.0")
app.include_router(historical_import_router)


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    request_id = request.headers.get("X-Correlation-ID", "").strip() or str(uuid.uuid4())
    token = correlation_id.set(request_id[:128])
    started = datetime.now()
    try:
        response = await call_next(request)
    finally:
        correlation_id.reset(token)
    response.headers["X-Correlation-ID"] = request_id[:128]
    access_logger.info(
        "%s %s status=%s duration_ms=%s correlation_id=%s",
        request.method, request.url.path, response.status_code,
        int((datetime.now() - started).total_seconds() * 1000), request_id[:128],
    )
    return response


# Recognize the common unique constraints so the 409 can name what actually
# collided, instead of a generic message that leaves the user guessing which
# field to change (e.g. an existing Vessel.registration_no or Organization.name
# used elsewhere in the system, not necessarily in the caller's own tenant).
_CONSTRAINT_MESSAGES = (
    ("vessels.registration_no", "Số đăng ký phương tiện này đã được dùng cho một hồ sơ khác trong hệ thống."),
    ("registration_no", "Số đăng ký phương tiện này đã được dùng cho một hồ sơ khác trong hệ thống."),
    ("organizations.name", "Đã có tổ chức khác dùng đúng tên này trong hệ thống. Kiểm tra lại tên doanh nghiệp hoặc chọn tổ chức có sẵn."),
    ("declarations.reference_no", "Mã phiếu bị trùng, vui lòng thử lưu lại."),
    ("reference_no", "Mã phiếu bị trùng, vui lòng thử lưu lại."),
    ("users.username", "Tên đăng nhập này đã được sử dụng."),
    ("username", "Tên đăng nhập này đã được sử dụng."),
)


@app.exception_handler(IntegrityError)
async def database_constraint_error(_: Request, exc: IntegrityError) -> JSONResponse:
    detail_text = str(getattr(exc, "orig", exc)).lower()
    message = "Dữ liệu xung đột với một bản ghi đã tồn tại."
    for needle, specific in _CONSTRAINT_MESSAGES:
        if needle in detail_text:
            message = specific
            break
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": message},
    )

origins_env = os.getenv("ALLOWED_ORIGINS")
if origins_env:
    origins = [o.strip() for o in origins_env.split(",") if o.strip()]
else:
    origins = ["http://127.0.0.1:8080", "http://localhost:8080"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB dependency ──────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# ── Attachment signature rules ─────────────────────────────────────────────────
MAGIC_BYTES: dict[str, bytes] = {
    ".pdf": b"%PDF",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG",
    ".xlsx": b"PK\x03\x04",
    ".xls": b"\xd0\xcf",
    ".doc": b"\xd0\xcf",
    ".docx": b"PK\x03\x04",
    ".webp": b"RIFF",
}
ALLOWED_ATTACHMENT_EXTENSIONS = frozenset(MAGIC_BYTES)
MAX_ATTACHMENT_BYTES = 12 * 1024 * 1024  # 12 MB


def validate_attachment_content(extension: str, content: bytes) -> None:
    extension = extension.lower()
    if extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Phần mở rộng file không được hỗ trợ.")
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise HTTPException(status_code=413, detail="File vượt quá giới hạn 12 MB.")
    expected = MAGIC_BYTES[extension]
    if not content.startswith(expected):
        raise HTTPException(
            status_code=400,
            detail=f"File không đúng định dạng {extension} (magic bytes không khớp).",
        )


# ── Certificate helper ─────────────────────────────────────────────────────────
def certificate_status(value: Optional[str], warning_days: int = 30) -> str:
    if not value:
        return "UNKNOWN"
    try:
        expiry = date.fromisoformat(value[:10])
    except ValueError:
        return "UNKNOWN"
    remaining = (expiry - date.today()).days
    if remaining < 0:
        return "EXPIRED"
    if remaining <= warning_days:
        return "EXPIRING"
    return "VALID"


# ── Workflow state machine ─────────────────────────────────────────────────────
WORKFLOW_TRANSITIONS: dict[str, dict[str, str]] = {
    "PORT_APPROVE":      {"from": "PENDING_REVIEW",  "to": "APPROVED"},
    "REQUEST_CHANGES":   {"from": "PENDING_REVIEW",  "to": "CHANGES_REQUESTED"},
    # Hủy thật (workflow_status = CANCELLED) — chỉ PLATFORM_ADMIN, từ cả 2
    # trạng thái nguồn (khách đổi ý trước khi kịp duyệt, hoặc hủy sau khi đã
    # duyệt). Xem ROADMAP_PORT_OPERATIONS.md Giai đoạn 4 — nhân viên khác dùng
    # /cancel-request (không đổi workflow_status), không đi qua action này.
    "CANCEL_FROM_PENDING":  {"from": "PENDING_REVIEW", "to": "CANCELLED"},
    "CANCEL_FROM_APPROVED": {"from": "APPROVED",        "to": "CANCELLED"},
}

# require_port_scope (dùng ở endpoint /workflow) cho phép cả PORT_STAFF lẫn
# PLATFORM_ADMIN gọi — không đủ để giới hạn hủy thật cho riêng Admin, nên kiểm
# tra role thêm ở đây.
ADMIN_ONLY_WORKFLOW_ACTIONS = frozenset({"CANCEL_FROM_PENDING", "CANCEL_FROM_APPROVED"})

RETIRED_WORKFLOW_ACTIONS = frozenset({"CV_APPROVE", "QLC_APPROVE", "BP_APPROVE", "ISSUE", "REVOKE"})


def _apply_workflow_transition(
    db: Session, declaration: Declaration, action: str, actor_role: str,
    actor_name: str, actor_user_id: int, note: str = ""
) -> Declaration:
    rule = WORKFLOW_TRANSITIONS.get(action)
    if not rule:
        raise HTTPException(status_code=400, detail=f"Hành động '{action}' không hợp lệ.")

    if action in ADMIN_ONLY_WORKFLOW_ACTIONS and actor_role != "PLATFORM_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Chỉ Platform admin mới được hủy phiếu trực tiếp. Dùng yêu cầu hủy để gửi Admin duyệt.",
        )

    current = declaration.workflow_status
    required_from = rule["from"]
    if required_from and current != required_from:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể thực hiện '{action}' từ trạng thái '{current}'. "
                   f"Cần trạng thái '{required_from}'.",
        )
    if action == "REQUEST_CHANGES" and not note.strip():
        raise HTTPException(status_code=400, detail="Cần nhập lý do cho thao tác này.")

    new_status = rule["to"]
    from_status = current
    declaration.workflow_status = new_status

    if action == "PORT_APPROVE":
        declaration.port_approval = "APPROVED"

    if action in ADMIN_ONLY_WORKFLOW_ACTIONS:
        # Hủy thật giải quyết dứt điểm mọi yêu cầu hủy đang chờ (nếu có) — dọn
        # 2 cột yêu cầu để không còn dữ liệu treo trên một phiếu đã CANCELLED.
        declaration.cancel_requested_at = None
        declaration.cancel_requested_by_user_id = None

    declaration.updated_at = now_iso()
    declaration.version += 1

    event = DeclarationEvent(
        declaration_id=declaration.id,
        action=action,
        from_status=from_status,
        to_status=new_status,
        actor_name=actor_name,
        actor_role=actor_role,
        actor_user_id=actor_user_id,
        correlation_id=correlation_id.get(),
        note=note,
        created_at=now_iso(),
    )
    db.add(event)
    return declaration


# ── Pydantic request models ────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


def _clean_email(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if "@" not in value or " " in value or len(value) > 200:
        raise ValueError("Email không hợp lệ.")
    return value


class ReportingUnitCreateRequest(BaseModel):
    name: str
    code: str
    notify_email: str = ""  # email chung của Cảng để nhận thông báo (tùy chọn)

    @field_validator("notify_email")
    @classmethod
    def valid_notify_email(cls, value: str) -> str:
        return _clean_email(value)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = " ".join(value.strip().split())
        if len(value) < 2 or len(value) > 150:
            raise ValueError("Tên đơn vị phải có từ 2 đến 150 ký tự.")
        return value

    @field_validator("code")
    @classmethod
    def valid_code(cls, value: str) -> str:
        value = "-".join(value.strip().upper().split())
        if len(value) < 2 or len(value) > 30:
            raise ValueError("Mã đơn vị phải có từ 2 đến 30 ký tự.")
        if any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in value):
            raise ValueError("Mã đơn vị chỉ dùng chữ A-Z, số, dấu gạch ngang hoặc gạch dưới.")
        return value


class UserCreateRequest(BaseModel):
    username: str
    password: str
    full_name: str = ""
    email: str = ""  # địa chỉ nhận thông báo (tùy chọn)
    role: str
    # CUSTOMER accounts must be tied to a customer Organization.
    organization_id: Optional[int] = None
    # PORT_STAFF accounts may be granted membership in one or more reporting units.
    reporting_unit_ids: List[int] = []

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        return _clean_email(value)

    @field_validator("username")
    @classmethod
    def valid_username(cls, value: str) -> str:
        value = value.strip().lower()
        if len(value) < 3 or len(value) > 50:
            raise ValueError("Tên đăng nhập phải có từ 3 đến 50 ký tự.")
        if any(char not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for char in value):
            raise ValueError("Tên đăng nhập chỉ dùng chữ thường a-z, số, dấu chấm, gạch ngang hoặc gạch dưới.")
        return value

    @field_validator("password")
    @classmethod
    def valid_password(cls, value: str) -> str:
        if len(value) < 8 or len(value) > 128:
            raise ValueError("Mật khẩu phải có từ 8 đến 128 ký tự.")
        return value

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        return " ".join((value or "").strip().split())[:150]

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str) -> str:
        value = (value or "").strip().upper()
        if value not in {"CUSTOMER", "PORT_STAFF", "PLATFORM_ADMIN"}:
            raise ValueError("Vai trò không hợp lệ.")
        return value


class OrganizationSaveRequest(BaseModel):
    name: str
    tax_code: str = ""
    address: str = ""
    contact_name: str = ""
    contact_role: str = ""
    phone: str = ""
    email: str = ""

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = " ".join((value or "").strip().split())
        if len(value) < 2 or len(value) > 200:
            raise ValueError("Tên tổ chức phải có từ 2 đến 200 ký tự.")
        return value

    @field_validator("tax_code", "address", "contact_name", "contact_role", "phone", "email")
    @classmethod
    def trim_optional(cls, value: str) -> str:
        return (value or "").strip()[:200]


class UserResetPasswordRequest(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def valid_password(cls, value: str) -> str:
        if len(value) < 8 or len(value) > 128:
            raise ValueError("Mật khẩu phải có từ 8 đến 128 ký tự.")
        return value


class UserActiveRequest(BaseModel):
    is_active: bool


class CargoPayload(BaseModel):
    cargo_type: str = ""
    movement_type: str = ""
    cargo_name: str = ""
    cont20_full: int = 0
    cont20_empty: int = 0
    cont40_full: int = 0
    cont40_empty: int = 0
    # Số tấn cho MỖI container theo từng loại (đơn giá). Dùng để tự tính Khối
    # lượng = Σ(số lượng × số tấn); vẫn cho phép sửa tay ``tons``.
    tons20_full: float = 0.0
    tons20_empty: float = 0.0
    tons40_full: float = 0.0
    tons40_empty: float = 0.0
    tons: float = 0.0

    @field_validator("cont20_full", "cont20_empty", "cont40_full", "cont40_empty")
    @classmethod
    def non_negative_containers(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Số lượng container không được âm.")
        return value

    @field_validator("tons20_full", "tons20_empty", "tons40_full", "tons40_empty", "tons")
    @classmethod
    def non_negative_tons(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Khối lượng không được âm.")
        return value


class VesselOperatingProfilePayload(BaseModel):
    sequence: int = 1
    activity_area: str
    deadweight_tons: Optional[float] = None
    cargo_capacity_tons: Optional[float] = None

    @field_validator("activity_area")
    @classmethod
    def required_activity_area(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Vùng hoạt động là bắt buộc.")
        return value

    @field_validator("deadweight_tons", "cargo_capacity_tons")
    @classmethod
    def non_negative_profile_value(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("Thông số vùng hoạt động không được âm.")
        return value


class VesselSaveRequest(BaseModel):
    id: Optional[int] = None
    version: Optional[int] = None
    organization_name: Optional[str] = None
    organization: Optional[Dict[str, Any]] = None
    name: str
    registration_no: str
    registry_or_imo: str = ""
    vessel_type: str
    vessel_category: Optional[str] = None
    vessel_class: str
    shell_material: str = ""
    build_year: Optional[int] = None
    length_m: Optional[float] = None
    width_m: Optional[float] = None
    side_height_m: Optional[float] = None
    draft_m: Optional[float] = None
    deadweight_tons: Optional[float] = None
    gross_tonnage: Optional[float] = None
    engine_power_cv: Optional[float] = None
    cargo_capacity_tons: Optional[float] = None
    container_capacity_teu: Optional[float] = None
    passenger_capacity: Optional[int] = None
    min_crew: Optional[int] = None
    safety_certificate_no: str = ""
    certificate_issue_date: Optional[str] = None
    certificate_expiry_date: Optional[str] = None
    tracking_master_name: str = ""
    tracking_master_phone: str = ""
    operating_profiles: Optional[List[VesselOperatingProfilePayload]] = None
    notes: str = ""

    @field_validator("name", "registration_no")
    @classmethod
    def required_vessel_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Trường này là bắt buộc.")
        return value

    @field_validator("length_m", "width_m", "side_height_m", "draft_m", "deadweight_tons", "gross_tonnage", "engine_power_cv", "cargo_capacity_tons", "container_capacity_teu")
    @classmethod
    def non_negative_measurements(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("Thông số không được âm.")
        return value

    @field_validator("build_year", "passenger_capacity", "min_crew")
    @classmethod
    def non_negative_integer_fields(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("Thông số không được âm.")
        return value


class PortRegisterRemoveRequest(BaseModel):
    ids: List[int]

    @field_validator("ids")
    @classmethod
    def valid_ids(cls, value: List[int]) -> List[int]:
        ids = list(dict.fromkeys(value))
        if not ids:
            raise ValueError("Cần chọn ít nhất một Salan.")
        if len(ids) > 100:
            raise ValueError("Mỗi lần chỉ được xử lý tối đa 100 Salan.")
        if any(item <= 0 for item in ids):
            raise ValueError("Mã Salan không hợp lệ.")
        return ids


class PortRegisterAddRequest(PortRegisterRemoveRequest):
    pass


class CrewSaveRequest(BaseModel):
    id: Optional[int] = None
    version: Optional[int] = None
    organization_id: Optional[int] = None
    vessel_id: Optional[int] = None
    full_name: str
    crew_role: str
    birth_date: Optional[str] = None
    phone: str = ""
    identity_no: str = ""
    professional_certificate_type: str = ""
    professional_certificate_no: str = ""
    certificate_issue_date: Optional[str] = None
    certificate_expiry_date: Optional[str] = None
    notes: str = ""

    @field_validator("full_name", "phone")
    @classmethod
    def required_crew_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Trường này là bắt buộc.")
        return value

    @field_validator("professional_certificate_type", "professional_certificate_no")
    @classmethod
    def optional_crew_text(cls, value: str) -> str:
        # Chứng chỉ chuyên môn có thể bổ sung sau; chỉ Họ tên và Số điện thoại là bắt buộc.
        return value.strip()

    @field_validator("crew_role")
    @classmethod
    def valid_crew_role(cls, value: str) -> str:
        canonical = CREW_ROLE_CANONICAL.get(import_match_key(value))
        if not canonical:
            raise ValueError(f"Chức danh phải là một trong: {', '.join(CREW_ROLES)}.")
        return canonical


class DeclarationSaveRequest(BaseModel):
    id: Optional[int] = None
    version: Optional[int] = None
    vessel_id: Optional[int] = None
    company_name: str = ""
    declaration_date: str
    vessel_name: str
    registration_no: str
    vessel_type: str
    vessel_class: str
    length_m: Optional[float] = None
    deadweight_tons: Optional[float] = None
    gross_tonnage: Optional[float] = None
    certificate_expiry_date: Optional[str] = None
    crew_count: int = 0
    crew_onboard_count: int = 0
    passenger_count: int = 0
    last_port: str
    working_port: str
    departure_berth: str = ""
    destination_port: str = ""
    agent_ptnd_name: str = ""
    is_passenger_call: bool = False
    eta: str
    etd: str
    master_name: str
    master_phone: str = ""
    movement_type: str = "ARRIVAL"
    purpose: str = ""
    cargo_description: str = ""
    actual_arrival_at: Optional[str] = None
    actual_departure_at: Optional[str] = None
    unload: CargoPayload = CargoPayload()
    load: CargoPayload = CargoPayload()
    crew_ids: List[int] = []

    @field_validator("crew_count", "crew_onboard_count", "passenger_count")
    @classmethod
    def non_negative_counts(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Số lượng không được âm.")
        return value

    @field_validator("movement_type")
    @classmethod
    def valid_movement_type(cls, value: str) -> str:
        if value not in {"ARRIVAL", "DEPARTURE"}:
            raise ValueError("Loại phiếu không hợp lệ.")
        return value

    @field_validator(
        "vessel_name", "registration_no", "vessel_type", "vessel_class",
        "last_port", "working_port", "master_name",
    )
    @classmethod
    def required_declaration_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Trường này là bắt buộc.")
        return value

    @field_validator("company_name", "master_phone")
    @classmethod
    def optional_declaration_text(cls, value: str) -> str:
        # Doanh nghiệp/Chủ phương tiện và Số điện thoại thuyền trưởng không bắt
        # buộc — có thể để trống và bổ sung sau. company_name của CUSTOMER luôn
        # bị ghi đè bằng tên tổ chức của họ khi lưu, xem save_declaration().
        return value.strip()

    @model_validator(mode="after")
    def eta_before_etd(self) -> "DeclarationSaveRequest":
        try:
            if self.eta and self.etd and self.eta[:16] > self.etd[:16]:
                raise ValueError("ETA phải trước ETD.")
        except (TypeError, AttributeError):
            pass
        return self


class WorkflowActionRequest(BaseModel):
    action: str
    note: str = ""


class PrepareSyncRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: Optional[str] = None
    to: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "PrepareSyncRequest":
        return cls(from_=data.get("from"), to=data.get("to"))


class NotificationPreferenceRequest(BaseModel):
    in_app_certificate_reminders: bool = True
    email_workflow_updates: bool = False
    email_certificate_reminders: bool = False


class MyProfileRequest(BaseModel):
    """Self-service profile update: a user editing their own contact + opt-in."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    in_app_certificate_reminders: bool = True
    email_workflow_updates: bool = False
    email_certificate_reminders: bool = False

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return " ".join(value.strip().split())[:150]

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _clean_email(value)


class UserUpdateRequest(BaseModel):
    """Admin editing another user's contact fields (not username/role/password)."""
    full_name: Optional[str] = None
    email: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return " ".join(value.strip().split())[:150]

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return _clean_email(value)


class SmtpConfigRequest(BaseModel):
    enabled: bool = False
    host: str = ""
    port: int = 587
    username: str = ""
    # Rỗng => giữ mật khẩu đã lưu (không ghi đè). Có giá trị => cập nhật.
    password: Optional[str] = None
    from_email: str = Field("", alias="from")
    use_tls: bool = True

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("from_email")
    @classmethod
    def valid_from(cls, value: str) -> str:
        value = (value or "").strip()
        if value and "@" not in value:
            raise ValueError("Email gửi không hợp lệ.")
        return value[:200]

    @field_validator("host", "username")
    @classmethod
    def trim(cls, value: str) -> str:
        return (value or "").strip()[:200]


class SmtpTestRequest(BaseModel):
    to: str

    @field_validator("to")
    @classmethod
    def valid_to(cls, value: str) -> str:
        value = (value or "").strip()
        if "@" not in value:
            raise ValueError("Địa chỉ nhận không hợp lệ.")
        return value


class ReportAdjustmentRequest(BaseModel):
    report_month: str
    metric: str
    delta: float
    reason: str
    organization_id: Optional[int] = None

    @field_validator("report_month")
    @classmethod
    def valid_report_month(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%Y-%m")
        except ValueError as exc:
            raise ValueError("Tháng báo cáo phải có định dạng YYYY-MM.") from exc
        return value

    @field_validator("metric")
    @classmethod
    def valid_metric(cls, value: str) -> str:
        allowed = {"calls", "passenger_calls"}
        if value not in allowed:
            raise ValueError(f"Chỉ tiêu điều chỉnh phải là một trong: {', '.join(sorted(allowed))}.")
        return value

    @field_validator("reason")
    @classmethod
    def required_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise ValueError("Lý do điều chỉnh phải có ít nhất 5 ký tự.")
        return value


# ── Catalog constants ──────────────────────────────────────────────────────────
# Gợi ý cho ô Công dụng/Loại phương tiện — trường này ghi nguyên văn theo GCN
# (nhập tự do), danh sách dưới đây chỉ để gợi ý autocomplete, không ràng buộc.
VESSEL_TYPE_SUGGESTIONS = [
    "Chở hàng khô", "Chở hàng khô hoặc container", "Chở container", "Chở nước",
]
# Phân loại phương tiện — trường nội bộ, không bắt buộc, không xuất hiện trong
# Phụ lục nào; tách khỏi vessel_type (Công dụng) vì không có căn cứ trên GCN.
VESSEL_CATEGORIES = [
    "Tàu hàng khô", "Tàu container", "Tàu hàng lỏng/dầu", "Tàu khách",
    "Tàu kéo/đẩy", "Sà lan tự hành", "Sà lan", "Khác",
]
# "VR-SI / VR-SII" là cấp ghép, ghi theo đúng GCN của phương tiện được cấp cả
# hai vùng hoạt động; VR-SIII theo đúng Phụ lục 2 dù dữ liệu hiện chưa có.
VESSEL_CLASSES = ["VR-SI", "VR-SII", "VR-SIII", "VR-SI / VR-SII", "Khác"]
SHELL_MATERIALS = ["Thép", "Gỗ", "Composite/GRP", "Xi măng lưới thép", "Nhôm", "Khác"]
CARGO_TYPES = ["Container", "Hàng khô", "Hàng lỏng"]
UNLOAD_MOVEMENTS = [
    "Nội địa", "Nhập khẩu", "Chuyển tải", "Quá cảnh có bốc dỡ", "Quá cảnh không bốc dỡ",
]
LOAD_MOVEMENTS = ["Nội địa", "Xuất khẩu"]


# Rate limiting tracker for login: {ip: {"failures": count, "blocked_until": datetime}}
_login_attempts: Dict[str, Dict[str, Any]] = {}

@app.post("/api/auth/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    now = datetime.now()

    # Rate limiting check
    tracker = _login_attempts.get(ip)
    if tracker and tracker["failures"] >= 5:
        if now < tracker["blocked_until"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Tài khoản hoặc IP bị tạm khóa do đăng nhập sai nhiều lần. Vui lòng thử lại sau 5 phút."
            )
        else:
            # Block expired, reset tracker
            _login_attempts[ip] = {"failures": 0, "blocked_until": now}

    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        # Register failure
        if ip not in _login_attempts:
            _login_attempts[ip] = {"failures": 1, "blocked_until": now}
        else:
            _login_attempts[ip]["failures"] += 1
            if _login_attempts[ip]["failures"] >= 5:
                from datetime import timedelta
                _login_attempts[ip]["blocked_until"] = now + timedelta(minutes=5)

        # Audit failure (NO password/token printed)
        audit(db, "auth", 0, "LOGIN_FAILURE", f"Đăng nhập thất bại từ IP={ip}")
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thông tin đăng nhập không đúng."
        )

    # Check active status
    if not getattr(user, "is_active", True):
        audit(db, "auth", user.id, "LOGIN_FAILURE_DISABLED", f"Đăng nhập thất bại do tài khoản bị vô hiệu hóa từ IP={ip}")
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa."
        )

    # Reset failure tracker on successful login
    if ip in _login_attempts:
        _login_attempts[ip] = {"failures": 0, "blocked_until": now}

    # Generate token containing username (sub), role, and org_id
    token = create_access_token(data={
        "sub": user.username,
        "role": user.role,
        "org_id": user.organization_id
    })

    # Audit success
    audit(db, "user", user.id, "LOGIN_SUCCESS", f"Đăng nhập thành công từ IP={ip}")
    db.commit()
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/auth/me")
def get_me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email or "",
        "role": user.role,
        "organization_id": user.organization_id,
        "organization_name": user.organization.name if user.organization else None,
        "notification_preferences": _notification_preferences(user),
        # Cho biết SMTP đã cấu hình chưa (không lộ thông tin nhạy cảm) để tab
        # Cài đặt hiển thị trạng thái email.
        "email_enabled": email_notifications_enabled(db),
    }


@app.post("/api/auth/logout")
def logout(user: User = Depends(get_current_user)):
    # Local client-side stateless token removal is primary, but we return 200 OK.
    return {"status": "ok", "detail": "Đăng xuất thành công."}


def _notification_preferences(user: User) -> dict[str, bool]:
    try:
        stored = json.loads(user.notification_preferences_json or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        stored = {}
    return {
        "in_app_certificate_reminders": bool(stored.get("in_app_certificate_reminders", True)),
        # Email opt-in: mặc định TẮT để tránh làm phiền; người dùng tự bật.
        "email_workflow_updates": bool(stored.get("email_workflow_updates", False)),
        "email_certificate_reminders": bool(stored.get("email_certificate_reminders", False)),
    }


@app.get("/api/notification-preferences")
def get_notification_preferences(user: User = Depends(get_current_user)):
    return _notification_preferences(user)


@app.put("/api/notification-preferences")
def update_notification_preferences(
    payload: NotificationPreferenceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    preferences = {
        "in_app_certificate_reminders": payload.in_app_certificate_reminders,
        "email_workflow_updates": payload.email_workflow_updates,
        "email_certificate_reminders": payload.email_certificate_reminders,
    }
    # `user` is supplied by the authentication dependency and can be bound to
    # a separate request session. Persist through this endpoint's transaction.
    current_user = db.query(User).filter(User.id == user.id).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="Không thể xác thực thông tin đăng nhập")
    current_user.notification_preferences_json = json.dumps(preferences, separators=(",", ":"))
    audit(
        db, "USER", current_user.id, "NOTIFICATION_PREFERENCES_UPDATE",
        f"in_app={payload.in_app_certificate_reminders},email_workflow={payload.email_workflow_updates},"
        f"email_cert={payload.email_certificate_reminders}",
        actor_user_id=user.id, organization_id=current_user.organization_id,
    )
    db.commit()
    return preferences


@app.put("/api/me")
def update_my_profile(
    payload: MyProfileRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Self-service: a user updates their own email, name and notification opt-ins."""
    current_user = db.query(User).filter(User.id == user.id).first()
    if not current_user:
        raise HTTPException(status_code=401, detail="Không thể xác thực thông tin đăng nhập")
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.email is not None:
        current_user.email = payload.email
    current_user.notification_preferences_json = json.dumps({
        "in_app_certificate_reminders": payload.in_app_certificate_reminders,
        "email_workflow_updates": payload.email_workflow_updates,
        "email_certificate_reminders": payload.email_certificate_reminders,
    }, separators=(",", ":"))
    audit(
        db, "USER", current_user.id, "PROFILE_SELF_UPDATE",
        f"email set={'yes' if payload.email else 'no'}",
        actor_user_id=user.id, organization_id=current_user.organization_id,
    )
    db.commit()
    db.refresh(current_user)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email or "",
        "role": current_user.role,
        "organization_id": current_user.organization_id,
        "organization_name": current_user.organization.name if current_user.organization else None,
        "notification_preferences": _notification_preferences(current_user),
        "email_enabled": email_notifications_enabled(db),
    }


# ══════════════════════════════════════════════════════════════════════════════
# EMAIL / SMTP CONFIG (PLATFORM_ADMIN) — cấu hình ngay trên UI, lưu DB, mã hóa
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/admin/smtp")
def get_smtp_settings(db: Session = Depends(get_db), user: User = Depends(require_roles("PLATFORM_ADMIN"))):
    """Trả cấu hình SMTP hiện tại — KHÔNG bao giờ trả mật khẩu."""
    cfg = get_smtp_config(db)
    return {
        "enabled": cfg.enabled,
        "host": cfg.host,
        "port": cfg.port,
        "username": cfg.username,
        "from": cfg.sender,
        "use_tls": cfg.use_tls,
        "password_set": bool(cfg.password),
        "source": cfg.source,  # db | env | none
        # Khi nguồn là env, không cho sửa trên UI (do dev quản lý qua .env).
        "editable": cfg.source != "env",
    }


@app.put("/api/admin/smtp")
def update_smtp_settings(
    payload: SmtpConfigRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    from .crypto_util import encrypt
    row = db.query(AppSetting).filter(AppSetting.key == SMTP_SETTING_KEY).first()
    existing = {}
    if row and row.value:
        try:
            existing = json.loads(row.value)
        except (TypeError, ValueError, json.JSONDecodeError):
            existing = {}
    # Mật khẩu: rỗng/None => giữ nguyên bản đã lưu; có giá trị => mã hóa & thay.
    if payload.password:
        password_enc = encrypt(payload.password)
    else:
        password_enc = existing.get("password_enc", "")
    data = {
        "enabled": payload.enabled,
        "host": payload.host,
        "port": payload.port,
        "username": payload.username,
        "password_enc": password_enc,
        "from": payload.from_email,
        "use_tls": payload.use_tls,
    }
    if row is None:
        row = AppSetting(key=SMTP_SETTING_KEY, value="", updated_at=now_iso())
        db.add(row)
    row.value = json.dumps(data, separators=(",", ":"))
    row.updated_at = now_iso()
    audit(
        db, "APP_SETTING", 0, "SMTP_CONFIG_UPDATE",
        f"enabled={payload.enabled},host={payload.host},from={payload.from_email}",
        actor_user_id=user.id,
    )
    db.commit()
    # Trả trạng thái mới (không có mật khẩu).
    cfg = get_smtp_config(db)
    return {
        "enabled": cfg.enabled, "host": cfg.host, "port": cfg.port,
        "username": cfg.username, "from": cfg.sender, "use_tls": cfg.use_tls,
        "password_set": bool(cfg.password), "source": cfg.source, "editable": cfg.source != "env",
    }


@app.post("/api/admin/smtp/test")
def send_smtp_test(
    payload: SmtpTestRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    """Gửi 1 email thử tới địa chỉ chỉ định bằng cấu hình hiện tại. Fail-soft."""
    cfg = get_smtp_config(db)
    if not cfg.ready:
        return {"sent": False, "detail": "Chưa bật/cấu hình SMTP. Lưu cấu hình trước khi gửi thử."}
    subject = "TIEN-TAN THUAN PORT — Email thử cấu hình"
    body = (
        "Đây là email thử từ hệ thống Quản lý Salan.\n\n"
        "Nếu bạn nhận được email này, cấu hình SMTP đã hoạt động đúng.\n"
    )
    sent = send_email([payload.to], subject, body, config=cfg)
    audit(
        db, "APP_SETTING", 0, "SMTP_TEST",
        f"to={payload.to},sent={sent}", actor_user_id=user.id,
    )
    db.commit()
    return {
        "sent": sent,
        "detail": "Đã gửi email thử. Vui lòng kiểm tra hộp thư." if sent
        else "Gửi thất bại. Kiểm tra lại host/cổng/tài khoản/mật khẩu.",
    }


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG (PLATFORM_ADMIN) — read-only view of every audit() call already
# written across the app (declarations, users, organizations, SMTP...), so an
# admin can answer "what was just created/changed, by whom, when" without
# touching the database directly.
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/admin/audit-log")
def get_audit_log(
    entity_type: Optional[str] = None,
    q: Optional[str] = None,
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    query = db.query(AuditEvent)
    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)
    if q:
        search = f"%{q}%"
        query = query.filter(AuditEvent.summary.like(search))
    if from_:
        query = query.filter(AuditEvent.created_at >= from_)
    if to:
        query = query.filter(AuditEvent.created_at <= f"{to}~")  # lexical upper bound on ISO timestamps
    total = query.count()
    rows = (
        query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    actor_ids = {r.actor_user_id for r in rows if r.actor_user_id}
    actors = {
        u.id: (u.full_name or u.username)
        for u in db.query(User).filter(User.id.in_(actor_ids)).all()
    } if actor_ids else {}
    unit_ids = {r.reporting_unit_id for r in rows if r.reporting_unit_id}
    units = {
        ru.id: ru.name
        for ru in db.query(ReportingUnit).filter(ReportingUnit.id.in_(unit_ids)).all()
    } if unit_ids else {}
    return {
        "items": [
            {
                "id": r.id,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "action": r.action,
                "summary": r.summary,
                "actor_name": actors.get(r.actor_user_id, "—"),
                "reporting_unit_name": units.get(r.reporting_unit_id),
                "created_at": r.created_at,
            }
            for r in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@app.get("/api/admin/audit-log/entity-types")
def get_audit_log_entity_types(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    rows = db.query(AuditEvent.entity_type).distinct().order_by(AuditEvent.entity_type).all()
    return [row[0] for row in rows]


@app.delete("/api/admin/audit-log/{event_id}")
def delete_audit_log_entry(
    event_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    # The audit log is itself an administrative record, not a legal/financial
    # one — admin has full authority to prune it (test noise, sensitive detail
    # in a summary, etc.) with no time restriction. Deleting a log row is
    # deliberately NOT itself audited: logging "deleted a log entry" here would
    # just recreate the same row it removed.
    row = db.query(AuditEvent).filter(AuditEvent.id == event_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Không tìm thấy dòng nhật ký.")
    db.delete(row)
    db.commit()
    return {"deleted": event_id}


@app.delete("/api/admin/audit-log")
def delete_all_audit_log(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    """Erase the entire audit log. PLATFORM_ADMIN-only, no time restriction."""
    deleted = db.query(AuditEvent).delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted}


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health_check():
    return {"status": "ok", "database": "postgresql-sqlalchemy", "storage": attachment_storage.backend_name, "version": "1.0.0"}


@app.get("/api/ready")
def readiness_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok", "storage": attachment_storage.backend_name}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database readiness check failed.") from exc


# ══════════════════════════════════════════════════════════════════════════════
# CATALOGS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/catalogs")
def get_catalogs():
    return {
        "vesselTypeSuggestions": VESSEL_TYPE_SUGGESTIONS,
        "vesselCategories": VESSEL_CATEGORIES,
        "vesselClasses": VESSEL_CLASSES,
        "shellMaterials": SHELL_MATERIALS,
        "cargoTypes": CARGO_TYPES,
        "unloadMovements": UNLOAD_MOVEMENTS,
        "loadMovements": LOAD_MOVEMENTS,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ORGANIZATIONS
# ══════════════════════════════════════════════════════════════════════════════

def _serialize_org(o: Organization) -> dict:
    return {c.name: getattr(o, c.name) for c in o.__table__.columns}


@app.get("/api/organizations")
def get_organizations(db: Session = Depends(get_db), user: User = Depends(require_roles("PLATFORM_ADMIN"))):
    orgs = db.query(Organization).order_by(Organization.name).all()
    return [_serialize_org(o) for o in orgs]


@app.post("/api/organizations", status_code=201)
def create_organization(
    payload: OrganizationSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    duplicate = db.query(Organization).filter(func.lower(Organization.name) == payload.name.lower()).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Đã có tổ chức dùng tên này.")
    org = Organization(
        name=payload.name, tax_code=payload.tax_code, address=payload.address,
        contact_name=payload.contact_name, contact_role=payload.contact_role,
        phone=payload.phone, email=payload.email,
        created_at=now_iso(), updated_at=now_iso(),
    )
    db.add(org)
    db.flush()
    audit(db, "ORGANIZATION", org.id, "CREATE", org.name, actor_user_id=user.id, organization_id=org.id)
    db.commit()
    db.refresh(org)
    return _serialize_org(org)


@app.put("/api/organizations/{org_id}")
def update_organization(
    org_id: int,
    payload: OrganizationSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Không tìm thấy tổ chức.")
    duplicate = db.query(Organization).filter(
        func.lower(Organization.name) == payload.name.lower(), Organization.id != org_id
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Đã có tổ chức khác dùng tên này.")
    org.name = payload.name
    org.tax_code = payload.tax_code
    org.address = payload.address
    org.contact_name = payload.contact_name
    org.contact_role = payload.contact_role
    org.phone = payload.phone
    org.email = payload.email
    org.updated_at = now_iso()
    audit(db, "ORGANIZATION", org.id, "UPDATE", org.name, actor_user_id=user.id, organization_id=org.id)
    db.commit()
    db.refresh(org)
    return _serialize_org(org)


# ══════════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT (PLATFORM_ADMIN)
# ══════════════════════════════════════════════════════════════════════════════

def _serialize_user(db: Session, item: User) -> dict:
    unit_rows = (
        db.query(ReportingUnit.id, ReportingUnit.name)
        .join(ReportingUnitUser, ReportingUnitUser.reporting_unit_id == ReportingUnit.id)
        .filter(ReportingUnitUser.user_id == item.id)
        .order_by(ReportingUnit.name)
        .all()
    )
    return {
        "id": item.id,
        "username": item.username,
        "full_name": item.full_name or "",
        "email": item.email or "",
        "role": item.role,
        "is_active": bool(item.is_active),
        "organization_id": item.organization_id,
        "organization_name": item.organization.name if item.organization else None,
        "reporting_units": [{"id": row[0], "name": row[1]} for row in unit_rows],
        "created_at": item.created_at,
    }


@app.get("/api/admin/users")
def list_users(
    db: Session = Depends(get_db), user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    users = db.query(User).order_by(User.role, User.username).all()
    return {"items": [_serialize_user(db, item) for item in users]}


@app.post("/api/admin/users", status_code=201)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    existing = db.query(User).filter(func.lower(User.username) == payload.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Tên đăng nhập đã tồn tại.")

    organization_id = None
    if payload.role == "CUSTOMER":
        if payload.organization_id is None:
            raise HTTPException(status_code=422, detail="Tài khoản khách hàng phải được gắn với một tổ chức.")
        organization = db.query(Organization).filter(Organization.id == payload.organization_id).first()
        if not organization:
            raise HTTPException(status_code=422, detail="Không tìm thấy tổ chức đã chọn.")
        organization_id = organization.id

    unit_ids: List[int] = []
    if payload.role == "PORT_STAFF" and payload.reporting_unit_ids:
        unit_ids = sorted(set(payload.reporting_unit_ids))
        found = db.query(ReportingUnit.id).filter(ReportingUnit.id.in_(unit_ids)).all()
        if len(found) != len(unit_ids):
            raise HTTPException(status_code=422, detail="Một hoặc nhiều đơn vị báo cáo không tồn tại.")

    new_user = User(
        username=payload.username,
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name,
        email=payload.email,
        role=payload.role,
        organization_id=organization_id,
        is_active=1,
        created_at=now_iso(),
    )
    db.add(new_user)
    db.flush()

    for unit_id in unit_ids:
        db.add(ReportingUnitUser(reporting_unit_id=unit_id, user_id=new_user.id, created_at=now_iso()))

    audit(
        db, "USER", new_user.id, "CREATE",
        f"Tạo tài khoản {new_user.username} ({new_user.role})",
        actor_user_id=user.id, organization_id=organization_id,
    )
    db.commit()
    db.refresh(new_user)
    return _serialize_user(db, new_user)


@app.put("/api/admin/users/{user_id}")
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    """Admin edits a user's contact fields (email, full name). Username, role and
    password are managed through their own dedicated flows."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if payload.full_name is not None:
        target.full_name = payload.full_name
    if payload.email is not None:
        target.email = payload.email
    audit(
        db, "USER", target.id, "PROFILE_ADMIN_UPDATE",
        f"Cập nhật thông tin {target.username}",
        actor_user_id=user.id, organization_id=target.organization_id,
    )
    db.commit()
    db.refresh(target)
    return _serialize_user(db, target)


@app.post("/api/admin/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    payload: UserResetPasswordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    target.password_hash = get_password_hash(payload.password)
    audit(
        db, "USER", target.id, "RESET_PASSWORD",
        f"Đặt lại mật khẩu cho {target.username}",
        actor_user_id=user.id, organization_id=target.organization_id,
    )
    db.commit()
    return {"status": "ok", "detail": "Đã đặt lại mật khẩu."}


@app.post("/api/admin/users/{user_id}/active")
def set_user_active(
    user_id: int,
    payload: UserActiveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    if target.id == user.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="Không thể tự vô hiệu hóa tài khoản của chính mình.")
    target.is_active = 1 if payload.is_active else 0
    audit(
        db, "USER", target.id, "SET_ACTIVE",
        f"{'Kích hoạt' if payload.is_active else 'Vô hiệu hóa'} tài khoản {target.username}",
        actor_user_id=user.id, organization_id=target.organization_id,
    )
    db.commit()
    db.refresh(target)
    return _serialize_user(db, target)


@app.get("/api/admin/operations-summary")
def admin_operations_summary(
    db: Session = Depends(get_db), user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    today = date.today()
    year_start = date(today.year, 1, 1).isoformat()
    declaration_query = db.query(Declaration).filter(Declaration.declaration_date >= year_start)
    declarations = declaration_query.all()
    approved = [item for item in declarations if item.workflow_status == "APPROVED"]
    pending = [item for item in declarations if item.workflow_status.startswith("PENDING_")]
    tons = teu = 0.0
    for item in approved:
        for cargo_item in (json.loads(item.unload_json or "{}"), json.loads(item.load_json or "{}")):
            tons += float(cargo_item.get("tons") or 0)
            teu += float(cargo_item.get("teu") or 0)

    expiring = sum(
        1 for vessel in db.query(Vessel).all()
        if certificate_status(vessel.certificate_expiry_date) in {"EXPIRING", "EXPIRED"}
    )
    backups = list(BACKUP_DIR.glob(BACKUP_GLOB)) if BACKUP_DIR.exists() else []
    latest_backup = max(backups, key=lambda item: item.stat().st_mtime).name if backups else None
    return {
        "period": {"from": year_start, "to": today.isoformat()},
        "operations": {"declarations": len(declarations), "approved": len(approved), "pending": len(pending), "tons": tons, "teu": teu},
        "fleet": {"vessels": db.query(Vessel).count(), "certificateWarnings": expiring},
        "imports": {"jobs": db.query(ImportJob).count(), "rejectedRows": db.query(func.coalesce(func.sum(ImportJob.rejected_count), 0)).scalar()},
        "storage": {"attachments": db.query(Attachment).count(), "backups": len(backups), "latestBackup": latest_backup},
        "security": {"failedLogins": db.query(AuditEvent).filter(AuditEvent.action.like("LOGIN_FAILURE%")).count(), "disabledUsers": db.query(User).filter(User.is_active == 0).count()},
    }


def _backup_record(path: Path) -> dict[str, Any]:
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
    created_at = manifest.get("created_at") or datetime.fromtimestamp(
        path.stat().st_mtime, timezone.utc
    ).isoformat()
    return {
        "filename": path.name,
        "createdAt": created_at,
        "sizeBytes": path.stat().st_size,
        "integrityCheck": manifest.get("integrity_check", "unknown"),
        "sha256": manifest.get("sha256", ""),
    }


@app.get("/api/admin/backups")
def list_admin_backups(user: User = Depends(require_roles("PLATFORM_ADMIN"))):
    del user
    if not BACKUP_DIR.exists():
        return []
    return [
        _backup_record(path)
        for path in sorted(
            BACKUP_DIR.glob(BACKUP_GLOB),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
    ]


@app.post("/api/admin/backups")
def create_admin_backup(
    db: Session = Depends(get_db), user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    if engine.url.get_backend_name() != "postgresql" or not engine.url.database:
        raise HTTPException(
            status_code=503,
            detail="Sao lưu trực tiếp chỉ khả dụng với cấu hình PostgreSQL.",
        )
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destination = BACKUP_DIR / f"cang_vu-{stamp}{BACKUP_SUFFIX}"
    try:
        create_local_backup(SQLALCHEMY_DATABASE_URL, destination)
        removed = prune_local_backups(BACKUP_DIR)
    except Exception as exc:
        access_logger.exception("Local backup failed")
        raise HTTPException(status_code=500, detail="Không thể tạo bản sao lưu cục bộ.") from exc
    audit(
        db, "BACKUP", 0, "CREATE", destination.name,
        actor_user_id=user.id, organization_id=user.organization_id,
    )
    db.commit()
    return {**_backup_record(destination), "pruned": len(removed)}


def _get_or_create_org(db: Session, name: Optional[str]) -> Optional[Organization]:
    if not name:
        return None
    org = db.query(Organization).filter(Organization.name == name).first()
    if not org:
        org = Organization(name=name, updated_at=now_iso(), created_at=now_iso())
        db.add(org)
        db.flush()
    return org


def _resolve_org_for_port_scope(db: Session, scope: Scope, name: Optional[str]) -> Optional[Organization]:
    """Look up or create an Organization by name for a PORT-scope mutation.

    A brand-new Organization is onboarded through (and linked to) the resolved
    reporting unit. An Organization that already exists must already belong to
    the resolved unit — otherwise it is another tenant's data and is rejected.
    """
    if not name:
        return None
    org = db.query(Organization).filter(Organization.name == name).first()
    if org is None:
        org = Organization(name=name, updated_at=now_iso(), created_at=now_iso())
        db.add(org)
        db.flush()
        db.add(ReportingUnitOrganization(
            reporting_unit_id=scope.reporting_unit_id, organization_id=org.id, created_at=now_iso(),
        ))
        return org
    if org.id not in scope.member_org_ids:
        raise HTTPException(status_code=403, detail="Tổ chức không thuộc đơn vị báo cáo hiện tại.")
    return org


def _resolve_unit_id_for_reference(db: Session, scope: Scope, org_id: Optional[int]) -> Optional[int]:
    """Reporting-unit id used to scope a declaration's daily sequence.

    PORT scope already carries the active unit. For a CUSTOMER, the unit is
    derived from the org's membership — but only when it belongs to exactly one
    unit; otherwise (multiple or none) we fall back to a shared, unit-agnostic
    sequence so a code can always be produced.
    """
    if scope.is_port and scope.reporting_unit_id:
        return scope.reporting_unit_id
    if org_id is None:
        return None
    unit_ids = [
        row[0] for row in db.query(ReportingUnitOrganization.reporting_unit_id)
        .filter(ReportingUnitOrganization.organization_id == org_id).all()
    ]
    return unit_ids[0] if len(unit_ids) == 1 else None


def _next_reference_no(db: Session, scope: Scope, org_id: Optional[int]) -> str:
    """Build a short, readable reference: ``TT-YYMMDD-NNN``.

    The 3-digit sequence resets each day and counts separately per reporting
    unit (falling back to a shared per-day counter when the unit is unknown).
    The count-then-increment is guarded by a unique constraint on
    ``reference_no`` plus a retry loop in the caller, so a race that reuses a
    number simply retries the next one.
    """
    day = datetime.now().strftime("%y%m%d")
    prefix = f"TT-{day}-"
    unit_id = _resolve_unit_id_for_reference(db, scope, org_id)
    query = db.query(func.count(Declaration.id)).filter(Declaration.reference_no.like(f"{prefix}%"))
    if unit_id is not None:
        # Restrict the count to this unit's declarations: either through an
        # Organization served by the unit, OR tagged directly via
        # reporting_unit_id (a declaration saved with no organization chosen —
        # see Declaration.reporting_unit_id — must still be counted here, or
        # its number gets reused and collides on the next save).
        member_org_ids = [
            row[0] for row in db.query(ReportingUnitOrganization.organization_id)
            .filter(ReportingUnitOrganization.reporting_unit_id == unit_id).all()
        ]
        org_clause = Declaration.organization_id.in_(member_org_ids) if member_org_ids else sql_false()
        query = query.filter(or_(org_clause, Declaration.reporting_unit_id == unit_id))
    count = query.scalar() or 0
    return f"{prefix}{count + 1:03d}"


def is_demo_data_active(db: Session) -> bool:
    return db.query(Organization.id).filter(
        Organization.tax_code == DEMO_ORGANIZATION_TAX_CODE
    ).first() is not None


def remove_demo_data_for_real_input(
    db: Session,
    *,
    retain_organization_id: int | None = None,
    organization_data: dict[str, Any] | None = None,
    allowed_organization_ids: tuple[int, ...] | None = None,
) -> bool:
    """Remove sentinel-marked records before the first real input.

    A demo CUSTOMER keeps its organization binding, but the sentinel is cleared
    and optional workbook metadata becomes the real profile. PLATFORM_ADMIN imports may
    remove the demo organization entirely.
    """
    demo_org = db.query(Organization).filter(
        Organization.tax_code == DEMO_ORGANIZATION_TAX_CODE
    ).first()
    if not demo_org:
        return False
    if allowed_organization_ids is not None and demo_org.id not in allowed_organization_ids:
        return False

    declaration_ids = [row[0] for row in db.query(Declaration.id).filter(
        Declaration.organization_id == demo_org.id
    ).all()]
    if declaration_ids:
        db.query(Attachment).filter(Attachment.declaration_id.in_(declaration_ids)).delete(synchronize_session=False)
        db.query(DeclarationCrew).filter(DeclarationCrew.declaration_id.in_(declaration_ids)).delete(synchronize_session=False)
        db.query(DeclarationEvent).filter(DeclarationEvent.declaration_id.in_(declaration_ids)).delete(synchronize_session=False)
        db.query(Declaration).filter(Declaration.id.in_(declaration_ids)).delete(synchronize_session=False)
    db.query(CrewMember).filter(CrewMember.organization_id == demo_org.id).delete(synchronize_session=False)
    db.query(Vessel).filter(Vessel.organization_id == demo_org.id).delete(synchronize_session=False)
    db.query(AuditEvent).filter(AuditEvent.organization_id == demo_org.id).delete(synchronize_session=False)
    db.query(ImportJob).filter(ImportJob.organization_id == demo_org.id).delete(synchronize_session=False)
    if retain_organization_id == demo_org.id:
        profile = organization_data or {}
        proposed_name = str(profile.get("name") or "").strip()
        name_in_use = proposed_name and db.query(Organization.id).filter(
            Organization.name == proposed_name, Organization.id != demo_org.id
        ).first()
        if proposed_name and not name_in_use:
            demo_org.name = proposed_name
        demo_org.tax_code = str(profile.get("tax_code") or "").strip()
        for field in ("address", "contact_name", "phone"):
            value = str(profile.get(field) or "").strip()
            if value:
                setattr(demo_org, field, value)
        demo_org.updated_at = now_iso()
    else:
        db.query(User).filter(User.organization_id == demo_org.id).update(
            {User.organization_id: None}, synchronize_session=False
        )
        db.delete(demo_org)
    db.flush()
    return True


def _attention_queue(db: Session, scope: Scope) -> dict[str, Any]:
    """Return only the actionable/observable queue for the authenticated scope."""
    role_rules = {
        "CUSTOMER": (["DRAFT", "CHANGES_REQUESTED"], "Phiếu cần khách hàng hoàn tất hoặc bổ sung"),
        "PORT_STAFF": (["PENDING_REVIEW"], "Phiếu chờ nhân viên Cảng xem xét"),
        "PLATFORM_ADMIN": (["PENDING_REVIEW"], "Theo dõi các phiếu đang chờ Cảng xử lý"),
    }
    statuses, label = role_rules.get(scope.user.role, ([], ""))
    if not statuses:
        return {"label": label, "count": 0, "items": []}
    query = db.query(Declaration).filter(Declaration.workflow_status.in_(statuses))
    if scope.is_customer:
        query = query.filter(Declaration.organization_id == scope.organization_id)
    else:
        # PORT scope: never combine ReportingUnits — restrict to the Organizations
        # linked to the resolved unit.
        org_ids = scope.member_org_ids
        query = query.filter(Declaration.organization_id.in_(org_ids)) if org_ids else query.filter(sql_false())
    declarations = query.order_by(Declaration.updated_at.asc(), Declaration.id.asc()).limit(5).all()
    now = datetime.now().astimezone()
    items = []
    for declaration in declarations:
        try:
            updated = datetime.fromisoformat(declaration.updated_at)
            age_hours = max(0, int((now - updated).total_seconds() // 3600))
        except (TypeError, ValueError):
            age_hours = None
        items.append({
            "id": declaration.id,
            "reference_no": declaration.reference_no,
            "vessel_name": declaration.vessel_name,
            "workflow_status": declaration.workflow_status,
            "updated_at": declaration.updated_at,
            "age_hours": age_hours,
        })
    return {"label": label, "count": query.count(), "items": items}


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/dashboard")
def get_dashboard(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    today_iso = date.today().isoformat()

    # Base queries
    vessels_q = db.query(Vessel)
    drafts_q = db.query(Declaration).filter(Declaration.workflow_status == "DRAFT")
    submitted_q = db.query(Declaration).filter(Declaration.workflow_status.notin_(["DRAFT", "CHANGES_REQUESTED", "CANCELLED"]))
    arriving_q = db.query(Declaration).filter(Declaration.eta.startswith(today_iso))
    warnings_q = db.query(Vessel).filter(Vessel.certificate_expiry_date.isnot(None))
    recent_q = db.query(Declaration)
    vessel_search_q = db.query(Vessel)

    # Scoping: CUSTOMER to its own Organization; PORT to the Organizations linked
    # to the resolved reporting unit. Never a global fetch filtered client-side.
    if scope.is_customer:
        vessels_q = vessels_q.filter(Vessel.organization_id == scope.organization_id)
        drafts_q = drafts_q.filter(Declaration.organization_id == scope.organization_id)
        submitted_q = submitted_q.filter(Declaration.organization_id == scope.organization_id)
        arriving_q = arriving_q.filter(Declaration.organization_id == scope.organization_id)
        warnings_q = warnings_q.filter(Vessel.organization_id == scope.organization_id)
        recent_q = recent_q.filter(Declaration.organization_id == scope.organization_id)
        vessel_search_q = vessel_search_q.filter(Vessel.organization_id == scope.organization_id)
    else:
        org_ids = scope.member_org_ids
        org_filter = org_ids if org_ids else (-1,)
        vessels_q = vessels_q.filter(Vessel.organization_id.in_(org_filter))
        submitted_q = submitted_q.filter(Declaration.organization_id.in_(org_filter))
        arriving_q = arriving_q.filter(Declaration.organization_id.in_(org_filter))
        warnings_q = warnings_q.filter(Vessel.organization_id.in_(org_filter))
        recent_q = recent_q.filter(Declaration.organization_id.in_(org_filter))
        vessel_search_q = vessel_search_q.filter(Vessel.organization_id.in_(org_filter))
        if scope.user.role == "PLATFORM_ADMIN":
            # PLATFORM_ADMIN creates its own drafts via "Lưu phiếu" and must be
            # able to find them again — see get_declarations() for the matching
            # exemption on the list endpoint.
            drafts_q = drafts_q.filter(Declaration.organization_id.in_(org_filter))
        else:
            # PORT_STAFF reviews submitted work only; a CUSTOMER's un-submitted
            # draft isn't theirs to see yet.
            drafts_q = drafts_q.filter(Declaration.id == -1)  # Drafts count is 0
            recent_q = recent_q.filter(Declaration.workflow_status != "DRAFT")

    # Counts
    vessels_count = vessels_q.with_entities(func.count(Vessel.id)).scalar()
    drafts_count = drafts_q.with_entities(func.count(Declaration.id)).scalar()
    submitted_count = submitted_q.with_entities(func.count(Declaration.id)).scalar()
    arriving_today = arriving_q.with_entities(func.count(Declaration.id)).scalar()
    cert_warnings = warnings_q.with_entities(func.count(Vessel.id)).scalar()

    recent_decls = recent_q.order_by(desc(Declaration.updated_at)).limit(8).all()

    matches: list[dict] = []
    if q:
        search = f"%{q}%"
        vessels = (
            vessel_search_q
            .filter(or_(Vessel.registration_no.like(search), Vessel.name.like(search)))
            .order_by(desc(Vessel.updated_at))
            .limit(12)
            .all()
        )
        for v in vessels:
            v_dict = {c.name: getattr(v, c.name) for c in v.__table__.columns}
            v_dict["organization_name"] = v.organization.name if v.organization else None
            v_dict["certificate_status"] = certificate_status(v.certificate_expiry_date)
            matches.append(v_dict)

    recent = []
    for d in recent_decls:
        d_dict = {c.name: getattr(d, c.name) for c in d.__table__.columns}
        d_dict["unload"] = json.loads(d_dict.pop("unload_json", "{}"))
        d_dict["load"] = json.loads(d_dict.pop("load_json", "{}"))
        recent.append(d_dict)

    return {
        "stats": {
            "vessels": vessels_count,
            "drafts": drafts_count,
            "submitted": submitted_count,
            "arrivingToday": arriving_today,
            "certificateWarnings": cert_warnings,
        },
        "recent": recent,
        "matches": matches,
        "attention": _attention_queue(db, scope),
        # Nhánh riêng cho PLATFORM_ADMIN — trục lọc khác hẳn _attention_queue
        # (cancel_requested_at, không phải workflow_status). None cho role khác.
        "cancel_queue": _cancel_request_queue(db) if scope.user.role == "PLATFORM_ADMIN" else None,
        "demo_mode": is_demo_data_active(db),
    }


# ══════════════════════════════════════════════════════════════════════════════
# VESSELS
# ══════════════════════════════════════════════════════════════════════════════

def _vessel_dict(v: Vessel) -> dict:
    d = {c.name: getattr(v, c.name) for c in v.__table__.columns}
    d["organization_name"] = v.organization.name if v.organization else None
    d["certificate_status"] = certificate_status(v.certificate_expiry_date)
    d["operating_profiles"] = [
        {
            "id": profile.id,
            "sequence": profile.sequence,
            "activity_area": profile.activity_area,
            "deadweight_tons": profile.deadweight_tons,
            "cargo_capacity_tons": profile.cargo_capacity_tons,
        }
        for profile in v.operating_profiles
    ]
    return d


def _sync_vessel_operating_profiles(
    vessel: Vessel,
    profiles: Optional[List[VesselOperatingProfilePayload | dict[str, Any]]],
) -> None:
    if profiles is None:
        return
    vessel.operating_profiles.clear()
    normalized: list[dict[str, Any]] = []
    for index, profile in enumerate(profiles, start=1):
        values = profile.model_dump() if isinstance(profile, BaseModel) else profile
        activity_area = str(values.get("activity_area") or "").strip()
        if not activity_area:
            continue
        item = {
            "sequence": index,
            "activity_area": activity_area,
            "deadweight_tons": values.get("deadweight_tons"),
            "cargo_capacity_tons": values.get("cargo_capacity_tons"),
        }
        normalized.append(item)
        vessel.operating_profiles.append(VesselOperatingProfile(**item))
    if normalized:
        vessel.vessel_class = " / ".join(item["activity_area"] for item in normalized)
        vessel.deadweight_tons = normalized[0]["deadweight_tons"]
        vessel.cargo_capacity_tons = normalized[0]["cargo_capacity_tons"]


@app.get("/api/reporting-units")
def list_reporting_units(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PORT_STAFF", "PLATFORM_ADMIN")),
):
    """Active reporting units the caller may select as tenant context.

    PORT_STAFF sees only units where it holds membership; PLATFORM_ADMIN sees all
    active units and must deliberately choose one before opening tenant data.
    """
    query = db.query(ReportingUnit).filter(ReportingUnit.is_active == 1)
    staff_functions: dict[int, str | None] = {}
    if user.role == "PORT_STAFF":
        memberships = db.query(ReportingUnitUser).filter_by(user_id=user.id).all()
        if not memberships:
            return {"items": [], "role": user.role}
        staff_functions = {m.reporting_unit_id: m.staff_function for m in memberships}
        query = query.filter(ReportingUnit.id.in_(staff_functions.keys()))
    units = query.order_by(ReportingUnit.name).all()
    return {
        "items": [
            {
                "id": u.id, "name": u.name, "code": u.code, "notify_email": u.notify_email or "",
                # None cho PLATFORM_ADMIN (không gate theo staff_function — full
                # authority ở mọi cổng, xem Scope.allows_staff_function).
                "staff_function": staff_functions.get(u.id) if user.role == "PORT_STAFF" else None,
            }
            for u in units
        ],
        "role": user.role,
    }


@app.post("/api/reporting-units", status_code=201)
def create_reporting_unit(
    payload: ReportingUnitCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    """Create an empty tenant. Memberships and customer links are separate.

    This is a platform operation and deliberately does not infer or copy the
    currently selected tenant's organizations, staff or historical data.
    """
    duplicate = db.query(ReportingUnit).filter(
        or_(
            func.lower(ReportingUnit.name) == payload.name.lower(),
            func.lower(ReportingUnit.code) == payload.code.lower(),
        )
    ).first()
    if duplicate:
        field = "tên" if duplicate.name.lower() == payload.name.lower() else "mã"
        raise HTTPException(status_code=409, detail=f"Đã có đơn vị báo cáo dùng {field} này.")
    item = ReportingUnit(
        name=payload.name, code=payload.code, official_header_json="{}",
        notify_email=payload.notify_email,
        is_active=1, created_at=now_iso(), updated_at=now_iso(),
    )
    db.add(item)
    db.flush()
    audit(
        db, "REPORTING_UNIT", item.id, "CREATE", f"{item.name} ({item.code})",
        actor_user_id=user.id, reporting_unit_id=item.id,
    )
    db.commit()
    db.refresh(item)
    return {
        "id": item.id, "name": item.name, "code": item.code,
        "notify_email": item.notify_email or "", "is_active": bool(item.is_active),
    }


@app.put("/api/reporting-units/{unit_id}")
def update_reporting_unit(
    unit_id: int,
    payload: ReportingUnitCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    """Update a reporting unit's name/code/notify_email (platform operation)."""
    item = db.query(ReportingUnit).filter(ReportingUnit.id == unit_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn vị báo cáo.")
    duplicate = db.query(ReportingUnit).filter(
        ReportingUnit.id != unit_id,
        or_(
            func.lower(ReportingUnit.name) == payload.name.lower(),
            func.lower(ReportingUnit.code) == payload.code.lower(),
        ),
    ).first()
    if duplicate:
        field = "tên" if duplicate.name.lower() == payload.name.lower() else "mã"
        raise HTTPException(status_code=409, detail=f"Đã có đơn vị báo cáo khác dùng {field} này.")
    item.name = payload.name
    item.code = payload.code
    item.notify_email = payload.notify_email
    item.updated_at = now_iso()
    audit(
        db, "REPORTING_UNIT", item.id, "UPDATE", f"{item.name} ({item.code})",
        actor_user_id=user.id, reporting_unit_id=item.id,
    )
    db.commit()
    db.refresh(item)
    return {
        "id": item.id, "name": item.name, "code": item.code,
        "notify_email": item.notify_email or "", "is_active": bool(item.is_active),
    }


@app.get("/api/reporting-unit/organizations")
def list_reporting_unit_organizations(
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    if not scope.member_org_ids:
        return {"items": []}
    organizations = (
        db.query(Organization)
        .filter(Organization.id.in_(scope.member_org_ids))
        .order_by(Organization.name, Organization.id)
        .all()
    )
    return {"items": [{"id": item.id, "name": item.name} for item in organizations]}


@app.get("/api/vessels")
def get_vessels(db: Session = Depends(get_db), scope: Scope = Depends(resolve_scope)):
    # Reads are scoped: CUSTOMER to its Organization; PORT to the Organizations
    # linked to the resolved reporting unit. Never a global fetch.
    org_ids = scope.visible_org_ids()
    if not org_ids:
        return []
    vessels = (
        db.query(Vessel)
        .filter(Vessel.organization_id.in_(org_ids))
        .order_by(Vessel.name, Vessel.registration_no)
        .all()
    )
    return [_vessel_dict(v) for v in vessels]


def _joined_profile_value(vessel: Vessel, field: str) -> Any:
    values = [getattr(profile, field) for profile in vessel.operating_profiles]
    values = [value for value in values if value is not None]
    if not values:
        return getattr(vessel, field, None)
    if len(values) == 1:
        return values[0]
    return " / ".join(f"{value:g}" for value in values)


@app.get("/api/port-vessel-register")
def get_port_vessel_register(
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    register_ids = register_vessel_ids(db, scope.reporting_unit_id)
    vessels = (
        db.query(Vessel)
        .filter(Vessel.id.in_(register_ids))
        .order_by(Vessel.name, Vessel.registration_no)
        .all()
    ) if register_ids else []

    # "Lượt gần nhất" — chỉ tham khảo, KHÔNG chuyển record giữa 2 tab (quyết
    # định nghiệp vụ đã chốt, xem ROADMAP_PORT_OPERATIONS.md Giai đoạn 3). Sổ
    # theo dõi lưu theo phương tiện (vĩnh viễn); Declaration là theo lượt.
    latest_calls: dict[int, dict] = {}
    if register_ids:
        recent = (
            db.query(Declaration)
            .filter(Declaration.vessel_id.in_(register_ids))
            # updated_at only has second precision — id DESC as tiebreak makes
            # "most recent" deterministic even when two saves land in the same second.
            .order_by(Declaration.vessel_id, Declaration.updated_at.desc(), Declaration.id.desc())
            .all()
        )
        for declaration in recent:
            if declaration.vessel_id not in latest_calls:
                latest_calls[declaration.vessel_id] = {
                    "reference_no": declaration.reference_no,
                    "workflow_status": declaration.workflow_status,
                    "actual_departure_at": declaration.actual_departure_at,
                    "updated_at": declaration.updated_at,
                }

    profile_count = sum(len(vessel.operating_profiles) for vessel in vessels)
    multi_area_count = sum(len(vessel.operating_profiles) > 1 for vessel in vessels)
    certificate_warnings = sum(
        certificate_status(vessel.certificate_expiry_date) in {"EXPIRING", "EXPIRED"}
        for vessel in vessels
    )
    teu_capacity = sum(vessel.container_capacity_teu or 0 for vessel in vessels)
    # Cộng theo từng dòng operating_profiles (không phải vessel.cargo_capacity_tons,
    # vốn chỉ giữ giá trị của vùng đầu tiên) để không bỏ sót năng lực vùng thứ hai
    # của Salan hoạt động cả VR-SI lẫn VR-SII.
    tonnage_capacity = sum(
        profile.cargo_capacity_tons or 0
        for vessel in vessels
        for profile in vessel.operating_profiles
    )
    area_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for vessel in vessels:
        type_counts[vessel.vessel_type] = type_counts.get(vessel.vessel_type, 0) + 1
        # Mỗi Salan tính đúng một lần: vùng đơn giữ nguyên nhãn, vùng kép gộp
        # thành một dòng riêng (vd "VR-SI / VR-SII") thay vì cộng trùng vào cả
        # hai thanh — nếu không tổng các thanh sẽ vượt quá tổng số Salan.
        areas = sorted({profile.activity_area for profile in vessel.operating_profiles if profile.activity_area})
        if not areas:
            continue
        label = " / ".join(areas)
        area_counts[label] = area_counts.get(label, 0) + 1
    items = []
    for vessel in vessels:
        item = _vessel_dict(vessel)
        item["latest_call"] = latest_calls.get(vessel.id)
        items.append(item)

    return {
        "items": items,
        "stats": {
            "vessels": len(vessels),
            "operatingProfiles": profile_count,
            "multiAreaVessels": multi_area_count,
            "certificateWarnings": certificate_warnings,
            "teuCapacity": teu_capacity,
            "tonnageCapacity": tonnage_capacity,
        },
        "byArea": [
            {"label": label, "value": value}
            for label, value in sorted(area_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "byType": [
            {"label": label, "value": value}
            for label, value in sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
    }


@app.get("/api/port-vessel-register/export")
def export_port_vessel_register(
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    register_ids = register_vessel_ids(db, scope.reporting_unit_id)
    vessels = (
        db.query(Vessel)
        .filter(Vessel.id.in_(register_ids))
        .order_by(Vessel.name, Vessel.registration_no)
        .all()
    ) if register_ids else []
    headers = [
        "STT", "TÊN PHƯƠNG TIỆN", "SỐ ĐĂNG KÝ", "LOẠI PHƯƠNG TIỆN (CÔNG DỤNG)",
        "CẤP PT (VÙNG HOẠT ĐỘNG)", "CHIỀU DÀI (M)", "TRỌNG TẢI TOÀN PHẦN (TẤN)",
        "DUNG TÍCH (M3)", "KHẢ NĂNG KHAI THÁC (TẤN)", "KHẢ NĂNG KHAI THÁC (TEU)",
        "NGÀY HẾT HẠN GCNATKT&BVMT", "SỐ THUYỀN VIÊN", "THUYỀN TRƯỞNG",
        "SỐ ĐIỆN THOẠI LIÊN HỆ",
    ]
    rows = []
    for index, vessel in enumerate(vessels, start=1):
        areas = [profile.activity_area for profile in vessel.operating_profiles if profile.activity_area]
        rows.append([
            index,
            vessel.name,
            vessel.registration_no,
            vessel.vessel_type,
            " / ".join(areas) if areas else vessel.vessel_class,
            vessel.length_m,
            _joined_profile_value(vessel, "deadweight_tons"),
            vessel.gross_tonnage,
            _joined_profile_value(vessel, "cargo_capacity_tons"),
            vessel.container_capacity_teu,
            vessel.certificate_expiry_date or "",
            vessel.min_crew,
            vessel.tracking_master_name,
            vessel.tracking_master_phone,
        ])
    content = make_xlsx("DỮ LIỆU SÀ LAN", headers, rows)
    filename = f"DU_LIEU_SA_LAN_{date.today().isoformat()}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/port-vessel-register/remove")
def remove_from_port_vessel_register(
    payload: PortRegisterRemoveRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    """Remove rows from THIS reporting unit's register without deleting masters."""
    register_ids = set(register_vessel_ids(db, scope.reporting_unit_id))
    missing_ids = [item for item in payload.ids if item not in register_ids]
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy Salan đang được theo dõi: {', '.join(map(str, missing_ids))}.",
        )

    updated_at = now_iso()
    removed = 0
    for vessel_id in payload.ids:
        link = (
            db.query(ReportingUnitVessel)
            .filter_by(reporting_unit_id=scope.reporting_unit_id, vessel_id=vessel_id)
            .first()
        )
        if link is None:
            continue
        vessel = db.get(Vessel, vessel_id)
        db.delete(link)
        # Legacy compatibility flag: clear only when no unit tracks it anymore.
        if vessel is not None:
            still_tracked = (
                db.query(ReportingUnitVessel).filter_by(vessel_id=vessel_id).count() > 1
            )
            if not still_tracked:
                vessel.is_port_tracked = 0
            vessel.port_tracking_updated_at = updated_at
            vessel.updated_at = updated_at
            vessel.version += 1
        audit(
            db, "VESSEL", vessel_id, "PORT_REGISTER_REMOVE",
            (vessel.name + " / " + vessel.registration_no) if vessel else str(vessel_id),
            actor_user_id=scope.user.id,
            organization_id=vessel.organization_id if vessel else None,
            reporting_unit_id=scope.reporting_unit_id,
        )
        removed += 1
    db.commit()
    return {"removed": removed, "ids": payload.ids}


@app.post("/api/port-vessel-register/add")
def add_to_port_vessel_register(
    payload: PortRegisterAddRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    """Link existing Vessel masters to this unit without changing ownership."""
    vessels = db.query(Vessel).filter(Vessel.id.in_(payload.ids)).all()
    by_id = {vessel.id: vessel for vessel in vessels}
    missing_ids = [item for item in payload.ids if item not in by_id]
    if missing_ids:
        raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện cần thêm vào sổ.")
    added = 0
    timestamp = now_iso()
    for vessel_id in payload.ids:
        if db.query(ReportingUnitVessel).filter_by(
            reporting_unit_id=scope.reporting_unit_id, vessel_id=vessel_id,
        ).first() is not None:
            continue
        vessel = by_id[vessel_id]
        db.add(ReportingUnitVessel(
            reporting_unit_id=scope.reporting_unit_id,
            vessel_id=vessel_id,
            added_by_user_id=scope.user.id,
            created_at=timestamp,
        ))
        vessel.is_port_tracked = 1
        vessel.port_tracking_updated_at = timestamp
        vessel.updated_at = timestamp
        vessel.version += 1
        audit(
            db, "VESSEL", vessel_id, "PORT_REGISTER_ADD",
            f"{vessel.name} / {vessel.registration_no}",
            actor_user_id=scope.user.id,
            organization_id=vessel.organization_id,
            reporting_unit_id=scope.reporting_unit_id,
        )
        added += 1
    db.commit()
    return {"added": added, "ids": payload.ids}


@app.post("/api/vessels")
def save_vessel(
    payload: VesselSaveRequest,
    port_register: bool = False,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    user = scope.user
    if port_register and scope.is_customer:
        raise HTTPException(status_code=403, detail="Sổ theo dõi Salan chỉ dành cho Nhân viên Cảng và Admin.")
    if scope.is_customer:
        # Force organization to the customer's bound organization
        org_id = user.organization_id
    else:
        # PLATFORM_ADMIN/PORT_STAFF can specify organization name
        org_name = (
            (payload.organization or {}).get("name") if isinstance(payload.organization, dict)
            else payload.organization_name
        )
        if port_register:
            # The internal register is vessel-scoped and Organization-agnostic:
            # it may reference any Organization's vessel.
            org = _get_or_create_org(db, org_name)
        else:
            org = _resolve_org_for_port_scope(db, scope, org_name)
        org_id = org.id if org else None

    if not payload.id:
        remove_demo_data_for_real_input(
            db,
            retain_organization_id=org_id if scope.is_customer else None,
            organization_data=payload.organization if isinstance(payload.organization, dict) else None,
            allowed_organization_ids=scope.member_org_ids if scope.is_port else None,
        )

    data = payload.model_dump(
        exclude={"id", "version", "organization", "organization_name", "operating_profiles"}
    )
    data["organization_id"] = org_id
    data["updated_at"] = now_iso()
    if port_register:
        data["is_port_tracked"] = 1
        data["port_tracking_updated_at"] = data["updated_at"]

    audit_unit_id = scope.reporting_unit_id if scope.is_port else None
    if payload.id:
        vessel = db.query(Vessel).filter(Vessel.id == payload.id).first()
        if not vessel:
            raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")
        if payload.version is not None and payload.version != vessel.version:
            raise HTTPException(status_code=409, detail="Hồ sơ phương tiện đã được cập nhật bởi người dùng khác.")
        # Tenant isolation check (customer org ownership or in-unit vessel/register).
        require_vessel_in_scope(db, scope, vessel)

        for k, v in data.items():
            if hasattr(vessel, k):
                setattr(vessel, k, v)
        _sync_vessel_operating_profiles(vessel, payload.operating_profiles)
        vessel.version += 1
        audit(
            db, "VESSEL", vessel.id, "UPDATE", f"{vessel.name} / {vessel.registration_no}",
            actor_user_id=user.id, organization_id=vessel.organization_id,
            reporting_unit_id=audit_unit_id,
        )
    else:
        data["created_at"] = now_iso()
        vessel = Vessel(**{k: v for k, v in data.items() if hasattr(Vessel, k)})
        db.add(vessel)
        db.flush()
        profiles = payload.operating_profiles
        if profiles is None and vessel.vessel_class:
            profiles = [VesselOperatingProfilePayload(
                activity_area=vessel.vessel_class,
                deadweight_tons=vessel.deadweight_tons,
                cargo_capacity_tons=vessel.cargo_capacity_tons,
            )]
        _sync_vessel_operating_profiles(vessel, profiles)
        audit(
            db, "VESSEL", vessel.id, "CREATE", f"{vessel.name} / {vessel.registration_no}",
            actor_user_id=user.id, organization_id=vessel.organization_id,
            reporting_unit_id=audit_unit_id,
        )

    # Internal register add is tenant-scoped through reporting_unit_vessels.
    if port_register and scope.is_port:
        exists = (
            db.query(ReportingUnitVessel)
            .filter_by(reporting_unit_id=scope.reporting_unit_id, vessel_id=vessel.id)
            .first()
        )
        if exists is None:
            db.add(ReportingUnitVessel(
                reporting_unit_id=scope.reporting_unit_id, vessel_id=vessel.id,
                added_by_user_id=user.id, created_at=now_iso(),
            ))
    db.commit()
    db.refresh(vessel)

    return _vessel_dict(vessel)


@app.delete("/api/vessels/{vessel_id}")
def delete_vessel(
    vessel_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    # Deletion is PLATFORM_ADMIN-only: PORT_STAFF keeps edit rights (fix wrong
    # fields) but a hard delete of a master vessel record is an admin action.
    if scope.user.role != "PLATFORM_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Chỉ Platform admin mới có quyền xóa hồ sơ phương tiện.",
        )
    vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if not vessel:
        raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")
    require_vessel_in_scope(db, scope, vessel)

    declaration_count = db.query(Declaration).filter(Declaration.vessel_id == vessel_id).count()
    if declaration_count:
        raise HTTPException(
            status_code=409,
            detail=f"Không thể xóa: phương tiện đang gắn với {declaration_count} phiếu khai báo. "
                   "Xóa các phiếu liên quan trước nếu chắc chắn cần xóa hồ sơ này.",
        )
    crew_count = db.query(CrewMember).filter(CrewMember.vessel_id == vessel_id).count()
    if crew_count:
        raise HTTPException(
            status_code=409,
            detail=f"Không thể xóa: phương tiện đang gắn với {crew_count} thuyền viên trong Danh sách thuyền viên. "
                   "Bỏ gán thuyền viên khỏi phương tiện này trước khi xóa.",
        )

    identity = f"{vessel.name} / {vessel.registration_no}"
    organization_id = vessel.organization_id
    audit_unit_id = scope.reporting_unit_id if scope.is_port else None
    db.delete(vessel)
    audit(
        db, "VESSEL", vessel_id, "DELETE", identity,
        actor_user_id=scope.user.id, organization_id=organization_id,
        reporting_unit_id=audit_unit_id,
    )
    db.commit()
    return {"deleted": vessel_id}


@app.post("/api/vessels/{vessel_id}/verify-registry")
def verify_vessel_registry(
    vessel_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    """
    Local-only registry date check. Does NOT call any external Maritime Authority API.
    Records verification source as 'local' and updates certificate_status.
    External registry integration is out of scope until T6.
    """
    vessel = db.query(Vessel).filter(Vessel.id == vessel_id).first()
    if not vessel:
        raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")

    # Tenant isolation check (customer org ownership or in-scope port vessel).
    require_vessel_in_scope(db, scope, vessel)

    adapter_status = registry_adapter().status()
    vessel.registry_verification_status = "VERIFIED_LOCAL"
    vessel.registry_verified_at = now_iso()
    vessel.registry_verification_source = "local"
    vessel.updated_at = now_iso()
    db.commit()
    db.refresh(vessel)
    result = _vessel_dict(vessel)
    result["adapter"] = adapter_status
    return result


# ══════════════════════════════════════════════════════════════════════════════
# CREW
# ══════════════════════════════════════════════════════════════════════════════

def _crew_dict(c: CrewMember, db: Session) -> dict:
    d = {col.name: getattr(c, col.name) for col in c.__table__.columns}
    d["certificate_status"] = certificate_status(c.certificate_expiry_date)
    if c.vessel_id:
        vessel = db.query(Vessel).filter(
            Vessel.id == c.vessel_id,
            Vessel.organization_id == c.organization_id,
        ).first()
        d["vessel_name"] = vessel.name if vessel else None
        d["registration_no"] = vessel.registration_no if vessel else None
    else:
        d["vessel_name"] = None
        d["registration_no"] = None
    return d


@app.get("/api/crew")
def get_crew(db: Session = Depends(get_db), scope: Scope = Depends(resolve_scope)):
    org_ids = scope.visible_org_ids()
    if not org_ids:
        return []
    crews = (
        db.query(CrewMember)
        .filter(CrewMember.organization_id.in_(org_ids))
        .order_by(CrewMember.full_name)
        .all()
    )
    return [_crew_dict(c, db) for c in crews]


@app.post("/api/crew")
def save_crew(
    payload: CrewSaveRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    user = scope.user
    data = payload.model_dump(exclude={"id", "version"})
    data["updated_at"] = now_iso()

    if scope.is_customer:
        data["organization_id"] = user.organization_id
    elif payload.id is None and data.get("organization_id") is None:
        raise HTTPException(status_code=422, detail="Cần chọn doanh nghiệp thuộc đơn vị báo cáo.")
    elif data.get("organization_id") is not None:
        scope.require_org(data.get("organization_id"))

    if data.get("vessel_id") is not None:
        vessel = db.get(Vessel, data["vessel_id"])
        if vessel is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")
        require_vessel_in_scope(db, scope, vessel)
        if data.get("organization_id") is not None and vessel.organization_id != data["organization_id"]:
            raise HTTPException(status_code=422, detail="Phương tiện không thuộc doanh nghiệp đã chọn.")

    if payload.id:
        member = db.query(CrewMember).filter(CrewMember.id == payload.id).first()
        if not member:
            raise HTTPException(status_code=404, detail="Không tìm thấy thuyền viên.")
        if payload.version is not None and payload.version != member.version:
            raise HTTPException(status_code=409, detail="Hồ sơ thuyền viên đã được cập nhật bởi người dùng khác.")
        if scope.is_customer or member.organization_id is not None:
            scope.require_org(member.organization_id)

        # For CUSTOMER we keep organization the same.
        if scope.is_customer:
            data.pop("organization_id", None)
        elif data.get("organization_id") is None:
            data.pop("organization_id", None)
        elif data["organization_id"] != member.organization_id and member.vessel_id is not None:
            assigned_vessel = db.get(Vessel, member.vessel_id)
            if assigned_vessel is None or assigned_vessel.organization_id != data["organization_id"]:
                data["vessel_id"] = None
        if "vessel_id" in data and data["vessel_id"] is None:
            if data.get("organization_id", member.organization_id) == member.organization_id:
                data.pop("vessel_id")

        for k, v in data.items():
            if hasattr(member, k):
                setattr(member, k, v)
        member.version += 1
        audit(
            db, "CREW", member.id, "UPDATE", f"{member.full_name} / {member.crew_role}",
            actor_user_id=user.id, organization_id=member.organization_id,
            reporting_unit_id=scope.reporting_unit_id if scope.is_port else None,
        )
        db.commit()
        db.refresh(member)
    else:
        data["created_at"] = now_iso()
        member = CrewMember(**{k: v for k, v in data.items() if hasattr(CrewMember, k)})
        db.add(member)
        db.flush()
        scope.require_org(member.organization_id)
        audit(
            db, "CREW", member.id, "CREATE", f"{member.full_name} / {member.crew_role}",
            actor_user_id=user.id, organization_id=member.organization_id,
            reporting_unit_id=scope.reporting_unit_id if scope.is_port else None,
        )
        db.commit()
        db.refresh(member)

    return _crew_dict(member, db)


# ══════════════════════════════════════════════════════════════════════════════
# DECLARATIONS
# ══════════════════════════════════════════════════════════════════════════════

def _declaration_dict(d: Declaration) -> dict:
    result = {c.name: getattr(d, c.name) for c in d.__table__.columns}
    result["unload"] = json.loads(result.pop("unload_json", "{}"))
    result["load"] = json.loads(result.pop("load_json", "{}"))
    return result


@app.get("/api/declarations")
def get_declarations(
    q: Optional[str] = None,
    movement_type: Optional[str] = None,
    workflow_status: Optional[str] = None,
    master_name: Optional[str] = None,
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = None,
    page: Optional[int] = Query(default=None, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: str = Query(default="updated_at"),
    direction: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    query = db.query(Declaration)

    if scope.is_customer:
        query = query.filter(Declaration.organization_id == scope.organization_id)
    else:
        # PORT: declarations belonging to an Organization linked to the
        # resolved unit, OR directly tagged with this unit (a declaration
        # created with no customer organization chosen — see
        # Declaration.reporting_unit_id — must still be visible to the unit
        # that created it, not silently disappear).
        org_ids = scope.member_org_ids
        org_clause = Declaration.organization_id.in_(org_ids) if org_ids else sql_false()
        query = query.filter(or_(org_clause, Declaration.reporting_unit_id == scope.reporting_unit_id))
        if scope.user.role != "PLATFORM_ADMIN":
            # PORT_STAFF reviews submitted work only — a CUSTOMER's un-submitted
            # draft isn't theirs to see yet. PLATFORM_ADMIN is exempt: drafts it
            # creates itself (see review-strip "Lưu phiếu" flow) must remain
            # visible to the admin who made them, or they're unreachable.
            query = query.filter(Declaration.workflow_status != "DRAFT")

    if q:
        search = f"%{q}%"
        query = query.filter(
            or_(
                Declaration.vessel_name.like(search),
                Declaration.registration_no.like(search),
                Declaration.reference_no.like(search),
            )
        )
    if movement_type:
        query = query.filter(Declaration.movement_type == movement_type)
    if workflow_status:
        query = query.filter(Declaration.workflow_status == workflow_status)
    if master_name:
        query = query.filter(Declaration.master_name.like(f"%{master_name}%"))
    if from_:
        query = query.filter(Declaration.declaration_date >= from_)
    if to:
        query = query.filter(Declaration.declaration_date <= to)
    sort_columns = {
        "updated_at": Declaration.updated_at,
        "declaration_date": Declaration.declaration_date,
        "reference_no": Declaration.reference_no,
        "workflow_status": Declaration.workflow_status,
    }
    order_column = sort_columns.get(sort, Declaration.updated_at)
    ordered = query.order_by(order_column.asc() if direction == "asc" else order_column.desc(), Declaration.id.desc())
    if page is None:
        # Compatibility mode for existing consumers. New UI clients must opt in
        # to the bounded envelope by sending an explicit page number.
        return [_declaration_dict(d) for d in ordered.all()]

    total = query.order_by(None).count()
    decls = ordered.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_declaration_dict(d) for d in decls],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "sort": sort if sort in sort_columns else "updated_at",
        "direction": direction,
    }


@app.post("/api/declarations")
def save_declaration(
    payload: DeclarationSaveRequest,
    background: BackgroundTasks,
    submit: bool = False,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    user = scope.user
    # PLATFORM_ADMIN has full authority and may submit on a customer's behalf
    # without logging into their account; the audit trail below still records
    # the admin as the real actor, so the customer's own submissions (through
    # their own login) remain the ordinary, unambiguous legal record.
    if submit and not (scope.is_customer or user.role == "PLATFORM_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ khách hàng/chủ phương tiện (CUSTOMER) hoặc Platform admin mới có quyền xác nhận gửi phiếu khai báo."
        )

    if scope.is_customer:
        # Force organization to the customer's bound organization
        org_id = user.organization_id
        company_name = user.organization.name if user.organization else "N/A"
    else:
        # PLATFORM_ADMIN/PORT_STAFF specify the company; a brand-new company is
        # onboarded through the resolved unit, an existing one must already
        # belong to it. The field is optional — a declaration can be created
        # before the customer organization is known — so a blank value simply
        # means no organization, displayed as "-" rather than a placeholder.
        company_name_raw = (payload.company_name or "").strip()
        org = _resolve_org_for_port_scope(db, scope, company_name_raw or None)
        org_id = org.id if org else None
        company_name = company_name_raw or "-"

    # Tenant tag independent of organization_id — see Declaration.reporting_unit_id.
    # PORT scope always carries its own unit; CUSTOMER falls back to the same
    # unit-resolution rule used for the reference number (unambiguous org
    # membership), so both remain consistent for the same declaration.
    unit_id = scope.reporting_unit_id if scope.is_port else _resolve_unit_id_for_reference(db, scope, org_id)

    # IDOR prevention: check vessel is inside the caller's scope
    if payload.vessel_id:
        vessel = db.query(Vessel).filter(Vessel.id == payload.vessel_id).first()
        if not vessel:
            raise HTTPException(status_code=404, detail="Không tìm thấy phương tiện.")
        require_vessel_in_scope(db, scope, vessel)

    # IDOR prevention: check crew members are inside the caller's scope
    if payload.crew_ids:
        for crew_id in payload.crew_ids:
            crew_member = db.query(CrewMember).filter(CrewMember.id == crew_id).first()
            if not crew_member:
                raise HTTPException(status_code=404, detail=f"Không tìm thấy thuyền viên ID {crew_id}.")
            scope.require_org(crew_member.organization_id)

    unload_data = cargo(payload.unload.model_dump())
    load_data = cargo(payload.load.model_dump())

    if payload.id:
        decl = db.query(Declaration).filter(Declaration.id == payload.id).first()
        if not decl:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiếu khai báo.")
        if payload.version is not None and payload.version != decl.version:
            raise HTTPException(status_code=409, detail="Phiếu khai báo đã được cập nhật bởi người dùng khác.")
        # Tenant isolation check
        scope.require_declaration(decl.organization_id, decl.reporting_unit_id)

        # A submitted/approved declaration is normally locked for editing; the
        # customer or Cảng must use the REQUEST_CHANGES flow to reopen it.
        # PLATFORM_ADMIN is exempt: an admin has full authority to correct or
        # clean up any record, including approved ones. The audit trail below
        # still records the admin as the actor.
        if decl.workflow_status not in ("DRAFT", "CHANGES_REQUESTED") and user.role != "PLATFORM_ADMIN":
            raise HTTPException(
                status_code=409,
                detail="Không thể chỉnh sửa phiếu đã xác nhận gửi. Dùng luồng REQUEST_CHANGES để điều chỉnh.",
            )
        # Update fields
        for field_name in (
            "declaration_date", "vessel_name", "registration_no",
            "vessel_type", "vessel_class", "length_m", "deadweight_tons", "gross_tonnage",
            "certificate_expiry_date", "crew_count", "crew_onboard_count", "passenger_count", "last_port",
            "working_port", "departure_berth", "destination_port", "agent_ptnd_name",
            "is_passenger_call", "eta", "etd", "master_name", "master_phone",
            "movement_type", "purpose", "cargo_description",
            "actual_arrival_at", "actual_departure_at", "vessel_id",
        ):
            val = getattr(payload, field_name, None)
            if val is not None and hasattr(decl, field_name):
                setattr(decl, field_name, val)

        decl.company_name = company_name
        decl.unload_json = json.dumps(unload_data, ensure_ascii=False)
        decl.load_json = json.dumps(load_data, ensure_ascii=False)
        decl.organization_id = org_id
        # Keep whichever unit tag the declaration already had if this save
        # can't newly resolve one (e.g. org removed on edit) — never erase it.
        decl.reporting_unit_id = unit_id or decl.reporting_unit_id
        decl.updated_at = now_iso()
        decl.version += 1
    else:
        ref_no = _next_reference_no(db, scope, org_id)
        decl = Declaration(
            reference_no=ref_no,
            organization_id=org_id,
            reporting_unit_id=unit_id,
            vessel_id=payload.vessel_id,
            company_name=company_name,
            declaration_date=payload.declaration_date,
            vessel_name=payload.vessel_name,
            registration_no=payload.registration_no,
            vessel_type=payload.vessel_type,
            vessel_class=payload.vessel_class,
            length_m=payload.length_m,
            deadweight_tons=payload.deadweight_tons,
            gross_tonnage=payload.gross_tonnage,
            certificate_expiry_date=payload.certificate_expiry_date,
            crew_count=payload.crew_count,
            crew_onboard_count=payload.crew_onboard_count,
            passenger_count=payload.passenger_count,
            last_port=payload.last_port,
            working_port=payload.working_port,
            departure_berth=payload.departure_berth,
            destination_port=payload.destination_port,
            agent_ptnd_name=payload.agent_ptnd_name,
            is_passenger_call=1 if payload.is_passenger_call else 0,
            eta=payload.eta,
            etd=payload.etd,
            master_name=payload.master_name,
            master_phone=payload.master_phone,
            movement_type=payload.movement_type,
            purpose=payload.purpose,
            cargo_description=payload.cargo_description,
            actual_arrival_at=payload.actual_arrival_at,
            actual_departure_at=payload.actual_departure_at,
            unload_json=json.dumps(unload_data, ensure_ascii=False),
            load_json=json.dumps(load_data, ensure_ascii=False),
            workflow_status="DRAFT",
            status="DRAFT",
            created_at=now_iso(),
            updated_at=now_iso(),
        )
        # Insert with a retry: if two declarations of the same unit/day race for
        # the same TT-YYMMDD-NNN, the unique constraint rejects the duplicate and
        # we regenerate the next number. A savepoint keeps prior work intact.
        for attempt in range(25):
            try:
                with db.begin_nested():
                    db.add(decl)
                    db.flush()
                break
            except IntegrityError as exc:
                if "reference_no" not in str(getattr(exc, "orig", exc)).lower():
                    raise
                # Exiting `begin_nested()` via exception already rolls back the
                # SAVEPOINT, which detaches `decl` from the session on its own —
                # an explicit db.expunge() here would raise
                # InvalidRequestError("not present in this Session"). Just clear
                # the id/reference and let the next db.add() re-attach it.
                decl.id = None
                decl.reference_no = _next_reference_no(db, scope, org_id)
        else:
            raise HTTPException(status_code=409, detail="Không tạo được mã phiếu, vui lòng thử lại.")

    # Sync crew snapshot
    if payload.crew_ids is not None:
        db.query(DeclarationCrew).filter(DeclarationCrew.declaration_id == decl.id).delete()
        for crew_id in payload.crew_ids:
            member = db.query(CrewMember).filter(CrewMember.id == crew_id).first()
            if member:
                db.add(DeclarationCrew(
                    declaration_id=decl.id,
                    crew_member_id=member.id,
                    crew_role_snapshot=member.crew_role,
                    certificate_no_snapshot=member.professional_certificate_no,
                    certificate_expiry_snapshot=member.certificate_expiry_date,
                ))

    # An admin may edit an already-APPROVED declaration to correct it. Saving
    # such a correction must NOT demote it back to PENDING_REVIEW — the record
    # stays approved. So treat a "submit" on an already-approved declaration as a
    # plain update (no status change, no re-notification).
    if submit and payload.id and decl.workflow_status == "APPROVED":
        submit = False

    submit_is_resubmit = False
    if submit:
        # Distinguish a fresh submit from a re-submit after the port asked for
        # changes — captured BEFORE the status is overwritten below.
        submit_is_resubmit = bool(payload.id and decl.workflow_status == "CHANGES_REQUESTED")
        if submit_is_resubmit:
            decl.port_approval = "PENDING"
        decl.workflow_status = "PENDING_REVIEW"
        decl.status = "SUBMITTED"
        decl.submitted_at = now_iso()
        event = DeclarationEvent(
            declaration_id=decl.id,
            action="SUBMIT",
            from_status="DRAFT",
            to_status="PENDING_REVIEW",
            actor_name=user.full_name or user.username,
            actor_role=user.role,
            actor_user_id=user.id,
            correlation_id=correlation_id.get(),
            note=(
                "Khách hàng xác nhận gửi phiếu khai báo."
                if scope.is_customer
                else f"{user.full_name or user.username} (Platform admin) xác nhận gửi phiếu thay mặt khách hàng."
            ),
            created_at=now_iso(),
        )
        db.add(event)

    audit(
        db, "DECLARATION", decl.id, "SUBMIT" if submit else ("UPDATE" if payload.id else "CREATE"),
        f"{decl.reference_no} / {decl.workflow_status}",
        actor_user_id=user.id, organization_id=decl.organization_id,
        reporting_unit_id=scope.reporting_unit_id if scope.is_port else None,
    )

    db.commit()
    db.refresh(decl)

    # Thông báo email (nền, fail-soft) khi khách xác nhận gửi/gửi lại → báo Cảng.
    if submit:
        try:
            notify_declaration_submitted(db, decl, submit_is_resubmit, background=background)
        except Exception:  # never let notifications break the response
            access_logger.exception("Bỏ qua lỗi thông báo email khi gửi phiếu %s", decl.reference_no)

    result = _declaration_dict(decl)
    result["id"] = decl.id
    result["status"] = decl.status
    return result


@app.delete("/api/declarations/{declaration_id}")
def delete_declaration(
    declaration_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    # PLATFORM_ADMIN-only. An admin has full authority over any record and may
    # delete a declaration at any workflow status, including PENDING_REVIEW and
    # APPROVED — used both to clean up test data and to remove a genuinely wrong
    # record. Every delete is written to the audit trail below. Customers and
    # Cảng staff never reach this endpoint.
    if scope.user.role != "PLATFORM_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Chỉ Platform admin mới có quyền xóa phiếu khai báo.",
        )
    decl = db.query(Declaration).filter(Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu.")
    scope.require_declaration(decl.organization_id, decl.reporting_unit_id)

    identity = decl.reference_no
    organization_id = decl.organization_id
    audit_unit_id = scope.reporting_unit_id if scope.is_port else None
    db.delete(decl)
    audit(
        db, "DECLARATION", declaration_id, "DELETE", identity,
        actor_user_id=scope.user.id, organization_id=organization_id,
        reporting_unit_id=audit_unit_id,
    )
    db.commit()
    return {"deleted": declaration_id}


# ══════════════════════════════════════════════════════════════════════════════
# DECLARATION EVENTS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/api/declarations/{declaration_id}/events")
def get_declaration_events(
    declaration_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    decl = db.query(Declaration).filter(Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu.")

    # Tenant isolation check
    scope.require_declaration(decl.organization_id, decl.reporting_unit_id)

    events = (
        db.query(DeclarationEvent)
        .filter(DeclarationEvent.declaration_id == declaration_id)
        .order_by(DeclarationEvent.created_at)
        .all()
    )
    return [
        {col.name: getattr(e, col.name) for col in e.__table__.columns}
        for e in events
    ]


# ══════════════════════════════════════════════════════════════════════════════
# PORT OPERATIONS — Bảo vệ (ATB/ATD, phí cầu bến) / Giao nhận (giao/nhận hàng)
#
# Trục trạng thái độc lập với workflow_status (thủ tục Admin duyệt) — xem
# ROADMAP_PORT_OPERATIONS.md Giai đoạn 2. Mọi endpoint dưới đây chỉ tác động khi
# phiếu đã APPROVED và ghi DeclarationEvent để audit theo quy ước:
# to_status = from_status (giữ nguyên workflow_status), phân biệt qua `action`.
# ══════════════════════════════════════════════════════════════════════════════

def _require_approved(decl: Declaration) -> None:
    if decl.workflow_status != "APPROVED":
        raise HTTPException(
            status_code=409,
            detail="Chỉ thao tác được trên phiếu đã được Admin duyệt (APPROVED).",
        )


def _fmt_vn_datetime(value: str) -> str:
    """"2026-07-23T12:30" (hoặc có giây) -> "23/07/2026 12:30". Chuỗi không đúng
    định dạng ISO (rỗng, lỗi nhập) được trả nguyên văn thay vì raise."""
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return value


def _log_port_event(
    db: Session, declaration: Declaration, action: str, scope: Scope, note: str = ""
) -> None:
    """Ghi 1 DeclarationEvent cho thao tác cảng KHÔNG đổi workflow_status.

    to_status = from_status = trạng thái hiện tại — cột NOT NULL nhưng thao tác
    này không chuyển trạng thái thủ tục; phân biệt loại sự kiện qua `action`.
    Frontend dùng `action` (không phải `to_status`) để tách timeline "Hoạt động
    tại cảng" khỏi timeline "Lịch sử duyệt thủ tục".
    """
    user = scope.user
    db.add(DeclarationEvent(
        declaration_id=declaration.id,
        action=action,
        from_status=declaration.workflow_status,
        to_status=declaration.workflow_status,
        actor_name=user.full_name or user.username,
        actor_role=user.role,
        actor_user_id=user.id,
        correlation_id=correlation_id.get(),
        note=note,
        created_at=now_iso(),
    ))


class AtbAtdRequest(BaseModel):
    actual_arrival_at: Optional[str] = None
    actual_departure_at: Optional[str] = None

    @model_validator(mode="after")
    def _at_least_one(self):
        if self.actual_arrival_at is None and self.actual_departure_at is None:
            raise ValueError("Cần cung cấp ít nhất một trong hai: giờ cập cầu hoặc giờ rời cầu.")
        return self


@app.post("/api/declarations/{declaration_id}/atb-atd")
def set_declaration_atb_atd(
    declaration_id: int,
    payload: AtbAtdRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    """Bảo vệ/Giao nhận/Admin ghi đè trực tiếp ATB/ATD thực tế.

    Ghi đè tự do, không cảnh báo xung đột (quyết định nghiệp vụ đã chốt) — giá
    trị cũ/mới được lưu lại trong DeclarationEvent.note để có dấu vết.
    """
    if not (scope.allows_staff_function("SECURITY") or scope.allows_staff_function("CARGO_OPS")):
        raise HTTPException(status_code=403, detail="Bạn không thuộc bộ phận Bảo vệ hoặc Giao nhận tại đơn vị này.")
    decl = db.query(Declaration).filter(Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu.")
    scope.require_declaration(decl.organization_id, decl.reporting_unit_id)
    _require_approved(decl)

    notes = []
    if payload.actual_arrival_at is not None:
        old_display = _fmt_vn_datetime(decl.actual_arrival_at) or "chưa có"
        new_display = _fmt_vn_datetime(payload.actual_arrival_at)
        notes.append(f"ATB: {old_display} → {new_display}")
        decl.actual_arrival_at = payload.actual_arrival_at
        _log_port_event(db, decl, "ATB_UPDATED", scope, notes[-1])
    if payload.actual_departure_at is not None:
        old_display = _fmt_vn_datetime(decl.actual_departure_at) or "chưa có"
        new_display = _fmt_vn_datetime(payload.actual_departure_at)
        notes.append(f"ATD: {old_display} → {new_display}")
        decl.actual_departure_at = payload.actual_departure_at
        _log_port_event(db, decl, "ATD_UPDATED", scope, notes[-1])

    decl.updated_at = now_iso()
    decl.version += 1
    db.commit()
    db.refresh(decl)
    return _declaration_dict(decl)


@app.post("/api/declarations/{declaration_id}/berth-fee")
def confirm_berth_fee(
    declaration_id: int,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    """Bảo vệ xác nhận đã thu phí cầu bến — điều kiện tiên quyết cho Giao nhận."""
    if not scope.allows_staff_function("SECURITY"):
        raise HTTPException(status_code=403, detail="Chỉ Bảo vệ hoặc Platform admin mới xác nhận được phí cầu bến.")
    decl = db.query(Declaration).filter(Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu.")
    scope.require_declaration(decl.organization_id, decl.reporting_unit_id)
    _require_approved(decl)

    if decl.berth_fee_status == "CONFIRMED":
        raise HTTPException(status_code=409, detail="Phí cầu bến đã được xác nhận trước đó.")

    decl.berth_fee_status = "CONFIRMED"
    decl.berth_fee_confirmed_at = now_iso()
    decl.berth_fee_confirmed_by_user_id = scope.user.id
    decl.updated_at = now_iso()
    decl.version += 1
    _log_port_event(db, decl, "BERTH_FEE_CONFIRMED", scope)
    db.commit()
    db.refresh(decl)
    return _declaration_dict(decl)


class CargoOpsRequest(BaseModel):
    direction: str  # "unload" | "load"
    adhoc: bool = False

    @field_validator("direction")
    @classmethod
    def valid_direction(cls, value: str) -> str:
        if value not in ("unload", "load"):
            raise ValueError("direction phải là 'unload' hoặc 'load'.")
        return value


@app.post("/api/declarations/{declaration_id}/cargo-ops")
def confirm_cargo_ops(
    declaration_id: int,
    payload: CargoOpsRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    """Giao nhận xác nhận một chiều giao/nhận hàng thực tế.

    Cổng cứng: chặn nếu phí cầu bến chưa CONFIRMED. `adhoc=True` đánh dấu chiều
    phát sinh ngoài kế hoạch đã khai — không cần Admin duyệt lại (quyết định
    nghiệp vụ đã chốt).
    """
    if not scope.allows_staff_function("CARGO_OPS"):
        raise HTTPException(status_code=403, detail="Chỉ Giao nhận hoặc Platform admin mới xác nhận được giao/nhận hàng.")
    decl = db.query(Declaration).filter(Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu.")
    scope.require_declaration(decl.organization_id, decl.reporting_unit_id)
    _require_approved(decl)

    if decl.berth_fee_status != "CONFIRMED":
        raise HTTPException(
            status_code=409,
            detail="Bảo vệ chưa xác nhận thu phí cầu bến — chưa thể xác nhận giao/nhận hàng.",
        )

    status_field = f"{payload.direction}_status"
    adhoc_field = f"{payload.direction}_is_adhoc"
    if getattr(decl, status_field) == "CONFIRMED":
        raise HTTPException(status_code=409, detail="Chiều này đã được xác nhận trước đó.")

    setattr(decl, status_field, "CONFIRMED")
    setattr(decl, adhoc_field, 1 if payload.adhoc else 0)
    decl.updated_at = now_iso()
    decl.version += 1
    action = "CARGO_UNLOAD_CONFIRMED" if payload.direction == "unload" else "CARGO_LOAD_CONFIRMED"
    note = "Chiều phát sinh ngoài kế hoạch." if payload.adhoc else ""
    _log_port_event(db, decl, action, scope, note)
    db.commit()
    db.refresh(decl)
    return _declaration_dict(decl)


@app.get("/api/work-schedule")
def get_work_schedule(
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    """Toàn cảnh quy trình cho nhân viên Cảng (Bảo vệ + Giao nhận).

    Không phải công cụ tìm kiếm hồ sơ như "Phiếu khai báo" — chỉ liệt kê các
    lượt còn đang trong chu trình. Không gate theo staff_function (khác với
    3 endpoint xác nhận cảng ở trên) — mọi PORT_STAFF xem được toàn cảnh.
    Điều kiện lọc: mọi workflow_status trừ CANCELLED, và chưa ghi nhận ATD
    (actual_departure_at IS NULL) — loại trừ hủy tường minh để không kẹt vĩnh
    viễn trên tab; ATD đánh dấu hoàn tất chu trình (quyết định nghiệp vụ đã chốt).
    """
    query = db.query(Declaration).filter(
        Declaration.workflow_status != "CANCELLED",
        Declaration.actual_departure_at.is_(None),
    )
    org_ids = scope.member_org_ids
    query = query.filter(Declaration.organization_id.in_(org_ids)) if org_ids else query.filter(sql_false())
    declarations = query.order_by(Declaration.updated_at.desc()).all()
    return {
        "items": [
            {
                "id": d.id,
                "reference_no": d.reference_no,
                "vessel_name": d.vessel_name,
                "registration_no": d.registration_no,
                "movement_type": d.movement_type,
                "workflow_status": d.workflow_status,
                "berth_fee_status": d.berth_fee_status,
                "unload_status": d.unload_status,
                "load_status": d.load_status,
                "actual_arrival_at": d.actual_arrival_at,
                "actual_departure_at": d.actual_departure_at,
                "eta": d.eta,
                "etd": d.etd,
                "updated_at": d.updated_at,
            }
            for d in declarations
        ],
    }


@app.post("/api/declarations/{declaration_id}/cancel-request")
def request_declaration_cancel(
    declaration_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    """Hủy hai cấp — bước 1: nhân viên KHÔNG PHẢI Admin yêu cầu hủy.

    Chỉ ghi yêu cầu (2 cột cancel_requested_*) và sự kiện audit — KHÔNG đổi
    workflow_status (chỉ Admin hủy thật, xem CANCEL_FROM_PENDING/APPROVED ở
    WORKFLOW_TRANSITIONS). Ẩn dòng cục bộ là việc của frontend (localStorage
    theo username), backend không biết ai đã ẩn. Gửi email mọi Admin qua
    notifications.notify_cancel_requested — tái dùng pipeline sẵn có.
    """
    user = scope.user
    if user.role == "PLATFORM_ADMIN":
        raise HTTPException(
            status_code=400,
            detail="Admin hủy trực tiếp qua thao tác 'Hủy phiếu' (workflow), không cần gửi yêu cầu.",
        )
    decl = db.query(Declaration).filter(Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu.")
    scope.require_declaration(decl.organization_id, decl.reporting_unit_id)
    if decl.workflow_status not in ("PENDING_REVIEW", "APPROVED"):
        raise HTTPException(
            status_code=409,
            detail="Chỉ yêu cầu hủy được từ phiếu đang chờ xử lý hoặc đã duyệt.",
        )
    if decl.cancel_requested_at is not None:
        raise HTTPException(status_code=409, detail="Đã có yêu cầu hủy đang chờ Admin xử lý.")

    decl.cancel_requested_at = now_iso()
    decl.cancel_requested_by_user_id = user.id
    decl.updated_at = now_iso()
    decl.version += 1
    _log_port_event(db, decl, "CANCEL_REQUESTED", scope)
    db.commit()
    db.refresh(decl)

    try:
        notify_cancel_requested(db, decl, user.full_name or user.username, background=background)
    except Exception:
        access_logger.exception("Bỏ qua lỗi thông báo email yêu cầu hủy %s", decl.reference_no)

    return _declaration_dict(decl)


@app.post("/api/declarations/{declaration_id}/cancel-request/reject")
def reject_declaration_cancel(
    declaration_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("PLATFORM_ADMIN")),
):
    """Hủy hai cấp — Admin từ chối yêu cầu: xóa yêu cầu, phiếu trở lại bình
    thường cho mọi người (quyết định nghiệp vụ đã chốt: tự động hiện lại,
    không chỉ ở phía người yêu cầu — frontend xóa state ẩn cục bộ khi thấy
    cancel_requested_at đã về None)."""
    decl = db.query(Declaration).filter(Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu.")
    if decl.cancel_requested_at is None:
        raise HTTPException(status_code=409, detail="Phiếu không có yêu cầu hủy đang chờ.")

    decl.cancel_requested_at = None
    decl.cancel_requested_by_user_id = None
    decl.updated_at = now_iso()
    decl.version += 1
    db.add(DeclarationEvent(
        declaration_id=decl.id,
        action="CANCEL_REJECTED",
        from_status=decl.workflow_status,
        to_status=decl.workflow_status,
        actor_name=user.full_name or user.username,
        actor_role=user.role,
        actor_user_id=user.id,
        correlation_id=correlation_id.get(),
        note="",
        created_at=now_iso(),
    ))
    db.commit()
    db.refresh(decl)
    return _declaration_dict(decl)


def _cancel_request_queue(db: Session) -> dict[str, Any]:
    """Hàng đợi Admin duyệt hủy — trục lọc cancel_requested_at, KHÁC hẳn
    _attention_queue (lọc workflow_status). Không tái dùng thẳng được, xem
    ROADMAP_PORT_OPERATIONS.md Giai đoạn 4."""
    query = (
        db.query(Declaration)
        .filter(Declaration.cancel_requested_at.isnot(None))
        .order_by(Declaration.cancel_requested_at.asc())
    )
    declarations = query.limit(5).all()
    items = [
        {
            "id": d.id,
            "reference_no": d.reference_no,
            "vessel_name": d.vessel_name,
            "workflow_status": d.workflow_status,
            "cancel_requested_at": d.cancel_requested_at,
        }
        for d in declarations
    ]
    return {"label": "Yêu cầu hủy chờ Admin duyệt", "count": query.count(), "items": items}


# ══════════════════════════════════════════════════════════════════════════════
# WORKFLOW
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/declarations/{declaration_id}/workflow")
def declaration_workflow(
    declaration_id: int,
    payload: WorkflowActionRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    user = scope.user
    decl = db.query(Declaration).filter(Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu.")
    # The declaration must belong to an Organization inside the resolved unit,
    # or (if org-less) be tagged directly with this unit.
    scope.require_declaration(decl.organization_id, decl.reporting_unit_id)

    if payload.action in RETIRED_WORKFLOW_ACTIONS:
        raise HTTPException(
            status_code=410,
            detail="Hành động thuộc quy trình cũ đã ngừng hỗ trợ. Dùng PORT_APPROVE hoặc REQUEST_CHANGES.",
        )

    # Derive actor details strictly from JWT
    actor_role = user.role
    actor_name = user.full_name or user.username

    updated = _apply_workflow_transition(
        db=db,
        declaration=decl,
        action=payload.action,
        actor_role=actor_role,
        actor_name=actor_name,
        actor_user_id=user.id,
        note=payload.note,
    )
    audit(
        db, "DECLARATION", declaration_id, payload.action,
        f"{actor_name} / {actor_role} / {updated.workflow_status}",
        actor_user_id=user.id, organization_id=updated.organization_id,
        reporting_unit_id=scope.reporting_unit_id,
    )
    db.commit()
    db.refresh(updated)

    # Thông báo email (nền, fail-soft) khi Cảng duyệt / yêu cầu bổ sung → báo khách.
    try:
        notify_declaration_workflow(db, updated, payload.action, payload.note or "", background=background)
    except Exception:  # never let notifications break the response
        access_logger.exception("Bỏ qua lỗi thông báo email cho workflow %s", updated.reference_no)

    return _declaration_dict(updated)


# ══════════════════════════════════════════════════════════════════════════════
# ATTACHMENTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/api/declarations/{declaration_id}/attachments")
async def upload_attachment(
    declaration_id: int,
    filename: str,
    request: Request,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    decl = db.query(Declaration).filter(Declaration.id == declaration_id).first()
    if not decl:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu.")

    # Tenant isolation check
    scope.require_declaration(decl.organization_id, decl.reporting_unit_id)

    content = await request.body()
    ext = Path(filename).suffix.lower()
    validate_attachment_content(ext, content)

    safe_name = f"{declaration_id}_{uuid.uuid4().hex}{ext}"
    stored_name = attachment_storage.put_quarantined(safe_name, content)
    scan_status = attachment_scanner.scan(stored_name)

    content_type = request.headers.get("content-type", "application/octet-stream")
    att = Attachment(
        declaration_id=declaration_id,
        original_name=filename[:255],
        stored_name=stored_name,
        content_type=content_type,
        size_bytes=len(content),
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        scan_status=scan_status,
        storage_backend=attachment_storage.backend_name,
        created_at=now_iso(),
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return {col.name: getattr(att, col.name) for col in att.__table__.columns}


# ══════════════════════════════════════════════════════════════════════════════
# SUGGESTIONS
# ══════════════════════════════════════════════════════════════════════════════

_SUGGESTION_FIELDS = {
    "last_port": Declaration.last_port,
    "working_port": Declaration.working_port,
    "destination_port": Declaration.destination_port,
    "master_name": Declaration.master_name,
}


@app.get("/api/suggestions")
def get_suggestions(
    field: str,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    col = _SUGGESTION_FIELDS.get(field)
    if not col:
        return []

    org_ids = scope.visible_org_ids()
    if not org_ids:
        return []
    query = db.query(col).filter(col.isnot(None), col != "").filter(Declaration.organization_id.in_(org_ids))

    rows = (
        query
        .distinct()
        .order_by(col)
        .limit(50)
        .all()
    )
    return [r[0] for r in rows if r[0]]


# ══════════════════════════════════════════════════════════════════════════════
# IMPORT (Excel)
# ══════════════════════════════════════════════════════════════════════════════

VESSEL_IMPORT_COMPARE_FIELDS = {
    "name": "Tên phương tiện",
    "vessel_type": "Loại phương tiện",
    "vessel_class": "Cấp phương tiện",
    "registry_or_imo": "Số đăng kiểm / IMO",
    "shell_material": "Vật liệu vỏ",
    "build_year": "Năm đóng",
    "length_m": "Chiều dài",
    "width_m": "Chiều rộng",
    "side_height_m": "Chiều cao mạn",
    "draft_m": "Mớn nước",
    "deadweight_tons": "Trọng tải",
    "gross_tonnage": "Dung tích",
    "engine_power_cv": "Công suất",
    "cargo_capacity_tons": "Sức chở hàng",
    "container_capacity_teu": "Sức chở container",
    "passenger_capacity": "Sức chở khách",
    "min_crew": "Số thuyền viên",
    "safety_certificate_no": "Số chứng nhận an toàn",
    "certificate_issue_date": "Ngày cấp chứng nhận",
    "certificate_expiry_date": "Ngày hết hạn chứng nhận",
    "tracking_master_name": "Thuyền trưởng theo dõi",
    "tracking_master_phone": "Số điện thoại liên hệ",
    "notes": "Ghi chú",
}


def _vessel_import_changes(existing: Vessel, row: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for field, label in VESSEL_IMPORT_COMPARE_FIELDS.items():
        if field not in row:
            continue
        incoming = excel_date(row[field]) if "date" in field else row[field]
        current = getattr(existing, field, None)
        if current != incoming:
            changes.append({
                "field": field,
                "label": label,
                "current": current,
                "incoming": incoming,
            })
    incoming_profiles = [
        (
            profile.get("activity_area") or "",
            profile.get("deadweight_tons"),
            profile.get("cargo_capacity_tons"),
        )
        for profile in row.get("operating_profiles", [])
    ]
    current_profiles = [
        (profile.activity_area, profile.deadweight_tons, profile.cargo_capacity_tons)
        for profile in existing.operating_profiles
    ]
    if incoming_profiles and incoming_profiles != current_profiles:
        changes.append({
            "field": "operating_profiles",
            "label": "Vùng hoạt động / trọng tải / khả năng khai thác",
            "current": current_profiles,
            "incoming": incoming_profiles,
        })
    return changes

@app.post("/api/import/port-vessel-register")
@app.post("/api/import/vessels")
async def import_vessels(
    request: Request,
    preview: bool = False,
    overwrite_existing: bool = False,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    user = scope.user
    is_port_register = request.url.path.endswith("/port-vessel-register")
    if is_port_register and scope.is_customer:
        raise HTTPException(status_code=403, detail="Sổ theo dõi Salan chỉ dành cho Nhân viên Cảng và Admin.")
    import_kind = "PORT_VESSEL_REGISTER" if is_port_register else "VESSELS"
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="File trống.")
    validate_attachment_content(".xlsx", content)
    try:
        sheets = read_workbook(content)
        org_data, rows = vessel_rows(sheets)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Lỗi đọc file: {exc}")

    # Scoping organization based on scope
    if scope.is_customer:
        org_id = user.organization_id
    elif is_port_register:
        # Register membership is vessel-scoped, but its customer-owned master
        # remains constrained to an Organization linked to this unit.
        org = _resolve_org_for_port_scope(db, scope, org_data.get("name"))
        org_id = org.id if org else None
    else:
        org = _resolve_org_for_port_scope(db, scope, org_data.get("name"))
        org_id = org.id if org else None

    checksum = hashlib.sha256(content).hexdigest()
    required_vessel_fields = {
        "name": "Tên phương tiện",
        "registration_no": "Số đăng ký",
        "vessel_type": "Loại phương tiện",
        "vessel_class": "Cấp phương tiện",
    }
    preview_rows = []
    conflict_count = 0
    for row in rows:
        clean_row = {key: value for key, value in row.items() if not key.startswith("_")}
        clean_row["sourceRow"] = row.get("_source_row")
        clean_row["sourceSheet"] = row.get("_source_sheet")
        clean_row["mappingWarnings"] = row.get("_mapping_warnings", [])
        clean_row["missingFields"] = [
            label for field, label in required_vessel_fields.items() if not row.get(field)
        ]
        existing = db.query(Vessel).filter(
            Vessel.registration_no == row.get("registration_no")
        ).first() if row.get("registration_no") else None
        if existing:
            conflict_count += 1
            same_scope = scope_allows_vessel(db, scope, existing)
            clean_row["existing"] = True
            clean_row["ownershipConflict"] = bool(overwrite_existing and not same_scope)
            if same_scope:
                clean_row["existingRecord"] = {
                    "id": existing.id,
                    "name": existing.name,
                    "registration_no": existing.registration_no,
                }
                clean_row["changes"] = _vessel_import_changes(existing, row)
        else:
            clean_row["existing"] = False
            clean_row["ownershipConflict"] = False
            clean_row["changes"] = []
        preview_rows.append(clean_row)
    prior = db.query(ImportJob).filter(
        ImportJob.organization_id == org_id,
        ImportJob.reporting_unit_id == (scope.reporting_unit_id if scope.is_port else None),
        ImportJob.import_kind == import_kind,
        ImportJob.source_checksum == checksum,
        ImportJob.mapping_version == IMPORT_MAPPING_VERSION,
    ).first()
    if preview:
        db.rollback()
        return {
            "preview": True,
            "mappingVersion": IMPORT_MAPPING_VERSION,
            "checksum": checksum,
            "organization": org_data,
            "mapping": {
                "strategy": "HEADER_LABEL_DETECTION",
                "sheet": rows[0].get("_source_sheet") if rows else None,
            },
            "rows": preview_rows,
            "conflictCount": conflict_count,
            "previousImportId": prior.id if prior else None,
            "accepted": 0,
            "rejected": [],
        }
    if prior and not overwrite_existing:
        result = json.loads(prior.result_json)
        result["idempotent"] = True
        result["importJobId"] = prior.id
        return result

    remove_demo_data_for_real_input(
        db,
        retain_organization_id=org_id if scope.is_customer else None,
        organization_data=org_data,
        allowed_organization_ids=scope.member_org_ids if scope.is_port else None,
    )

    accepted = 0
    created = 0
    updated = 0
    skipped = 0
    rejected: list[dict] = []
    for row in rows:
        source_row = row.get("_source_row")
        missing_fields = [
            label for field, label in required_vessel_fields.items() if not row.get(field)
        ]
        if missing_fields:
            rejected.append({
                "sourceRow": source_row,
                "row": row.get("name"),
                "error": f"Thiếu {', '.join(missing_fields)}",
            })
            continue
        try:
            with db.begin_nested():
                existing = db.query(Vessel).filter(
                    Vessel.registration_no == row.get("registration_no")
                ).first()
                if existing:
                    if not overwrite_existing:
                        skipped += 1
                        if not is_port_register:
                            continue
                        # A port may link an existing shared Vessel master into
                        # its own register without mutating that master.
                        vessel = existing
                    else:
                        # Adding a register link may span master ownership, but an
                        # overwrite is still a tenant-bound master-data mutation.
                        require_vessel_in_scope(db, scope, existing)
                        for k, v in row.items():
                            if k != "operating_profiles" and hasattr(existing, k) and k not in ("id", "created_at", "organization_id"):
                                setattr(existing, k, excel_date(v) if "date" in k else v)
                        _sync_vessel_operating_profiles(existing, row.get("operating_profiles", []))
                        existing.organization_id = org_id
                        existing.updated_at = now_iso()
                        if is_port_register:
                            existing.is_port_tracked = 1
                            existing.port_tracking_updated_at = existing.updated_at
                        existing.version += 1
                        updated += 1
                        vessel = existing
                else:
                    safe = {
                        k: (excel_date(v) if "date" in k else v)
                        for k, v in row.items()
                        if not k.startswith("_") and hasattr(Vessel, k) and k not in ("id", "organization_id", "operating_profiles")
                    }
                    safe["organization_id"] = org_id
                    safe["created_at"] = now_iso()
                    safe["updated_at"] = now_iso()
                    if is_port_register:
                        safe["is_port_tracked"] = 1
                        safe["port_tracking_updated_at"] = safe["updated_at"]
                    vessel = Vessel(**safe)
                    db.add(vessel)
                    db.flush()
                    _sync_vessel_operating_profiles(vessel, row.get("operating_profiles", []))
                    created += 1
                if is_port_register and scope.is_port:
                    link = (
                        db.query(ReportingUnitVessel)
                        .filter_by(reporting_unit_id=scope.reporting_unit_id, vessel_id=vessel.id)
                        .first()
                    )
                    if link is None:
                        db.add(ReportingUnitVessel(
                            reporting_unit_id=scope.reporting_unit_id, vessel_id=vessel.id,
                            added_by_user_id=user.id, created_at=now_iso(),
                        ))
                db.flush()
            accepted += 1
        except Exception:
            access_logger.exception(
                "Vessel import row rejected source_row=%s registration_no=%s",
                source_row, row.get("registration_no"),
            )
            rejected.append({
                "sourceRow": source_row,
                "row": row.get("name"),
                "error": "Không thể nhập dòng này. Hãy kiểm tra định dạng số, ngày hoặc mã đăng ký trùng.",
            })
    result = {
        "accepted": accepted,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "rejected": rejected,
        "mappingVersion": IMPORT_MAPPING_VERSION,
        "checksum": checksum,
        "idempotent": False,
    }
    if prior:
        result["reapplied"] = True
        result["importJobId"] = prior.id
        prior.accepted_count = accepted
        prior.rejected_count = len(rejected)
        prior.result_json = json.dumps(result, ensure_ascii=False)
        db.commit()
        return result
    job = ImportJob(
        organization_id=org_id, import_kind=import_kind, source_checksum=checksum,
        reporting_unit_id=scope.reporting_unit_id if scope.is_port else None,
        mapping_version=IMPORT_MAPPING_VERSION, accepted_count=accepted,
        rejected_count=len(rejected), result_json=json.dumps(result, ensure_ascii=False),
        created_by_user_id=user.id, created_at=now_iso(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    result["importJobId"] = job.id
    return result


CREW_IMPORT_COMPARE_FIELDS = {
    "full_name": "Họ và tên",
    "crew_role": "Chức danh",
    "birth_date": "Ngày sinh",
    "phone": "Số điện thoại",
    "identity_no": "CCCD / Hộ chiếu",
    "professional_certificate_type": "Loại chứng chỉ",
    "professional_certificate_no": "Số chứng chỉ",
    "certificate_issue_date": "Ngày cấp",
    "certificate_expiry_date": "Ngày hết hạn",
    "notes": "Ghi chú",
}


def _import_organization(db: Session, name: str) -> Organization | None:
    key = import_match_key(name)
    return next(
        (organization for organization in db.query(Organization).all()
         if import_match_key(organization.name) == key),
        None,
    )


def _existing_import_crew(
    db: Session, organization_id: int, row: dict[str, Any],
) -> CrewMember | None:
    query = db.query(CrewMember).filter(CrewMember.organization_id == organization_id)
    identity_no = str(row.get("identity_no") or "").strip()
    certificate_no = str(row.get("professional_certificate_no") or "").strip()
    if identity_no:
        existing = query.filter(CrewMember.identity_no == identity_no).first()
        if existing:
            return existing
    if certificate_no:
        return query.filter(CrewMember.professional_certificate_no == certificate_no).first()
    birth_date = row.get("birth_date")
    if birth_date:
        return query.filter(
            CrewMember.full_name == row.get("full_name"),
            CrewMember.birth_date == birth_date,
        ).first()
    return None


def _crew_import_changes(existing: CrewMember, row: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for field, label in CREW_IMPORT_COMPARE_FIELDS.items():
        if field not in row:
            continue
        current = getattr(existing, field, None)
        incoming = row[field]
        if current != incoming:
            changes.append({
                "field": field,
                "label": label,
                "current": current,
                "incoming": incoming,
            })
    return changes


@app.post("/api/import/crew")
async def import_crew(
    request: Request,
    preview: bool = False,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    user = scope.user
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="File trống.")
    validate_attachment_content(".xlsx", content)
    try:
        rows = crew_rows(read_workbook(content))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Lỗi đọc file: {exc}")

    checksum = hashlib.sha256(content).hexdigest()
    required_fields = {
        "organization_name": "Tên doanh nghiệp",
        "full_name": "Họ và tên",
        "crew_role": "Chức danh",
    }
    prepared: list[tuple[dict[str, Any], Organization | None, CrewMember | None]] = []
    preview_rows: list[dict[str, Any]] = []
    for row in rows:
        raw_role = str(row.get("crew_role") or "")
        canonical_role = CREW_ROLE_CANONICAL.get(import_match_key(raw_role))
        if canonical_role:
            row["crew_role"] = canonical_role
        elif raw_role:
            row["_invalid_crew_role"] = raw_role
        organization = _import_organization(db, str(row.get("organization_name") or ""))
        existing = _existing_import_crew(db, organization.id, row) if organization else None
        missing = [label for field, label in required_fields.items() if not row.get(field)]
        if row.get("_invalid_crew_role"):
            missing.append("Chức danh hợp lệ")
        if row.get("organization_name") and not organization:
            missing.append("Doanh nghiệp đã có trong hệ thống")
        clean = {key: value for key, value in row.items() if not key.startswith("_")}
        clean.update({
            "sourceRow": row.get("_source_row"),
            "sourceSheet": row.get("_source_sheet"),
            "mappingWarnings": row.get("_mapping_warnings", []),
            "missingFields": missing,
            "existing": bool(existing),
            "changes": _crew_import_changes(existing, row) if existing else [],
        })
        preview_rows.append(clean)
        prepared.append((row, organization, existing))

    recognized_organization_ids = {
        organization.id for _, organization, _ in prepared if organization
    }
    if len(recognized_organization_ids) > 1:
        raise HTTPException(
            status_code=422,
            detail="Mỗi file thuyền viên chỉ được chứa dữ liệu của một doanh nghiệp.",
        )
    job_organization_id = next(iter(recognized_organization_ids), None)
    if job_organization_id is not None:
        scope.require_org(job_organization_id)
    prior = db.query(ImportJob).filter(
        ImportJob.organization_id == job_organization_id,
        ImportJob.reporting_unit_id == scope.reporting_unit_id,
        ImportJob.import_kind == "CREW",
        ImportJob.source_checksum == checksum,
        ImportJob.mapping_version == IMPORT_MAPPING_VERSION,
    ).first()
    if preview:
        return {
            "preview": True,
            "mappingVersion": IMPORT_MAPPING_VERSION,
            "checksum": checksum,
            "mapping": {
                "strategy": "HEADER_LABEL_DETECTION",
                "sheet": rows[0].get("_source_sheet") if rows else None,
            },
            "rows": preview_rows,
            "previousImportId": prior.id if prior else None,
            "accepted": 0,
            "rejected": [],
        }
    if prior:
        result = json.loads(prior.result_json)
        result["idempotent"] = True
        result["importJobId"] = prior.id
        return result
    if job_organization_id is None:
        raise HTTPException(
            status_code=422,
            detail="File không có doanh nghiệp nào khớp với dữ liệu hệ thống.",
        )

    created = 0
    updated = 0
    rejected: list[dict[str, Any]] = []
    for row, organization, existing in prepared:
        missing = [label for field, label in required_fields.items() if not row.get(field)]
        if row.get("_invalid_crew_role"):
            missing.append("Chức danh hợp lệ")
        if row.get("organization_name") and not organization:
            missing.append("Doanh nghiệp đã có trong hệ thống")
        if missing:
            rejected.append({
                "sourceRow": row.get("_source_row"),
                "row": row.get("full_name"),
                "error": f"Thiếu hoặc không hợp lệ: {', '.join(missing)}",
            })
            continue
        data = {
            key: value for key, value in row.items()
            if not key.startswith("_") and key != "organization_name" and hasattr(CrewMember, key)
        }
        data["organization_id"] = organization.id
        data["vessel_id"] = None
        data["updated_at"] = now_iso()
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            existing.version += 1
            member = existing
            updated += 1
            action = "IMPORT_UPDATE"
        else:
            data["created_at"] = now_iso()
            member = CrewMember(**data)
            db.add(member)
            created += 1
            action = "IMPORT_CREATE"
        db.flush()
        audit(
            db, "CREW", member.id, action, f"{member.full_name} / {member.crew_role}",
            actor_user_id=user.id, organization_id=organization.id,
            reporting_unit_id=scope.reporting_unit_id,
        )

    result = {
        "accepted": created + updated,
        "created": created,
        "updated": updated,
        "rejected": rejected,
        "mappingVersion": IMPORT_MAPPING_VERSION,
        "checksum": checksum,
        "idempotent": False,
    }
    job = ImportJob(
        organization_id=job_organization_id,
        reporting_unit_id=scope.reporting_unit_id,
        import_kind="CREW",
        source_checksum=checksum,
        mapping_version=IMPORT_MAPPING_VERSION,
        accepted_count=result["accepted"],
        rejected_count=len(rejected),
        result_json=json.dumps(result, ensure_ascii=False),
        created_by_user_id=user.id,
        created_at=now_iso(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    result["importJobId"] = job.id
    return result


@app.post("/api/import/declaration")
async def import_declaration(
    request: Request,
    preview: bool = False,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    user = scope.user
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="File trống.")
    validate_attachment_content(".xlsx", content)
    try:
        sheets = read_workbook(content)
        row = declaration_row(sheets)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Lỗi đọc file: {exc}")

    checksum = hashlib.sha256(content).hexdigest()
    if preview:
        return {
            "preview": True,
            "mappingVersion": IMPORT_MAPPING_VERSION,
            "checksum": checksum,
            "row": row,
            "accepted": 0,
            "rejected": [],
        }
    row["created_at"] = now_iso()
    row["updated_at"] = now_iso()
    # Import rows keep the IMP marker and a microsecond tail for uniqueness in
    # bulk (they are not the per-day human sequence used for manual entry).
    row["reference_no"] = f"TT-IMP-{datetime.now():%y%m%d}-{datetime.now().microsecond:06d}"
    row["workflow_status"] = "DRAFT"
    row["status"] = "DRAFT"
    row["unload_json"] = json.dumps(cargo(row.pop("unload", {})), ensure_ascii=False)
    row["load_json"] = json.dumps(cargo(row.pop("load", {})), ensure_ascii=False)

    safe = {k: v for k, v in row.items() if not k.startswith("_") and hasattr(Declaration, k)}
    imported_company_name = str(safe.get("company_name") or "").strip()
    if not safe.get("declaration_date"):
        safe["declaration_date"] = date.today().isoformat()
    for required in ("company_name", "vessel_name", "registration_no", "vessel_type",
                     "vessel_class", "last_port", "working_port", "eta", "etd",
                     "master_name", "master_phone"):
        if not safe.get(required):
            safe[required] = "N/A"

    # CUSTOMER imports stay tenant-bound. PLATFORM_ADMIN may import a declaration sent by
    # any customer inside its resolved reporting unit; the workbook company name
    # selects (or creates) the tenant.
    if scope.is_customer:
        target_organization = user.organization
    else:
        if not imported_company_name:
            raise HTTPException(status_code=422, detail="File phải có tên doanh nghiệp để Admin nhập phiếu khai báo.")
        target_organization = _import_organization(db, imported_company_name)
        if target_organization is None:
            # Brand-new Organization: onboard it through this resolved unit.
            target_organization = _get_or_create_org(db, imported_company_name)
            db.add(ReportingUnitOrganization(
                reporting_unit_id=scope.reporting_unit_id, organization_id=target_organization.id,
                created_at=now_iso(),
            ))
        else:
            scope.require_org(target_organization.id)
    if target_organization is None:
        raise HTTPException(status_code=422, detail="File phải có tên doanh nghiệp để Admin nhập phiếu khai báo.")

    target_organization_id = target_organization.id
    safe["organization_id"] = target_organization_id

    prior = db.query(ImportJob).filter(
        ImportJob.organization_id == target_organization_id,
        ImportJob.reporting_unit_id == (scope.reporting_unit_id if scope.is_port else None),
        ImportJob.import_kind == "DECLARATION",
        ImportJob.source_checksum == checksum,
        ImportJob.mapping_version == IMPORT_MAPPING_VERSION,
    ).first()
    if prior:
        result = json.loads(prior.result_json)
        result["idempotent"] = True
        result["importJobId"] = prior.id
        return result

    remove_demo_data_for_real_input(
        db,
        retain_organization_id=target_organization_id,
        organization_data={"name": imported_company_name},
        allowed_organization_ids=scope.member_org_ids if scope.is_port else None,
    )
    safe["company_name"] = target_organization.name

    decl = Declaration(**safe)
    db.add(decl)
    db.flush()
    audit(
        db, "DECLARATION", decl.id, "IMPORT_CREATE", decl.reference_no,
        actor_user_id=user.id, organization_id=target_organization_id,
        reporting_unit_id=scope.reporting_unit_id if scope.is_port else None,
    )
    result = {
        "accepted": 1, "rejected": [], "id": decl.id,
        "mappingVersion": IMPORT_MAPPING_VERSION, "checksum": checksum,
        "idempotent": False,
    }
    job = ImportJob(
        organization_id=target_organization_id, import_kind="DECLARATION",
        reporting_unit_id=scope.reporting_unit_id if scope.is_port else None,
        source_checksum=checksum, mapping_version=IMPORT_MAPPING_VERSION,
        accepted_count=1, rejected_count=0,
        result_json=json.dumps(result, ensure_ascii=False),
        created_by_user_id=user.id, created_at=now_iso(),
    )
    db.add(job)
    db.commit()
    db.refresh(decl)
    db.refresh(job)
    result["importJobId"] = job.id
    return result


# ══════════════════════════════════════════════════════════════════════════════
# REPORTS (Appendix 1 / 2 / 3)
# ══════════════════════════════════════════════════════════════════════════════

ANALYTICS_PERIODS = {"week", "month", "quarter", "year"}
ANALYTICS_SOURCES = {"live", "historical", "combined"}
ACTIVE_HISTORICAL_STATUSES = ("COMMITTED", "REVIEW")


def _month_shift(value: date, offset: int) -> date:
    month_index = value.year * 12 + value.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def _analytics_period(period: str, anchor: date) -> dict[str, Any]:
    if period == "week":
        current_start = anchor - timedelta(days=anchor.weekday())
        current_end = current_start + timedelta(days=6)
        previous_start = current_start - timedelta(days=364)
        labels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        bucket = lambda value, start: (value - start).days
        title = "Tổng hợp theo tuần"
        trend_title = "Lượt tàu theo ngày"
        compare = "Tuần này so với cùng kỳ năm trước"
    elif period == "month":
        current_start = anchor.replace(day=1)
        current_end = _month_shift(current_start, 1) - timedelta(days=1)
        previous_start = date(current_start.year - 1, current_start.month, 1)
        labels = [f"Tuần {index}" for index in range(1, 6)]
        bucket = lambda value, start: min(4, (value.day - 1) // 7)
        title = "Tổng hợp theo tháng"
        trend_title = "Lượt tàu theo tuần"
        compare = f"Tháng {current_start.month}/{current_start.year} so với cùng kỳ {previous_start.year}"
    elif period == "quarter":
        quarter_month = ((anchor.month - 1) // 3) * 3 + 1
        current_start = date(anchor.year, quarter_month, 1)
        current_end = _month_shift(current_start, 3) - timedelta(days=1)
        previous_start = date(current_start.year - 1, current_start.month, 1)
        labels = [f"T{_month_shift(current_start, index).month}" for index in range(3)]
        bucket = lambda value, start: (value.year - start.year) * 12 + value.month - start.month
        title = "Tổng hợp theo quý"
        trend_title = "Lượt tàu theo tháng"
        compare = f"Quý {(quarter_month - 1) // 3 + 1}/{current_start.year} so với cùng kỳ {previous_start.year}"
    else:
        current_start = date(anchor.year, 1, 1)
        current_end = date(anchor.year, 12, 31)
        previous_start = date(anchor.year - 1, 1, 1)
        labels = [f"T{index}" for index in range(1, 13)]
        bucket = lambda value, start: value.month - 1
        title = "Tổng hợp theo năm"
        trend_title = "Lượt tàu theo tháng"
        compare = f"Năm {anchor.year} so với {anchor.year - 1}"
    if period == "week":
        previous_end = previous_start + timedelta(days=6)
    elif period == "month":
        previous_end = _month_shift(previous_start, 1) - timedelta(days=1)
    elif period == "quarter":
        previous_end = _month_shift(previous_start, 3) - timedelta(days=1)
    else:
        previous_end = date(previous_start.year, 12, 31)
    return {
        "current_start": current_start,
        "current_end": current_end,
        "previous_start": previous_start,
        "previous_end": previous_end,
        "labels": labels,
        "bucket": bucket,
        "title": title,
        "trend_title": trend_title,
        "compare": compare,
    }


def _date_from_value(raw: Any) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw)[:10])
    except ValueError:
        return None


def _arrival_operating_date(declaration: Declaration) -> date | None:
    for raw in (declaration.actual_arrival_at, declaration.eta):
        value = _date_from_value(raw)
        if value:
            return value
    return None


def _departure_operating_date(declaration: Declaration) -> date | None:
    for raw in (declaration.actual_departure_at, declaration.etd):
        value = _date_from_value(raw)
        if value:
            return value
    return None


def _declaration_operating_date(declaration: Declaration) -> date | None:
    values = (
        (declaration.actual_departure_at, declaration.etd)
        if declaration.movement_type == "DEPARTURE"
        else (declaration.actual_arrival_at, declaration.eta)
    )
    for raw in values:
        if not raw:
            continue
        value = _date_from_value(raw)
        if value:
            return value
    return None


def _declaration_metrics(declaration: Declaration) -> dict[str, float]:
    def numeric(value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    tons = 0.0
    teu = 0.0
    for raw in (declaration.unload_json, declaration.load_json):
        try:
            item = json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            item = {}
        tons += numeric(item.get("tons"))
        teu += numeric(item.get("teu"))
    return {
        "trips": 1.0,
        "tons": tons,
        "teu": teu,
        "pax": numeric(declaration.passenger_count),
    }


def _month_key(value: date) -> str:
    return value.strftime("%Y-%m")


def _months_between(start: date, end: date) -> list[str]:
    value = start.replace(day=1)
    result = []
    while value <= end:
        result.append(_month_key(value))
        value = _month_shift(value, 1)
    return result


def _historical_window(
    db: Session, unit_id: int, start: date, end: date, labels: list[str], bucket,
) -> dict[str, Any]:
    """Aggregate only active, validated TOS facts using ATB as operating time.

    PL.03 reported times are deliberately excluded: the approved business rule
    makes matched TOS ATB/ATD authoritative. Missing TOS coverage remains
    missing and is never converted to a numeric zero.
    """
    window_months = set(_months_between(start, end))
    imports = db.query(HistoricalReportImport).filter(
        HistoricalReportImport.reporting_unit_id == unit_id,
        HistoricalReportImport.status.in_(ACTIVE_HISTORICAL_STATUSES),
    ).all()
    active_ids = {item.id for item in imports}
    berth_imports = [item for item in imports
                      if item.source_kind == "tos_berth_call" and item.reporting_period in window_months]
    cargo_imports = [item for item in imports
                     if item.source_kind == "tos_cargo_detail" and item.reporting_period in window_months]
    berth_months = {item.reporting_period for item in berth_imports}
    cargo_months = {item.reporting_period for item in cargo_imports}
    reported_months = {
        item.reporting_period for item in imports
        if item.source_kind == "reported_pl03" and item.reporting_period in window_months
    }
    if not active_ids:
        return {
            "values": {"trips": None, "tons": None, "teu": None, "pax": None},
            "available": {"trips": False, "tons": False, "teu": False, "pax": False},
            "trend": [0] * len(labels), "months": {}, "coverageMonths": [],
            "reportedMonths": sorted(reported_months), "hasCoverage": bool(reported_months),
            "hasReview": False,
        }

    calls = db.query(HistoricalPortCall).filter(
        HistoricalPortCall.reporting_unit_id == unit_id,
        HistoricalPortCall.import_id.in_(active_ids),
        HistoricalPortCall.validation_status == "VALID",
        HistoricalPortCall.actual_berthing_at >= start.isoformat(),
        HistoricalPortCall.actual_berthing_at < (end + timedelta(days=1)).isoformat(),
    ).all()
    call_ids = [item.id for item in calls]
    cargo_rows = []
    if call_ids:
        cargo_rows = db.query(HistoricalCargoRow).filter(
            HistoricalCargoRow.reporting_unit_id == unit_id,
            HistoricalCargoRow.import_id.in_(active_ids),
            HistoricalCargoRow.port_call_id.in_(call_ids),
            HistoricalCargoRow.match_status == "MATCHED",
            HistoricalCargoRow.validation_status == "VALID",
        ).all()

    trend = [0] * len(labels)
    months: dict[str, dict[str, int]] = {}
    for call in calls:
        operating_date = _date_from_value(call.actual_berthing_at)
        if operating_date is None:
            continue
        month = _month_key(operating_date)
        months.setdefault(month, {"calls": 0, "cargoRows": 0})["calls"] += 1
        index = bucket(operating_date, start)
        if 0 <= index < len(trend):
            trend[index] += 1
    call_month_by_id = {call.id: call.reporting_month for call in calls}
    for row in cargo_rows:
        month = call_month_by_id.get(row.port_call_id)
        if month:
            months.setdefault(month, {"calls": 0, "cargoRows": 0})["cargoRows"] += 1
            cargo_months.add(month)

    berth_complete = bool(berth_months) and all(
        item.status == "COMMITTED" and item.review_count == 0 for item in berth_imports
    )
    cargo_complete = bool(cargo_months) and all(
        item.status == "COMMITTED" and item.review_count == 0 for item in cargo_imports
    )
    has_review = any(
        item.status == "REVIEW" or item.review_count > 0 for item in berth_imports + cargo_imports
    )
    return {
        "values": {
            "trips": float(len(calls)) if berth_complete else None,
            "tons": float(sum(row.weight_tonnes or 0 for row in cargo_rows)) if cargo_complete else None,
            "teu": float(sum(row.teu_factor or 0 for row in cargo_rows)) if cargo_complete else None,
            "pax": None,
        },
        "available": {
            "trips": berth_complete, "tons": cargo_complete,
            "teu": cargo_complete, "pax": False,
        },
        "trend": trend if berth_complete else [0] * len(labels), "months": months,
        "coverageMonths": sorted(berth_months | cargo_months | reported_months),
        "reportedMonths": sorted(reported_months),
        "hasCoverage": bool(berth_months or cargo_months or reported_months),
        "hasReview": has_review,
    }


def _analytics_payload(
    db: Session, scope: Scope, period: str, anchor: date, source: str = "live",
) -> dict[str, Any]:
    config = _analytics_period(period, anchor)
    query = db.query(Declaration).filter(Declaration.workflow_status == "APPROVED")
    if scope.is_customer:
        query = query.filter(Declaration.organization_id == scope.organization_id)
    else:
        org_ids = scope.member_org_ids
        query = query.filter(Declaration.organization_id.in_(org_ids)) if org_ids else query.filter(sql_false())
    declarations = query.all()
    live_totals = {
        "cur": {key: 0.0 for key in ("trips", "tons", "teu", "pax")},
        "prev": {key: 0.0 for key in ("trips", "tons", "teu", "pax")},
    }
    live_trend_current = [0] * len(config["labels"])
    live_trend_previous = [0] * len(config["labels"])
    live_months: dict[str, int] = {}
    for declaration in declarations:
        operating_date = _declaration_operating_date(declaration)
        if not operating_date:
            continue
        if config["current_start"] <= operating_date <= config["current_end"]:
            group = "cur"
            trend = live_trend_current
            start = config["current_start"]
        elif config["previous_start"] <= operating_date <= config["previous_end"]:
            group = "prev"
            trend = live_trend_previous
            start = config["previous_start"]
        else:
            continue
        for key, value in _declaration_metrics(declaration).items():
            live_totals[group][key] += value
        month = _month_key(operating_date)
        live_months[month] = live_months.get(month, 0) + 1
        index = config["bucket"](operating_date, start)
        if 0 <= index < len(trend):
            trend[index] += 1
    historical = None
    overlap_months: list[str] = []
    warnings: list[str] = []
    if source in {"historical", "combined"}:
        if not scope.is_port:
            raise HTTPException(
                status_code=403,
                detail="Dữ liệu lịch sử/TOS chỉ dành cho Nhân viên Cảng trong đúng đơn vị báo cáo.",
            )
        historical = {
            "cur": _historical_window(
                db, scope.reporting_unit_id, config["current_start"], config["current_end"],
                config["labels"], config["bucket"],
            ),
            "prev": _historical_window(
                db, scope.reporting_unit_id, config["previous_start"], config["previous_end"],
                config["labels"], config["bucket"],
            ),
        }
        historical_months = (
            set(historical["cur"]["coverageMonths"]) | set(historical["prev"]["coverageMonths"])
        )
        overlap_months = sorted(set(live_months) & historical_months)
        if overlap_months:
            warnings.append(
                "Có kỳ đồng thời chứa dữ liệu LIVE và LỊCH SỬ; tổng KẾT HỢP bị khóa cho đến khi đối soát nguồn."
            )
        if historical["cur"]["reportedMonths"] or historical["prev"]["reportedMonths"]:
            warnings.append(
                "PL.03 cũ chỉ được giữ làm dấu vết báo cáo; thống kê thời gian dùng ATB/ATD từ TOS."
            )
        if historical["cur"]["hasReview"] or historical["prev"]["hasReview"]:
            warnings.append(
                "Một hoặc nhiều lượt import còn dòng cần kiểm tra; chỉ tiêu liên quan không được hiển thị như tổng hoàn chỉnh."
            )

    combined_blocked = source == "combined" and bool(overlap_months)
    kpis: dict[str, dict[str, float | None]] = {}
    if source == "live":
        kpis = {key: {"cur": live_totals["cur"][key], "prev": live_totals["prev"][key]}
                for key in live_totals["cur"]}
        trend_current, trend_previous = live_trend_current, live_trend_previous
    elif source == "historical":
        kpis = {key: {"cur": historical["cur"]["values"][key],
                       "prev": historical["prev"]["values"][key]}
                for key in live_totals["cur"]}
        trend_current, trend_previous = historical["cur"]["trend"], historical["prev"]["trend"]
    elif combined_blocked:
        kpis = {key: {"cur": None, "prev": None} for key in live_totals["cur"]}
        trend_current = trend_previous = [0] * len(config["labels"])
    else:
        for key in live_totals["cur"]:
            values: dict[str, float | None] = {}
            for group in ("cur", "prev"):
                hist_value = historical[group]["values"][key]
                # Never turn absent/incomplete historical coverage into zero.
                # Passenger counts are absent from TOS, and any other metric is
                # withheld while its relevant import still needs review.
                if (historical[group]["hasCoverage"]
                        and not historical[group]["available"][key]):
                    values[group] = None
                else:
                    values[group] = live_totals[group][key] + (hist_value or 0)
            kpis[key] = values
        trend_current = [a + b for a, b in zip(live_trend_current, historical["cur"]["trend"])]
        trend_previous = [a + b for a, b in zip(live_trend_previous, historical["prev"]["trend"])]

    coverage_periods = []
    all_months = _months_between(config["previous_start"], config["previous_end"])
    all_months += [month for month in _months_between(config["current_start"], config["current_end"])
                   if month not in all_months]
    for month in all_months:
        hist_month = None
        if historical:
            hist_month = historical["cur"]["months"].get(month) or historical["prev"]["months"].get(month)
        coverage_periods.append({
            "month": month, "liveApproved": live_months.get(month, 0),
            "historicalCalls": (hist_month or {}).get("calls", 0),
            "historicalCargoRows": (hist_month or {}).get("cargoRows", 0),
            "overlap": month in overlap_months,
        })
    if combined_blocked:
        coverage_status = "BLOCKED"
    elif source == "live":
        coverage_status = "COMPLETE"
    elif historical and all(historical["cur"]["available"][key] for key in ("trips", "tons", "teu")):
        coverage_status = "COMPLETE"
    elif historical and historical["cur"]["hasCoverage"]:
        coverage_status = "PARTIAL"
    else:
        coverage_status = "MISSING"

    return {
        "period": period,
        "asOf": anchor.isoformat(),
        "source": source,
        "dataSource": "DEMO" if source == "live" and is_demo_data_active(db) else source.upper(),
        "combinedAllowed": not combined_blocked,
        "kpis": kpis,
        "trend": {"labels": config["labels"], "cur": trend_current, "prev": trend_previous},
        "coverage": {
            "status": coverage_status, "periods": coverage_periods,
            "overlapPeriods": overlap_months, "warnings": warnings,
        },
        "meta": {
            "analyticsTitle": config["title"],
            "trendTitle": config["trend_title"],
            "trendSub": f"{config['current_start'].isoformat()} → {config['current_end'].isoformat()}",
            "compareSub": config["compare"],
        },
    }


@app.get("/api/reports/analytics")
def report_analytics(
    period: str = "month",
    source: str = "live",
    as_of: Optional[date] = None,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    if period not in ANALYTICS_PERIODS:
        raise HTTPException(status_code=422, detail="Kỳ thống kê phải là week, month, quarter hoặc year.")
    if source not in ANALYTICS_SOURCES:
        raise HTTPException(status_code=422, detail="Nguồn thống kê phải là live, historical hoặc combined.")
    return _analytics_payload(db, scope, period, as_of or date.today(), source)


@app.get("/api/reports/analytics/export")
def export_analytics(
    period: str = "month",
    source: str = "live",
    as_of: Optional[date] = None,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    if period not in ANALYTICS_PERIODS:
        raise HTTPException(status_code=422, detail="Kỳ thống kê không hợp lệ.")
    if source not in ANALYTICS_SOURCES:
        raise HTTPException(status_code=422, detail="Nguồn thống kê không hợp lệ.")
    payload = _analytics_payload(db, scope, period, as_of or date.today(), source)
    if not payload["combinedAllowed"]:
        raise HTTPException(status_code=409, detail="Không thể xuất tổng kết hợp khi kỳ dữ liệu còn chồng lấn chưa đối soát.")
    labels = {"trips": "Lượt tàu", "tons": "Khối lượng (tấn)", "teu": "TEU", "pax": "Hành khách"}
    rows = [[labels[key], values["cur"], values["prev"],
             None if values["cur"] is None or values["prev"] is None else values["cur"] - values["prev"]]
            for key, values in payload["kpis"].items()]
    content = make_xlsx(payload["meta"]["analyticsTitle"], ["Chỉ tiêu", "Kỳ này", "Kỳ trước", "Chênh lệch"], rows)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="analytics_{source}_{period}_{payload["asOf"]}.xlsx"'},
    )


def _approved_report_query(db: Session, scope: Scope):
    query = db.query(Declaration).filter(Declaration.workflow_status == "APPROVED")
    if scope.is_customer:
        query = query.filter(Declaration.organization_id == scope.organization_id)
    else:
        org_ids = scope.member_org_ids
        query = query.filter(Declaration.organization_id.in_(org_ids)) if org_ids else query.filter(sql_false())
    return query


def _report_vessel(db: Session, declaration: Declaration) -> Optional[Vessel]:
    if declaration.vessel_id:
        vessel = db.query(Vessel).filter(Vessel.id == declaration.vessel_id).first()
        if vessel:
            return vessel
    return db.query(Vessel).filter(
        Vessel.registration_no == declaration.registration_no
    ).first()


def _report_static_value(vessel: Optional[Vessel], declaration: Optional[Declaration], field: str) -> Any:
    if vessel is not None:
        value = getattr(vessel, field, None)
        if value not in (None, ""):
            return value
    return getattr(declaration, field, None) if declaration is not None else None


def _report_base_vessels(db: Session, scope: Scope) -> list[Vessel]:
    query = db.query(Vessel)
    if scope.is_customer:
        query = query.filter(Vessel.organization_id == scope.organization_id)
    else:
        # The tenant-scoped register (not the legacy global flag) bounds this unit's fleet.
        register_ids = register_vessel_ids(db, scope.reporting_unit_id)
        query = query.filter(Vessel.id.in_(register_ids)) if register_ids else query.filter(sql_false())
    return query.order_by(Vessel.registration_no, Vessel.id).all()


def _report_group_key(vessel_id: Optional[int], registration_no: str) -> str:
    return f"id:{vessel_id}" if vessel_id else f"reg:{import_match_key(registration_no)}"


def _declaration_report_group_key(db: Session, declaration: Declaration) -> str:
    vessel = _report_vessel(db, declaration)
    return _report_group_key(
        vessel.id if vessel else declaration.vessel_id,
        vessel.registration_no if vessel else declaration.registration_no,
    )


def _cargo_summary(item: dict[str, Any]) -> str:
    parts = [str(item.get("cargo_name") or item.get("cargo_type") or "").strip()]
    tons = float(item.get("tons") or 0)
    teu = float(item.get("teu") or 0)
    if tons:
        parts.append(f"{tons:g} tấn")
    if teu:
        parts.append(f"{teu:g} TEU")
    return " - ".join(part for part in parts if part)


def _appendix1_rows(
    db: Session,
    declarations: list[Declaration],
    vessels: Optional[list[Vessel]] = None,
) -> list[list[Any]]:
    groups: dict[str, list[Declaration]] = {}
    for declaration in declarations:
        groups.setdefault(_declaration_report_group_key(db, declaration), []).append(declaration)
    base_vessels = vessels or []
    vessel_by_key = {_report_group_key(vessel.id, vessel.registration_no): vessel for vessel in base_vessels}
    ordered_keys = list(vessel_by_key)
    ordered_keys.extend(key for key in groups if key not in vessel_by_key)

    rows = []
    for index, key in enumerate(ordered_keys, start=1):
        group = groups.get(key, [])
        group.sort(key=lambda item: (_declaration_operating_date(item) or date.max, item.id))
        declaration = group[0] if group else None
        vessel = vessel_by_key.get(key) or (_report_vessel(db, declaration) if declaration else None)
        capacity_tons = _joined_profile_value(vessel, "cargo_capacity_tons") if vessel else None
        capacity_teu = getattr(vessel, "container_capacity_teu", None) if vessel else None
        capacity = " / ".join(
            value for value in (
                f"{capacity_tons} tấn" if capacity_tons not in (None, "") else "",
                f"{capacity_teu:g} TEU" if isinstance(capacity_teu, (int, float)) and capacity_teu else "",
            ) if value
        )
        master_name = getattr(vessel, "tracking_master_name", "") if vessel else ""
        master_phone = getattr(vessel, "tracking_master_phone", "") if vessel else ""
        rows.append([
            index,
            _report_static_value(vessel, declaration, "name") or (declaration.vessel_name if declaration else ""),
            _report_static_value(vessel, declaration, "registration_no") or (declaration.registration_no if declaration else ""),
            _report_static_value(vessel, declaration, "vessel_class") or "",
            _report_static_value(vessel, declaration, "vessel_type") or "",
            _report_static_value(vessel, declaration, "certificate_expiry_date") or "",
            capacity,
            getattr(vessel, "passenger_capacity", None) if vessel else None,
            _distinct_join([item.working_port for item in group]),
            _distinct_join([item.actual_arrival_at or item.eta for item in group]),
            _distinct_join([item.departure_berth for item in group]),
            _distinct_join([item.actual_departure_at or item.etd for item in group]),
            _distinct_join([_cargo_summary(json.loads(item.unload_json or "{}")) for item in group]),
            _distinct_join([_cargo_summary(json.loads(item.load_json or "{}")) for item in group]),
            _distinct_join([f"{item.crew_count} / {item.passenger_count}" for item in group]),
            " - ".join(value for value in (
                master_name or (declaration.master_name if declaration else ""),
                master_phone or (declaration.master_phone if declaration else ""),
            ) if value),
        ])
    return rows


def _report_period_metrics(declarations: list[Declaration]) -> dict[str, float | None]:
    metrics = {
        "container_tons": None, "container_teu": None,
        "dry_tons": None, "liquid_tons": None, "foreign_tons": None,
        "calls": None,
        "passenger_calls": None, "passengers": None,
    }

    def add(key: str, value: float, *, applicable: bool = False) -> None:
        if not applicable and not value:
            return
        metrics[key] = float(metrics[key] or 0) + value

    for declaration in declarations:
        if declaration.movement_type == "ARRIVAL":
            add("calls", 1.0, applicable=True)
        add("passengers", float(declaration.passenger_count or 0), applicable=bool(declaration.passenger_count))
        if declaration.movement_type == "ARRIVAL" and declaration.is_passenger_call:
            add("passenger_calls", 1.0, applicable=True)
        for item in (json.loads(declaration.unload_json or "{}"), json.loads(declaration.load_json or "{}")):
            cargo_key = import_match_key(item.get("cargo_type"))
            movement_key = import_match_key(item.get("movement_type"))
            tons = float(item.get("tons") or 0)
            teu = float(item.get("teu") or 0)
            if "CONTAINER" in cargo_key or "CONGTENO" in cargo_key:
                add("container_tons", tons, applicable=bool(tons))
                add("container_teu", teu, applicable=bool(teu))
            elif "HANGKHO" in cargo_key or cargo_key == "KHO":
                add("dry_tons", tons, applicable=bool(tons))
            elif "HANGLONG" in cargo_key or cargo_key == "LONG":
                add("liquid_tons", tons, applicable=bool(tons))
            if "NHAPKHAU" in movement_key or "XUATKHAU" in movement_key:
                add("foreign_tons", tons, applicable=bool(tons))
    return metrics


def _appendix2_rows(
    current: list[Declaration],
    cumulative: list[Declaration],
    current_adjustments: Optional[dict[str, float]] = None,
    cumulative_adjustments: Optional[dict[str, float]] = None,
) -> list[list[Any]]:
    current_metrics = _report_period_metrics(current)
    cumulative_metrics = _report_period_metrics(cumulative)
    for metrics, adjustments in (
        (current_metrics, current_adjustments or {}),
        (cumulative_metrics, cumulative_adjustments or {}),
    ):
        for key, delta in adjustments.items():
            if key in metrics and delta:
                metrics[key] = float(metrics[key] or 0) + float(delta)
    values = [
        current_metrics["container_tons"], current_metrics["container_teu"],
        cumulative_metrics["container_tons"], cumulative_metrics["container_teu"],
        current_metrics["dry_tons"], cumulative_metrics["dry_tons"],
        current_metrics["liquid_tons"], cumulative_metrics["liquid_tons"],
        current_metrics["foreign_tons"], cumulative_metrics["foreign_tons"],
        current_metrics["calls"], cumulative_metrics["calls"],
        current_metrics["passenger_calls"], current_metrics["passengers"],
    ]
    return [
        ["I", "Bến cảng biển", *([None] * 14)],
        [None, "- Cảng Tân Thuận", *values],
        ["Tổng", None, *values],
    ]


def _cargo_column_start(movement_type: str, cargo_direction: str = "") -> int:
    key = import_match_key(movement_type)
    if "XUATKHAU" in key:
        return 8
    if "NHAPKHAU" in key:
        return 11
    if "NOIDIADEN" in key:
        return 14
    if "NOIDIAROI" in key:
        return 17
    if "NOIDIA" in key:
        if cargo_direction == "unload":
            return 14
        if cargo_direction == "load":
            return 17
    if "CHUYENTAI" in key:
        return 20
    if "QUACANH" in key and ("BOCDO" in key or "XEPDO" in key):
        return 22
    if "QUACANH" in key or "QUACANG" in key:
        return 24
    raise ValueError(f"Không nhận diện được nhóm hàng hóa '{movement_type or '(trống)'}'.")


def _distinct_join(values: list[Any]) -> str:
    result: list[str] = []
    for value in values:
        text_value = str(value or "").strip()
        if text_value and text_value not in result:
            result.append(text_value)
    return "\n".join(result)


def _appendix3_rows(
    db: Session,
    declarations: list[Declaration],
    vessels: Optional[list[Vessel]] = None,
) -> list[list[Any]]:
    rows: list[list[Any]] = []
    groups: dict[str, list[Declaration]] = {}
    for declaration in declarations:
        key = _declaration_report_group_key(db, declaration)
        groups.setdefault(key, []).append(declaration)

    base_vessels = vessels or []
    vessel_by_key = {_report_group_key(vessel.id, vessel.registration_no): vessel for vessel in base_vessels}
    ordered_keys = list(vessel_by_key)
    unmatched_keys = [key for key in groups if key not in vessel_by_key]
    unmatched_keys.sort(key=lambda key: (_declaration_operating_date(groups[key][0]) or date.max, groups[key][0].id))
    ordered_keys.extend(unmatched_keys)
    for key in ordered_keys:
        group = groups.get(key, [])
        group.sort(key=lambda item: (_declaration_operating_date(item) or date.max, item.id))
        declaration = group[0] if group else None
        vessel = vessel_by_key.get(key) or (_report_vessel(db, declaration) if declaration else None)
        row: list[Any] = [None] * 35
        row[0] = len(rows) + 1
        row[1] = _report_static_value(vessel, declaration, "name") or (declaration.vessel_name if declaration else "")
        row[2] = _report_static_value(vessel, declaration, "registration_no") or (declaration.registration_no if declaration else "")
        row[3] = _report_static_value(vessel, declaration, "vessel_type") or ""
        row[4] = _report_static_value(vessel, declaration, "vessel_class") or ""
        row[5] = _report_static_value(vessel, declaration, "length_m")
        row[6] = _joined_profile_value(vessel, "deadweight_tons") if vessel else (declaration.deadweight_tons if declaration else None)
        row[7] = _report_static_value(vessel, declaration, "gross_tonnage")
        cargo_names: list[str] = []
        for item_declaration in group:
            for cargo_direction, item in (
                ("unload", json.loads(item_declaration.unload_json or "{}")),
                ("load", json.loads(item_declaration.load_json or "{}")),
            ):
                if not any((item.get("cargo_type"), item.get("cargo_name"), item.get("tons"), item.get("teu"), item.get("empty_teu"))):
                    continue
                cargo_start = _cargo_column_start(str(item.get("movement_type") or ""), cargo_direction)
                for offset, item_key in ((0, "tons"), (1, "teu")):
                    value = float(item.get(item_key) or 0)
                    if value:
                        row[cargo_start + offset] = float(row[cargo_start + offset] or 0) + value
                if cargo_start in {8, 11, 14, 17}:
                    empty_teu = float(item.get("empty_teu") or 0)
                    if empty_teu:
                        row[cargo_start + 2] = float(row[cargo_start + 2] or 0) + empty_teu
                cargo_names.append(str(item.get("cargo_name") or item.get("cargo_type") or ""))
        for item_declaration in group:
            if item_declaration.passenger_count:
                column = 26 if item_declaration.movement_type == "ARRIVAL" else 27
                row[column] = int(row[column] or 0) + int(item_declaration.passenger_count)
        row[28] = _distinct_join(cargo_names)
        row[29] = _distinct_join([item.last_port for item in group])
        row[30] = _distinct_join([item.working_port for item in group])
        row[31] = _distinct_join([item.destination_port for item in group])
        row[32] = _distinct_join([item.actual_arrival_at or item.eta for item in group])
        row[33] = _distinct_join([item.actual_departure_at or item.etd for item in group])
        row[34] = _distinct_join([item.agent_ptnd_name for item in group])
        rows.append(row)
    return rows


def _report_adjustment_totals(
    db: Session,
    start_month: str,
    end_month: str,
    scope: Scope,
) -> dict[str, float]:
    query = db.query(ReportAdjustment).filter(
        ReportAdjustment.report_kind == "appendix2",
        ReportAdjustment.report_month >= start_month,
        ReportAdjustment.report_month <= end_month,
    )
    if scope.is_customer:
        query = query.filter(ReportAdjustment.organization_id == scope.organization_id)
    else:
        query = query.filter(ReportAdjustment.reporting_unit_id == scope.reporting_unit_id)
    totals: dict[str, float] = {}
    for adjustment in query.all():
        totals[adjustment.metric] = totals.get(adjustment.metric, 0.0) + adjustment.delta
    return totals


@app.get("/api/reports/appendix2/adjustments")
def list_appendix2_adjustments(
    report_month: Optional[str] = None,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    query = db.query(ReportAdjustment).filter(
        ReportAdjustment.report_kind == "appendix2",
        ReportAdjustment.reporting_unit_id == scope.reporting_unit_id,
    )
    if report_month:
        try:
            datetime.strptime(report_month, "%Y-%m")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Tháng báo cáo phải có định dạng YYYY-MM.") from exc
        query = query.filter(ReportAdjustment.report_month == report_month)
    return [
        {column.name: getattr(item, column.name) for column in item.__table__.columns}
        for item in query.order_by(ReportAdjustment.created_at.desc(), ReportAdjustment.id.desc()).all()
    ]


@app.post("/api/reports/appendix2/adjustments")
def create_appendix2_adjustment(
    payload: ReportAdjustmentRequest,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    user = scope.user
    if payload.organization_id is not None:
        organization = db.query(Organization).filter(Organization.id == payload.organization_id).first()
        if not organization:
            raise HTTPException(status_code=404, detail="Không tìm thấy đơn vị cần điều chỉnh.")
        scope.require_org(payload.organization_id)
    adjustment = ReportAdjustment(
        report_kind="appendix2",
        report_month=payload.report_month,
        metric=payload.metric,
        delta=payload.delta,
        reason=payload.reason,
        organization_id=payload.organization_id,
        reporting_unit_id=scope.reporting_unit_id,
        actor_user_id=user.id,
        created_at=now_iso(),
    )
    db.add(adjustment)
    db.flush()
    audit(
        db, "REPORT_ADJUSTMENT", adjustment.id, "CREATE",
        f"PL.02 {payload.report_month} {payload.metric} {payload.delta:+g}: {payload.reason}",
        actor_user_id=user.id, organization_id=payload.organization_id,
        reporting_unit_id=scope.reporting_unit_id,
    )
    db.commit()
    db.refresh(adjustment)
    return {column.name: getattr(adjustment, column.name) for column in adjustment.__table__.columns}

@app.get("/api/reports/{kind}")
def export_report(
    kind: str,
    from_: Optional[str] = Query(default=None, alias="from"),
    to: Optional[str] = None,
    db: Session = Depends(get_db),
    scope: Scope = Depends(resolve_scope),
):
    user = scope.user
    if kind not in ("appendix1", "appendix2", "appendix3"):
        raise HTTPException(status_code=404, detail=f"Loại báo cáo '{kind}' không tồn tại.")

    if to:
        try:
            report_end = date.fromisoformat(to)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Ngày kết thúc báo cáo không hợp lệ.") from exc
    else:
        report_end = date.today()
        to = report_end.isoformat()
    if from_:
        try:
            report_start = date.fromisoformat(from_)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Ngày bắt đầu báo cáo không hợp lệ.") from exc
    else:
        report_start = date(report_end.year, 1, 1)
        from_ = report_start.isoformat()
    if report_start > report_end:
        raise HTTPException(status_code=422, detail="Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.")

    query = _approved_report_query(db, scope)
    approved = query.order_by(Declaration.id).all()

    if kind == "appendix2":
        report_start = date(report_end.year, report_end.month, 1)
        report_end = date(report_end.year, report_end.month, monthrange(report_end.year, report_end.month)[1])
        from_ = report_start.isoformat()
        to = report_end.isoformat()
        decls = [item for item in approved if (value := _arrival_operating_date(item)) and report_start <= value <= report_end]
    else:
        decls = [item for item in approved if (value := _declaration_operating_date(item)) and report_start <= value <= report_end]
    decls.sort(key=lambda item: (_declaration_operating_date(item) or date.max, item.id))
    base_vessels = _report_base_vessels(db, scope) if kind in {"appendix1", "appendix3"} else []

    if kind == "appendix1":
        rows = _appendix1_rows(db, decls, base_vessels)

    elif kind == "appendix2":
        cumulative_start = date(report_end.year, 1, 1)
        cumulative = [
            item for item in approved
            if (value := _arrival_operating_date(item)) and cumulative_start <= value <= report_end
        ]
        month_key = report_end.strftime("%Y-%m")
        rows = _appendix2_rows(
            decls,
            cumulative,
            _report_adjustment_totals(db, month_key, month_key, scope),
            _report_adjustment_totals(db, f"{report_end.year}-01", month_key, scope),
        )

    else:  # appendix3
        try:
            rows = _appendix3_rows(db, decls, base_vessels)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    if scope.is_customer:
        reporting_unit_label = user.organization.name if user.organization else "CÔNG TY CỔ PHẦN CẢNG TÂN THUẬN"
    else:
        unit = db.get(ReportingUnit, scope.reporting_unit_id)
        reporting_unit_label = unit.name if unit else "CÔNG TY CỔ PHẦN CẢNG TÂN THUẬN"
    xlsx_bytes = make_report_xlsx(
        kind,
        rows,
        appendix3_template=ROOT / "templates" / "Phụ lục 3.xlsx",
        report_from=report_start,
        report_to=report_end,
        reporting_unit=reporting_unit_label,
    )
    filename = f"report_{kind}_{from_ or 'all'}_{to or 'all'}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATIONS (Maritime Authority — PREPARE ONLY, no external calls in T0)
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_connector(db: Session) -> IntegrationConnector:
    connector = db.query(IntegrationConnector).filter(
        IntegrationConnector.connector_key == "maritime-authority"
    ).first()
    if not connector:
        connector = IntegrationConnector(
            connector_key="maritime-authority",
            display_name="Cảng vụ Đường thủy nội địa",
            status="NOT_CONFIGURED",
            auth_mode="PENDING_AUTHORITY_SPEC",
            updated_at=now_iso(),
        )
        db.add(connector)
        db.commit()
        db.refresh(connector)
    return connector


@app.get("/api/integrations/maritime-authority")
def get_integration_status(
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    if scope.user.role != "PLATFORM_ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Platform Admin được quản lý tích hợp.")
    connector = _ensure_connector(db)
    jobs = (
        db.query(SyncJob)
        .filter(
            SyncJob.connector_key == "maritime-authority",
            SyncJob.reporting_unit_id == scope.reporting_unit_id,
        )
        .order_by(desc(SyncJob.created_at))
        .limit(20)
        .all()
    )
    connector_dict = {c.name: getattr(connector, c.name) for c in connector.__table__.columns}
    connector_dict["readyToSend"] = connector.status == "READY"
    return {
        "connector": connector_dict,
        "adapter": maritime_authority_adapter().status(),
        "jobs": [
            {c.name: getattr(j, c.name) for c in j.__table__.columns}
            for j in jobs
        ],
    }


@app.post("/api/integrations/prepare-sync")
async def prepare_sync(
    request: Request,
    db: Session = Depends(get_db),
    scope: Scope = Depends(require_port_scope),
):
    """
    Prepare a sync payload (PREPARED status).
    Does NOT send data to any external API — that is out of scope until T6
    and requires official API contract, credentials and sandbox from the authority.
    """
    if scope.user.role != "PLATFORM_ADMIN":
        raise HTTPException(status_code=403, detail="Chỉ Platform Admin được chuẩn bị tích hợp.")
    body = await request.json()
    from_ = body.get("from")
    to = body.get("to")

    query = db.query(Declaration).filter(
        Declaration.workflow_status == "APPROVED"
    )
    org_ids = scope.member_org_ids
    query = query.filter(Declaration.organization_id.in_(org_ids)) if org_ids else query.filter(sql_false())
    if from_:
        query = query.filter(Declaration.declaration_date >= from_)
    if to:
        query = query.filter(Declaration.declaration_date <= to)
    decls = query.all()

    payload_data = [
        {"reference_no": d.reference_no, "vessel_name": d.vessel_name,
         "workflow_status": d.workflow_status}
        for d in decls
    ]

    job = SyncJob(
        connector_key="maritime-authority",
        reporting_unit_id=scope.reporting_unit_id,
        report_from=from_ or "",
        report_to=to or "",
        status="PREPARED",
        record_count=len(payload_data),
        payload_json=json.dumps(payload_data, ensure_ascii=False),
        created_at=now_iso(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {
        "id": job.id,
        "recordCount": job.record_count,
        "status": job.status,
        "note": "Payload đã chuẩn bị nhưng chưa gửi. External sync chưa được kích hoạt (chờ T6).",
    }


# ══════════════════════════════════════════════════════════════════════════════
# STATIC FRONTEND (must be last)
# ══════════════════════════════════════════════════════════════════════════════

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
