# APPENDIX EXPORT VERIFICATION — 2026-07-16

## 1. Kết luận điều hành

**Kết luận: CHƯA đủ điều kiện xác nhận cả ba file xuất đúng chuẩn mẫu.**

Phần dữ liệu cốt lõi đạt yêu cầu: PL.01 có 16 cột và 47 phương tiện; PL.02 có 16 cột, toàn bộ chỉ tiêu hoạt động để trống phù hợp với database có 0 declaration; PL.03 có 35 cột và 47 phương tiện. Không thấy dữ liệu tĩnh bị đẩy sang cột hoạt động/hàng hóa, không có cột kỹ thuật `sum_total`, không có lỗi công thức/hiển thị, và các dòng PL.03 mở rộng đến dòng 56 giữ style nhất quán.

Tuy nhiên, độ trung thành với mẫu chưa đạt vì:

1. **Major — PL.01:** file xuất chỉ có bảng, thiếu toàn bộ khối tiêu đề, ngày, tên doanh nghiệp và ghi chú của mẫu DOCX.
2. **Major — PL.02:** file xuất chỉ có bảng, thiếu tiêu đề và trường `Tháng`; header đổi nghĩa từ `tháng báo cáo` sang `kỳ báo cáo`.
3. **Major — PL.03:** file xuất giữ tiêu đề/header nhưng bỏ khối ký tên cuối mẫu (`Người lập báo cáo` và `Thủ trưởng đơn vị ký, đóng dấu`).
4. Việc render trực quan hai mẫu DOCX chưa thực hiện được vì máy không có LibreOffice/`soffice`.

## 2. Phạm vi và nguyên tắc

- Audit read-only; không sửa code ứng dụng, template hoặc workbook nguồn.
- Không commit và không xóa artifact.
- XLSX chỉ được đọc, inspect và render bằng `@oai/artifact-tool`; không dùng openpyxl, pandas, Excel COM hoặc parser XLSX thay thế.
- DOCX được kiểm tra bằng skill Documents với bundled Python và `python-docx`/OOXML theo workflow của skill.
- Database chỉ được mở ở chế độ SQLite read-only để xác nhận số lượng nguồn; không thay đổi dữ liệu.

## 3. Công cụ và runtime thực tế

| Thành phần | Giá trị |
|---|---|
| Workspace dependency bundle | `26.715.11153` |
| Spreadsheet engine | `@oai/artifact-tool` — API reference `2.8.6+` |
| Node runtime | Bundled Codex primary runtime (local path withheld) |
| Python runtime | Bundled Codex primary runtime (local path withheld) |
| Documents skill | `documents/26.715.11153` |
| DOCX renderer | `render_docx.py`; không chạy được do thiếu `soffice` |
| Database verification | SQLite read-only: `47 vessels`, `0 declarations`, `0 declaration_events` |

## 4. File đã kiểm tra

### File xuất thực tế

1. `outputs/salan-appendix-review-20260716-095835/PL.01_Ho_so_Salan_kiem_tra.xlsx`
2. `outputs/salan-appendix-review-20260716-095835/PL.02_Ho_so_Salan_kiem_tra.xlsx`
3. `outputs/salan-appendix-review-20260716-095835/PL.03_Ho_so_Salan_kiem_tra.xlsx`

### Mẫu đối chiếu

1. `templates/Phụ lục 1.docx`
2. `templates/Phụ lục 2.docx`
3. `templates/Phụ lục 3.xlsx`

## 5. Tổng hợp PASS/FAIL

| Tiêu chí | PL.01 | PL.02 | PL.03 | Bằng chứng |
|---|---:|---:|---:|---|
| Workbook import được | PASS | PASS | PASS | Mỗi file có 1 sheet, inspect thành công |
| Đúng số cột | PASS — 16 | PASS — 16 | PASS — 35 | `A1:P51`, `A1:P7`, `A1:AI56` |
| Đúng số đối tượng/dòng dữ liệu | PASS — 47 | N/A — báo cáo tổng hợp | PASS — 47 | PL.01 `A5:P51`; PL.03 `A10:AI56` |
| Thứ tự header đúng cấu trúc bảng mẫu | PASS | PASS với sai khác từ ngữ | PASS | PL.01 `A1:P4`; PL.02 `A1:P4`; PL.03 `A5:AI9` |
| Merge layout của phần bảng | PASS theo render/anchor | PASS theo render/anchor | PASS theo render/anchor | Danh sách merge tại mục chi tiết |
| Column width/header height đầy đủ | PASS | PASS | PASS; khớp mẫu XLSX | Xem mục chi tiết |
| Wrap/border/alignment hiển thị hợp lệ | PASS | PASS | PASS | `computedStyle` và render toàn sheet |
| Dữ liệu không bị dịch cột | PASS | PASS | PASS | PL.01 dữ liệu tĩnh A:H/P; PL.02 C:P trống; PL.03 dữ liệu tĩnh A:H |
| Không đưa trường tĩnh vào hoạt động/hàng hóa | PASS | PASS | PASS | PL.01 `I5:O51` trống; PL.02 `C5:P7` trống; PL.03 `I10:AI56` trống |
| PL.02 không coi sức chở là sản lượng | PASS | PASS | N/A | Database có 0 declaration; PL.02 C:P đều trống |
| Không có `sum_total` | PASS | PASS | PASS | Match trên toàn bộ values: 0 |
| Công thức/lỗi hiển thị | PASS | PASS | PASS | Không có formula; không có `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, `#N/A`, `#NUM!`, `#NULL!` |
| PL.03 dòng >5 giữ style | N/A | N/A | PASS | Row 10 và row 56 có cùng style theo từng cột; row 10 cũng khớp data-row mẫu |
| Render toàn sheet đã xem | PASS | PASS | PASS | Tên render tại mục chi tiết |
| Trung thành đầy đủ với mẫu | **FAIL** | **FAIL** | **FAIL** | Thiếu title block PL.01/PL.02; thiếu signature block PL.03 |

## 6. PL.01 — Hồ sơ/Kế hoạch phương tiện

### 6.1 Cấu trúc và dữ liệu

- Sheet: `Phụ lục 1`.
- Used range: `A1:P51` — **51 hàng × 16 cột**.
- Header: hàng 1–4; dữ liệu: hàng 5–51, đúng **47 phương tiện**.
- Header logic theo thứ tự A:P:
  1. `TT`
  2. `Tên`
  3. `Số đăng ký`
  4. `Cấp phương tiện`
  5. `Công dụng`
  6. `Ngày hết hạn GCNATKT & BVMT`
  7. `Khả năng khai thác / Lượng hàng (tấn/TEU)`
  8. `Khả năng khai thác / Sức chở (khách)`
  9. `Đến / Vị trí (Cảng/cầu)`
  10. `Đến / Thời gian (ngày, giờ)`
  11. `Rời / Vị trí (Cảng/cầu)`
  12. `Rời / Thời gian (ngày, giờ)`
  13. `Hàng dỡ (loại, số lượng)`
  14. `Hàng xếp (loại, số lượng)`
  15. `Số thuyền viên/Hành khách`
  16. `Tên và số điện thoại thuyền trưởng`
- Merge ranges của bảng xuất, khớp cấu trúc bảng DOCX:
  - `A1:A4`, `B1:H1`, `I1:O1`, `P1:P4`
  - `B2:B4`, `C2:C4`, `D2:D4`, `E2:E4`, `F2:F4`, `G2:H3`
  - `I2:J2`, `K2:L2`, `M2:M4`, `N2:N4`, `O2:O4`
  - `I3:I4`, `J3:J4`, `K3:K4`, `L3:L4`
- Column widths A:P: `6, 18, 14, 16, 22, 16, 20, 12, 18, 18, 18, 18, 24, 24, 16, 24`.
- Header row heights 1–4: `28 pt, 28 pt, 28 pt, 28 pt`.
- Style: header Times New Roman 10 bold, wrap text, căn giữa, border đen mảnh; data wrap text, căn giữa theo cả hai chiều, border mảnh xuyên suốt từ row 5 đến row 51.
- Số cell trong data range `A5:P51`: **752**; điền **369**, trống **383**.
- Theo cột: A–E đủ `47/47`; F `46/47`; G `46/47`; H `0/47`; I–O `0/47`; P `42/47`.
- Các thiếu hụt tĩnh đáng chú ý: `F43`, `G43`; cột thuyền trưởng trống tại `P5`, `P6`, `P8`, `P11`, `P42`.

### 6.2 Dòng đầu và dòng cuối

- Dòng đầu `A5:P5` và dòng cuối `A51:P51` đã được kiểm tra đủ 16 cột; tên,
  đăng ký và người liên hệ được lược khỏi bản tài liệu public.
- Dữ liệu nằm đúng cột: thông tin tĩnh ở A:H và P; toàn bộ hoạt động I:O trống. Không phát hiện dịch cột.

### 6.3 Render đã xem

- `outputs/spreadsheet-scan-20260716/audit-appendices-20260716/renders/PL01_1_Ph_l_c_1.png`
- Kết quả: toàn bộ 51 hàng hiển thị; header không bị cắt; border liên tục; text dài được wrap. Một số tên/công dụng/thông tin thuyền trưởng dày nhưng vẫn nằm trong cell.

### 6.4 Đối chiếu mẫu và phân loại

| Mức | Sai khác |
|---|---|
| **Major** | File XLSX bắt đầu trực tiếp từ bảng tại A1, trong khi DOCX có `Phụ lục 1`, dòng văn bản kèm theo, tiêu đề `KẾ HOẠCH HOẠT ĐỘNG...`, `Ngày`, `Tên doanh nghiệp` và ghi chú container. Toàn bộ khối này bị thiếu. |
| Minor | Khác khoảng trắng/cách viết: `GCNATKT & BVMT` so với `GCNATKT&BVMT`; `Cảng/cầu` so với `Cảng/ cầu`; `Số thuyền viên/Hành khách` so với `Số thuyền viên/ Hành khách`. |
| Minor | Mẫu DOCX có 3 dòng mẫu + dòng `…`; file xuất mở rộng động thành 47 dòng. Đây là thay đổi hợp lý về dữ liệu nhưng khác số hàng vật lý của mẫu. |

## 7. PL.02 — Khối lượng hàng hóa/lượt tàu/hành khách

### 7.1 Cấu trúc và dữ liệu

- Sheet: `Phụ lục 2`.
- Used range: `A1:P7` — **7 hàng × 16 cột**.
- Header: hàng 1–4; dữ liệu/tổng hợp: hàng 5–7.
- Header A:P:
  - A `STT`, B `Chỉ tiêu`.
  - C:F `Container`: thực hiện/lũy kế, mỗi nhóm gồm `Tấn`, `TEUs`.
  - G:H `Hàng khô`: thực hiện/lũy kế, đơn vị `Tấn`.
  - I:J `Hàng lỏng`: thực hiện/lũy kế, đơn vị `Tấn`.
  - K:L `Hàng XNK`: thực hiện/lũy kế, đơn vị `Tấn`.
  - M:N `Lượt tàu`: thực hiện/lũy kế, đơn vị `Lượt`.
  - O:P `Hành khách`: `Lượt tàu khách`, `Lượt khách`.
- Merge ranges:
  - `A1:A3`, `B1:B3`
  - `C1:F1`, `G1:H1`, `I1:J1`, `K1:L1`, `M1:N1`, `O1:P1`
  - `C2:D2`, `E2:F2`
  - `A7:B7` cho dòng `Tổng`
- Column widths A:P: `6, 24, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12`.
- Header row heights 1–4: `28 pt, 28 pt, 28 pt, 28 pt`.
- Style: header Times New Roman 10 bold, wrap text, căn giữa, fill xám nhạt, border đen mảnh; thân bảng wrap/căn giữa/border mảnh.
- Data range `A5:P7`: **48 cell**; điền **4**, trống **44**.
- Hoạt động `C5:P7`: **42/42 cell trống**.
- Database read-only: `47 vessels`, `0 declarations`, `0 declaration_events`. Vì không có declaration, việc không có sản lượng/hành trình là đúng; sức chở tĩnh của phương tiện không được đưa vào PL.02.

### 7.2 Dòng đầu và dòng cuối

- Dòng đầu `A5:P5`: `I | Bến cảng biển | [C:P trống]`.
- Dòng cơ sở `A6:P6`: `[A trống] | - Cảng Tân Thuận | [C:P trống]`.
- Dòng cuối `A7:P7`: `Tổng | [B:P trống]`.
- Không có giá trị tĩnh hoặc sức chở bị ghi vào các cột sản lượng C:P.

### 7.3 Render đã xem

- `outputs/spreadsheet-scan-20260716/audit-appendices-20260716/renders/PL02_1_Ph_l_c_2.png`
- Kết quả: toàn bộ A1:P7 hiển thị rõ; merge, wrap, border và alignment không vỡ; vùng hoạt động trống đúng chủ ý.

### 7.4 Đối chiếu mẫu và phân loại

| Mức | Sai khác |
|---|---|
| **Major** | Thiếu khối `Phụ lục 2`, dòng văn bản kèm theo, tiêu đề báo cáo và trường `Tháng ……` của DOCX. |
| **Major** | Header mẫu dùng `Thực hiện tháng báo cáo` / `Lũy kế đến tháng báo cáo`; XLSX đổi thành `Thực hiện kỳ báo cáo` / `Lũy kế đến kỳ báo cáo`. Đây là thay đổi ngữ nghĩa kỳ báo cáo, không chỉ là định dạng. |
| Minor | Mẫu có thêm dòng placeholder `- ………` trước dòng Tổng; XLSX bỏ dòng placeholder và đưa Tổng lên hàng 7. |
| Minor | Column proportions của XLSX được nới đều hơn DOCX; render vẫn đọc được nhưng không phải bản sao hình học của mẫu Word. |

## 8. PL.03 — Báo cáo chi tiết phương tiện ra/vào cảng

### 8.1 Cấu trúc và dữ liệu

- Sheet: `Sheet`.
- Used range: `A1:AI56` — **56 hàng × 35 cột**.
- Title/header: hàng 1–9; dữ liệu: hàng 10–56, đúng **47 phương tiện**.
- Header hàng 1–9 có nội dung và thứ tự giống mẫu `templates/Phụ lục 3.xlsx`.
- Thứ tự 35 cột:
  - A `STT`.
  - B:H lần lượt: `Tên PTTND`, `Số đăng ký`, `Loại phương tiện`, `Cấp PTTND`, `Chiều dài (m)`, `Trọng tải toàn phần`, `Dung tích`.
  - I:K `Xuất khẩu`: Tấn, Teus, Teus Rỗng.
  - L:N `Nhập khẩu`: Tấn, Teus, Teus Rỗng.
  - O:Q `Nội địa đến`: Tấn, Teus, Tues Rỗng.
  - R:T `Nội địa rời`: Tấn, Teus, Tues Rỗng.
  - U:V `Chuyển tải`: Tấn, Tues.
  - W:X `Quá cảnh (bốc dỡ)`: Tấn, Tues.
  - Y:Z `Quá cảng (không bốc dỡ)`: Tấn, Teus.
  - AA:AB `Hành khách (Lượt)`: Đến cảng, Rời cảng.
  - AC:AI: `Tên hàng`, `Cảng rời cuối cùng`, `Cảng đến (Cảng làm hàng)`, `Cảng đích`, `Ngày đến cảng`, `Ngày rời cảng`, `Đại lý PTTND`.

### 8.2 Merge ranges

Merge layout của header file xuất khớp render mẫu:

- `A1:AI1`, `A2:AI2`, `A3:AI3`, `A4:AI4`.
- `A5:A8`, `B5:B8`, `C5:C8`, `D5:D8`, `E5:E8`, `F5:F8`, `G5:G8`, `H5:H8`.
- `I5:Z5`, `AA5:AB6`, `AC5:AC8`, `AD5:AD8`, `AE5:AE8`, `AF5:AF8`, `AG5:AG8`, `AH5:AH8`, `AI5:AI8`.
- `I6:K6`, `L6:N6`, `O6:Q6`, `R6:T6`, `U6:V6`, `W6:X6`, `Y6:Z6`.
- `I7:I8`, `J7:J8`, `K7:K8`, `L7:L8`, `M7:M8`, `N7:N8`, `O7:O8`, `P7:P8`, `Q7:Q8`, `R7:R8`, `S7:S8`, `T7:T8`, `U7:U8`, `V7:V8`, `W7:W8`, `X7:X8`, `Y7:Y8`, `Z7:Z8`, `AA7:AA8`, `AB7:AB8`.

Mẫu còn có khối cuối tài liệu hiển thị theo hai nửa trang ở hàng 15–16 (`Người lập báo cáo` và `Thủ trưởng đơn vị...`). File xuất kết thúc tại hàng dữ liệu 56 và không chuyển khối này xuống sau dữ liệu.

### 8.3 Kích thước và style

- Column widths A:AI:
  - `A=6, B=9.5547, C=6.7773, D=9.6641, E=9.1094, F=7.8867, G=8.6641, H=7.3320`
  - `I=6.1094, J=7.1094, K=7.7773, L=6.2188, M=7.1094, N=7.4414`
  - `O=6, P=7, Q=7.4414, R=6, S=7.2188, T=7.1094, U=6.1094, V=6.8867`
  - `W=6.1094, X=6.7773, Y=6, Z=6.8867, AA=7, AB=6.4414, AC=7.7773`
  - `AD=7.8867, AE=8.3320, AF=9, AG=7.2188, AH=7.5547, AI=8.6641`.
- Các width trên khớp mẫu PL.03.
- Header row heights 1–9: `25.2, 21.6, 45, 31.8, 100.8, 48, 21.6, 41.4, 17.25 pt`; khớp mẫu.
- Header: Times New Roman 11–14, wrap text, căn giữa, border đen mảnh.
- Data: Times New Roman 11, wrap text; A và F:H căn phải, B:E căn giữa, các cell đều có border mảnh và vertical alignment giữa.
- Style của row 10 và row 56 giống nhau theo từng cột; row 10 cũng khớp data-row mẫu. Các dòng mới vượt quá 5 dòng mẫu giữ đúng style.

### 8.4 Dữ liệu

- Data range `A10:AI56`: **1.645 cell**; điền **373**, trống **1.272**.
- A:G đủ `47/47`; H `44/47`; I:AI `0/47` ở tất cả các cột hoạt động/hàng hóa/hành trình.
- Dung tích còn trống tại `H43`, `H47`, `H48`.
- Không phát hiện dữ liệu tĩnh bị dịch sang I:AI.
- Không có `sum_total` hoặc cột kỹ thuật khác.
- Dòng đầu `A10:AI10` và dòng cuối `A56:AI56` đã được kiểm tra đủ 35 cột;
  định danh phương tiện được lược khỏi bản tài liệu public và `I:AI` trống đúng
  trạng thái không có activity.

### 8.5 Render đã xem

- File xuất: `outputs/spreadsheet-scan-20260716/audit-appendices-20260716/renders/PL03_1_Sheet.png`.
- Mẫu XLSX: `outputs/spreadsheet-scan-20260716/audit-appendices-20260716/renders/TPL03_1_Sheet.png`.
- Kết quả: toàn bộ 47 dòng hiện đủ; border của các dòng mới liên tục; không thấy cột bị lệch hoặc mất style. Header rất rộng nhưng vẫn đọc được trong render toàn sheet.

### 8.6 Đối chiếu mẫu và phân loại

| Mức | Sai khác |
|---|---|
| **Major** | Khối ký tên cuối mẫu tại hàng 15–16 không xuất hiện sau 47 dòng dữ liệu. File xuất kết thúc tại row 56. |
| Minor | Các style ID nội bộ được tái tạo khi xuất; giá trị header, width, height, wrap/alignment và hình ảnh render vẫn khớp. |
| Minor | Mẫu và file xuất cùng chứa lỗi/không thống nhất nhãn: `Tues`, `Tues Rỗng` và `Quá cảng (không bốc dỡ)`. Vì lỗi có sẵn trong mẫu nên không phải lỗi dịch cột, nhưng nên chuẩn hóa thành `TEUs`/`TEUs Rỗng` và `Quá cảnh`. |

## 9. Danh sách vấn đề cần sửa

| ID | Mức | File | Vấn đề | Hướng xử lý đề xuất |
|---|---|---|---|---|
| APPX-01 | Major | PL.01 | Thiếu title/date/company/note của mẫu DOCX | Đưa khối mở đầu vào XLSX trước bảng hoặc xác nhận chính thức rằng file xuất chỉ yêu cầu table extract |
| APPX-02 | Major | PL.02 | Thiếu title và trường tháng | Giữ lại khối mở đầu của mẫu hoặc ban hành spec XLSX riêng |
| APPX-03 | Major | PL.02 | `tháng báo cáo` bị đổi thành `kỳ báo cáo` | Dùng đúng wording mẫu nếu báo cáo bắt buộc theo tháng |
| APPX-04 | Major | PL.03 | Thiếu khối ký tên cuối báo cáo | Di chuyển/copy khối ký tên xuống sau dòng dữ liệu cuối cùng |
| APPX-05 | Minor | PL.03/template | `Tues`, `Tues Rỗng`, `Quá cảng` không thống nhất | Chuẩn hóa nhãn trong template và logic xuất |
| APPX-06 | Minor | PL.01/PL.03 data | Một số field tĩnh thiếu (`F43`, `G43`, `P5/P6/P8/P11/P42`, `H43/H47/H48`) | Xác minh đây là thiếu dữ liệu nguồn hay cần bắt buộc nhập |

## 10. Mục chưa kiểm chứng

1. **Render DOCX:** không thể chạy `render_docx.py` vì môi trường không có LibreOffice/`soffice`. Hai mẫu Word đã được kiểm tra đầy đủ cấu trúc, text, grid width, merge, row height, alignment và border metadata nhưng chưa có QA PNG từng trang.
2. **Merge metadata XLSX:** facade của `@oai/artifact-tool` không cung cấp getter đọc merge collection. Danh sách merge XLSX ở báo cáo được xác nhận bằng value anchors, border/style inspect và render toàn sheet; merge DOCX được trích trực tiếp từ OOXML qua skill Documents. Không dùng parser XLSX thay thế.
3. **Print setup trong Microsoft Excel:** chưa kiểm tra print area, page scaling hoặc ngắt trang bằng Excel desktop; phạm vi hiện tại dùng renderer của artifact-tool.
4. **Ý định nghiệp vụ về title/signature:** chưa có spec riêng xác nhận XLSX được phép chỉ chứa bảng. Theo yêu cầu “đối chiếu với mẫu”, các phần bị thiếu được phân loại Major.

## 11. Canonical Field Mapping

### 11.1 Nguyên tắc phân lớp và ưu tiên nguồn

- **Static data (S):** hồ sơ phương tiện hiện tại trong `vessels` và `vessel_operating_profiles`. Khi có `vessel_id` hoặc khớp `registration_no`, giá trị hiện tại của hồ sơ phương tiện được ưu tiên hơn snapshot cũ trong `declarations`. Dữ liệu tĩnh không tự tạo ra lượt tàu, sản lượng, hành khách hoặc hàng hóa.
- **Activity data (A):** dữ liệu của lượt đến/rời trong `declarations`, chỉ đủ điều kiện khi `workflow_status = 'APPROVED'`, đúng tenant và thuộc kỳ báo cáo. Giá trị của lượt đã duyệt là snapshot nghiệp vụ; ATA/ATD ưu tiên hơn ETA/ETD.
- **Aggregate data (G):** PL.02 chỉ tổng hợp từ các activity record đủ điều kiện. `vessels.deadweight_tons`, `vessel_operating_profiles.cargo_capacity_tons`, `vessels.container_capacity_teu` và `vessels.passenger_capacity` là sức chở thiết kế, **không phải sản lượng** và không được dùng cho PL.02.
- **Quy tắc xung đột chung:** static dùng hồ sơ `vessels` hiện tại; activity/cargo dùng declaration đã duyệt. Không dùng static để lấp chỗ trống activity. Nếu có nhiều declaration, mỗi lượt/cargo item được giữ riêng rồi mới tổng hợp; không lấy bản ghi mới nhất để ghi đè lượt cũ.
- **Quy tắc kỳ báo cáo chuẩn:** PL.02 phải dùng ngày hoạt động thực tế (`actual_arrival_at`/`actual_departure_at`, fallback ETA/ETD khi chưa có actual). Việc implementation hiện lọc bằng `declarations.declaration_date` là sai ngữ nghĩa đối với sản lượng thực tế.
- **Ký hiệu trạng thái:** `Có nguồn` = field/schema và luồng nhập đã tồn tại; `Thiếu dữ liệu` = field có nhưng database kiểm tra không có giá trị; `Mapping sai` = logic hiện tại dùng sai loại dữ liệu/ý nghĩa; `Cần DB/UI` = thiếu field chuyên biệt hoặc thiếu nơi nhập.

### 11.2 PL.01 — mapping 16 cột

| PL/cột | Ý nghĩa nghiệp vụ | Bảng nguồn chuẩn | Field nguồn chuẩn | Field dự phòng | Loại | Thời điểm | Điều kiện đưa vào báo cáo | Quy tắc để trống | Xung đột nhiều nguồn | Bằng chứng file xuất | Trạng thái |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PL.01/A | Số thứ tự dòng | Derived | `row_number` | Không | S/derived | Tại lúc xuất | Có dòng phương tiện/lượt đủ điều kiện | Không để trống | Đánh lại theo thứ tự xuất | `A5:A51` = 1–47 | Có nguồn |
| PL.01/B | Tên phương tiện | `vessels` | `name` | `declarations.vessel_name` | S | Hiện tại | Phương tiện/lượt đủ điều kiện | Trống chỉ khi cả master và snapshot đều thiếu | `vessels.name` thắng snapshot | `B5:B51` điền đủ 47/47; giá trị lược khỏi bản public | Có nguồn |
| PL.01/C | Số đăng ký | `vessels` | `registration_no` | `declarations.registration_no` | S | Hiện tại | Như B | Không được trống đối với hồ sơ hợp lệ | Khớp bằng `vessel_id`, sau đó `registration_no` | `C5:C51` điền đủ 47/47; giá trị lược khỏi bản public | Có nguồn |
| PL.01/D | Cấp/vùng hoạt động phương tiện | `vessels` / `vessel_operating_profiles` | `vessel_class` / `activity_area` | `declarations.vessel_class` | S | Hiện tại | Như B | Trống khi hồ sơ và snapshot đều thiếu | Hồ sơ hiện tại thắng; nhiều profile phải giữ thứ tự, không chọn/average tùy tiện | `D5:D51` điền 47/47; `D5=VR-SII` | Có nguồn; cần chốt một canonical field giữa `vessel_class` và `activity_area` |
| PL.01/E | Công dụng/loại phương tiện | `vessels` | `vessel_type` | `declarations.vessel_type` | S | Hiện tại | Như B | Trống khi cả hai nguồn thiếu | `vessels.vessel_type` thắng | `E5:E51` điền 47/47 | Có nguồn |
| PL.01/F | Hạn GCN ATKT & BVMT | `vessels` | `certificate_expiry_date` | `declarations.certificate_expiry_date` | S | Hiện tại | Như B | Trống nếu chưa có hạn chứng nhận | Hồ sơ hiện tại thắng snapshot | `F5:F51` 46/47; thiếu `F43` | Có nguồn; thiếu dữ liệu 1 phương tiện |
| PL.01/G | Khả năng khai thác hàng (tấn/TEU) | `vessel_operating_profiles` + `vessels` | `cargo_capacity_tons` + `container_capacity_teu` | `vessels.cargo_capacity_tons`; không fallback activity | S | Hiện tại | Như B | Trống nếu không có cả tấn và TEU | Giữ toàn bộ profile theo `sequence`; không cộng/average; TEU lấy từ vessel | `G5=740 tấn`; `G51=670 tấn / 36 TEU`; thiếu `G43` | Có nguồn; thiếu dữ liệu 1 phương tiện |
| PL.01/H | Sức chở thiết kế (khách) | `vessels` | `passenger_capacity` | **Không dùng** `declarations.passenger_count` | S | Hiện tại | Như B | Trống nếu phương tiện không khai báo sức chở khách | Static capacity thắng; tuyệt đối không lấy khách thực chở | `H5:H51` trống 47/47 | **Mapping sai trong code** vì fallback sang `passenger_count`; cần dữ liệu/UI bắt buộc khi là tàu khách |
| PL.01/I | Vị trí đến (cảng/cầu) | `declarations` | `working_port` | Không | A | Snapshot lượt được duyệt | `APPROVED`, đúng tenant/kỳ | Trống nếu không có lượt đủ điều kiện; không lấy địa chỉ/hồ sơ tàu | Declaration của chính lượt | `I5:I51` trống do 0 declaration | Có nguồn; thiếu activity thực tế |
| PL.01/J | Thời gian đến | `declarations` | `actual_arrival_at` | `eta` | A | Snapshot lượt được duyệt | Như I | Trống nếu không có cả ATA và ETA | ATA thắng ETA | `J5:J51` trống | Có DB; **cần UI nhập/xác nhận ATA** |
| PL.01/K | Vị trí rời (cảng/cầu) | `declarations` | `working_port` hoặc field `departure_berth` chuyên biệt | Không dùng `destination_port` làm vị trí rời | A | Snapshot lượt được duyệt | Như I | Trống nếu không có lượt/vị trí rời | Vị trí rời của chính lượt thắng cảng đích | `K5:K51` trống | **Mapping sai**: code dùng `destination_port`; cần DB/UI `departure_berth` nếu khác `working_port` |
| PL.01/L | Thời gian rời | `declarations` | `actual_departure_at` | `etd` | A | Snapshot lượt được duyệt | Như I | Trống nếu không có cả ATD và ETD | ATD thắng ETD | `L5:L51` trống | Có DB; **cần UI nhập/xác nhận ATD** |
| PL.01/M | Hàng dỡ: loại và số lượng | `declarations` | `unload_json.{cargo_name,cargo_type,tons,teu}` | `cargo_description` chỉ để mô tả, không thay số lượng | A | Snapshot lượt được duyệt | Như I; item dỡ có nội dung | Trống nếu không có hàng dỡ; không lấy sức chở | Giữ item của lượt; không ghi đè bằng `load_json` | `M5:M51` trống | Có nguồn/UI; thiếu activity thực tế |
| PL.01/N | Hàng xếp: loại và số lượng | `declarations` | `load_json.{cargo_name,cargo_type,tons,teu}` | `cargo_description` chỉ để mô tả | A | Snapshot lượt được duyệt | Như I; item xếp có nội dung | Trống nếu không có hàng xếp; không lấy sức chở | Giữ item của lượt; không ghi đè bằng `unload_json` | `N5:N51` trống | Có nguồn/UI; thiếu activity thực tế |
| PL.01/O | Số thuyền viên / hành khách thực tế | `declarations` | `crew_count` / `passenger_count` | Có thể đối chiếu `declaration_crew`, không dùng `vessels.min_crew/passenger_capacity` | A | Snapshot lượt được duyệt | Như I | Trống khi không có lượt; với lượt hợp lệ cho phép `0 / 0` | Snapshot declaration thắng static capacity | `O5:O51` trống | Có nguồn/UI; thiếu activity thực tế |
| PL.01/P | Tên và điện thoại thuyền trưởng | `vessels` | `tracking_master_name` + `tracking_master_phone` | `declarations.master_name` + `master_phone` | S theo đặc tả hiện hành | Hiện tại | Như B | Trống phần nào thiếu phần đó | Hồ sơ Salan hiện tại thắng snapshot | `P5:P51` 42/47; trống `P5,P6,P8,P11,P42` | Có nguồn/UI; thiếu dữ liệu 5 phương tiện |

### 11.3 PL.02 — mapping 16 cột

Các cột C:P chỉ được tính từ declaration đã `APPROVED` và ngày hoạt động thuộc kỳ. Khi không có bất kỳ activity đủ điều kiện, toàn bộ metric phải để trống; `0` chỉ dùng khi có activity đủ điều kiện nhưng giá trị đo hợp lệ bằng 0. File thực tế đáp ứng quy tắc này tại `C5:P7`, nhưng `_appendix2_rows` hiện khởi tạo số 0 và endpoint lọc bằng `declaration_date`; hai điểm này cần được sửa trước khi coi luồng xuất production là canonical.

| PL/cột | Ý nghĩa nghiệp vụ | Bảng nguồn chuẩn | Field nguồn chuẩn | Field dự phòng | Loại | Thời điểm | Điều kiện đưa vào báo cáo | Quy tắc để trống | Xung đột nhiều nguồn | Bằng chứng file xuất | Trạng thái |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PL.02/A | Mã nhóm/dòng tổng | Derived/template | hằng `I`, `Tổng` | Không | G/label | Tại lúc xuất | Luôn có cấu trúc báo cáo | Không trống ở dòng nhóm/tổng | Template thắng | `A5=I`, `A7=Tổng` | Có nguồn |
| PL.02/B | Chỉ tiêu/đơn vị cảng | Config/template | `Cảng Tân Thuận` | Reporting-unit config | G/label | Tại lúc xuất | Luôn có dòng đơn vị | Không trống ở dòng đơn vị | Config đã duyệt thắng chuỗi tự do | `B5=Bến cảng biển`, `B6=- Cảng Tân Thuận` | Có nguồn; nên đưa reporting unit vào config thay vì hard-code |
| PL.02/C | Container kỳ báo cáo, tấn | `declarations` | `unload_json/load_json[].tons` khi `cargo_type=Container` | Không | G từ A | Snapshot đã duyệt | Approved + operating date trong kỳ | Trống nếu không có activity; không lấy capacity | Cộng tất cả item đủ điều kiện, không chọn một nguồn | `C5:C7` trống | Có nguồn/UI; logic lọc kỳ hiện **mapping sai** |
| PL.02/D | Container kỳ báo cáo, TEU | `declarations` | `unload_json/load_json[].teu` | Tính từ container 20/40 ft trong cùng snapshot | G từ A | Snapshot đã duyệt | Như C | Như C | TEU snapshot/derived của item thắng mọi capacity TEU | `D5:D7` trống | Có nguồn/UI; logic lọc kỳ hiện mapping sai |
| PL.02/E | Container lũy kế, tấn | `declarations` | như C, từ 01/01 đến ngày cuối báo cáo | Không | G từ A | Snapshot đã duyệt | Approved + operating date YTD | Trống nếu không có activity YTD | Cộng item YTD duy nhất một lần | `E5:E7` trống | Có nguồn; logic lọc kỳ hiện mapping sai |
| PL.02/F | Container lũy kế, TEU | `declarations` | như D, YTD | Tính từ container snapshot | G từ A | Snapshot đã duyệt | Như E | Như E | Như D | `F5:F7` trống | Có nguồn; logic lọc kỳ hiện mapping sai |
| PL.02/G | Hàng khô kỳ báo cáo, tấn | `declarations` | `unload_json/load_json[].tons` khi `cargo_type=Hàng khô` | Không | G từ A | Snapshot đã duyệt | Approved + operating date trong kỳ | Trống nếu không có activity | Cộng item đúng cargo type | `G5:G7` trống | Có nguồn/UI; logic lọc kỳ hiện mapping sai |
| PL.02/H | Hàng khô lũy kế, tấn | `declarations` | như G, YTD | Không | G từ A | Snapshot đã duyệt | Approved + operating date YTD | Trống nếu không có activity YTD | Cộng item YTD | `H5:H7` trống | Có nguồn; logic lọc kỳ hiện mapping sai |
| PL.02/I | Hàng lỏng kỳ báo cáo, tấn | `declarations` | `unload_json/load_json[].tons` khi `cargo_type=Hàng lỏng` | Không | G từ A | Snapshot đã duyệt | Approved + operating date trong kỳ | Trống nếu không có activity | Cộng item đúng cargo type | `I5:I7` trống | Có nguồn/UI; logic lọc kỳ hiện mapping sai |
| PL.02/J | Hàng lỏng lũy kế, tấn | `declarations` | như I, YTD | Không | G từ A | Snapshot đã duyệt | Approved + operating date YTD | Trống nếu không có activity YTD | Cộng item YTD | `J5:J7` trống | Có nguồn; logic lọc kỳ hiện mapping sai |
| PL.02/K | Hàng xuất nhập khẩu kỳ báo cáo, tấn | `declarations` | `unload_json/load_json[].tons` khi `movement_type` là nhập/xuất khẩu | Không | G từ A | Snapshot đã duyệt | Approved + operating date trong kỳ | Trống nếu không có activity | Phân loại theo movement của cargo item, không theo sức chở/type tàu | `K5:K7` trống | Có nguồn/UI; logic lọc kỳ hiện mapping sai |
| PL.02/L | Hàng xuất nhập khẩu lũy kế, tấn | `declarations` | như K, YTD | Không | G từ A | Snapshot đã duyệt | Approved + operating date YTD | Trống nếu không có activity YTD | Cộng item YTD | `L5:L7` trống | Có nguồn; logic lọc kỳ hiện mapping sai |
| PL.02/M | Lượt tàu kỳ báo cáo | `declarations` | `COUNT(id)` | Không | G từ A | Snapshot đã duyệt | Approved + operating date trong kỳ; một declaration phải đại diện đúng một lượt | Trống nếu không có activity | Khử trùng theo `declarations.id`; không đếm cargo row | `M5:M7` trống | Có nguồn; cần xác nhận quy ước một declaration = một lượt |
| PL.02/N | Lượt tàu lũy kế | `declarations` | `COUNT(id)` YTD | Không | G từ A | Snapshot đã duyệt | Approved + operating date YTD | Trống nếu không có activity YTD | Như M | `N5:N7` trống | Có nguồn; cần xác nhận quy ước lượt |
| PL.02/O | Lượt tàu khách kỳ báo cáo | `declarations` | `COUNT(id WHERE passenger_count > 0)` | Nên có cờ/type tàu khách chuyên biệt trong activity | G từ A | Snapshot đã duyệt | Approved + operating date trong kỳ | Trống nếu không có activity | Không dùng `vessels.passenger_capacity`; khử trùng theo declaration | `O5:O7` trống | Có nguồn tạm; **cần DB/UI** tiêu chí “tàu khách” rõ hơn nếu tàu khách có 0 khách |
| PL.02/P | Lượt khách kỳ báo cáo | `declarations` | `SUM(passenger_count)` | Không | G từ A | Snapshot đã duyệt | Approved + operating date trong kỳ | Trống nếu không có activity | Cộng khách thực tế; không dùng `vessels.passenger_capacity` | `P5:P7` trống | Có nguồn/UI; không có lẫn sức chở trong file thực tế |

### 11.4 PL.03 — mapping 35 cột

| PL/cột | Ý nghĩa nghiệp vụ | Bảng nguồn chuẩn | Field nguồn chuẩn | Field dự phòng | Loại | Thời điểm | Điều kiện đưa vào báo cáo | Quy tắc để trống | Xung đột nhiều nguồn | Bằng chứng file xuất | Trạng thái |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PL.03/A | STT | Derived | `row_number` | Không | S/derived | Tại lúc xuất | Có dòng detail đủ điều kiện | Không trống | Đánh lại sau khi cargo expansion | `A10:A56` = 1–47 | Có nguồn |
| PL.03/B | Tên phương tiện | `vessels` | `name` | `declarations.vessel_name` | S | Hiện tại | Dòng approved/cargo đủ điều kiện; file kiểm tra dùng static row | Trống khi cả hai nguồn thiếu | Vessel master thắng snapshot | `B10:B56` điền đủ 47/47; giá trị lược khỏi bản public | Có nguồn |
| PL.03/C | Số đăng ký | `vessels` | `registration_no` | `declarations.registration_no` | S | Hiện tại | Như B | Không trống với hồ sơ hợp lệ | Vessel master thắng | `C10:C56` điền đủ 47/47; giá trị lược khỏi bản public | Có nguồn |
| PL.03/D | Loại/công dụng phương tiện | `vessels` | `vessel_type` | `declarations.vessel_type` | S | Hiện tại | Như B | Trống khi cả hai thiếu | Vessel master thắng | `D10:D56` 47/47 | Có nguồn |
| PL.03/E | Cấp phương tiện | `vessels` / `vessel_operating_profiles` | `vessel_class` / `activity_area` | `declarations.vessel_class` | S | Hiện tại | Như B | Trống khi thiếu | Master/profile hiện tại thắng; cần chốt canonical giữa 2 field | `E10:E56` 47/47; `E10=VR-SII` | Có nguồn; cần chuẩn hóa field |
| PL.03/F | Chiều dài lớn nhất (m) | `vessels` | `length_m` | `declarations.length_m` | S | Hiện tại | Như B | Trống nếu chưa có; không đổi thành 0 | Master thắng snapshot | `F10=46.75`; `F56=45.44` | Có nguồn |
| PL.03/G | Trọng tải toàn phần (tấn) | `vessel_operating_profiles` | `deadweight_tons` | `vessels.deadweight_tons`, rồi `declarations.deadweight_tons` | S | Hiện tại | Như B | Trống nếu chưa có; không đổi thành 0 | Giữ profile theo sequence, không cộng/average | `G10=746`; `G56=680`; 47/47 | Có nguồn |
| PL.03/H | Dung tích toàn phần | `vessels` | `gross_tonnage` | `declarations.gross_tonnage` | S | Hiện tại | Như B | Trống nếu chưa có; không đổi thành 0 | Master thắng snapshot | `H10=357`; `H56=307`; thiếu `H43,H47,H48` | Có nguồn; thiếu dữ liệu 3 phương tiện |
| PL.03/I | Xuất khẩu, tấn | `declarations` | cargo item `tons`, `movement_type=Xuất khẩu` | Không | A | Snapshot đã duyệt | Approved + item xuất khẩu + operating date kỳ | Trống nếu không áp dụng/không có activity | Item movement quyết định cột | `I10:I56` trống | Có nguồn/UI; chưa có activity để kiểm chứng |
| PL.03/J | Xuất khẩu, TEU | `declarations` | cargo item `teu` | Derived từ container snapshot | A | Snapshot đã duyệt | Như I | Như I | Snapshot item thắng capacity | `J10:J56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/K | Xuất khẩu, TEU rỗng | `declarations` | cargo item `empty_teu` | Derived từ `cont20_empty/cont40_empty` | A | Snapshot đã duyệt | Như I | Như I | Derived trong cùng item | `K10:K56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/L | Nhập khẩu, tấn | `declarations` | cargo item `tons`, `movement_type=Nhập khẩu` | Không | A | Snapshot đã duyệt | Approved + item nhập khẩu + operating date kỳ | Trống nếu không áp dụng | Item movement quyết định cột | `L10:L56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/M | Nhập khẩu, TEU | `declarations` | cargo item `teu` | Derived từ container snapshot | A | Snapshot đã duyệt | Như L | Như L | Như J | `M10:M56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/N | Nhập khẩu, TEU rỗng | `declarations` | cargo item `empty_teu` | Derived từ container rỗng snapshot | A | Snapshot đã duyệt | Như L | Như L | Như K | `N10:N56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/O | Nội địa đến, tấn | `declarations` | cargo item `tons`, `movement_type=Nội địa đến` | Không | A | Snapshot đã duyệt | Approved + đúng movement + kỳ | Trống nếu không áp dụng | Item movement quyết định cột | `O10:O56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/P | Nội địa đến, TEU | `declarations` | cargo item `teu` | Derived | A | Snapshot đã duyệt | Như O | Như O | Như J | `P10:P56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/Q | Nội địa đến, TEU rỗng | `declarations` | cargo item `empty_teu` | Derived | A | Snapshot đã duyệt | Như O | Như O | Như K | `Q10:Q56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/R | Nội địa rời, tấn | `declarations` | cargo item `tons`, `movement_type=Nội địa rời` | Không | A | Snapshot đã duyệt | Approved + đúng movement + kỳ | Trống nếu không áp dụng | Item movement quyết định cột | `R10:R56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/S | Nội địa rời, TEU | `declarations` | cargo item `teu` | Derived | A | Snapshot đã duyệt | Như R | Như R | Như J | `S10:S56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/T | Nội địa rời, TEU rỗng | `declarations` | cargo item `empty_teu` | Derived | A | Snapshot đã duyệt | Như R | Như R | Như K | `T10:T56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/U | Chuyển tải, tấn | `declarations` | cargo item `tons`, `movement_type=Chuyển tải` | Không | A | Snapshot đã duyệt | Approved + đúng movement + kỳ | Trống nếu không áp dụng | Item movement quyết định cột | `U10:U56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/V | Chuyển tải, TEU | `declarations` | cargo item `teu` | Derived | A | Snapshot đã duyệt | Như U | Như U | Như J | `V10:V56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/W | Quá cảnh có xếp dỡ, tấn | `declarations` | cargo item `tons`, movement quá cảnh + bốc/xếp dỡ | Không | A | Snapshot đã duyệt | Approved + đúng movement + kỳ | Trống nếu không áp dụng | Item movement quyết định cột | `W10:W56` trống | Có nguồn/UI; cần khóa catalog canonical để tránh biến thể text |
| PL.03/X | Quá cảnh có xếp dỡ, TEU | `declarations` | cargo item `teu` | Derived | A | Snapshot đã duyệt | Như W | Như W | Như J | `X10:X56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/Y | Quá cảnh không xếp dỡ, tấn | `declarations` | cargo item `tons`, movement quá cảnh không bốc/xếp dỡ | Không | A | Snapshot đã duyệt | Approved + đúng movement + kỳ | Trống nếu không áp dụng | Item movement quyết định cột | `Y10:Y56` trống | Có nguồn/UI; cần khóa catalog canonical |
| PL.03/Z | Quá cảnh không xếp dỡ, TEU | `declarations` | cargo item `teu` | Derived | A | Snapshot đã duyệt | Như Y | Như Y | Như J | `Z10:Z56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/AA | Hành khách đến | `declarations` | `passenger_count` khi `movement_type=ARRIVAL` | Không | A | Snapshot đã duyệt | Approved + arrival + operating date kỳ | Trống nếu không có lượt; 0 chỉ khi có lượt với 0 khách | Không dùng `passenger_capacity` | `AA10:AA56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/AB | Hành khách rời | `declarations` | `passenger_count` khi `movement_type=DEPARTURE` | Không | A | Snapshot đã duyệt | Approved + departure + operating date kỳ | Như AA | Không dùng `passenger_capacity` | `AB10:AB56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/AC | Tên hàng | `declarations` | cargo item `cargo_name` | cargo item `cargo_type` | A | Snapshot đã duyệt | Approved + cargo item có nội dung | Trống khi không có hàng | `cargo_name` thắng `cargo_type` mô tả chung | `AC10:AC56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/AD | Cảng rời cuối cùng | `declarations` | `last_port` | Không | A | Snapshot đã duyệt | Approved + operating date kỳ | Trống nếu không có lượt | Declaration của chính lượt | `AD10:AD56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/AE | Cảng đến/làm hàng | `declarations` | `working_port` | Không | A | Snapshot đã duyệt | Như AD | Trống nếu không có lượt | Declaration của chính lượt | `AE10:AE56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/AF | Cảng đích | `declarations` | `destination_port` | Không | A | Snapshot đã duyệt | Như AD | Cho phép trống nếu chưa/không có cảng đích | Không thay bằng `working_port` | `AF10:AF56` trống | Có nguồn/UI; chưa kiểm chứng |
| PL.03/AG | Ngày đến cảng | `declarations` | `actual_arrival_at` | `eta` | A | Snapshot đã duyệt | Approved + arrival time thuộc kỳ | Trống khi không có cả ATA và ETA | ATA thắng ETA | `AG10:AG56` trống | Có DB; **cần UI nhập/xác nhận ATA** |
| PL.03/AH | Ngày rời cảng | `declarations` | `actual_departure_at` | `etd` | A | Snapshot đã duyệt | Approved + departure time thuộc kỳ | Trống khi không có cả ATD và ETD | ATD thắng ETD | `AH10:AH56` trống | Có DB; **cần UI nhập/xác nhận ATD** |
| PL.03/AI | Đại lý/người khai thác PTTNĐ | Chưa có bảng/field chuyên biệt | Cần `declarations.agent_or_operator_name` snapshot hoặc quan hệ agent/operator | `company_name` chỉ dùng nếu được xác nhận cùng nghĩa | A | Snapshot đã duyệt | Approved + có chủ thể đại lý/khai thác | Trống nếu chưa xác định; không tự gán tên doanh nghiệp | Field chuyên biệt thắng organization/company | `AI10:AI56` trống | **Thiếu canonical field; mapping hiện tại sang `company_name` có nguy cơ sai; cần DB/UI** |

### 11.5 Phân loại field và hành động cần thiết

#### Đã có nguồn chuẩn

- Static: PL.01 `B:G`, `P`; PL.03 `B:H`, với nguồn chính `vessels`/`vessel_operating_profiles` và fallback snapshot tương ứng trong `declarations`.
- Activity: PL.01 `I:J`, `L:O`; PL.03 `I:AH`, với nguồn `declarations` và hai cargo snapshot `unload_json`/`load_json`.
- Aggregate: PL.02 `C:P` có đủ dữ liệu đầu vào về cargo, container, passenger và declaration id để tính, nhưng chỉ được tổng hợp sau khi áp dụng đúng approval + operating-date filter.
- Derived/template: PL.01 `A`; PL.02 `A:B`; PL.03 `A`.

#### Đang thiếu

- **Thiếu field canonical trong schema:** PL.03/AI chưa có field đại lý/người khai thác chuyên biệt; PL.01/K chưa có `departure_berth` riêng nếu vị trí rời khác `working_port`.
- **Thiếu dữ liệu trong database kiểm tra:** PL.01/F thiếu tại `F43`, PL.01/G thiếu tại `G43`, PL.01/H thiếu toàn bộ `H5:H51`, PL.01/P thiếu `P5,P6,P8,P11,P42`; PL.03/H thiếu `H43,H47,H48`.
- **Thiếu activity:** database có `0 declarations`, nên PL.01 `I:O`, PL.02 `C:P`, PL.03 `I:AI` không có dữ liệu thực tế để chứng minh mapping dương.

#### Đang mapping sai hoặc chưa đủ chặt

- PL.01/H: code fallback từ sức chở thiết kế sang `declarations.passenger_count`; đây là trộn static capacity với actual passenger và phải loại bỏ.
- PL.01/K: code dùng `destination_port` cho “vị trí rời”; cảng đích không đồng nghĩa cảng/cầu rời.
- PL.02/C:P: endpoint chọn kỳ bằng `declaration_date`, không phải ngày hoạt động thực tế; đồng thời logic nội bộ tạo `0` khi không có declaration, trái quy tắc để trống đã thể hiện đúng trong file kiểm tra.
- PL.03/AI: code ghi `company_name` vào cột đại lý/người khai thác khi chưa có bằng chứng hai khái niệm đồng nhất.
- PL.03/F:H và các metric activity: code dùng `0` làm fallback cho field chưa có; canonical blank rule yêu cầu để trống khi dữ liệu không tồn tại, chỉ ghi 0 khi đó là giá trị thực đã ghi nhận.
- PL.01/PL.03 cột cấp phương tiện: đang có cả `vessels.vessel_class` và `vessel_operating_profiles.activity_area`; cần chọn một định nghĩa canonical hoặc quy tắc hiển thị đa profile rõ ràng.

#### Cần bổ sung database hoặc UI

- DB + UI: `departure_berth` (và `arrival_berth` nếu cần phân biệt với `working_port`) cho PL.01/I,K.
- DB + UI: `agent_or_operator_name` dạng snapshot cho PL.03/AI, tốt hơn là có quan hệ tới tổ chức/đại lý và lưu tên snapshot khi duyệt.
- UI/workflow: trường xác nhận ATA/ATD cho `actual_arrival_at` và `actual_departure_at`; DB đã có field nhưng frontend hiện chưa có control nhập.
- DB/UI hoặc quy tắc nghiệp vụ: cờ `is_passenger_call`/loại lượt tàu khách nếu PL.02/O phải đếm tàu khách kể cả khi `passenger_count = 0`.
- Validation UI: bắt buộc `passenger_capacity` cho loại tàu khách; cảnh báo thiếu certificate expiry, cargo capacity, gross tonnage và tracked-master contact theo các cell thiếu đã nêu.
- Data model dài hạn: cân nhắc chuẩn hóa cargo item thành bảng activity/cargo riêng hoặc lưu version snapshot bất biến khi duyệt; hiện `unload_json`/`load_json` đủ để xuất nhưng khó ràng buộc và audit ở cấp field.

## 12. Kết luận cuối

- **Mapping vị trí dữ liệu trong ba file kiểm tra tĩnh:** ĐẠT — không thấy static field bị ghi sang vùng activity/cargo.
- **Đúng số cột/số phương tiện:** CÓ.
- **PL.02 để trống sản lượng vì database không có declaration:** CÓ, đã xác nhận database read-only.
- **PL.03 mở rộng 47 dòng vẫn giữ style:** CÓ.
- **Canonical field mapping đã có cho đủ 67 cột:** CÓ, tại mục 11.
- **Đủ nguồn và logic để xác nhận production mapping:** CHƯA. Các blocker mapping là PL.01/H, PL.01/K, kỳ/no-data rule của PL.02 và PL.03/AI; activity dương chưa thể kiểm chứng vì database có 0 declaration.
- **Đúng hoàn toàn theo mẫu tương ứng:** KHÔNG.
- **Đủ điều kiện xác nhận ba file xuất đúng chuẩn:** **CHƯA** — cần xử lý hoặc phê duyệt ngoại lệ cho APPX-01 đến APPX-04, đóng các lỗi canonical mapping tại mục 11.5 và hoàn tất kiểm chứng activity dương; đồng thời nên hoàn tất DOCX render QA khi có `soffice`.

Vì vậy, kết luận tổng thể không đổi: **chưa đủ điều kiện xác nhận ba file xuất đúng chuẩn**. Ngoài các sai khác layout đã nêu, cần đóng các mapping sai/field thiếu ở mục 11.5 và kiểm chứng lại bằng ít nhất một bộ declaration `APPROVED` có arrival, departure, cargo, container rỗng và hành khách thực tế.
