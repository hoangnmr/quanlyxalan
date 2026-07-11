from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
from datetime import date, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import audit, cargo, connection, decode_declaration, init_db, now_iso, rows_to_dicts
from xlsx_io import declaration_row, excel_date, make_xlsx, read_workbook, vessel_rows


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
MAX_BODY = 12 * 1024 * 1024

VESSEL_TYPES = ["Tàu hàng khô", "Tàu container", "Tàu hàng lỏng/dầu", "Tàu khách", "Tàu kéo/đẩy", "Sà lan tự hành", "Sà lan", "Khác"]
VESSEL_CLASSES = ["VR-SI", "VR-SII", "VR-SIII", "Khác"]
SHELL_MATERIALS = ["Thép", "Gỗ", "Composite/GRP", "Xi măng lưới thép", "Nhôm", "Khác"]
CARGO_TYPES = ["Container", "Hàng khô", "Hàng lỏng"]
UNLOAD_MOVEMENTS = ["Nội địa", "Nhập khẩu", "Chuyển tải", "Quá cảnh có bốc dỡ", "Quá cảnh không bốc dỡ"]
LOAD_MOVEMENTS = ["Nội địa", "Xuất khẩu"]


class ApiError(Exception):
    def __init__(self, status: int, message: str, fields: dict[str, str] | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.fields = fields or {}


def as_number(value: Any, integer: bool = False) -> int | float | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value)) if integer else float(value)
    except (TypeError, ValueError):
        return None


def clean_date(value: Any) -> str | None:
    value = excel_date(value)
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec="minutes")
    return str(value)


def validate_required(payload: dict[str, Any], names: list[str]) -> None:
    missing = {name: "Bắt buộc nhập" for name in names if not str(payload.get(name) or "").strip()}
    if missing:
        raise ApiError(422, "Vui lòng hoàn tất các trường bắt buộc.", missing)


def upsert_organization(db: Any, payload: dict[str, Any]) -> int:
    name = str(payload.get("name") or payload.get("company_name") or "").strip()
    if not name:
        raise ApiError(422, "Tên doanh nghiệp là bắt buộc.", {"name": "Bắt buộc nhập"})
    row = db.execute("SELECT id FROM organizations WHERE name = ?", (name,)).fetchone()
    values = (
        str(payload.get("tax_code") or ""), str(payload.get("address") or ""),
        str(payload.get("contact_name") or ""), str(payload.get("contact_role") or ""),
        str(payload.get("phone") or ""), str(payload.get("email") or ""), now_iso(),
    )
    if row:
        db.execute(
            "UPDATE organizations SET tax_code=?,address=?,contact_name=?,contact_role=?,phone=?,email=?,updated_at=? WHERE id=?",
            (*values, row["id"]),
        )
        return int(row["id"])
    cursor = db.execute(
        "INSERT INTO organizations(name,tax_code,address,contact_name,contact_role,phone,email,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (name, *values[:-1], values[-1], values[-1]),
    )
    return int(cursor.lastrowid)


def save_vessel(db: Any, payload: dict[str, Any], imported: bool = False) -> dict[str, Any]:
    validate_required(payload, ["name", "registration_no", "vessel_type", "vessel_class"])
    organization_id = payload.get("organization_id")
    if not organization_id and payload.get("organization"):
        organization_id = upsert_organization(db, payload["organization"])
    columns = [
        "organization_id", "name", "registration_no", "registry_or_imo", "vessel_type", "vessel_class",
        "shell_material", "build_year", "length_m", "width_m", "side_height_m", "draft_m",
        "deadweight_tons", "gross_tonnage", "engine_power_cv", "cargo_capacity_tons",
        "container_capacity_teu", "passenger_capacity", "min_crew", "safety_certificate_no",
        "certificate_issue_date", "certificate_expiry_date", "notes",
    ]
    integer_fields = {"build_year", "passenger_capacity", "min_crew"}
    numeric_fields = integer_fields | {"length_m", "width_m", "side_height_m", "draft_m", "deadweight_tons", "gross_tonnage", "engine_power_cv", "cargo_capacity_tons", "container_capacity_teu"}
    normalized = dict(payload)
    normalized["organization_id"] = as_number(organization_id, True)
    for key in numeric_fields:
        normalized[key] = as_number(payload.get(key), key in integer_fields)
    for key in ("certificate_issue_date", "certificate_expiry_date"):
        normalized[key] = clean_date(payload.get(key))
    for key in columns:
        if key not in normalized:
            normalized[key] = "" if key not in numeric_fields and key != "organization_id" else None
    existing = db.execute("SELECT id FROM vessels WHERE registration_no = ?", (normalized["registration_no"],)).fetchone()
    stamp = now_iso()
    if existing:
        assignments = ",".join(f"{name}=?" for name in columns)
        db.execute(f"UPDATE vessels SET {assignments},updated_at=? WHERE id=?", (*[normalized[name] for name in columns], stamp, existing["id"]))
        vessel_id = int(existing["id"])
        action = "IMPORT_UPDATE" if imported else "UPDATE"
    else:
        placeholders = ",".join("?" for _ in columns)
        cursor = db.execute(
            f"INSERT INTO vessels({','.join(columns)},created_at,updated_at) VALUES({placeholders},?,?)",
            (*[normalized[name] for name in columns], stamp, stamp),
        )
        vessel_id = int(cursor.lastrowid)
        action = "IMPORT_CREATE" if imported else "CREATE"
    audit(db, "VESSEL", vessel_id, action, f"{normalized['name']} / {normalized['registration_no']}")
    return dict(db.execute("SELECT * FROM vessels WHERE id=?", (vessel_id,)).fetchone())


def declaration_payload(payload: dict[str, Any]) -> dict[str, Any]:
    validate_required(payload, ["company_name", "declaration_date", "vessel_name", "registration_no", "vessel_type", "vessel_class", "last_port", "working_port", "eta", "etd", "master_name", "master_phone"])
    eta = clean_date(payload.get("eta")) or ""
    etd = clean_date(payload.get("etd")) or ""
    if eta and etd and eta >= etd:
        raise ApiError(422, "Thời gian rời cảng phải sau thời gian đến cảng.", {"etd": "Phải sau thời gian đến"})
    unload = cargo(payload.get("unload"))
    load = cargo(payload.get("load"))
    return {
        **payload,
        "declaration_date": clean_date(payload.get("declaration_date")) or date.today().isoformat(),
        "eta": eta,
        "etd": etd,
        "certificate_expiry_date": clean_date(payload.get("certificate_expiry_date")),
        "length_m": as_number(payload.get("length_m")),
        "deadweight_tons": as_number(payload.get("deadweight_tons")),
        "gross_tonnage": as_number(payload.get("gross_tonnage")),
        "crew_count": as_number(payload.get("crew_count"), True) or 0,
        "passenger_count": as_number(payload.get("passenger_count"), True) or 0,
        "unload": unload,
        "load": load,
    }


def save_declaration(db: Any, payload: dict[str, Any], submit: bool = False, imported: bool = False) -> dict[str, Any]:
    data = declaration_payload(payload)
    organization_id = payload.get("organization_id") or upsert_organization(db, {"name": data["company_name"]})
    vessel_id = payload.get("vessel_id")
    existing = db.execute("SELECT id FROM declarations WHERE id=?", (payload.get("id"),)).fetchone() if payload.get("id") else None
    stamp = now_iso()
    reference = str(payload.get("reference_no") or f"TT-{datetime.now():%Y%m%d-%H%M%S%f}")
    status = "SUBMITTED" if submit else str(payload.get("status") or "DRAFT")
    columns = [
        "reference_no", "status", "organization_id", "vessel_id", "declaration_date", "company_name",
        "vessel_name", "registration_no", "vessel_type", "vessel_class", "length_m", "deadweight_tons",
        "gross_tonnage", "certificate_expiry_date", "crew_count", "passenger_count", "last_port",
        "working_port", "destination_port", "eta", "etd", "unload_json", "load_json", "master_name", "master_phone",
    ]
    values = {
        **data, "reference_no": reference, "status": status, "organization_id": organization_id,
        "vessel_id": as_number(vessel_id, True), "unload_json": json.dumps(data["unload"], ensure_ascii=False),
        "load_json": json.dumps(data["load"], ensure_ascii=False),
    }
    if existing:
        if db.execute("SELECT status FROM declarations WHERE id=?", (existing["id"],)).fetchone()["status"] == "SUBMITTED":
            raise ApiError(409, "Phiếu đã nộp không thể sửa. Hãy tạo phiếu điều chỉnh mới.")
        db.execute(
            f"UPDATE declarations SET {','.join(f'{name}=?' for name in columns)},submitted_at=?,updated_at=? WHERE id=?",
            (*[values.get(name, "") for name in columns], stamp if submit else None, stamp, existing["id"]),
        )
        declaration_id = int(existing["id"])
        action = "SUBMIT" if submit else "UPDATE_DRAFT"
    else:
        cursor = db.execute(
            f"INSERT INTO declarations({','.join(columns)},submitted_at,created_at,updated_at) VALUES({','.join('?' for _ in columns)},?,?,?)",
            (*[values.get(name, "") for name in columns], stamp if submit else None, stamp, stamp),
        )
        declaration_id = int(cursor.lastrowid)
        action = "IMPORT" if imported else ("SUBMIT" if submit else "CREATE_DRAFT")
    audit(db, "DECLARATION", declaration_id, action, reference)
    return decode_declaration(db.execute("SELECT * FROM declarations WHERE id=?", (declaration_id,)).fetchone())


class Handler(BaseHTTPRequestHandler):
    server_version = "TanThuanDeclaration/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{datetime.now():%H:%M:%S}] {self.address_string()} {fmt % args}")

    def do_GET(self) -> None:
        try:
            self.route_get()
        except ApiError as error:
            self.json(error.status, {"error": error.message, "fields": error.fields})
        except Exception as error:
            self.json(500, {"error": "Lỗi máy chủ.", "detail": str(error)})

    def do_POST(self) -> None:
        try:
            self.route_post()
        except ApiError as error:
            self.json(error.status, {"error": error.message, "fields": error.fields})
        except Exception as error:
            self.json(500, {"error": "Lỗi máy chủ.", "detail": str(error)})

    def route_get(self) -> None:
        parsed = urlparse(self.path)
        path, query = parsed.path, parse_qs(parsed.query)
        if path == "/api/health":
            return self.json(200, {"status": "ok", "database": "sqlite", "version": "0.1.0"})
        if path == "/api/catalogs":
            return self.json(200, {"vesselTypes": VESSEL_TYPES, "vesselClasses": VESSEL_CLASSES, "shellMaterials": SHELL_MATERIALS, "cargoTypes": CARGO_TYPES, "unloadMovements": UNLOAD_MOVEMENTS, "loadMovements": LOAD_MOVEMENTS})
        if path == "/api/dashboard":
            with connection() as db:
                stats = {
                    "vessels": db.execute("SELECT COUNT(*) FROM vessels").fetchone()[0],
                    "drafts": db.execute("SELECT COUNT(*) FROM declarations WHERE status='DRAFT'").fetchone()[0],
                    "submitted": db.execute("SELECT COUNT(*) FROM declarations WHERE status='SUBMITTED'").fetchone()[0],
                    "arrivingToday": db.execute("SELECT COUNT(*) FROM declarations WHERE substr(eta,1,10)=?", (date.today().isoformat(),)).fetchone()[0],
                }
                recent = [decode_declaration(row) for row in db.execute("SELECT * FROM declarations ORDER BY updated_at DESC LIMIT 8")]
            return self.json(200, {"stats": stats, "recent": recent})
        if path == "/api/organizations":
            with connection() as db:
                return self.json(200, rows_to_dicts(db.execute("SELECT * FROM organizations ORDER BY name")))
        if path == "/api/vessels":
            with connection() as db:
                rows = db.execute("SELECT v.*,o.name organization_name FROM vessels v LEFT JOIN organizations o ON o.id=v.organization_id ORDER BY v.updated_at DESC")
                return self.json(200, rows_to_dicts(rows))
        if path == "/api/declarations":
            status = (query.get("status") or [""])[0]
            sql, params = "SELECT * FROM declarations", []
            if status:
                sql, params = sql + " WHERE status=?", [status]
            with connection() as db:
                return self.json(200, [decode_declaration(row) for row in db.execute(sql + " ORDER BY updated_at DESC", params)])
        if path == "/api/suggestions":
            field = (query.get("field") or [""])[0]
            allowed = {"last_port", "working_port", "destination_port", "master_name", "master_phone", "company_name"}
            if field not in allowed:
                raise ApiError(400, "Trường gợi ý không hợp lệ.")
            with connection() as db:
                values = [row[0] for row in db.execute(f"SELECT {field} FROM declarations WHERE {field}<>'' GROUP BY {field} ORDER BY MAX(updated_at) DESC LIMIT 20")]
            return self.json(200, values)
        if path.startswith("/api/reports/"):
            return self.report(path.rsplit("/", 1)[-1], query)
        return self.static(path)

    def route_post(self) -> None:
        parsed = urlparse(self.path)
        path, query = parsed.path, parse_qs(parsed.query)
        if path == "/api/organizations":
            payload = self.body_json()
            with connection() as db:
                org_id = upsert_organization(db, payload)
                audit(db, "ORGANIZATION", org_id, "UPSERT", str(payload.get("name") or ""))
                return self.json(201, dict(db.execute("SELECT * FROM organizations WHERE id=?", (org_id,)).fetchone()))
        if path == "/api/vessels":
            with connection() as db:
                return self.json(201, save_vessel(db, self.body_json()))
        if path == "/api/declarations":
            submit = (query.get("submit") or ["false"])[0].lower() == "true"
            with connection() as db:
                return self.json(201, save_declaration(db, self.body_json(), submit=submit))
        if path in ("/api/import/vessels", "/api/import/declaration"):
            content = self.body_bytes()
            sheets = read_workbook(content)
            with connection() as db:
                if path.endswith("vessels"):
                    organization, rows = vessel_rows(sheets)
                    org_id = upsert_organization(db, organization)
                    accepted, errors = [], []
                    for index, row in enumerate(rows, 1):
                        try:
                            row["organization_id"] = org_id
                            accepted.append(save_vessel(db, row, imported=True))
                        except Exception as error:
                            errors.append({"row": index, "error": str(error)})
                    return self.json(200, {"accepted": len(accepted), "rejected": errors})
                row = declaration_row(sheets)
                result = save_declaration(db, row, imported=True)
                return self.json(200, {"accepted": 1, "declaration": result})
        raise ApiError(404, "Không tìm thấy API.")

    def report(self, kind: str, query: dict[str, list[str]]) -> None:
        start = (query.get("from") or ["1900-01-01"])[0]
        end = (query.get("to") or ["2999-12-31"])[0]
        with connection() as db:
            items = [decode_declaration(row) for row in db.execute("SELECT * FROM declarations WHERE status='SUBMITTED' AND substr(eta,1,10) BETWEEN ? AND ? ORDER BY eta", (start, end))]
        if kind == "appendix-1":
            headers = ["TT", "Tên PT", "Số đăng ký", "Cấp PT", "Công dụng", "Hết hạn GCN", "Khả năng tấn/TEU", "Sức chở khách", "Vị trí đến", "Thời gian đến", "Vị trí rời", "Thời gian rời", "Hàng dỡ", "Hàng xếp", "Thuyền viên/Hành khách", "Thuyền trưởng/SĐT"]
            rows = [[i, d["vessel_name"], d["registration_no"], d["vessel_class"], d["vessel_type"], d["certificate_expiry_date"], f"{d.get('deadweight_tons') or 0} t / {max(d['unload']['teu'], d['load']['teu'])} TEU", d["passenger_count"], d["working_port"], d["eta"], d["working_port"], d["etd"], cargo_text(d["unload"]), cargo_text(d["load"]), f"{d['crew_count']} / {d['passenger_count']}", f"{d['master_name']} / {d['master_phone']}"] for i, d in enumerate(items, 1)]
            title = "PHỤ LỤC 1 - KẾ HOẠCH HOẠT ĐỘNG CỦA PTTND"
        elif kind == "appendix-2":
            headers = ["Chỉ tiêu", "Container tấn", "Container TEU", "Hàng khô tấn", "Hàng lỏng tấn", "Hàng XNK tấn", "Lượt tàu", "Lượt tàu khách", "Lượt khách"]
            totals = summarize(items)
            rows = [["Tổng kỳ báo cáo", totals["container_tons"], totals["container_teu"], totals["dry_tons"], totals["liquid_tons"], totals["foreign_tons"], len(items), totals["passenger_calls"], totals["passengers"]]]
            title = "PHỤ LỤC 2 - KHỐI LƯỢNG HÀNG HÓA, LƯỢT TÀU, HÀNH KHÁCH"
        elif kind == "appendix-3":
            headers = ["STT", "Tên PTTND", "Số đăng ký", "Loại PT", "Cấp PTTND", "Chiều dài", "Trọng tải", "Dung tích", "Dỡ - loại hình", "Dỡ - tấn", "Dỡ - TEU", "Dỡ - TEU rỗng", "Xếp - loại hình", "Xếp - tấn", "Xếp - TEU", "Xếp - TEU rỗng", "Hành khách", "Tên hàng", "Cảng rời cuối", "Cảng làm hàng", "Cảng đích", "Ngày đến", "Ngày rời", "Đại lý PTTND"]
            rows = [[i, d["vessel_name"], d["registration_no"], d["vessel_type"], d["vessel_class"], d["length_m"], d["deadweight_tons"], d["gross_tonnage"], d["unload"]["movement_type"], d["unload"]["tons"], d["unload"]["teu"], d["unload"]["empty_teu"], d["load"]["movement_type"], d["load"]["tons"], d["load"]["teu"], d["load"]["empty_teu"], d["passenger_count"], " / ".join(filter(None, [d["unload"]["cargo_name"], d["load"]["cargo_name"]])), d["last_port"], d["working_port"], d["destination_port"], d["eta"], d["etd"], d["company_name"]] for i, d in enumerate(items, 1)]
            title = "PHỤ LỤC 3 - BÁO CÁO CHI TIẾT PTTND RA, VÀO CẢNG BIỂN"
        else:
            raise ApiError(404, "Loại báo cáo không hợp lệ.")
        content = make_xlsx(title, headers, rows)
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.send_header("Content-Disposition", f'attachment; filename="{kind}.xlsx"')
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def body_bytes(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY:
            raise ApiError(413, "File rỗng hoặc vượt quá 12 MB.")
        return self.rfile.read(length)

    def body_json(self) -> dict[str, Any]:
        try:
            return json.loads(self.body_bytes().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(400, "Dữ liệu JSON không hợp lệ.")

    def json(self, status: int, payload: Any) -> None:
        content = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def static(self, path: str) -> None:
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (FRONTEND / relative).resolve()
        if FRONTEND.resolve() not in target.parents or not target.is_file():
            target = FRONTEND / "index.html"
        content = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def cargo_text(item: dict[str, Any]) -> str:
    details = [item.get("cargo_type"), item.get("cargo_name")]
    if item.get("teu"):
        details.append(f"{item['total_containers']} cont / {item['teu']} TEU")
    if item.get("tons"):
        details.append(f"{item['tons']} tấn")
    return " - ".join(str(value) for value in details if value)


def summarize(items: list[dict[str, Any]]) -> dict[str, Any]:
    result = {"container_tons": 0.0, "container_teu": 0, "dry_tons": 0.0, "liquid_tons": 0.0, "foreign_tons": 0.0, "passenger_calls": 0, "passengers": 0}
    for declaration in items:
        if declaration.get("passenger_count", 0) > 0:
            result["passenger_calls"] += 1
            result["passengers"] += declaration["passenger_count"]
        for item in (declaration["unload"], declaration["load"]):
            if item["cargo_type"] == "Container":
                result["container_tons"] += item["tons"]
                result["container_teu"] += item["teu"]
            elif item["cargo_type"] == "Hàng khô":
                result["dry_tons"] += item["tons"]
            elif item["cargo_type"] == "Hàng lỏng":
                result["liquid_tons"] += item["tons"]
            if item["movement_type"] in ("Nhập khẩu", "Xuất khẩu"):
                result["foreign_tons"] += item["tons"]
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Tan Thuan Port declaration server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()
    init_db()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Server ready at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
