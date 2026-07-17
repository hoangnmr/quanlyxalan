# Codex Desktop Spreadsheet QA Result — PL.01, PL.02, PL.03

Ngày kiểm tra: 2026-07-17
Phạm vi: ba workbook baseline trong `outputs/salan-appendix-review-20260716-095835/`
Chế độ: chỉ đọc; không sửa code, template hoặc workbook đầu vào

## 1. Kết luận điều hành

Runtime Spreadsheets hoạt động đúng. `load_workspace_dependencies` đã trả về bundle `26.715.12143`; Node runtime được cấp từ workspace dependency runtime. Cả ba workbook được mở, inspect và render trực tiếp bằng `@oai/artifact-tool`; không dùng `openpyxl`, `pandas`, `xlsxwriter`, LibreOffice, Excel COM, unzip/OOXML hay thư viện đọc XLSX thay thế.

| Workbook | Structure / Format | Business data | Kết luận |
|---|---|---|---|
| PL.01 | **FAIL** — bảng 16 cột đúng trật tự và hiển thị ổn, nhưng thiếu title/kỳ báo cáo/đơn vị/ghi chú/khối ký tên theo FORM | **NOT PROVABLE** — 47 dòng là dữ liệu tĩnh; toàn bộ vùng hoạt động `I5:O51` trống và không có bằng chứng declaration đã duyệt | Chưa đủ điều kiện xác nhận đúng chuẩn |
| PL.02 | **FAIL** — 16 cột đúng, nhưng thiếu khối title/tháng/đơn vị và dùng “kỳ báo cáo” thay vì “tháng báo cáo” | **NOT PROVABLE** — `C5:P7` trống; không có nguồn hoạt động/API/DB để chứng minh tháng và lũy kế | Chưa đủ điều kiện xác nhận đúng chuẩn |
| PL.03 | **FAIL** — đủ 35 cột/47 phương tiện, nhưng nhãn `Teus/Tues` sai và cột D bị clipping ở nhiều dòng | **NOT PROVABLE** — `I10:AI56` trống; không có declaration/cargo đã duyệt để chứng minh tổng hợp một dòng/phương tiện | Chưa đủ điều kiện xác nhận đúng chuẩn |

Không phát hiện dữ liệu tĩnh bị ghi sang vùng hoạt động/hàng hóa; không phát hiện cột kỹ thuật như `sum_total`; không phát hiện lỗi công thức/hiển thị dạng lỗi Excel. Tuy nhiên, các kết luận này chỉ áp dụng cho ba file baseline đã nêu, không chứng minh đây là file vừa xuất từ web.

## 2. Runtime proof và phương pháp

- Skill: `spreadsheets:Spreadsheets`, bundle `26.715.12143`.
- Đã đọc đầy đủ `SKILL.md`, `style_guidelines.md` và `artifact_tool_docs/API_QUICK_START.md` của bundle.
- `load_workspace_dependencies`: **PASS**.
- Node executable thực dùng: loader-provided runtime (đường dẫn máy người dùng đã được lược bỏ).
- Node modules thực dùng: loader-provided dependencies (đường dẫn máy người dùng đã được lược bỏ).
- Import `FileBlob` và `SpreadsheetFile` từ `@oai/artifact-tool`: **PASS**.
- API reference của artifact tool: `2.8.6+`.
- Bằng chứng máy đọc được: `outputs/codex-desktop-spreadsheet-qa-20260717/xlsx_qa_full.json` và `artifact_tool_help_merge_hidden.ndjson`.
- Mọi sheet được inspect toàn bộ giá trị, công thức và style; mỗi used range được render một ảnh toàn sheet và các ảnh liên tiếp đủ đọc, phủ 100% vùng dùng. Tất cả 16 PNG đã được mở và xem trực tiếp ở độ phân giải gốc.

### Giới hạn API cần ghi nhận

Artifact facade hiện tại có thao tác `range.merge()`/`unmerge()` nhưng không công bố getter/enumerator để đọc danh sách merge có sẵn. Các thuộc tính thử đọc cho hidden row/column và sheet visibility trả về `undefined`. Vì yêu cầu cấm phương pháp thay thế, QA này **không thể chứng minh trực tiếp metadata merge hoặc hidden**. Danh sách merge ở mục 5 lấy từ audit FORM đã có và được đối chiếu bằng bố cục render/anchor nội dung; không được trình bày như kết quả đọc metadata XLSX trực tiếp.

## 3. File, sheet và used range

| File | Size | Sheet | Used range | Hàng × cột | Vùng dữ liệu |
|---|---:|---|---|---:|---|
| `PL.01_Ho_so_Salan_kiem_tra.xlsx` | 10,472 bytes | `Phụ lục 1` | `A1:P51` | 51 × 16 | `A5:P51`, 47 dòng |
| `PL.02_Ho_so_Salan_kiem_tra.xlsx` | 5,998 bytes | `Phụ lục 2` | `A1:P7` | 7 × 16 | `A5:P7` |
| `PL.03_Ho_so_Salan_kiem_tra.xlsx` | 18,749 bytes | `Sheet` | `A1:AI56` | 56 × 35 | `A10:AI56`, 47 dòng |

Mỗi workbook có đúng một sheet; không thấy sheet trắng ngoài ý muốn trong workbook overview. Khả năng sheet/hàng/cột bị đặt hidden không thể chứng minh bằng public facade hiện tại.

## 4. Ma trận kiểm tra

Ký hiệu: **PASS** = có đủ bằng chứng; **FAIL** = có sai khác xác định; **NP** = NOT PROVABLE do API hoặc thiếu nguồn nghiệp vụ.

| Tiêu chí | PL.01 | PL.02 | PL.03 | Bằng chứng chính |
|---|---|---|---|---|
| Số sheet/used range | PASS | PASS | PASS | `xlsx_qa_full.json`; ranges mục 3 |
| Số cột/thứ tự header | PASS — 16 | PASS — 16 | PASS — 35 | `A1:P4`, `A1:P3`, `A5:AI8` |
| Full FORM structure | FAIL | FAIL | PASS theo ngoại lệ APPX-04 | PL.01/02 thiếu title và metadata; PL.03 không cần khối ký theo quyết định đã khóa |
| Merge cells | NP metadata; visual PASS | NP metadata; visual PASS | NP metadata; visual PASS | Full renders; giới hạn API mục 2 |
| Width/row height | PASS | PASS | FAIL | PL.03 `D13:D56` có clipping |
| Wrap/alignment | PASS | PASS | FAIL | PL.03 cột D wrap nhưng chiều rộng/chiều cao không đủ |
| Border/fill/font | PASS | PASS | PASS | Computed-style scan và toàn bộ render; viền liên tục |
| Formula/error | PASS | PASS | PASS | Không có formula; không có `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, `#N/A`, `#NUM!`, `#NULL!` |
| Data alignment | PASS về vị trí cột | PASS về vị trí cột | PASS về vị trí cột | Không có giá trị tĩnh trong `I:O`, `C:P`, `I:AI`; không có spill sang ô lân cận |
| Nhãn nghiệp vụ | PASS | FAIL — “kỳ” | FAIL — `Teus/Tues` | PL.02 `C2:N2`; PL.03 các cell liệt kê tại F-04 |
| Render 100% used range | PASS | PASS | PASS | 16 ảnh tại mục 8 |
| Business-data correctness | NP | NP | NP | Không có DB/API/declaration provenance trong phạm vi QA |

## 5. Cấu trúc, header, merge, width và height

### PL.01

Header giữ đúng thứ tự 16 cột `A:P`: TT; nhóm PHƯƠNG TIỆN (`B:H`); nhóm HOẠT ĐỘNG (`I:O`); thuyền trưởng/điện thoại (`P`). Các tầng con tại `G4:H4`, `I2:L4`, `M2:O4` nằm đúng vị trí; không thấy lệch header.

Merge theo audit FORM, được render corroborate nhưng không đọc trực tiếp được metadata:

`A1:A4`, `B1:H1`, `I1:O1`, `P1:P4`, `B2:B4`, `C2:C4`, `D2:D4`, `E2:E4`, `F2:F4`, `G2:H3`, `I2:J2`, `K2:L2`, `M2:M4`, `N2:N4`, `O2:O4`, `I3:I4`, `J3:J4`, `K3:K4`, `L3:L4`.

Độ rộng `A:P`: `6, 18, 14, 16, 22, 16, 20, 12, 18, 18, 18, 18, 24, 24, 16, 24`. Hàng header `1:4` cao `28`; các hàng dữ liệu dùng chiều cao mặc định. Wrap, căn giữa/căn dọc và border hiển thị ổn trên toàn bộ 47 dòng.

### PL.02

Header có 16 cột `A:P`; các nhóm lượt tàu, hàng hóa và hành khách được đặt đúng dải cột. Sai nội dung xác định: `C2:N2` dùng “Thực hiện kỳ báo cáo”/“Lũy kế đến kỳ báo cáo”, trong khi quyết định chuẩn yêu cầu “tháng báo cáo”. Workbook cũng bắt đầu ngay ở bảng `A1`, thiếu title/tháng/đơn vị theo FORM.

Merge theo audit FORM, được render corroborate nhưng không đọc trực tiếp được metadata:

`A1:A3`, `B1:B3`, `C1:F1`, `G1:H1`, `I1:J1`, `K1:L1`, `M1:N1`, `O1:P1`, `C2:D2`, `E2:F2`, `A7:B7`.

Độ rộng: `A=6`, `B=24`, `C:P=12`. Hàng `1:4` cao `28`; `5:7` dùng chiều cao mặc định. Wrap, alignment và border không có lỗi trực quan.

### PL.03

Workbook có đúng 35 cột `A:AI` (STT + 34 cột nội dung), title tại `A1:A4`, header đa tầng tại `A5:AI8`, dữ liệu tại `A10:AI56`. Thứ tự `AE=cảng làm hàng`, `AF=cảng đích`, `AI=Đại lý PTND` đúng quyết định đã khóa. Không có cột kỹ thuật `sum_total`.

Merge theo audit FORM, được render corroborate nhưng không đọc trực tiếp được metadata:

- Title: `A1:AI1`, `A2:AI2`, `A3:AI3`, `A4:AI4`.
- Cột đơn: `A5:A8` đến `H5:H8`; `AC5:AC8` đến `AI5:AI8`.
- Nhóm: `I5:Z5`, `AA5:AB6`; `I6:K6`, `L6:N6`, `O6:Q6`, `R6:T6`, `U6:V6`, `W6:X6`, `Y6:Z6`.
- Header lá: `I7:I8` đến `Z7:Z8`, `AA7:AA8`, `AB7:AB8`.

Độ rộng `A:AI`:

`6, 9.5703, 6.7109, 9.7109, 9.1406, 7.8555, 8.7109, 7.2852, 6.1406, 7.1406, 7.7109, 6.2852, 7.1406, 7.4258, 6, 7, 7.4258, 6, 7.2852, 7.1406, 6.1406, 6.8555, 6.1406, 6.7109, 6, 6.8555, 7, 6.4258, 7.7109, 7.8555, 8.2852, 9, 7.2852, 7.5703, 8.7109`.

Chiều cao hàng `1:9`: `25.15, 21.6, 45, 31.9, 100.9, 48, 21.6, 41.45, 17.25`; tất cả hàng dữ liệu `10:56` cao `48.6`. Viền và style được giữ liên tục đến dòng 56, chứng minh các dòng vượt quá 5 vẫn giữ style. Tuy nhiên, độ rộng D khoảng `9.71` và chiều cao `48.6` không đủ cho nhiều giá trị “CHỞ HÀNG KHÔ HOẶC CONTAINER”, gây clipping.

## 6. Kiểm tra dữ liệu toàn bộ dòng

| Workbook/range | Tổng ô dữ liệu | Điền | Trống | Dòng đầu | Dòng cuối |
|---|---:|---:|---:|---|---|
| PL.01 `A5:P51` | 752 | 369 | 383 | Dòng đầu đã kiểm tra đủ 16 cột (định danh đã lược bỏ) | Dòng cuối đã kiểm tra đủ 16 cột (định danh đã lược bỏ) |
| PL.02 `A5:P7` | 48 | 4 | 44 | `A5=I`, `B5=Bến cảng biển` | `A7=Tổng` |
| PL.03 `A10:AI56` | 1,645 | 373 | 1,272 | Dòng đầu đã kiểm tra đủ 35 cột (định danh đã lược bỏ) | Dòng cuối đã kiểm tra đủ 35 cột (định danh đã lược bỏ) |

- PL.01: mỗi cột `A:E` có 47 giá trị; `F:G` có 46; `H` và `I:O` có 0; `P` có 42. Không coi sức chở thiết kế ở G là sản lượng hoạt động.
- PL.02: chỉ A/B có dữ liệu nhãn; toàn bộ chỉ tiêu `C:P` trống. Blank không được tự động quy thành 0.
- PL.03: `A:G` có 47 giá trị; H có 44; toàn bộ `I:AI` trống. Không có dữ liệu tĩnh rơi vào hàng hóa/hoạt động.
- Không có bằng chứng DB/API trong work order để xác minh giá trị tĩnh, snapshot tại duyệt, số tháng, lũy kế, chuyến, hàng hóa hoặc hành khách. Vì vậy, “đúng vị trí cột” là PASS cấu trúc nhưng “đúng nghiệp vụ” vẫn là NOT PROVABLE.

## 7. Findings chi tiết

| Finding ID | File/sheet | Cell/range | Expected | Actual | Severity | Evidence image | Recommended code area |
|---|---|---|---|---|---|---|---|
| F-01 | PL.01 / `Phụ lục 1` | Trước `A1:P4` và sau dòng 51 | Đủ title, ngày/kỳ, đơn vị, ghi chú và khối ký theo FORM | Workbook chỉ có bảng header+dữ liệu | HIGH | `PL01_1_FULL_Ph_l_c_1.png` | Exporter PL.01: layout/title/footer composition |
| F-02 | PL.02 / `Phụ lục 2` | Trước `A1:P3` | Đủ title, tháng báo cáo, đơn vị báo cáo | Workbook bắt đầu ngay tại bảng | HIGH | `PL02_1_FULL_Ph_l_c_2.png` | Exporter PL.02: report metadata/title block |
| F-03 | PL.02 / `Phụ lục 2` | `C2:N2` | “Thực hiện tháng báo cáo”; “Lũy kế đến tháng báo cáo” | Dùng từ “kỳ báo cáo” | MEDIUM | `PL02_1_PART_01_A1-P7.png` | PL.02 header constants/template mapping |
| F-04 | PL.03 / `Sheet` | `J7,M7,P7,S7,Z7`; `K7,N7`; `Q7,T7`; `V7,X7` | `TEUs`; `TEUs Rỗng` | Lần lượt có `Teus`, `Teus Rỗng`, `Tues Rỗng`, `Tues` | MEDIUM | `PL03_1_FULL_Sheet.png`; parts 01–03 | PL.03 header label constants |
| F-05 | PL.03 / `Sheet` | `D13:D34,D41,D44:D46,D49,D52,D54:D56` | Loại phương tiện đọc trọn vẹn sau wrap | Nhiều ô “CHỞ HÀNG KHÔ HOẶC CONTAINER” bị cắt/không hiển thị trọn từ cuối | MEDIUM | `PL03_1_PART_01_A1-L20.png`; `PART_04_A21-L40.png`; `PART_07_A41-L56.png` | PL.03 column D width/row auto-fit policy |
| F-06 | Cả ba workbook | Merge metadata; hidden row/column/sheet | Có bằng chứng máy đọc được cho toàn bộ merge/hidden | Public facade không có getter/enumerator; chỉ corroborate bằng render | LOW | Ba full renders; `artifact_tool_help_merge_hidden.ndjson` | QA tooling/API capability; không phải exporter defect đã chứng minh |
| F-07 | PL.01 / `Phụ lục 1` | `A5:P51`, đặc biệt `I5:O51` | Official daily report chỉ từ declaration đã duyệt | 47 dòng tĩnh, vùng hoạt động trống; provenance không có | HIGH | Ba PL.01 part renders | Query/filter/mapping PL.01; cần fixture approved/unapproved |
| F-08 | PL.02 / `Phụ lục 2` | `C5:P7` | Tổng hợp từ hoạt động thực tế đã duyệt, tháng và YTD tách riêng | Toàn bộ blank; không thể chứng minh aggregation | HIGH | `PL02_1_PART_01_A1-P7.png` | PL.02 aggregation query and blank-vs-zero rules |
| F-09 | PL.03 / `Sheet` | `I10:AI56` | Một dòng/phương tiện, tổng hợp declaration/cargo hợp lệ | Toàn bộ hoạt động/hàng hóa blank; chỉ chứng minh được grain tĩnh | HIGH | 9 PL.03 part renders | PL.03 approved-declaration aggregation and snapshot mapping |

Không ghi F-07–F-09 là “dữ liệu sai”; đây là thiếu bằng chứng đủ để xác nhận dữ liệu nghiệp vụ.

## 8. Render coverage và ảnh đã xem

### PL.01 — phủ `A1:P51`

- `renders/PL01_1_FULL_Ph_l_c_1.png`
- `renders/PL01_1_PART_01_A1-P18.png`
- `renders/PL01_1_PART_02_A19-P36.png`
- `renders/PL01_1_PART_03_A37-P51.png`

### PL.02 — phủ `A1:P7`

- `renders/PL02_1_FULL_Ph_l_c_2.png`
- `renders/PL02_1_PART_01_A1-P7.png`

### PL.03 — phủ `A1:AI56`

- `renders/PL03_1_FULL_Sheet.png`
- `renders/PL03_1_PART_01_A1-L20.png`
- `renders/PL03_1_PART_02_M1-X20.png`
- `renders/PL03_1_PART_03_Y1-AI20.png`
- `renders/PL03_1_PART_04_A21-L40.png`
- `renders/PL03_1_PART_05_M21-X40.png`
- `renders/PL03_1_PART_06_Y21-AI40.png`
- `renders/PL03_1_PART_07_A41-L56.png`
- `renders/PL03_1_PART_08_M41-X56.png`
- `renders/PL03_1_PART_09_Y41-AI56.png`

Các part PL.03 cắt theo chiều ngang để đủ đọc. Vì vậy, chữ của merged header có thể chỉ xuất hiện ở part chứa ô neo; đó là đặc tính crop render, không được ghi là lỗi merge workbook. Full render được dùng để kiểm tra tổng thể header.

## 9. Đối chiếu APPX và MAP

| Mục | Trạng thái QA | Lý do/bằng chứng |
|---|---|---|
| APPX-01 | **Không đóng** | PL.01 thiếu toàn bộ khối FORM ngoài bảng (`F-01`) |
| APPX-02 | **Không đóng** | PL.02 thiếu title/tháng/đơn vị (`F-02`) |
| APPX-03 | **Không đóng** | PL.02 vẫn dùng “kỳ báo cáo” tại `C2:N2` (`F-03`) |
| APPX-04 | **Có thể xác nhận đóng theo ngoại lệ đã duyệt** | Decision register quy định PL.03 không cần signature block; không ghi nhận việc thiếu signature là defect |
| MAP-01 | **Không đóng** | PL.01/H và O đều blank; không có positive case để chứng minh design capacity khác actual passenger |
| MAP-02 | **Không đóng** | Header I/K và PL.03 AE/AF đúng thứ tự, nhưng mọi giá trị hoạt động trống; chưa chứng minh departure berth không fallback sang destination |
| MAP-03 | **Không đóng** | PL.02 `C:P` blank; chưa chứng minh selected-month/YTD và blank-vs-zero |
| MAP-04 | **Không đóng** | Nhãn `AI5=Đại lý PTND` đúng, nhưng `AI10:AI56` blank; chưa chứng minh dedicated customer-declared snapshot |

MAP-05 trong decision register (grain PL.03) cũng chưa đủ bằng chứng đóng: 47 dòng hiện tại cho thấy một dòng/phương tiện về mặt cấu trúc, nhưng không có fixture nhiều declaration/nhiều cargo item để chứng minh aggregate đúng.

## 10. Acceptance tests cần bổ sung cho exporter

1. PL.01 xuất đầy đủ title/kỳ/đơn vị/ghi chú/khối ký và đúng 16 cột; static-only vessel không xuất trong official daily report.
2. PL.01 có fixture phân biệt `H` sức chở hành khách thiết kế và `O` hành khách thực tế; cấm fallback giữa hai field.
3. PL.01 có fixture vị trí đến khác vị trí rời và cảng đích; khẳng định K dùng departure berth, không dùng destination.
4. PL.02 kiểm tra exact text “tháng báo cáo”, đầy đủ title/tháng/đơn vị và 16 cột.
5. PL.02 có declarations qua ranh giới tháng để kiểm tra selected month và lũy kế từ tháng 1; tính lượt theo arrival theo quyết định.
6. PL.02 kiểm tra ba trạng thái độc lập: không có hoạt động → blank; hoạt động không áp dụng chỉ tiêu → blank; hoạt động áp dụng với giá trị thực bằng 0 → `0`.
7. PL.02 chứng minh không dùng sức chở thiết kế làm sản lượng; có ca tàu khách 0 hành khách nhưng vẫn tính lượt.
8. PL.03 có một phương tiện với nhiều declaration và nhiều cargo item; chỉ xuất một dòng và tổng tấn/TEUs/lượt khớp nguồn đã duyệt.
9. PL.03 kiểm tra exact header `TEUs`, `TEUs Rỗng`, `Quá cảnh`, `Đại lý PTND`; AE là working port, AF là destination.
10. PL.03 kiểm tra dedicated customer/agent snapshot tại thời điểm duyệt và không fallback từ field tĩnh khác.
11. Visual regression kiểm tra full used range, merge/title, border, wrap/clipping; đặc biệt chuỗi dài tại D và style của dòng thứ 6 trở đi.
12. Quét formula/error sau export; kiểm tra không có cột kỹ thuật hoặc vùng dữ liệu ngoài FORM.

## 11. File mới hoặc thay đổi

### Có trước lượt QA, không bị sửa

- `docs/WORK_ORDER_CODEX_DESKTOP_SPREADSHEET_QA_20260717.md` — file untracked đã tồn tại theo trạng thái ban đầu.

### Được tạo bởi lượt QA này

- `docs/CODEX_DESKTOP_SPREADSHEET_QA_RESULT_20260717.md`
- `outputs/codex-desktop-spreadsheet-qa-20260717/qa_workbooks.mjs` — script hỗ trợ tạm, không phải kết quả QA.
- `outputs/codex-desktop-spreadsheet-qa-20260717/xlsx_qa_full.json`
- `outputs/codex-desktop-spreadsheet-qa-20260717/artifact_tool_help_merge_hidden.ndjson`
- 16 PNG trong `outputs/codex-desktop-spreadsheet-qa-20260717/renders/`, liệt kê đầy đủ tại mục 8.
- `outputs/codex-desktop-spreadsheet-qa-20260717/node_modules` — junction cục bộ tới dependency runtime do loader cấp, phục vụ import `@oai/artifact-tool`.

Không sửa `backend/`, `frontend/`, `migrations/`, `templates/`, `tests/`, ba workbook đầu vào hoặc tài liệu audit/decision/roadmap hiện có. Không commit, không push, không xóa artifact.

## 12. Release/verification gate

**FAIL — chưa đủ điều kiện xác nhận ba file xuất đúng chuẩn.**

- PL.01: Structure/Format **FAIL**; Business data **NOT PROVABLE**.
- PL.02: Structure/Format **FAIL**; Business data **NOT PROVABLE**.
- PL.03: Structure/Format **FAIL**; Business data **NOT PROVABLE**.
- Chỉ APPX-04 có thể xác nhận đóng theo ngoại lệ đã được quyết định. APPX-01–03 và MAP-01–04 chưa đủ bằng chứng đóng.
