"""Fail-closed tenant validation for the historical / TOS import store (H2).

Some tenant-isolation rules are multi-hop and cannot be expressed as a single
portable database constraint. This module holds the fail-closed service
validators that enforce them, alongside the composite-foreign-key enforcement
carried by the historical tables and the FK-backed membership tables.

Membership model:
  - a user's authority over a Port is a row in ``reporting_unit_users``;
  - a customer Organization's relationship to a Port is a row in
    ``reporting_unit_organizations``;
  - both sides are real foreign keys, so an invalid id cannot be stored;
  - a user or Organization may belong to several Ports; every operation still
    targets exactly one explicit active reporting unit.

Roles are explicit (there is no tenant-local ADMIN):
  - ``PORT_STAFF`` acts on a reporting unit only where the user holds membership;
  - ``PLATFORM_ADMIN`` carries platform identity in the role itself and acts on a
    unit only with an explicit ``platform_context=True`` — membership is neither
    required nor sufficient;
  - ``CUSTOMER`` and any legacy ``ADMIN`` are rejected.

These validators exist now (H2) with negative tests; H3 endpoints must call them
rather than re-deriving authorization.
"""
from __future__ import annotations

from .models import (
    Organization,
    ReportingUnit,
    ReportingUnitOrganization,
    ReportingUnitUser,
    User,
    Vessel,
)


class HistoricalTenantError(ValueError):
    """Raised when a historical operation would cross a reporting-unit boundary."""


class HistoricalAuthorizationError(ValueError):
    """Raised when an actor/reviewer is not authorized for a reporting unit."""


def _load_active_reporting_unit(session, reporting_unit_id: int) -> ReportingUnit:
    """Return the reporting unit, or fail closed if it is missing or inactive.

    Distinct messages for the two cases. This gate runs before any membership or
    platform-override decision, so no actor — not even a platform ADMIN — can act
    on a nonexistent or deactivated reporting unit.
    """
    unit = session.get(ReportingUnit, reporting_unit_id)
    if unit is None:
        raise HistoricalAuthorizationError(f"reporting unit {reporting_unit_id} does not exist")
    if unit.is_active != 1:
        raise HistoricalAuthorizationError(f"reporting unit {reporting_unit_id} is not active")
    return unit


def user_has_unit_membership(session, user_id: int, reporting_unit_id: int) -> bool:
    """True when the user has an FK-backed membership in the reporting unit."""
    return session.query(ReportingUnitUser).filter_by(
        user_id=user_id, reporting_unit_id=reporting_unit_id
    ).first() is not None


def organization_has_unit_membership(session, organization_id: int, reporting_unit_id: int) -> bool:
    """True when the Organization has an FK-backed membership in the reporting unit."""
    return session.query(ReportingUnitOrganization).filter_by(
        organization_id=organization_id, reporting_unit_id=reporting_unit_id
    ).first() is not None


def _authorize_unit_role(session, *, user, reporting_unit_id: int, platform_context: bool) -> None:
    """Shared fail-closed authorization for historical actors and reviewers.

    Order of checks (each fails closed):

    1. an acting user must be supplied;
    2. the reporting unit must exist and be active — this gate runs before any
       role/membership decision, so nobody (not even a PLATFORM_ADMIN) may act on
       a missing or deactivated unit;
    3. the user must be active;
    4. authorization by explicit role:
       - ``PORT_STAFF``: allowed only with membership in the target unit; a
         platform context never lets PORT_STAFF cross ports;
       - ``PLATFORM_ADMIN``: allowed only with ``platform_context=True``;
         membership is neither required nor sufficient;
       - anything else (``CUSTOMER``, legacy ``ADMIN``, unknown roles): rejected.
    """
    if user is None:
        raise HistoricalAuthorizationError("no acting user supplied")

    # Missing/inactive reporting unit is rejected up front.
    _load_active_reporting_unit(session, reporting_unit_id)

    if not user.is_active:
        raise HistoricalAuthorizationError(f"user {user.id} is inactive")

    if user.role == "PORT_STAFF":
        if user_has_unit_membership(session, user.id, reporting_unit_id):
            return
        raise HistoricalAuthorizationError(
            f"PORT_STAFF user {user.id} has no membership in reporting unit {reporting_unit_id}"
        )
    if user.role == "PLATFORM_ADMIN":
        if platform_context:
            return
        raise HistoricalAuthorizationError(
            f"PLATFORM_ADMIN user {user.id} requires an explicit platform context "
            f"to act on reporting unit {reporting_unit_id}"
        )
    raise HistoricalAuthorizationError(
        f"role {user.role!r} may not act on reporting unit {reporting_unit_id}"
    )


def validate_import_actor(session, *, reporting_unit_id: int, user, platform_context: bool = False) -> None:
    """Fail closed unless ``user`` may create/select/supersede an import in the unit.

    ``PORT_STAFF`` needs membership in the reporting unit; ``PLATFORM_ADMIN`` needs
    an explicit ``platform_context=True`` (membership is neither required nor
    sufficient); ``CUSTOMER``, legacy ``ADMIN`` and inactive users are rejected;
    a missing or inactive reporting unit is rejected. Covers creation, revision
    selection and supersession actor decisions.
    """
    _authorize_unit_role(
        session, user=user, reporting_unit_id=reporting_unit_id, platform_context=platform_context,
    )


def validate_reviewer(session, *, reporting_unit_id: int, reviewer, platform_context: bool = False) -> None:
    """Fail closed unless ``reviewer`` may resolve a manual review in the unit.

    Same rule as :func:`validate_import_actor`: an active ``PORT_STAFF`` with
    membership in the link's reporting unit, or a ``PLATFORM_ADMIN`` with explicit
    context. A cross-port reviewer is rejected.
    """
    _authorize_unit_role(
        session, user=reviewer, reporting_unit_id=reporting_unit_id, platform_context=platform_context,
    )


def validate_vessel_link_tenant(session, *, reporting_unit_id: int, candidate_vessel_id: int | None) -> None:
    """Fail closed unless the candidate vessel's Organization is a member of the unit.

    A link with no candidate vessel is allowed (an unresolved, pending candidate).
    Otherwise the vessel and its owning Organization must exist, and that
    Organization must hold an FK-backed membership in the target reporting unit.
    An Organization may be a member of several ports; the vessel is valid for any
    of them. Any other case — missing vessel, unbound vessel, missing
    Organization, or membership only in another port — fails closed.
    """
    if candidate_vessel_id is None:
        return

    vessel = session.get(Vessel, candidate_vessel_id)
    if vessel is None:
        raise HistoricalTenantError(f"candidate vessel {candidate_vessel_id} does not exist")
    if vessel.organization_id is None:
        raise HistoricalTenantError(
            f"candidate vessel {candidate_vessel_id} has no owning organization; "
            "cannot confirm reporting unit"
        )

    organization = session.get(Organization, vessel.organization_id)
    if organization is None:
        raise HistoricalTenantError(
            f"organization {vessel.organization_id} for candidate vessel "
            f"{candidate_vessel_id} does not exist"
        )
    if not organization_has_unit_membership(session, organization.id, reporting_unit_id):
        raise HistoricalTenantError(
            f"organization {organization.id} has no membership in reporting unit "
            f"{reporting_unit_id}; candidate vessel {candidate_vessel_id} cannot be linked there"
        )
