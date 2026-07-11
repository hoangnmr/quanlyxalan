from __future__ import annotations

import io
import re
import zipfile
from datetime import date, datetime
from html import escape
from typing import Any
from xml.etree import ElementTree as ET


NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}


def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref.upper())
    value = 0
    for char in letters.group(0) if letters else "A":
        value = value * 26 + ord(char) - 64
    return value


def read_workbook(content: bytes) -> dict[str, dict[str, Any]]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("m:si", NS):
                shared.append("".join(node.text or "" for node in item.iter() if node.tag.endswith("}t")))

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {node.attrib["Id"]: node.attrib["Target"] for node in rels}
        sheets: dict[str, dict[str, Any]] = {}
        for sheet in workbook.find("m:sheets", NS) or []:
            rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rel_map[rel_id].lstrip("/")
            path = target if target.startswith("xl/") else f"xl/{target}"
            root = ET.fromstring(archive.read(path))
            cells: dict[str, Any] = {}
            for cell in root.findall(".//m:c", NS):
                ref = cell.attrib.get("r", "")
                kind = cell.attrib.get("t")
                value_node = cell.find("m:v", NS)
                inline = cell.find("m:is", NS)
                raw = value_node.text if value_node is not None else None
                if kind == "s" and raw is not None:
                    value: Any = shared[int(raw)]
                elif kind == "inlineStr" and inline is not None:
                    value = "".join(node.text or "" for node in inline.iter() if node.tag.endswith("}t"))
                elif kind == "b":
                    value = raw == "1"
                else:
                    value = raw
                    if raw is not None:
                        try:
                            value = float(raw) if "." in raw else int(raw)
                        except ValueError:
                            pass
                if ref:
                    cells[ref] = value
            sheets[sheet.attrib["name"]] = cells
        return sheets


def vessel_rows(sheets: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sheet = sheets.get("HỒ SƠ PHƯƠNG TIỆN") or sheets.get("HO SO PHUONG TIEN")
    if not sheet:
        raise ValueError("Khong tim thay sheet HO SO PHUONG TIEN")
    organization = {
        "name": sheet.get("B4") or sheet.get("C4") or "Khach hang import",
        "tax_code": sheet.get("B5") or sheet.get("C5") or "",
        "address": sheet.get("B6") or sheet.get("C6") or "",
        "contact_name": sheet.get("B7") or sheet.get("C7") or "",
        "phone": sheet.get("B8") or sheet.get("C8") or "",
    }
    keys = [
        "name", "registration_no", "registry_or_imo", "vessel_type", "vessel_class",
        "shell_material", "build_year", "length_m", "width_m", "side_height_m", "draft_m",
        "deadweight_tons", "gross_tonnage", "engine_power_cv", "cargo_capacity_tons",
        "container_capacity_teu", "passenger_capacity", "min_crew", "safety_certificate_no",
        "certificate_issue_date", "certificate_expiry_date", "notes", "updated_at",
    ]
    rows: list[dict[str, Any]] = []
    for row_no in range(11, 1001):
        values = [sheet.get(f"{chr(66 + i)}{row_no}") for i in range(23)]
        if not any(value not in (None, "") for value in values):
            continue
        row = dict(zip(keys, values))
        if row.get("name") and row.get("registration_no"):
            rows.append(row)
    return organization, rows


DECLARATION_CELLS = {
    "company_name": "C6", "declaration_date": "C7", "vessel_name": "C10",
    "registration_no": "C11", "vessel_type": "C12", "vessel_class": "C13",
    "length_m": "C14", "deadweight_tons": "C15", "gross_tonnage": "C16",
    "certificate_expiry_date": "C17", "crew_count": "C18", "passenger_count": "C19",
    "last_port": "C22", "working_port": "C23", "destination_port": "C24",
    "eta": "C25", "etd": "C26", "master_name": "C57", "master_phone": "C58",
}


def declaration_row(sheets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sheet = sheets.get("KHAI BÁO") or sheets.get("KHAI BAO")
    if not sheet:
        raise ValueError("Khong tim thay sheet KHAI BAO")
    result = {key: sheet.get(cell) for key, cell in DECLARATION_CELLS.items()}
    result["unload"] = _cargo_from_cells(sheet, 30, 31, 32, 33)
    result["load"] = _cargo_from_cells(sheet, 44, 45, 46, 47)
    return result


def _cargo_from_cells(sheet: dict[str, Any], type_row: int, movement_row: int, name_row: int, count_row: int) -> dict[str, Any]:
    return {
        "cargo_type": sheet.get(f"C{type_row}") or "",
        "movement_type": sheet.get(f"C{movement_row}") or "",
        "cargo_name": sheet.get(f"C{name_row}") or "",
        "cont20_full": sheet.get(f"C{count_row}") or 0,
        "cont20_empty": sheet.get(f"C{count_row + 1}") or 0,
        "cont40_full": sheet.get(f"C{count_row + 2}") or 0,
        "cont40_empty": sheet.get(f"C{count_row + 3}") or 0,
        "tons": sheet.get(f"C{count_row + 7}") or 0,
    }


def make_xlsx(title: str, headers: list[str], rows: list[list[Any]]) -> bytes:
    all_rows = [[title], [], headers, *rows]
    sheet_rows = []
    for row_number, values in enumerate(all_rows, 1):
        cells = []
        for column_number, value in enumerate(values, 1):
            if value is None:
                continue
            ref = f"{_column_name(column_number)}{row_number}"
            if isinstance(value, (int, float)):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
        sheet_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types())
        archive.writestr("_rels/.rels", _root_rels())
        archive.writestr("xl/workbook.xml", _workbook())
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels())
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return output.getvalue()


def _column_name(index: int) -> str:
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _content_types() -> str:
    return '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'


def _root_rels() -> str:
    return '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'


def _workbook() -> str:
    return '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Bao cao" sheetId="1" r:id="rId1"/></sheets></workbook>'


def _workbook_rels() -> str:
    return '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'


def excel_date(value: Any) -> Any:
    if isinstance(value, (int, float)) and value > 20000:
        return date.fromordinal(date(1899, 12, 30).toordinal() + int(value)).isoformat()
    return value
