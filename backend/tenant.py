"""Shared live-operation tenant-context guard (R4).

A single reusable FastAPI dependency resolves the tenant scope for a request so
individual routes never re-implement ad-hoc role checks or query globally.

Two scopes exist:

- ``CUSTOMER`` scope: a customer user operating on its own Organization. No
  reporting-unit context is required; existing Organization ownership rules
  apply unchanged.
- ``PORT`` scope: a ``PORT_STAFF`` or ``PLATFORM_ADMIN`` user operating a single
  explicit, active reporting unit supplied via the ``X-Reporting-Unit-ID`` header.
  ``PORT_STAFF`` must hold an FK-backed membership in that unit; ``PLATFORM_ADMIN``
  must supply the explicit context but does not need membership. Reads and
  mutations are scoped to the reporting unit and the Organizations linked to it
  through ``reporting_unit_organizations``; the register uses
  ``reporting_unit_vessels``. Tenant data from multiple units is never combined.

Every failure is a deterministic ``400/403/404`` and never leaks another
tenant's data. Platform-wide operations (backup, reporting-unit and membership
management, integrations) do not use this guard and remain platform-scoped.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import get_db
from .models import (
    Organization,
    ReportingUnit,
    ReportingUnitOrganization,
    ReportingUnitUser,
    ReportingUnitVessel,
    User,
    Vessel,
)

CUSTOMER = "CUSTOMER"
PORT = "PORT"
_PORT_ROLES = {"PORT_STAFF", "PLATFORM_ADMIN"}


@dataclass
class Scope:
    kind: str
    user: User
    organization_id: int | None = None            # CUSTOMER scope
    reporting_unit_id: int | None = None           # PORT scope
    member_org_ids: tuple[int, ...] = field(default_factory=tuple)  # PORT scope
    # PORT scope only: staff_function of this user's membership in the resolved
    # reporting unit (SECURITY / CARGO_OPS / None). Always None for
    # PLATFORM_ADMIN — an admin is authorized for every port operation
    # regardless of function, so callers must check ``user.role ==
    # "PLATFORM_ADMIN"`` explicitly rather than relying on this field to gate
    # admin access. See ROADMAP_PORT_OPERATIONS.md Giai đoạn 1.
    staff_function: str | None = None

    @property
    def is_port(self) -> bool:
        return self.kind == PORT

    @property
    def is_customer(self) -> bool:
        return self.kind == CUSTOMER

    def allows_staff_function(self, function: str) -> bool:
        """True if this scope may act on the given port function's endpoints.

        PLATFORM_ADMIN always may (full authority, see ``staff_function``
        docstring). PORT_STAFF may only if their membership in the resolved
        unit carries that exact function.
        """
        if self.user.role == "PLATFORM_ADMIN":
            return True
        return self.is_port and self.staff_function == function

    def visible_org_ids(self) -> tuple[int, ...]:
        """Organization ids whose customer data this scope may read."""
        if self.is_customer:
            return (self.organization_id,) if self.organization_id is not None else ()
        return self.member_org_ids

    def owns_org(self, organization_id: int | None) -> bool:
        if organization_id is None:
            return False
        return organization_id in self.visible_org_ids()

    def require_org(self, organization_id: int | None) -> None:
        """Fail closed if the target Organization is not inside this scope."""
        if not self.owns_org(organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tổ chức không thuộc phạm vi được phép.",
            )

    def require_declaration(self, organization_id: int | None, reporting_unit_id: int | None) -> None:
        """Fail closed unless this scope may access a declaration.

        A declaration with no customer Organization (left blank at save time —
        see ``Declaration.reporting_unit_id``) cannot be checked via
        ``require_org``, since ``owns_org(None)`` is always false. Such a
        declaration is scoped by its own ``reporting_unit_id`` tag instead: PORT
        scope may access it only if it matches the resolved unit; CUSTOMER scope
        never can, since an org-less declaration has no customer to belong to.
        """
        if organization_id is not None:
            self.require_org(organization_id)
        elif self.is_port and reporting_unit_id == self.reporting_unit_id:
            return
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Phiếu không thuộc phạm vi được phép.",
            )


def _parse_unit_id(raw: str | None) -> int:
    if raw is None or str(raw).strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu ngữ cảnh đơn vị báo cáo (X-Reporting-Unit-ID).",
        )
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ngữ cảnh đơn vị báo cáo không hợp lệ.",
        )


def resolve_scope(
    x_reporting_unit_id: str | None = Header(default=None, alias="X-Reporting-Unit-ID"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Scope:
    """Resolve the tenant scope for a live request; fail closed on any problem."""
    if not getattr(user, "is_active", 1):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị vô hiệu hóa.")

    if user.role == CUSTOMER:
        if user.organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản chưa được liên kết với tổ chức nào.",
            )
        return Scope(kind=CUSTOMER, user=user, organization_id=user.organization_id)

    if user.role in _PORT_ROLES:
        unit_id = _parse_unit_id(x_reporting_unit_id)
        unit = db.get(ReportingUnit, unit_id)
        if unit is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn vị báo cáo.")
        if unit.is_active != 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Đơn vị báo cáo đang ngừng hoạt động.")
        staff_function = None
        if user.role == "PORT_STAFF":
            member = (
                db.query(ReportingUnitUser)
                .filter_by(reporting_unit_id=unit_id, user_id=user.id)
                .first()
            )
            if member is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền tại đơn vị báo cáo này.",
                )
            staff_function = member.staff_function
        org_ids = tuple(
            row[0] for row in db.query(ReportingUnitOrganization.organization_id)
            .filter_by(reporting_unit_id=unit_id).all()
        )
        return Scope(
            kind=PORT, user=user, reporting_unit_id=unit_id,
            member_org_ids=org_ids, staff_function=staff_function,
        )

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vai trò không hợp lệ.")


def require_port_scope(scope: Scope = Depends(resolve_scope)) -> Scope:
    """Tenant scope that must be a PORT scope (rejects CUSTOMER from port ops)."""
    if not scope.is_port:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chức năng nội bộ Cảng không dành cho tài khoản khách hàng.",
        )
    return scope


def register_vessel_ids(db: Session, reporting_unit_id: int) -> list[int]:
    """Vessel ids tracked in one reporting unit's port register."""
    return [
        row[0] for row in db.query(ReportingUnitVessel.vessel_id)
        .filter_by(reporting_unit_id=reporting_unit_id).all()
    ]


def scope_allows_vessel(db: Session, scope: Scope, vessel: Vessel) -> bool:
    """True if this scope may read/mutate the given vessel.

    CUSTOMER: the vessel's Organization is the customer's own. PORT: the vessel's
    Organization is linked to the resolved unit, or the vessel is in that unit's
    register (``reporting_unit_vessels``).
    """
    if vessel is None:
        return False
    if scope.is_customer:
        return vessel.organization_id == scope.organization_id
    if vessel.organization_id in scope.member_org_ids:
        return True
    return (
        db.query(ReportingUnitVessel)
        .filter_by(reporting_unit_id=scope.reporting_unit_id, vessel_id=vessel.id)
        .first() is not None
    )


def require_vessel_in_scope(db: Session, scope: Scope, vessel: Vessel) -> None:
    if not scope_allows_vessel(db, scope, vessel):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phương tiện không thuộc phạm vi được phép.",
        )
