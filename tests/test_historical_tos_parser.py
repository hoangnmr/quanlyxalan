from __future__ import annotations

import io

import pytest
from openpyxl import Workbook

from backend.historical_tos_parser import HistoricalWorkbookError, parse_workbook


def _xlsx(headers: dict[int, str], rows: list[dict[int, object]], *, title: str = "Anything") -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title
    for column, value in headers.items():
        sheet.cell(1, column, value)
    for row_number, row in enumerate(rows, 2):
        for column, value in row.items():
            sheet.cell(row_number, column, value)
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_detects_berth_by_headers_and_preserves_leading_zero_voyage():
    content = _xlsx(
        {2: "Năm", 3: "Chuyến", 5: "Tên tàu", 8: "Mã bến", 20: "ATB", 23: "ATD"},
        [{2: "2026", 3: "0007", 5: "SÀ LAN-01", 8: "K12", 20: "18/07/2026 08:30:00", 23: "18/07/2026 13:00:00"}],
        title="Renamed by user",
    )
    parsed = parse_workbook(content)
    assert parsed.source_kind == "tos_berth_call"
    assert parsed.reporting_period == "2026-07"
    assert parsed.rows[0]["voyage_number_raw"] == "0007"
    assert parsed.rows[0]["call_key_normalized"].endswith("|2026|7")
    assert parsed.rows[0]["actual_berthing_at"] == "2026-07-18T08:30:00"


def test_cargo_dimensions_are_independent_and_hidden_rows_are_read():
    content = _xlsx(
        {3: "Kích cỡ", 5: "F/E", 17: "Tên sà lan | Năm | Chuyến", 18: "Trọng lượng", 20: "Hàng nội/ ngoại", 23: "Phương án"},
        [{3: "40HC", 5: "E", 17: "SÀ LAN-01 | 2026 | 0007", 18: "4.00", 20: "Hàng nội", 23: "Hạ bãi"}],
    )
    parsed = parse_workbook(content)
    row = parsed.rows[0]
    assert row["teu_factor"] == 2
    assert row["full_empty_code_raw"] == "E"
    assert row["weight_tonnes"] == 4.0
    assert row["derived_direction"] == "unload"
    assert row["trade_scope"] == "domestic"


def test_unknown_size_and_invalid_weight_enter_review_not_zero():
    content = _xlsx(
        {3: "Kích cỡ", 5: "F/E", 17: "Tên sà lan | Năm | Chuyến", 18: "Trọng lượng", 20: "Hàng nội/ ngoại", 23: "Phương án"},
        [{3: "45HC", 5: "F", 17: "A | 2026 | 1", 18: "n/a", 20: "Hàng ngoại", 23: "Lấy Nguyên"}],
    )
    row = parse_workbook(content).rows[0]
    assert row["validation_status"] == "REVIEW"
    assert row["teu_factor"] is None
    assert row["weight_tonnes"] is None
    assert row["weight_state"] == "INVALID"


def test_unknown_workbook_fails_closed():
    with pytest.raises(HistoricalWorkbookError, match="Không nhận diện"):
        parse_workbook(_xlsx({1: "unrelated"}, [{1: "value"}]))
