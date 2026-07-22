from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, DateTime, Text,
    UniqueConstraint, Index, ForeignKeyConstraint, CheckConstraint,
)
from sqlalchemy.orm import declarative_base, relationship, backref

Base = declarative_base()

def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, default="")
    email = Column(String, nullable=False, default="")  # địa chỉ nhận thông báo (tùy chọn)
    role = Column(String, default="CUSTOMER")  # PLATFORM_ADMIN, PORT_STAFF, CUSTOMER
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    # Reporting-unit membership is modelled as an FK-backed association
    # (``reporting_unit_users``), not a soft column, so it cannot hold an
    # invalid/nonexistent unit id. A user may belong to more than one port; a
    # platform administrator may have no membership at all. See ReportingUnitUser.
    is_active = Column(Integer, nullable=False, default=1)  # 0/1 integer flag (legacy boolean encoding)
    notification_preferences_json = Column(Text, nullable=False, default='{"in_app_certificate_reminders": true}')
    created_at = Column(String, default=now_iso)

    organization = relationship("Organization", back_populates="users", lazy="select")

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    tax_code = Column(String, nullable=False, default="")
    address = Column(String, nullable=False, default="")
    contact_name = Column(String, nullable=False, default="")
    contact_role = Column(String, nullable=False, default="")
    phone = Column(String, nullable=False, default="")
    email = Column(String, nullable=False, default="")
    # Reporting-unit membership is modelled as an FK-backed association
    # (``reporting_unit_organizations``), not a soft column. A customer company
    # may be served by more than one port; see ReportingUnitOrganization.
    created_at = Column(String, nullable=False, default=now_iso)
    updated_at = Column(String, nullable=False, default=now_iso)
    vessels = relationship("Vessel", back_populates="organization", lazy="dynamic")
    users = relationship("User", back_populates="organization", lazy="dynamic")
    crew_members = relationship("CrewMember", back_populates="organization", lazy="dynamic")
    declarations = relationship("Declaration", back_populates="organization", lazy="dynamic")

class Vessel(Base):
    __tablename__ = "vessels"
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    name = Column(String, nullable=False)
    registration_no = Column(String, nullable=False, unique=True)
    registry_or_imo = Column(String, nullable=False, default="")
    vessel_type = Column(String, nullable=False)  # Công dụng, nguyên văn theo GCN
    vessel_category = Column(String, nullable=True)  # phân loại nội bộ, không bắt buộc
    vessel_class = Column(String, nullable=False)
    shell_material = Column(String, nullable=False, default="")
    build_year = Column(Integer)
    length_m = Column(Float)
    width_m = Column(Float)
    side_height_m = Column(Float)
    draft_m = Column(Float)
    deadweight_tons = Column(Float)
    gross_tonnage = Column(Float)
    engine_power_cv = Column(Float)
    cargo_capacity_tons = Column(Float)
    container_capacity_teu = Column(Float)
    passenger_capacity = Column(Integer)
    min_crew = Column(Integer)
    safety_certificate_no = Column(String, nullable=False, default="")
    certificate_issue_date = Column(String)
    certificate_expiry_date = Column(String)
    tracking_master_name = Column(String, nullable=False, default="")
    tracking_master_phone = Column(String, nullable=False, default="")
    is_port_tracked = Column(Integer, nullable=False, default=0)
    port_tracking_updated_at = Column(String)
    registry_verification_status = Column(String, nullable=False, default="NOT_VERIFIED")
    registry_verified_at = Column(String)
    registry_verification_source = Column(String, nullable=False, default="")
    notes = Column(Text, nullable=False, default="")
    created_at = Column(String, nullable=False, default=now_iso)
    updated_at = Column(String, nullable=False, default=now_iso)
    version = Column(Integer, nullable=False, default=1)
    organization = relationship("Organization", back_populates="vessels", lazy="select")
    crew_members = relationship("CrewMember", back_populates="vessel", lazy="dynamic")
    declarations = relationship("Declaration", back_populates="vessel", lazy="dynamic")
    operating_profiles = relationship(
        "VesselOperatingProfile",
        back_populates="vessel",
        cascade="all, delete-orphan",
        order_by="VesselOperatingProfile.sequence",
    )


class VesselOperatingProfile(Base):
    __tablename__ = "vessel_operating_profiles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    vessel_id = Column(Integer, ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(Integer, nullable=False, default=1)
    activity_area = Column(String, nullable=False, default="")
    deadweight_tons = Column(Float)
    cargo_capacity_tons = Column(Float)
    vessel = relationship("Vessel", back_populates="operating_profiles")

class Declaration(Base):
    __tablename__ = "declarations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    reference_no = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, default="DRAFT")
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    vessel_id = Column(Integer, ForeignKey("vessels.id"))
    declaration_date = Column(String, nullable=False)
    company_name = Column(String, nullable=False)
    vessel_name = Column(String, nullable=False)
    registration_no = Column(String, nullable=False)
    vessel_type = Column(String, nullable=False)
    vessel_class = Column(String, nullable=False)
    length_m = Column(Float)
    deadweight_tons = Column(Float)
    gross_tonnage = Column(Float)
    certificate_expiry_date = Column(String)
    crew_count = Column(Integer, nullable=False, default=0)  # số thuyền viên tối thiểu theo GCN, khóa từ hồ sơ phương tiện
    crew_onboard_count = Column(Integer, nullable=False, default=0)  # số thuyền viên thực tế đi theo lượt này
    passenger_count = Column(Integer, nullable=False, default=0)
    last_port = Column(String, nullable=False)
    working_port = Column(String, nullable=False)
    departure_berth = Column(String, nullable=False, default="")
    destination_port = Column(String, nullable=False, default="")
    agent_ptnd_name = Column(String, nullable=False, default="")
    is_passenger_call = Column(Integer, nullable=False, default=0)
    eta = Column(String, nullable=False)
    etd = Column(String, nullable=False)
    unload_json = Column(Text, nullable=False)
    load_json = Column(Text, nullable=False)
    master_name = Column(String, nullable=False)
    master_phone = Column(String, nullable=False)
    movement_type = Column(String, nullable=False, default="ARRIVAL")
    purpose = Column(String, nullable=False, default="")
    cargo_description = Column(String, nullable=False, default="")
    actual_arrival_at = Column(String)
    actual_departure_at = Column(String)
    workflow_status = Column(String, nullable=False, default="DRAFT")
    port_approval = Column(String, nullable=False, default="PENDING")
    submitted_at = Column(String)
    created_at = Column(String, nullable=False, default=now_iso)
    updated_at = Column(String, nullable=False, default=now_iso)
    version = Column(Integer, nullable=False, default=1)
    organization = relationship("Organization", back_populates="declarations", lazy="select")
    vessel = relationship("Vessel", back_populates="declarations", lazy="select")
    crew_links = relationship("DeclarationCrew", back_populates="declaration", cascade="all, delete-orphan")
    events = relationship("DeclarationEvent", back_populates="declaration", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="declaration", cascade="all, delete-orphan")


class ReportAdjustment(Base):
    __tablename__ = "report_adjustments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_kind = Column(String, nullable=False, default="appendix2")
    report_month = Column(String, nullable=False)
    metric = Column(String, nullable=False)
    delta = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    reporting_unit_id = Column(Integer, ForeignKey("reporting_units.id"), nullable=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(String, nullable=False, default=now_iso)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"))
    organization_id = Column(Integer, ForeignKey("organizations.id"))  # customer Organization; never a Port id
    # Optional tenant scope (added in H2). Historical import/revision/review audit
    # carries the affected reporting unit; existing non-historical audit stays NULL.
    reporting_unit_id = Column(Integer, ForeignKey("reporting_units.id"), nullable=True)
    correlation_id = Column(String, nullable=False, default="")
    created_at = Column(String, nullable=False, default=now_iso)

class DeclarationEvent(Base):
    __tablename__ = "declaration_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    declaration_id = Column(Integer, ForeignKey("declarations.id", ondelete="CASCADE"), nullable=False)
    action = Column(String, nullable=False)
    from_status = Column(String, nullable=False, default="")
    to_status = Column(String, nullable=False)
    actor_name = Column(String, nullable=False)
    actor_role = Column(String, nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"))
    correlation_id = Column(String, nullable=False, default="")
    note = Column(Text, nullable=False, default="")
    created_at = Column(String, nullable=False, default=now_iso)
    declaration = relationship("Declaration", back_populates="events")

class CrewMember(Base):
    __tablename__ = "crew_members"
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    vessel_id = Column(Integer, ForeignKey("vessels.id"))
    full_name = Column(String, nullable=False)
    crew_role = Column(String, nullable=False)
    birth_date = Column(String)
    phone = Column(String, nullable=False, default="")
    identity_no = Column(String, nullable=False, default="")
    professional_certificate_type = Column(String, nullable=False)
    professional_certificate_no = Column(String, nullable=False)
    certificate_issue_date = Column(String)
    certificate_expiry_date = Column(String)
    notes = Column(Text, nullable=False, default="")
    created_at = Column(String, nullable=False, default=now_iso)
    updated_at = Column(String, nullable=False, default=now_iso)
    version = Column(Integer, nullable=False, default=1)
    organization = relationship("Organization", back_populates="crew_members", lazy="select")
    vessel = relationship("Vessel", back_populates="crew_members", lazy="select")
    declaration_links = relationship("DeclarationCrew", back_populates="crew_member")

class DeclarationCrew(Base):
    __tablename__ = "declaration_crew"
    declaration_id = Column(Integer, ForeignKey("declarations.id", ondelete="CASCADE"), primary_key=True)
    crew_member_id = Column(Integer, ForeignKey("crew_members.id"), primary_key=True)
    crew_role_snapshot = Column(String, nullable=False)
    certificate_no_snapshot = Column(String, nullable=False)
    certificate_expiry_snapshot = Column(String)
    declaration = relationship("Declaration", back_populates="crew_links")
    crew_member = relationship("CrewMember", back_populates="declaration_links")

class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    declaration_id = Column(Integer, ForeignKey("declarations.id", ondelete="CASCADE"), nullable=False)
    original_name = Column(String, nullable=False)
    stored_name = Column(String, nullable=False, unique=True)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    checksum_sha256 = Column(String, nullable=False, default="")
    scan_status = Column(String, nullable=False, default="QUARANTINED")
    storage_backend = Column(String, nullable=False, default="LOCAL_QUARANTINE")
    scanned_at = Column(String)
    created_at = Column(String, nullable=False, default=now_iso)
    declaration = relationship("Declaration", back_populates="attachments")

class IntegrationConnector(Base):
    __tablename__ = "integration_connectors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    connector_key = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="NOT_CONFIGURED")
    base_url = Column(String, nullable=False, default="")
    auth_mode = Column(String, nullable=False, default="PENDING_AUTHORITY_SPEC")
    last_sync_at = Column(String)
    updated_at = Column(String, nullable=False, default=now_iso)

class AppSetting(Base):
    """Simple key-value store for runtime settings edited from the admin UI.

    Values are JSON strings. Secrets inside a value (e.g. the SMTP password) are
    encrypted before storage — see backend/crypto_util.py.
    """
    __tablename__ = "app_settings"
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False, default="")
    updated_at = Column(String, nullable=False, default=now_iso)

class SyncJob(Base):
    __tablename__ = "sync_jobs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    connector_key = Column(String, nullable=False)
    reporting_unit_id = Column(Integer, ForeignKey("reporting_units.id"), nullable=True, index=True)
    report_from = Column(String, nullable=False)
    report_to = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PREPARED")
    record_count = Column(Integer, nullable=False, default=0)
    payload_json = Column(Text, nullable=False)
    created_at = Column(String, nullable=False, default=now_iso)
    sent_at = Column(String)


class ImportJob(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        UniqueConstraint("organization_id", "import_kind", "source_checksum", "mapping_version", name="uq_import_idempotency"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    reporting_unit_id = Column(Integer, ForeignKey("reporting_units.id"), nullable=True, index=True)
    import_kind = Column(String, nullable=False)
    source_checksum = Column(String, nullable=False)
    mapping_version = Column(String, nullable=False)
    status = Column(String, nullable=False, default="COMPLETED")
    accepted_count = Column(Integer, nullable=False, default=0)
    rejected_count = Column(Integer, nullable=False, default=0)
    result_json = Column(Text, nullable=False, default="{}")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(String, nullable=False, default=now_iso)


# ─────────────────────────────────────────────────────────────────────────────
# Historical / TOS import store (H2 — schema, migration and provenance
# foundation).
#
# These tables hold reported historical appendix facts (PL.01/PL.02/PL.03) and
# normalized TOS operational facts (Berth calls and cargo detail) imported from
# old official workbooks. They are a SEPARATE boundary from live operations:
#   - they never create a Declaration or mark one APPROVED;
#   - they never overwrite canonical Vessel/Crew/Organization master data;
#   - every source cell, checksum and blank/zero state is preserved as evidence.
#
# Tenancy model (corrected in H2):
#   - ReportingUnit is a distinct entity — a Port that operates the product. It
#     is NOT an Organization. Organization stays a customer company that owns
#     vessels and declarations. Cang Tan Thuan is simply the first reporting-unit
#     row and is never hardcoded in a model, migration, default row or rule.
#   - Every historical import/row/metric/call/cargo/link/revision belongs to
#     exactly one ReportingUnit via reporting_unit_id -> reporting_units.
#   - Tenant consistency is enforced with COMPOSITE foreign keys, not by
#     unrelated single-column keys plus a repeated reporting_unit_id. A child
#     carrying reporting unit B therefore cannot reference a parent owned by
#     reporting unit A: (import_id, reporting_unit_id) must match a real
#     historical_report_imports(id, reporting_unit_id) pair, and likewise for
#     rows, port calls and revision lineage.
#   - PostgreSQL enforces declared foreign keys unconditionally, so these
#     constraints and ON DELETE CASCADE are real.
#
# Candidate-vessel tenancy is a multi-hop rule (link -> vessel -> organization ->
# reporting_unit) that is not portably expressible as a single database
# constraint. The database boundary is the plain candidate_vessel_id foreign
# key; the cross-unit rule is enforced fail-closed in
# backend.historical.validate_vessel_link_tenant with negative tests. This
# residual limitation is documented in the handoff.
# ─────────────────────────────────────────────────────────────────────────────

# Approved value sets, kept next to the CHECK constraints that reference them.
HISTORICAL_IMPORT_STATUSES = ("PENDING", "PREVIEWED", "COMMITTED", "REVIEW", "REJECTED", "SUPERSEDED")
HISTORICAL_VALIDATION_STATUSES = ("PENDING", "VALID", "REVIEW", "REJECTED")
HISTORICAL_VALUE_CLASSES = ("SELECTED_PERIOD", "YTD", "REPORTED_TOTAL", "TEXT")
HISTORICAL_METRIC_VALUE_STATES = ("PRESENT", "BLANK", "ZERO")
HISTORICAL_WEIGHT_STATES = ("PRESENT", "BLANK", "ZERO", "INVALID")
HISTORICAL_AMBIGUITY_STATES = ("NONE", "UNMATCHED", "AMBIGUOUS")
HISTORICAL_CARGO_MATCH_STATES = ("PENDING", "MATCHED", "UNMATCHED", "AMBIGUOUS")
HISTORICAL_LINK_STATUSES = ("PENDING", "ACCEPTED", "REJECTED")
HISTORICAL_LINK_METHODS = ("", "EXACT", "NORMALIZED", "MANUAL")
HISTORICAL_LINK_CONFIDENCES = ("", "HIGH", "MEDIUM", "LOW")


def _in_clause(column: str, values) -> str:
    rendered = ", ".join("'" + str(v).replace("'", "''") + "'" for v in values)
    return f"{column} IN ({rendered})"


class ReportingUnit(Base):
    """A Port/reporting unit that operates the product — the historical tenant.

    Distinct from Organization (a customer company). Cang Tan Thuan is the first
    reporting unit but is created as ordinary data, never hardcoded here.
    """
    __tablename__ = "reporting_units"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    code = Column(String, nullable=False, default="")
    official_header_json = Column(Text, nullable=False, default="{}")  # tenant-scoped official report header details
    notify_email = Column(String, nullable=False, default="")  # email chung của Cảng để nhận thông báo
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(String, nullable=False, default=now_iso)
    updated_at = Column(String, nullable=False, default=now_iso)


class ReportingUnitUser(Base):
    """FK-backed membership of a user in a reporting unit (many-to-many).

    A staff user may legitimately serve more than one port; every operation still
    uses one explicit active reporting unit. Both sides are real foreign keys so an
    invalid/nonexistent user or unit fails at the database. Membership is deleted
    when either the user or the unit is deleted. A platform administrator may have
    no membership at all — and the absence of membership never implies access.
    """
    __tablename__ = "reporting_unit_users"
    reporting_unit_id = Column(
        Integer, ForeignKey("reporting_units.id", ondelete="CASCADE"), primary_key=True
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    membership_role = Column(String, nullable=False, default="")  # optional local scope label
    created_at = Column(String, nullable=False, default=now_iso)


class ReportingUnitOrganization(Base):
    """FK-backed membership of a customer Organization in a reporting unit (M2M).

    A customer company may be served by more than one port. Both sides are real
    foreign keys; membership is deleted when either side is deleted.
    """
    __tablename__ = "reporting_unit_organizations"
    reporting_unit_id = Column(
        Integer, ForeignKey("reporting_units.id", ondelete="CASCADE"), primary_key=True
    )
    organization_id = Column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    created_at = Column(String, nullable=False, default=now_iso)


class ReportingUnitVessel(Base):
    """FK-backed per-port vessel register membership (many-to-many).

    The internal Port register is tenant-scoped: the same physical Vessel may be
    tracked by reporting unit A and not by reporting unit B. This association is
    the authorization and tenant boundary for the register; the legacy global
    ``vessels.is_port_tracked`` boolean is retained only for backward
    compatibility and is deprecated as a tenant/authorization signal.
    """
    __tablename__ = "reporting_unit_vessels"
    reporting_unit_id = Column(
        Integer, ForeignKey("reporting_units.id", ondelete="CASCADE"), primary_key=True
    )
    vessel_id = Column(Integer, ForeignKey("vessels.id", ondelete="CASCADE"), primary_key=True)
    added_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(String, nullable=False, default=now_iso)


class HistoricalReportImport(Base):
    """Immutable source-file import/revision record for a historical workbook."""
    __tablename__ = "historical_report_imports"
    __table_args__ = (
        # Composite identity target so children can reference (id, reporting_unit_id).
        UniqueConstraint("id", "reporting_unit_id", name="uq_hist_import_identity"),
        # Tenant-scoped checksum idempotency.
        UniqueConstraint(
            "reporting_unit_id", "source_kind", "source_checksum", "mapping_version",
            name="uq_historical_import_idempotency",
        ),
        # Revision lineage stays inside one reporting unit: a superseding import
        # must share this import's reporting unit.
        ForeignKeyConstraint(
            ["superseded_by_import_id", "reporting_unit_id"],
            ["historical_report_imports.id", "historical_report_imports.reporting_unit_id"],
            name="fk_hist_import_supersede",
        ),
        CheckConstraint("revision_no >= 1", name="ck_hist_import_revision"),
        CheckConstraint("accepted_count >= 0", name="ck_hist_import_accepted"),
        CheckConstraint("rejected_count >= 0", name="ck_hist_import_rejected"),
        CheckConstraint("review_count >= 0", name="ck_hist_import_review"),
        CheckConstraint("source_size_bytes >= 0", name="ck_hist_import_size"),
        CheckConstraint(_in_clause("status", HISTORICAL_IMPORT_STATUSES), name="ck_hist_import_status"),
        Index("ix_historical_imports_unit_period", "reporting_unit_id", "reporting_period"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    reporting_unit_id = Column(Integer, ForeignKey("reporting_units.id"), nullable=False, index=True)
    source_kind = Column(String, nullable=False)  # tos_berth_call, tos_cargo_detail, port_vessel_register, reported_pl03, historical_pl01, historical_pl02
    appendix_kind = Column(String, nullable=False, default="")  # PL.01 / PL.02 / PL.03 / "" for TOS operational
    mapping_version = Column(String, nullable=False)  # detected content signature / mapping version, never the filename
    reporting_period = Column(String)  # YYYY-MM by ATB; NULL means undetermined and pending review
    source_filename = Column(String, nullable=False, default="")  # provenance metadata only, not a parser/query key
    source_checksum = Column(String, nullable=False)  # sha256 of the original file
    source_size_bytes = Column(Integer, nullable=False, default=0)
    source_sheets_json = Column(Text, nullable=False, default="[]")
    status = Column(String, nullable=False, default="PENDING")
    revision_no = Column(Integer, nullable=False, default=1)
    superseded_by_import_id = Column(Integer, nullable=True)  # composite FK above; must be same reporting unit
    supersede_reason = Column(Text, nullable=False, default="")
    accepted_count = Column(Integer, nullable=False, default=0)
    rejected_count = Column(Integer, nullable=False, default=0)
    review_count = Column(Integer, nullable=False, default=0)
    mapping_receipt_json = Column(Text, nullable=False, default="{}")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(String, nullable=False, default=now_iso)
    updated_at = Column(String, nullable=False, default=now_iso)


class HistoricalReportRow(Base):
    """A single reported source row (e.g. one PL.03 vessel row) with provenance."""
    __tablename__ = "historical_report_rows"
    __table_args__ = (
        # Composite identity target so a metric can reference (id, import_id, reporting_unit_id).
        UniqueConstraint("id", "import_id", "reporting_unit_id", name="uq_hist_row_identity"),
        # A row's import must belong to the row's reporting unit.
        ForeignKeyConstraint(
            ["import_id", "reporting_unit_id"],
            ["historical_report_imports.id", "historical_report_imports.reporting_unit_id"],
            ondelete="CASCADE", name="fk_hist_row_import",
        ),
        CheckConstraint(_in_clause("validation_status", HISTORICAL_VALIDATION_STATUSES), name="ck_hist_row_validation"),
        Index("ix_historical_rows_import", "import_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    reporting_unit_id = Column(Integer, ForeignKey("reporting_units.id"), nullable=False, index=True)
    import_id = Column(Integer, nullable=False)  # composite FK above
    source_sheet = Column(String, nullable=False, default="")
    source_row = Column(Integer, nullable=False, default=0)  # 1-based source-row index
    appendix_row_no = Column(Integer)  # e.g. PL.03 STT; NULL when not applicable
    vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=True)  # optional controlled canonical link
    normalized_registration = Column(String, nullable=False, default="")
    raw_payload_json = Column(Text, nullable=False, default="{}")  # sanitized raw row values
    mapped_dimensions_json = Column(Text, nullable=False, default="{}")
    validation_status = Column(String, nullable=False, default="PENDING")
    warning_json = Column(Text, nullable=False, default="[]")
    provenance_json = Column(Text, nullable=False, default="{}")  # sheet/row/cell receipt
    created_at = Column(String, nullable=False, default=now_iso)


class HistoricalReportMetric(Base):
    """A typed reported metric with value class, blank/zero state and source cell."""
    __tablename__ = "historical_report_metrics"
    __table_args__ = (
        # Import ownership (always enforced: import_id is non-null).
        ForeignKeyConstraint(
            ["import_id", "reporting_unit_id"],
            ["historical_report_imports.id", "historical_report_imports.reporting_unit_id"],
            ondelete="CASCADE", name="fk_hist_metric_import",
        ),
        # Row ownership (enforced when row_id is present): guarantees row_id,
        # import_id and reporting unit all agree.
        ForeignKeyConstraint(
            ["row_id", "import_id", "reporting_unit_id"],
            ["historical_report_rows.id", "historical_report_rows.import_id", "historical_report_rows.reporting_unit_id"],
            ondelete="CASCADE", name="fk_hist_metric_row",
        ),
        CheckConstraint(_in_clause("value_class", HISTORICAL_VALUE_CLASSES), name="ck_hist_metric_value_class"),
        CheckConstraint(_in_clause("value_state", HISTORICAL_METRIC_VALUE_STATES), name="ck_hist_metric_value_state"),
        # Blank keeps no measured number; measured zero keeps an explicit 0.
        CheckConstraint("value_state <> 'BLANK' OR numeric_value IS NULL", name="ck_hist_metric_blank_null"),
        CheckConstraint("value_state <> 'ZERO' OR numeric_value = 0", name="ck_hist_metric_zero_value"),
        Index("ix_historical_metrics_import_code", "import_id", "metric_code"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    reporting_unit_id = Column(Integer, ForeignKey("reporting_units.id"), nullable=False, index=True)
    import_id = Column(Integer, nullable=False)  # composite FK above
    row_id = Column(Integer, nullable=True)  # composite FK above (enforced when present)
    metric_code = Column(String, nullable=False)  # canonical fact code, e.g. export_full_teu_reported
    direction = Column(String, nullable=False, default="")
    category = Column(String, nullable=False, default="")
    unit = Column(String, nullable=False, default="")  # tonne / teu / count
    value_class = Column(String, nullable=False)
    numeric_value = Column(Float)
    text_value = Column(Text)
    value_state = Column(String, nullable=False, default="PRESENT")
    source_cell = Column(String, nullable=False, default="")  # e.g. "BAO CAO!J10"
    source_header_raw = Column(String, nullable=False, default="")  # observed (possibly misspelled) header
    mapping_version = Column(String, nullable=False)
    reconciliation_status = Column(String, nullable=False, default="NONE")
    created_at = Column(String, nullable=False, default=now_iso)


class HistoricalPortCall(Base):
    """Normalized TOS Berth call fact: identity, berth and authoritative ATB/ATD."""
    __tablename__ = "historical_port_calls"
    __table_args__ = (
        # Composite identity target so cargo/links can reference (id, import_id, reporting_unit_id).
        UniqueConstraint("id", "import_id", "reporting_unit_id", name="uq_hist_call_identity"),
        # TOS detail and berth calls arrive in separate source-file imports.  This
        # tenant identity lets detail/link rows point across imports without ever
        # crossing a reporting-unit boundary.
        UniqueConstraint("id", "reporting_unit_id", name="uq_hist_call_tenant_identity"),
        # A source row appears once per import.
        UniqueConstraint(
            "reporting_unit_id", "import_id", "source_sheet", "source_row",
            name="uq_historical_port_call_source_row",
        ),
        ForeignKeyConstraint(
            ["import_id", "reporting_unit_id"],
            ["historical_report_imports.id", "historical_report_imports.reporting_unit_id"],
            ondelete="CASCADE", name="fk_hist_call_import",
        ),
        CheckConstraint(_in_clause("validation_status", HISTORICAL_VALIDATION_STATUSES), name="ck_hist_call_validation"),
        CheckConstraint(_in_clause("ambiguity_status", HISTORICAL_AMBIGUITY_STATES), name="ck_hist_call_ambiguity"),
        Index("ix_historical_calls_unit_key", "reporting_unit_id", "call_key_normalized"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    reporting_unit_id = Column(Integer, ForeignKey("reporting_units.id"), nullable=False, index=True)
    import_id = Column(Integer, nullable=False)  # composite FK above
    source_sheet = Column(String, nullable=False, default="")
    source_row = Column(Integer, nullable=False, default=0)
    mapping_version = Column(String, nullable=False)
    vessel_name_raw = Column(String, nullable=False, default="")
    vessel_name_normalized = Column(String, nullable=False, default="")
    call_year_raw = Column(String, nullable=False, default="")
    voyage_number_raw = Column(String, nullable=False, default="")
    call_key_normalized = Column(String, nullable=False, default="")  # name + year + voyage normalized join key
    vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=True)  # reviewed canonical link only
    source_berth_raw = Column(String, nullable=False, default="")
    arrival_berth = Column(String, nullable=False, default="")  # initialized from the single source berth
    departure_berth = Column(String, nullable=False, default="")  # initialized from the single source berth
    berth_correction_json = Column(Text, nullable=False, default="{}")  # audited split/correction provenance
    actual_berthing_at_raw = Column(String, nullable=False, default="")  # ATB, kept as ATB — never renamed to ATA
    actual_berthing_at = Column(String)  # parsed ISO; NULL when blank/unparseable
    actual_departure_at_raw = Column(String, nullable=False, default="")  # ATD, distinct from ATB
    actual_departure_at = Column(String)
    reporting_month = Column(String)  # YYYY-MM by ATB; NULL blank enters review, no filename/ATA/ATD fallback
    validation_status = Column(String, nullable=False, default="PENDING")
    ambiguity_status = Column(String, nullable=False, default="NONE")
    reconciliation_status = Column(String, nullable=False, default="NONE")
    provenance_json = Column(Text, nullable=False, default="{}")
    created_at = Column(String, nullable=False, default=now_iso)


class HistoricalCargoRow(Base):
    """Normalized TOS cargo/detail fact: separate dimensions before derived measures."""
    __tablename__ = "historical_cargo_rows"
    __table_args__ = (
        UniqueConstraint(
            "reporting_unit_id", "import_id", "source_sheet", "source_row",
            name="uq_historical_cargo_source_row",
        ),
        ForeignKeyConstraint(
            ["import_id", "reporting_unit_id"],
            ["historical_report_imports.id", "historical_report_imports.reporting_unit_id"],
            ondelete="CASCADE", name="fk_hist_cargo_import",
        ),
        # Berth and cargo detail are separate source files/imports.  A cargo row
        # may therefore link across imports, but only to a call in the same unit.
        ForeignKeyConstraint(
            ["port_call_id", "reporting_unit_id"],
            ["historical_port_calls.id", "historical_port_calls.reporting_unit_id"],
            ondelete="CASCADE", name="fk_hist_cargo_call",
        ),
        CheckConstraint("teu_factor IS NULL OR teu_factor IN (1, 2)", name="ck_hist_cargo_teu_factor"),
        CheckConstraint(_in_clause("weight_state", HISTORICAL_WEIGHT_STATES), name="ck_hist_cargo_weight_state"),
        CheckConstraint("weight_state <> 'BLANK' OR weight_tonnes IS NULL", name="ck_hist_cargo_blank_null"),
        CheckConstraint("weight_state <> 'ZERO' OR weight_tonnes = 0", name="ck_hist_cargo_zero_value"),
        CheckConstraint(_in_clause("match_status", HISTORICAL_CARGO_MATCH_STATES), name="ck_hist_cargo_match"),
        CheckConstraint(_in_clause("validation_status", HISTORICAL_VALIDATION_STATUSES), name="ck_hist_cargo_validation"),
        Index("ix_historical_cargo_call", "port_call_id"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    reporting_unit_id = Column(Integer, ForeignKey("reporting_units.id"), nullable=False, index=True)
    import_id = Column(Integer, nullable=False)  # composite FK above
    source_sheet = Column(String, nullable=False, default="")
    source_row = Column(Integer, nullable=False, default=0)
    port_call_id = Column(Integer, nullable=True)  # composite FK above; unmatched -> NULL + review
    source_call_key_raw = Column(String, nullable=False, default="")  # raw "name | year | voyage" composite
    call_key_normalized = Column(String, nullable=False, default="")
    container_size_code_raw = Column(String, nullable=False, default="")
    teu_factor = Column(Integer)  # 1 or 2; NULL when size unsupported (review, not zero)
    full_empty_code_raw = Column(String, nullable=False, default="")  # F / E, independent of movement
    trade_scope_raw = Column(String, nullable=False, default="")  # Hang noi / ngoai
    movement_method_raw = Column(String, nullable=False, default="")  # Phuong an
    derived_direction = Column(String, nullable=False, default="")  # load / unload / "" when unknown
    weight_raw = Column(String, nullable=False, default="")
    weight_tonnes = Column(Float)  # parsed; both full and empty container weight contributes to report tonnes
    weight_state = Column(String, nullable=False, default="PRESENT")
    transform_version = Column(String, nullable=False)
    match_status = Column(String, nullable=False, default="PENDING")
    validation_status = Column(String, nullable=False, default="PENDING")
    provenance_json = Column(Text, nullable=False, default="{}")
    created_at = Column(String, nullable=False, default=now_iso)


class HistoricalVesselLink(Base):
    """Controlled candidate link from a TOS/historical identity to a canonical vessel.

    Records the reviewed decision only; it has no authority to mutate canonical
    Vessel fields. ``import_id`` is non-null so every link is traceable to one
    import. ``port_call_id`` may be null for a link originating from an imported
    report row, but when present it must belong to the same import/reporting unit.
    """
    __tablename__ = "historical_vessel_links"
    __table_args__ = (
        ForeignKeyConstraint(
            ["import_id", "reporting_unit_id"],
            ["historical_report_imports.id", "historical_report_imports.reporting_unit_id"],
            ondelete="CASCADE", name="fk_hist_link_import",
        ),
        ForeignKeyConstraint(
            ["port_call_id", "reporting_unit_id"],
            ["historical_port_calls.id", "historical_port_calls.reporting_unit_id"],
            ondelete="CASCADE", name="fk_hist_link_call",
        ),
        CheckConstraint(_in_clause("link_status", HISTORICAL_LINK_STATUSES), name="ck_hist_link_status"),
        CheckConstraint(_in_clause("match_method", HISTORICAL_LINK_METHODS), name="ck_hist_link_method"),
        CheckConstraint(_in_clause("confidence", HISTORICAL_LINK_CONFIDENCES), name="ck_hist_link_confidence"),
        Index("ix_historical_links_unit_norm", "reporting_unit_id", "normalized_vessel_name"),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    reporting_unit_id = Column(Integer, ForeignKey("reporting_units.id"), nullable=False, index=True)
    import_id = Column(Integer, nullable=False)  # composite FK above; every link traces to one import
    port_call_id = Column(Integer, nullable=True)  # composite FK above (enforced when present)
    raw_vessel_name = Column(String, nullable=False, default="")
    normalized_vessel_name = Column(String, nullable=False, default="")
    raw_registration = Column(String, nullable=False, default="")
    candidate_vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=True)
    match_method = Column(String, nullable=False, default="")  # EXACT, NORMALIZED, MANUAL
    confidence = Column(String, nullable=False, default="")  # HIGH, MEDIUM, LOW
    link_status = Column(String, nullable=False, default="PENDING")
    reason = Column(Text, nullable=False, default="")
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(String)
    created_at = Column(String, nullable=False, default=now_iso)
