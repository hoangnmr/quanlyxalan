"""port operations phase 1 — berth fee / cargo ops / cancel-request / staff_function

Nền dữ liệu cho luồng xử lý tại cảng (Bảo vệ / Giao nhận / Hủy phiếu), xem
ROADMAP_PORT_OPERATIONS.md. Không đổi hành vi hiện có — chỉ thêm cột.

ATB/ATD thực tế TÁI DÙNG declarations.actual_arrival_at / actual_departure_at
đã có từ trước (không tạo cột mới ở đây — xem finding #1 trong roadmap).

Revision ID: u20f0f000020
Revises: t19f0f000019
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa


revision = "u20f0f000020"
down_revision = "t19f0f000019"
branch_labels = None
depends_on = None


DECLARATION_COLUMNS = (
    ("berth_fee_status", "VARCHAR NOT NULL DEFAULT 'PENDING'"),
    ("berth_fee_confirmed_at", "VARCHAR"),
    ("berth_fee_confirmed_by_user_id", "INTEGER REFERENCES users (id)"),
    ("unload_status", "VARCHAR NOT NULL DEFAULT 'PENDING'"),
    ("unload_is_adhoc", "INTEGER NOT NULL DEFAULT 0"),
    ("load_status", "VARCHAR NOT NULL DEFAULT 'PENDING'"),
    ("load_is_adhoc", "INTEGER NOT NULL DEFAULT 0"),
    ("cancel_requested_at", "VARCHAR"),
    ("cancel_requested_by_user_id", "INTEGER REFERENCES users (id)"),
)

DECLARATION_CHECKS = (
    ("ck_decl_berth_fee_status", "berth_fee_status IN ('PENDING', 'CONFIRMED')"),
    ("ck_decl_unload_status", "unload_status IN ('PENDING', 'CONFIRMED')"),
    ("ck_decl_load_status", "load_status IN ('PENDING', 'CONFIRMED')"),
)

RU_USER_CHECK = (
    "ck_ru_user_staff_function",
    "staff_function IS NULL OR staff_function IN ('SECURITY', 'CARGO_OPS')",
)


def _has_table(connection, name: str) -> bool:
    return sa.inspect(connection).has_table(name)


def upgrade() -> None:
    connection = op.get_bind()

    if _has_table(connection, "declarations"):
        decl_columns = {c["name"] for c in sa.inspect(connection).get_columns("declarations")}
        for name, ddl_type in DECLARATION_COLUMNS:
            if name not in decl_columns:
                op.execute(f"ALTER TABLE declarations ADD COLUMN {name} {ddl_type}")
        decl_checks = {
            c["name"] for c in sa.inspect(connection).get_check_constraints("declarations")
        }
        for name, expr in DECLARATION_CHECKS:
            if name not in decl_checks:
                op.execute(f"ALTER TABLE declarations ADD CONSTRAINT {name} CHECK ({expr})")

    if _has_table(connection, "reporting_unit_users"):
        ru_columns = {c["name"] for c in sa.inspect(connection).get_columns("reporting_unit_users")}
        if "staff_function" not in ru_columns:
            op.execute("ALTER TABLE reporting_unit_users ADD COLUMN staff_function VARCHAR")
        ru_checks = {
            c["name"] for c in sa.inspect(connection).get_check_constraints("reporting_unit_users")
        }
        check_name, check_expr = RU_USER_CHECK
        if check_name not in ru_checks:
            op.execute(f"ALTER TABLE reporting_unit_users ADD CONSTRAINT {check_name} CHECK ({check_expr})")


def downgrade() -> None:
    connection = op.get_bind()

    if _has_table(connection, "reporting_unit_users"):
        ru_columns = {c["name"] for c in sa.inspect(connection).get_columns("reporting_unit_users")}
        if "staff_function" in ru_columns:
            check_name, _ = RU_USER_CHECK
            op.execute(f"ALTER TABLE reporting_unit_users DROP CONSTRAINT IF EXISTS {check_name}")
            with op.batch_alter_table("reporting_unit_users") as batch_op:
                batch_op.drop_column("staff_function")

    if _has_table(connection, "declarations"):
        decl_columns = {c["name"] for c in sa.inspect(connection).get_columns("declarations")}
        for name, expr in DECLARATION_CHECKS:
            op.execute(f"ALTER TABLE declarations DROP CONSTRAINT IF EXISTS {name}")
        with op.batch_alter_table("declarations") as batch_op:
            for name, _ in DECLARATION_COLUMNS:
                if name in decl_columns:
                    batch_op.drop_column(name)
