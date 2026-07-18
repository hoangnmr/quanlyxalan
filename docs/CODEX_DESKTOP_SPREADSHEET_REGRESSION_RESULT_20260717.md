# Codex Desktop Spreadsheet Regression Result — 2026-07-17

Phạm vi: Bộ A operational review và Bộ B positive fixture synthetic
Chế độ: chỉ đọc; không sửa code, template hoặc sáu workbook đầu vào

## 1. Kết luận điều hành

`load_workspace_dependencies` và `@oai/artifact-tool` hoạt động đúng. Sáu workbook, tổng cộng sáu sheet, đã được inspect toàn bộ và render 24 ảnh phủ 100% used range. Không dùng `openpyxl`, `pandas`, `xlsxwriter`, LibreOffice, Excel COM, unzip/OOXML hoặc thư viện XLSX thay thế.

| Bộ/file | Implementation evidence | Live business data evidence | Kết luận |
|---|---|---|---|
| A / PL.01 | **PASS** | **NOT PROVABLE** | Đủ FORM, 16 cột, 47 Salan; `I11:O57` trống đúng manifest 0 APPROVED |
| A / PL.02 | **PASS** | **NOT PROVABLE** | Đủ FORM, 16 cột; `C11:P13` trống, không bị đổi thành zero |
| A / PL.03 | **PASS** | **NOT PROVABLE** | 35 cột, 47 Salan không trùng; `I10:AI56` trống; D không còn clipping |
| B / PL.01 | **PASS** | **NOT PROVABLE** | Full FORM và positive mapping H/O, I/K, ngày, hàng hóa đều đúng vị trí |
| B / PL.02 | **PASS** | **NOT PROVABLE** | Tháng 07/2046, wording đúng, tháng khác YTD, blank vẫn blank |
| B / PL.03 | **FAIL visual; PASS mapping** | **NOT PROVABLE** | Aggregate một dòng và mapping đúng, nhưng `AG10:AH10` bị clipping timestamp |

**Regression gate tổng thể: FAIL có giới hạn.** Exporter structure và positive mapping đã qua; còn một visual defect tại positive PL.03 phải sửa trước khi xác nhận toàn bộ spreadsheet PASS.

Fixture synthetic chỉ chứng minh implementation positive path. Nó không chứng minh dữ liệu khách hàng thật. Theo work order, tất cả mục `Live business data evidence` giữ **NOT PROVABLE** cho tới khi có declaration thật đã duyệt và nguồn DB/API độc lập để đối chiếu.

## 2. Runtime proof

- Skill: `spreadsheets:Spreadsheets`, bundle `26.715.12143`.
- Đã đọc đầy đủ `SKILL.md`, `style_guidelines.md`, `artifact_tool_docs/API_QUICK_START.md` và work order.
- `load_workspace_dependencies`: **PASS**.
- Node executable: loader-provided Codex primary runtime.
- Node packages: loader-provided `node_modules` của bundle `26.715.12143`.
- `FileBlob` và `SpreadsheetFile` import từ `@oai/artifact-tool`: **PASS**.
- Artifact tool API reference: `2.8.6+`.
- Machine-readable inspection: `outputs/codex-desktop-spreadsheet-regression-20260717/xlsx_regression_full.json`.

## 3. Files, sheets và used ranges

| Key | Workbook | Size | Sheet | Used range | Rows × columns |
|---|---|---:|---|---|---:|
| A/PL.01 | `PL.01_operational_review.xlsx` | 11,116 bytes | `Phụ lục 1` | `A1:P59` | 59 × 16 |
| A/PL.02 | `PL.02_operational_review.xlsx` | 6,318 bytes | `Phụ lục 2` | `A1:P13` | 13 × 16 |
| A/PL.03 | `PL.03_operational_review.xlsx` | 14,445 bytes | `Sheet` | `A1:AI56` | 56 × 35 |
| B/PL.01 | `PL.01_positive_fixture.xlsx` | 6,669 bytes | `Phụ lục 1` | `A1:P13` | 13 × 16 |
| B/PL.02 | `PL.02_positive_fixture.xlsx` | 6,350 bytes | `Phụ lục 2` | `A1:P13` | 13 × 16 |
| B/PL.03 | `PL.03_positive_fixture.xlsx` | 8,348 bytes | `Sheet` | `A1:AI10` | 10 × 35 |

Mỗi workbook có đúng một sheet; không phát hiện sheet trắng ngoài ý muốn hoặc vùng dữ liệu ngoài FORM.

## 4. Ma trận regression

| Tiêu chí | A/PL.01 | A/PL.02 | A/PL.03 | B/PL.01 | B/PL.02 | B/PL.03 |
|---|---|---|---|---|---|---|
| Sheet/range/column count | PASS | PASS | PASS | PASS | PASS | PASS |
| Full FORM/title/metadata | PASS | PASS | PASS theo APPX-04 | PASS | PASS | PASS theo APPX-04 |
| Header/order/labels | PASS | PASS | PASS | PASS | PASS | PASS |
| Merge visual | PASS | PASS | PASS | PASS | PASS | PASS |
| Width/row height | PASS | PASS | PASS | PASS | PASS | **FAIL AG10:AH10** |
| Wrap/alignment | PASS | PASS | PASS | PASS | PASS | **FAIL AG10:AH10** |
| Border continuity | PASS | PASS | PASS | PASS | PASS | PASS |
| Column shift/spill | PASS | PASS | PASS | PASS | PASS | PASS |
| Formula/display errors | PASS | PASS | PASS | PASS | PASS | PASS |
| Exact `TEUs`/`TEUs Rỗng`/`Quá cảnh` | PASS | PASS | PASS | PASS | PASS | PASS |
| `Teus`/`Tues`/`Quá cảng`/`sum_total` absent | PASS | PASS | PASS | PASS | PASS | PASS |
| Render 100% used range | PASS | PASS | PASS | PASS | PASS | PASS |
| Business data correctness | NOT PROVABLE | NOT PROVABLE | NOT PROVABLE | NOT PROVABLE | NOT PROVABLE | NOT PROVABLE |

Artifact facade hiện tại không có public getter/enumerator cho merged ranges đã tồn tại hoặc hidden-row/column metadata. Merge được kiểm tra bằng full render, header anchors và đối chiếu cấu trúc đã audit; vì không được dùng phương pháp thay thế, báo cáo không tuyên bố đã đọc trực tiếp merge metadata từ XLSX.

## 5. Bộ A — operational 47 Salan

Manifest ghi `canonical_salan_rows=47`, `approved_declarations_in_period=0`, `approved_arrivals_in_month=0`.

### A/PL.01

- Title/date/company/note tại `A1:P6`; header 16 cột tại `A7:P10`; 47 dòng tại `A11:P57`; signature tại `A59:P59`.
- `A11:A57` đủ STT 1–47; `C11:C57` có 47 registration, không trùng.
- Filled-count theo cột dữ liệu: `A:E=47`, `F:G=46`, `H=0`, `I:O=0`, `P=42`.
- `I11:O57` trống hoàn toàn. Không có static capacity bị coi là hoạt động giả.
- Static skeleton A:H/P giữ đúng vị trí; border liên tục qua dòng 57.

### A/PL.02

- Full FORM tại `A1:P13`; `A4=Tháng 07 năm 2026`, `A5` có đơn vị báo cáo.
- Header chứa đúng “Thực hiện tháng báo cáo” và “Lũy kế đến tháng báo cáo”.
- Toàn bộ chỉ tiêu `C11:P13` blank; không có numeric zero giả.

### A/PL.03

- Đúng 35 cột `A:AI`; 47 dòng `A10:AI56`; registration `C10:C56` không trùng.
- Filled-count: `A:G=47`, `H=44`, `I:AI=0`.
- Không có dữ liệu static rơi vào vùng hoạt động/hàng hóa.
- Cột D đã tăng từ baseline khoảng `9.71` lên `18`; hàng dữ liệu `10:56` cao `66`, wrap bật. Chuỗi “CHỞ HÀNG KHÔ HOẶC CONTAINER” đọc trọn vẹn trên toàn bộ ba vertical bands; lỗi clipping baseline đã hết ở operational set.

## 6. Bộ B — positive fixture synthetic

### B/PL.01

- Đủ title, `A4=Ngày 31/07/2046`, company, note, header 16 cột và signature.
- Positive row `A11:P11`:
  - `H11=80` là design passenger capacity; `O11="6 / 7"` là actual crew/passengers — không fallback lẫn nhau.
  - `I11=CẦU 1 - CẢNG TÂN THUẬN`; `K11=CẦU 2 - CẢNG TÂN THUẬN` — departure berth distinct, không dùng destination.
  - `J11` và `L11` chứa arrival/departure timestamps đúng cột.
  - `N11=HÀNG XUẤT - 20 tấn - 2 TEU`; M blank đúng positive row này.
- Không clipping, không lệch cột, border và merge visual ổn.

### B/PL.02

- `A4=Tháng 07 năm 2046`; `A5` có đơn vị báo cáo.
- Header `C8:N8` dùng exact “Thực hiện tháng báo cáo”/“Lũy kế đến tháng báo cáo”.
- `C12=20`, `D12=2` khác `E12=32`, `F12=4`: tháng 7 khác YTD tháng 1–7.
- `K12=20`, `L12=32`; `M12=1`, `N12=2`; `O12=1`, `P12=7`.
- `G12:J12` vẫn blank, không biến thành zero. Dòng total 13 reconcile đúng dòng 12.

### B/PL.03

- Đúng 35 cột và chỉ một data row `A10:AI10` cho `QA-CANONICAL-01`, dù fixture có hai declaration.
- Additive aggregation:
  - Export: `I10=20`, `J10=2`.
  - Import: `L10=12`, `M10=2`, `N10=1`.
  - Passenger arrival: `AA10=7`.
- Non-additive distinct, chronological values nằm cùng cell:
  - `AC10`: `HÀNG NHẬP` rồi `HÀNG XUẤT`.
  - `AG10`: arrival tháng 1 rồi tháng 7; `AH10`: departure tháng 1 rồi tháng 7.
  - `AI10`: `ĐẠI LÝ PTND A` rồi `ĐẠI LÝ PTND B`.
- `AD10=CẢNG A`, `AE10=CẦU 1 - CẢNG TÂN THUẬN`, `AF10=CẢNG C`: last port, working port và destination không lệch.
- Cột D rộng `18`, hàng 10 cao `66`; loại phương tiện không còn clipping.
- **Visual defect:** hai timestamp distinct tại `AG10:AH10` bị cắt ở đáy. Mapping/value inspect đúng nhưng người đọc không nhìn thấy trọn nội dung. Nên dùng compact datetime display hoặc tăng chiều rộng/chiều cao theo số distinct values.

## 7. Formula và error scan

Cả sáu workbook không chứa formula. Artifact-tool trả về “No records matched” cho formula inspect và “Cell search matched 0 entries” cho `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, `#N/A`, `#NUM!`, `#NULL!`. Đây không phải lỗi vì exporter đang ghi static output values.

Case-sensitive scan trên toàn bộ values cho `Teus`, `Tues`, `Quá cảng`, `sum_total` trả 0 ở cả sáu workbook. Các label chuẩn `TEUs`, `TEUs Rỗng`, `Quá cảnh` hiện đúng.

## 8. Findings

| ID | File/sheet | Cell/range | Expected | Actual | Severity | Evidence |
|---|---|---|---|---|---|---|
| REG-01 | B/PL.03 `Sheet` | `AG10:AH10` | Hai arrival/departure timestamps đọc trọn vẹn sau wrap | Dữ liệu đúng và theo thứ tự nhưng dòng cuối bị cắt ở đáy | MEDIUM | `B_PL03_1_FULL_Sheet.png`, `B_PL03_1_PART_03_Y1-AI10.png` |
| REG-02 | Cả 6 workbook | Merge/hidden metadata | Direct metadata proof | Public artifact facade không expose merge/hidden enumerator; visual corroboration PASS | LOW / tooling limitation | 6 full renders; prior API limitation retained |

Không phát hiện lỗi lệch cột, border đứt, merge vỡ trực quan, nhãn sai, formula error, cột kỹ thuật hoặc duplicate vessel.

## 9. APPX/MAP disposition hai lớp

`Implementation evidence` dưới đây là item-level. Một item chỉ PASS khi zero-path Bộ A và positive-path Bộ B liên quan đều PASS. `Live business data evidence` vẫn NOT PROVABLE theo chỉ thị work order.

| Item | Implementation evidence | Live business data evidence | Disposition |
|---|---|---|---|
| APPX-01 | **PASS** | **NOT PROVABLE** | Có thể đóng implementation: PL.01 full FORM có ở cả A/B |
| APPX-02 | **PASS** | **NOT PROVABLE** | Có thể đóng implementation: PL.02 title/month/company có ở cả A/B |
| APPX-03 | **PASS** | **NOT PROVABLE** | Có thể đóng implementation: exact “tháng báo cáo” ở cả A/B |
| APPX-04 | **PASS by approved exception** | **NOT PROVABLE** | Giữ đóng: PL.03 không cần signature block |
| MAP-01 | **PASS** | **NOT PROVABLE** | Có thể đóng implementation: A blank đúng zero-path; B phân biệt H=80 với O=6/7 |
| MAP-02 | **PASS** | **NOT PROVABLE** | Có thể đóng implementation: A blank đúng zero-path; B chứng minh I/K distinct và AE/AF đúng nguồn |
| MAP-03 | **PASS** | **NOT PROVABLE** | Có thể đóng implementation: A blank; B chứng minh month/YTD, call và blank-vs-zero |
| MAP-04 | **PASS** | **NOT PROVABLE** | Có thể đóng implementation: A AI blank; B AI giữ hai agent snapshots distinct |
| MAP-05 | **PASS** | **NOT PROVABLE** | Có thể đóng implementation mapping: A 47 unique rows; B hai declarations aggregate thành một row |

REG-01 không làm sai các giá trị MAP-04/MAP-05, nên item-level mapping vẫn PASS. Tuy nhiên, REG-01 giữ **visual regression/release gate tổng thể ở FAIL** cho tới khi render lại `AG10:AH10` đọc trọn vẹn.

## 10. Render coverage — 24 ảnh đã xem

### A/PL.01 — `A1:P59`

- `A_PL01_1_FULL_Ph_l_c_1.png`
- `A_PL01_1_PART_01_A1-P20.png`
- `A_PL01_1_PART_02_A21-P40.png`
- `A_PL01_1_PART_03_A41-P59.png`

### A/PL.02 — `A1:P13`

- `A_PL02_1_FULL_Ph_l_c_2.png`
- `A_PL02_1_PART_01_A1-P13.png`

### A/PL.03 — `A1:AI56`

- `A_PL03_1_FULL_Sheet.png`
- `A_PL03_1_PART_01_A1-L20.png`
- `A_PL03_1_PART_02_M1-X20.png`
- `A_PL03_1_PART_03_Y1-AI20.png`
- `A_PL03_1_PART_04_A21-L40.png`
- `A_PL03_1_PART_05_M21-X40.png`
- `A_PL03_1_PART_06_Y21-AI40.png`
- `A_PL03_1_PART_07_A41-L56.png`
- `A_PL03_1_PART_08_M41-X56.png`
- `A_PL03_1_PART_09_Y41-AI56.png`

### B/PL.01 — `A1:P13`

- `B_PL01_1_FULL_Ph_l_c_1.png`
- `B_PL01_1_PART_01_A1-P13.png`

### B/PL.02 — `A1:P13`

- `B_PL02_1_FULL_Ph_l_c_2.png`
- `B_PL02_1_PART_01_A1-P13.png`

### B/PL.03 — `A1:AI10`

- `B_PL03_1_FULL_Sheet.png`
- `B_PL03_1_PART_01_A1-L10.png`
- `B_PL03_1_PART_02_M1-X10.png`
- `B_PL03_1_PART_03_Y1-AI10.png`

Các horizontal part của PL.03 cắt qua merged header; text anchor chỉ hiện ở part chứa anchor. Full render được dùng để phân biệt crop boundary với workbook merge defect.

## 11. File tạo/thay đổi

Trạng thái Git trước regression: clean.

Được tạo trong lượt này:

- `docs/CODEX_DESKTOP_SPREADSHEET_REGRESSION_RESULT_20260717.md`.
- `outputs/codex-desktop-spreadsheet-regression-20260717/regression_workbooks.mjs` — support script, không phải QA result.
- `outputs/codex-desktop-spreadsheet-regression-20260717/xlsx_regression_full.json`.
- `outputs/codex-desktop-spreadsheet-regression-20260717/renders/` — 24 PNG liệt kê tại mục 10.
- `outputs/codex-desktop-spreadsheet-regression-20260717/node_modules` — junction tới loader-provided runtime.

Không sửa code, schema, template, tests, tài liệu chuẩn hoặc sáu workbook đầu vào. Không commit, không push.

## 12. Final gate

- Operational zero-path: **PASS implementation**, live business data **NOT PROVABLE**.
- Positive fixture mapping: **PASS implementation**, live business data **NOT PROVABLE**.
- Visual regression: **FAIL** tại `B/PL.03!AG10:AH10`.
- Overall spreadsheet regression: **FAIL có giới hạn**; cần sửa clipping và render lại trước khi xác nhận release-ready.
