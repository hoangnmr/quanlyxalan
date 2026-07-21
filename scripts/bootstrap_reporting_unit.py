"""Idempotently bind a legacy single-port database to one ReportingUnit.

The command is preview-only unless ``--apply`` is supplied. It never infers a
staff account, port identity or Organization set from filenames or role gaps;
all of them are explicit arguments.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

EXPECTED_REVISION = "n13f0f000013"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def scalar(connection, sql: str, parameters=None):
    row = connection.execute(text(sql), parameters or {}).fetchone()
    return row[0] if row else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=None, help="PostgreSQL URL (default: app configuration)")
    parser.add_argument("--unit-name", required=True)
    parser.add_argument("--unit-code", required=True)
    parser.add_argument("--staff-username", action="append", required=True)
    parser.add_argument("--actor-username", required=True)
    organizations = parser.add_mutually_exclusive_group(required=True)
    organizations.add_argument("--organization-id", type=int, action="append")
    organizations.add_argument("--all-organizations", action="store_true")
    parser.add_argument("--map-legacy-tracked", action="store_true", required=True)
    parser.add_argument("--allow-shared-organizations", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.url:
        url = args.url
    else:
        from backend.database import SQLALCHEMY_DATABASE_URL

        url = os.environ.get("DATABASE_URL") or SQLALCHEMY_DATABASE_URL

    engine = create_engine(url)
    connection = engine.connect()
    transaction = connection.begin()
    try:
        revision = scalar(connection, "SELECT version_num FROM alembic_version")
        if revision != EXPECTED_REVISION:
            raise RuntimeError(f"Expected Alembic {EXPECTED_REVISION}, found {revision!r}")

        actor = connection.execute(
            text("SELECT id, role, is_active FROM users WHERE username=:username"),
            {"username": args.actor_username},
        ).fetchone()
        if actor is None or actor[1] != "PLATFORM_ADMIN" or actor[2] != 1:
            raise RuntimeError("--actor-username must identify one active PLATFORM_ADMIN")

        staff_rows = []
        for username in dict.fromkeys(args.staff_username):
            row = connection.execute(
                text("SELECT id, role, is_active FROM users WHERE username=:username"),
                {"username": username},
            ).fetchone()
            if row is None or row[1] != "PORT_STAFF" or row[2] != 1:
                raise RuntimeError(f"Staff {username!r} is missing, inactive or not PORT_STAFF")
            staff_rows.append((username, row[0]))

        if args.all_organizations:
            organization_ids = [
                row[0] for row in connection.execute(text("SELECT id FROM organizations ORDER BY id"))
            ]
        else:
            organization_ids = list(dict.fromkeys(args.organization_id or []))
            found = {
                row[0] for row in connection.execute(
                    text("SELECT id FROM organizations WHERE id = ANY(:ids)"),
                    {"ids": organization_ids},
                )
            } if organization_ids else set()
            missing = sorted(set(organization_ids) - found)
            if missing:
                raise RuntimeError(f"Unknown Organization ids: {missing}")
        if not organization_ids:
            raise RuntimeError("No Organizations selected; aborting instead of creating an ambiguous unit")

        unit = connection.execute(
            text("SELECT id, name FROM reporting_units WHERE code=:code"),
            {"code": args.unit_code},
        ).fetchone()
        timestamp = now_iso()
        created_unit = 0
        if unit is None:
            unit_id = connection.execute(
                text(
                    "INSERT INTO reporting_units"
                    "(name,code,is_active,official_header_json,created_at,updated_at) "
                    "VALUES (:name,:code,1,'{}',:ts,:ts) RETURNING id"
                ),
                {"name": args.unit_name, "code": args.unit_code, "ts": timestamp},
            ).scalar_one()
            created_unit = 1
        else:
            unit_id = unit[0]
            if unit[1] != args.unit_name:
                raise RuntimeError(
                    f"Unit code {args.unit_code!r} already belongs to {unit[1]!r}; aborting"
                )
            connection.execute(
                text("UPDATE reporting_units SET is_active=1, updated_at=:ts WHERE id=:id"),
                {"ts": timestamp, "id": unit_id},
            )

        if not args.allow_shared_organizations:
            conflicts = connection.execute(
                text(
                    "SELECT organization_id, reporting_unit_id FROM reporting_unit_organizations "
                    "WHERE organization_id = ANY(:ids) AND reporting_unit_id<>:unit_id"
                ),
                {"ids": organization_ids, "unit_id": unit_id},
            ).fetchall()
            if conflicts:
                raise RuntimeError(f"Organizations already linked to another unit: {conflicts}")

        before = {
            "units": scalar(connection, "SELECT count(*) FROM reporting_units"),
            "memberships": scalar(connection, "SELECT count(*) FROM reporting_unit_users"),
            "organization_links": scalar(connection, "SELECT count(*) FROM reporting_unit_organizations"),
            "register_links": scalar(connection, "SELECT count(*) FROM reporting_unit_vessels"),
        }

        for _, user_id in staff_rows:
            connection.execute(
                text(
                    "INSERT INTO reporting_unit_users(reporting_unit_id,user_id,membership_role,created_at) "
                    "VALUES (:unit_id,:user_id,'',:ts) ON CONFLICT DO NOTHING"
                ),
                {"unit_id": unit_id, "user_id": user_id, "ts": timestamp},
            )
        for organization_id in organization_ids:
            connection.execute(
                text(
                    "INSERT INTO reporting_unit_organizations(reporting_unit_id,organization_id,created_at) "
                    "VALUES (:unit_id,:organization_id,:ts) ON CONFLICT DO NOTHING"
                ),
                {"unit_id": unit_id, "organization_id": organization_id, "ts": timestamp},
            )
        connection.execute(
            text(
                "INSERT INTO reporting_unit_vessels(reporting_unit_id,vessel_id,added_by_user_id,created_at) "
                "SELECT :unit_id,id,:actor_id,:ts FROM vessels WHERE is_port_tracked=1 "
                "ON CONFLICT DO NOTHING"
            ),
            {"unit_id": unit_id, "actor_id": actor[0], "ts": timestamp},
        )

        connection.execute(
            text(
                "UPDATE import_jobs SET reporting_unit_id=:unit_id WHERE reporting_unit_id IS NULL "
                "AND organization_id = ANY(:ids)"
            ),
            {"unit_id": unit_id, "ids": organization_ids},
        )
        connection.execute(
            text(
                "UPDATE report_adjustments SET reporting_unit_id=:unit_id WHERE reporting_unit_id IS NULL "
                "AND (organization_id IS NULL OR organization_id = ANY(:ids))"
            ),
            {"unit_id": unit_id, "ids": organization_ids},
        )
        connection.execute(
            text("UPDATE sync_jobs SET reporting_unit_id=:unit_id WHERE reporting_unit_id IS NULL"),
            {"unit_id": unit_id},
        )
        connection.execute(
            text(
                "INSERT INTO audit_events"
                "(entity_type,entity_id,action,summary,actor_user_id,reporting_unit_id,correlation_id,created_at) "
                "VALUES ('REPORTING_UNIT',:unit_id,'LEGACY_BOOTSTRAP',:summary,:actor_id,:unit_id,'',:ts)"
            ),
            {
                "unit_id": unit_id,
                "summary": f"Bootstrap {args.unit_code}: {len(organization_ids)} organizations, {len(staff_rows)} staff",
                "actor_id": actor[0],
                "ts": timestamp,
            },
        )

        after = {
            "units": scalar(connection, "SELECT count(*) FROM reporting_units"),
            "memberships": scalar(connection, "SELECT count(*) FROM reporting_unit_users"),
            "organization_links": scalar(connection, "SELECT count(*) FROM reporting_unit_organizations"),
            "register_links": scalar(connection, "SELECT count(*) FROM reporting_unit_vessels"),
            "unit_register_vessels": scalar(
                connection, "SELECT count(*) FROM reporting_unit_vessels WHERE reporting_unit_id=:id", {"id": unit_id}
            ),
            "unit_import_jobs": scalar(
                connection, "SELECT count(*) FROM import_jobs WHERE reporting_unit_id=:id", {"id": unit_id}
            ),
            "unit_adjustments": scalar(
                connection, "SELECT count(*) FROM report_adjustments WHERE reporting_unit_id=:id", {"id": unit_id}
            ),
            "unit_sync_jobs": scalar(
                connection, "SELECT count(*) FROM sync_jobs WHERE reporting_unit_id=:id", {"id": unit_id}
            ),
        }

        result = {
            "mode": "APPLY" if args.apply else "DRY_RUN",
            "database": engine.url.database,
            "revision": revision,
            "unit": {"id": unit_id, "name": args.unit_name, "code": args.unit_code, "created": bool(created_unit)},
            "staff": [username for username, _ in staff_rows],
            "organization_ids": organization_ids,
            "before": before,
            "after": after,
        }
        if args.apply:
            transaction.commit()
        else:
            transaction.rollback()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception:
        transaction.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
