# Codex Desktop Spreadsheet Regression Recheck Result — 2026-07-17

## Kết luận

| Gate | Kết quả |
|---|---|
| REG-01 | **CLOSED** |
| Positive PL.03 visual gate | **PASS** |
| Operational PL.03 guardrail | **PASS** |
| Overall Spreadsheet implementation gate | **PASS** |
| Live business data evidence | **NOT PROVABLE** |

Hai workbook kiểm tra đều đạt các điều kiện của work order. Positive fixture chứng minh implementation có thể render đầy đủ hai hoạt động trong cùng một dòng sau khi chiều cao dòng được tăng động. Operational workbook chứng minh thay đổi đó không tạo dữ liệu hoạt động giả hoặc làm vỡ bố cục bộ 47 Salan. Fixture synthetic **không** phải bằng chứng rằng dữ liệu nghiệp vụ thực của khách hàng đầy đủ hoặc đúng.

## Phạm vi và công cụ

- Work order: `docs/WORK_ORDER_CODEX_DESKTOP_SPREADSHEET_REGRESSION_RECHECK_20260717.md`.
- Workbook positive: `outputs/appendix-positive-fixture-20260717/PL.03_positive_fixture.xlsx`.
- Workbook guardrail: `outputs/appendix-operational-review-20260717/PL.03_operational_review.xlsx`.
- Đã đọc đối chiếu: `docs/CODEX_DESKTOP_SPREADSHEET_REGRESSION_RESULT_20260717.md`, `docs/CANONICAL_DATA_AND_APPENDIX_ASSURANCE_ROADMAP_20260716.md`, `docs/AGENT_HANDOFF.md`.
- Skill: **Spreadsheets**.
- `load_workspace_dependencies`: **PASS**, bundle thực tế `26.715.12143`.
- Node runtime: loader-provided Codex primary runtime.
- `@oai/artifact-tool`: import **PASS**; API reference của bundle `2.8.6+`.
- Chỉ dùng `@oai/artifact-tool` để đọc, inspect và render XLSX. Không dùng openpyxl, pandas, xlsxwriter, LibreOffice, Excel COM, unzip hoặc đọc OOXML.
- Không sửa code ứng dụng, template, workbook nguồn hoặc tài liệu hiện có; không commit/push.

Machine-readable evidence: `outputs/codex-desktop-spreadsheet-regression-recheck-20260717/pl03_recheck_inspect.json`.

## Positive fixture — PL.03_positive_fixture.xlsx

### Kiểm tra cấu trúc và dữ liệu

| Tiêu chí | Kết quả | Bằng chứng |
|---|---|---|
| Workbook mở được bằng artifact-tool | PASS | 1 sheet tên `Sheet`; file 8,348 bytes |
| Used range | PASS | `A1:AI10`, 10 hàng, đúng 35 cột |
| Thứ tự dữ liệu không lệch | PASS | Dữ liệu tĩnh ở `A10:H10`; dữ liệu hoạt động ở các cột tương ứng trong `I10:AI10` |
| Hai timestamp đến cảng | PASS | `AG10 = 2046-01-10T08:15\n2046-07-15T08:20`; tháng 1 trước tháng 7 |
| Hai timestamp rời cảng | PASS | `AH10 = 2046-01-10T16:50\n2046-07-15T17:45`; tháng 1 trước tháng 7 |
| Chiều cao dòng 10 | PASS | `108 pt`, đạt ngưỡng tối thiểu 108 pt |
| Nội dung wrap trọng yếu | PASS | `D10 = CHỞ HÀNG KHÔ HOẶC CONTAINER`; `AC10 = HÀNG NHẬP\nHÀNG XUẤT`; `AE10 = CẦU 1 - CẢNG TÂN THUẬN`; `AI10 = ĐẠI LÝ PTND A\nĐẠI LÝ PTND B`; tất cả đọc đủ trên render |
| Alignment | PASS | Các ô trọng yếu D10/AC10/AE10/AG10/AH10/AI10 được inspect là wrap, căn giữa ngang và giữa dọc |
| Border/header merge/print-layout nhìn thấy | PASS | Full render giữ nguyên khối tiêu đề nhiều tầng, đường viền và thứ tự cột; focus render không có border spill |
| Formula/display errors | PASS | Formula inspect: không có record; error search: 0 match |
| Nhãn cấm | PASS | Không tìm thấy `Teus`, `Tues`, `Quá cảng`, `sum_total` |

Các độ rộng cột trọng yếu do artifact-tool trả về: `A=6`, `B=9.5546875`, `C=6.77734375`, `D=18`, `AC=7.77734375`, `AE=8.33203125`, `AG=7.21875`, `AH=7.5546875`, `AI=8.6640625`.

### Kiểm tra trực quan

Đã xem trực tiếp 100% vùng dữ liệu và các crop sau:

1. `renders/POSITIVE_FULL_A1-AI10_S1.png` — toàn bộ `A1:AI10`; 35 cột, header nhiều tầng, merge hiển thị, border và dòng dữ liệu đều liên tục.
2. `renders/POSITIVE_LEFT_A1-L10_S2.png` — xác nhận `D10` đọc trọn loại phương tiện, không clipping hoặc tràn ô.
3. `renders/POSITIVE_MIDDLE_M1-X10_S2.png` — xác nhận vùng hàng hóa giữa sheet không lệch cột và border không vỡ.
4. `renders/POSITIVE_FOCUS_Y1-AI10_S3.png` — xác nhận `AC10`, `AE10`, `AG10`, `AH10`, `AI10` đều wrap đủ. Cả bốn timestamp ở AG10:AH10 hiển thị đầy đủ, không cắt đáy, không đè border, không tràn sang ô kế bên.

Kết quả REG-01: **CLOSED**. Hiện tượng timestamp thứ hai bị cắt đáy ở bản kiểm tra trước không còn tái hiện.

## Operational guardrail — PL.03_operational_review.xlsx

| Tiêu chí | Kết quả | Bằng chứng |
|---|---|---|
| Workbook mở được bằng artifact-tool | PASS | 1 sheet tên `Sheet`; file 14,445 bytes |
| Used range | PASS | `A1:AI56`, 56 hàng, đúng 35 cột |
| Số dòng phương tiện | PASS | `A10:A56` có 47 STT/dòng Salan |
| Registration duy nhất | PASS | 47 registration, 47 unique, 0 duplicate |
| Không có activity giả | PASS | `I10:AI56` có 0 ô nonblank |
| Dữ liệu tĩnh đúng vùng | PASS | Các trường phương tiện nằm trong `A:H`; vùng hoạt động `I:AI` trống |
| Chiều cao dòng dữ liệu | PASS | `10:56 = 66 pt`; không bị tăng ngoài nhu cầu của nội dung tĩnh |
| Wrap/alignment/border | PASS | Loại phương tiện tại cột D wrap trong ô; căn giữa và border liên tục trên full/crop render |
| Header/merge/layout | PASS | Header 35 cột giữ đúng cấu trúc; không có clipping, overlap, lệch cột hoặc border spill quan sát được |
| Formula/display errors | PASS | Formula inspect: không có record; error search: 0 match |
| Nhãn cấm | PASS | Không tìm thấy `Teus`, `Tues`, `Quá cảng`, `sum_total` |

Đã xem trực tiếp các render:

1. `renders/OPERATIONAL_FULL_A1-AI56_S1.png` — 100% `A1:AI56`, gồm toàn bộ 47 dòng; border và thứ tự cột liên tục đến dòng 56.
2. `renders/OPERATIONAL_LEFT_A1-L20_S2.png` — các dòng tĩnh đầu tiên, wrap cột D, registration và số liệu kỹ thuật không bị clipping/lệch cột.
3. `renders/OPERATIONAL_FOCUS_Y1-AI20_S2.png` — header cuối sheet nguyên vẹn; vùng activity của các dòng quan sát trống và không phát sinh giá trị giả.

Operational guardrail: **PASS**.

## Phân biệt implementation với bằng chứng nghiệp vụ

- **Implementation PASS:** cấu trúc 35 cột, mapping vị trí, wrap, row height động, border, alignment và render của hai workbook đều đạt; positive fixture thể hiện đúng hai hoạt động synthetic.
- **Operational guardrail PASS:** 47 Salan được giữ nguyên, unique registration và không có dữ liệu activity giả trong `I10:AI56`.
- **Live business data NOT PROVABLE:** operational workbook trống activity; positive fixture là dữ liệu kiểm thử synthetic. Vì vậy không thể suy diễn rằng database/UI thực tế đã có đầy đủ lượt đến/rời, cảng, hàng hóa, hành khách hoặc rằng dữ liệu khách hàng thật đã được duyệt đúng.

## Giới hạn chưa kiểm chứng

- Permitted artifact-tool facade không cung cấp danh sách địa chỉ merge trực tiếp trong inspect output của lần chạy này. Merge/header được xác minh bằng full render và crop, không bằng một danh sách merge-range machine-readable.
- Không có nguồn live/database snapshot hay audit approval record trong phạm vi recheck; tính đúng nghiệp vụ của dữ liệu thật vẫn **NOT PROVABLE**.
- Không chạy lại exporter hoặc test suite ứng dụng vì work order chỉ yêu cầu recheck hai workbook đã xuất và cấm sửa nguồn.

## File tạo mới

- `docs/CODEX_DESKTOP_SPREADSHEET_REGRESSION_RECHECK_RESULT_20260717.md`
- `outputs/codex-desktop-spreadsheet-regression-recheck-20260717/recheck_pl03.mjs`
- `outputs/codex-desktop-spreadsheet-regression-recheck-20260717/pl03_recheck_inspect.json`
- `outputs/codex-desktop-spreadsheet-regression-recheck-20260717/renders/POSITIVE_FULL_A1-AI10_S1.png`
- `outputs/codex-desktop-spreadsheet-regression-recheck-20260717/renders/POSITIVE_LEFT_A1-L10_S2.png`
- `outputs/codex-desktop-spreadsheet-regression-recheck-20260717/renders/POSITIVE_MIDDLE_M1-X10_S2.png`
- `outputs/codex-desktop-spreadsheet-regression-recheck-20260717/renders/POSITIVE_FOCUS_Y1-AI10_S3.png`
- `outputs/codex-desktop-spreadsheet-regression-recheck-20260717/renders/OPERATIONAL_FULL_A1-AI56_S1.png`
- `outputs/codex-desktop-spreadsheet-regression-recheck-20260717/renders/OPERATIONAL_LEFT_A1-L20_S2.png`
- `outputs/codex-desktop-spreadsheet-regression-recheck-20260717/renders/OPERATIONAL_FOCUS_Y1-AI20_S2.png`

Không có file nào bị sửa hoặc xóa. Không commit hoặc push.

`git diff --check`: **PASS** (exit code 0). `git status --short` sau kiểm tra chỉ hiện báo cáo mới chưa track; thư mục evidence dưới `outputs/` được ignore theo cấu hình repo.

## Release statement

Đủ điều kiện đóng **Spreadsheet implementation gate** cho phạm vi regression recheck này: **PASS**. Điều này chỉ xác nhận implementation và artifact kiểm thử; **không** xác nhận dữ liệu nghiệp vụ live.
