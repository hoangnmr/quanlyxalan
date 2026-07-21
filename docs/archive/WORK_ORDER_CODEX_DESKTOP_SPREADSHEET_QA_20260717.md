# Work Order — Codex Desktop Spreadsheet QA cho PL.01, PL.02 và PL.03

Ngày lập: 2026-07-17
Repo: `D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu-recovery-ux`

## Mục tiêu

Dùng đúng skill **Spreadsheets** và workspace dependency runtime của Codex Desktop để kiểm tra trực quan, cấu trúc và dữ liệu của ba workbook xuất phụ lục hiện có. Đây là đợt QA baseline trước khi sửa exporter; không sửa application code, schema, template hoặc workbook nguồn.

## Prompt dán vào Codex Desktop

```text
Làm việc tại repo:

D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu-recovery-ux

Nhiệm vụ: dùng đúng skill Spreadsheets để kiểm tra toàn bộ ba file Excel sau:

1. outputs/salan-appendix-review-20260716-095835/PL.01_Ho_so_Salan_kiem_tra.xlsx
2. outputs/salan-appendix-review-20260716-095835/PL.02_Ho_so_Salan_kiem_tra.xlsx
3. outputs/salan-appendix-review-20260716-095835/PL.03_Ho_so_Salan_kiem_tra.xlsx

Đây là QA baseline trước khi sửa exporter. Không được sửa code hoặc các workbook.

Yêu cầu công cụ bắt buộc:

1. Đọc đầy đủ SKILL.md của skill Spreadsheets, style_guidelines.md và artifact_tool_docs/API_QUICK_START.md.
2. Gọi load_workspace_dependencies và xác nhận rõ đường dẫn dependency runtime được cấp.
3. Dùng @oai/artifact-tool cho việc mở, inspect và render ba workbook.
4. Không dùng openpyxl, pandas, xlsxwriter, LibreOffice, Excel COM, unzip/OOXML hoặc phương pháp thay thế để đọc hay kiểm tra workbook.
5. Nếu load_workspace_dependencies hoặc @oai/artifact-tool không hoạt động, dừng ngay và báo BLOCKED; không tạo báo cáo suy đoán.
6. Script hỗ trợ chỉ là artifact tạm, không phải kết quả QA. Không để script tạm ở root repo và không đưa script thay cho báo cáo.

Nguồn đối chiếu:

- templates/Phụ lục 1.docx
- templates/Phụ lục 2.docx
- templates/Phụ lục 3.xlsx
- docs/APPENDIX_TEMPLATE_AUDIT_20260716.md
- docs/APPENDIX_EXPORT_VERIFICATION_20260716.md
- docs/APPENDIX_BUSINESS_DECISION_REGISTER_20260717.md
- docs/REPORT_MAPPING_SPEC.md
- docs/CANONICAL_DATA_AND_APPENDIX_ASSURANCE_ROADMAP_20260716.md

Đối với mẫu PL.01 và PL.02 ở định dạng DOCX, dùng kết quả audit và decision register đã có làm chuẩn nội dung/cấu trúc. Nếu cần render DOCX thì có thể dùng thêm skill Documents, nhưng không được dùng nó hoặc thư viện Python để thay thế việc kiểm tra ba workbook XLSX bằng skill Spreadsheets.

Phạm vi kiểm tra bắt buộc cho từng workbook và từng sheet:

A. Kiểm tra cấu trúc

- Tên và số lượng sheet; used range thực tế.
- Số hàng, số cột và vị trí bảng dữ liệu.
- Toàn bộ merged ranges, kể cả merge ở title/header/signature/note.
- Vị trí title, kỳ báo cáo, đơn vị báo cáo, ghi chú và khối ký tên nếu biểu mẫu yêu cầu.
- Header nhiều tầng có đúng thứ tự cột và đúng phạm vi merge hay không.
- Dòng dữ liệu có đúng số cột; không lệch trái/phải; không ghi sang cột lân cận.
- Không có cột/hàng ẩn bất thường, vùng dữ liệu ngoài bảng hoặc sheet trắng ngoài ý muốn.

B. Kiểm tra định dạng

- Độ rộng từng cột và chiều cao các hàng title/header/data.
- Wrap text, vertical/horizontal alignment, font, bold, fill và number/date format.
- Border của toàn bộ bảng: cạnh ngoài, cạnh trong, header và các dòng dữ liệu.
- Nội dung dài có bị cắt, tràn, che mất hoặc wrap không hợp lý.
- Các ô merge có giữ đúng nội dung và căn chỉnh sau khi render.

C. Kiểm tra dữ liệu và mapping

- Kiểm tra tất cả dòng, không lấy mẫu.
- PL.01 phải có 16 cột dữ liệu đúng thứ tự.
- PL.02 phải có 16 cột dữ liệu đúng thứ tự; tách rõ số tháng báo cáo và lũy kế từ tháng 1 đến tháng được chọn.
- PL.03 phải có 34 cột nội dung cộng cột STT theo FORM, tổng cộng 35 cột trong workbook; một sà lan/phương tiện là một dòng tổng hợp, không tách thành nhiều dòng theo cargo item.
- Phân biệt blank với số 0; không coi blank là 0 nếu nghiệp vụ không có hoạt động áp dụng.
- Kiểm tra kiểu dữ liệu ngày, số tấn, TEUs, lượt và hành khách.
- Kiểm tra dữ liệu có rơi nhầm cột, đặc biệt các vùng hàng hóa, hành khách, cảng, ngày đến/rời và Đại lý PTND.
- Đối chiếu các quyết định đã khóa: PL.01/H là sức chở hành khách thiết kế; PL.01/O là số thực tế; PL.01/K không dùng cảng đích thay vị trí rời; PL.03/AE là cảng làm hàng; PL.03/AF là cảng đích; PL.03/AI giữ nhãn “Đại lý PTND”.
- Kiểm tra đúng các nhãn “TEUs”, “TEUs Rỗng”, “Quá cảnh”; liệt kê chính xác cell nào còn sai.

D. Kiểm tra công thức và lỗi workbook

- Inspect toàn bộ công thức và kết quả tính, nếu có.
- Quét #REF!, #DIV/0!, #VALUE!, #NAME?, #N/A và tham chiếu sai.
- Ghi rõ workbook nào không có công thức; không coi đó tự động là lỗi nếu FORM chỉ chứa dữ liệu tĩnh.

E. Kiểm tra trực quan

- Render toàn bộ từng sheet, không chỉ vùng mẫu.
- Xem trực quan tất cả ảnh render ở mức đủ đọc được header và dữ liệu.
- Nếu sheet dài, render theo các vùng liên tiếp sao cho bao phủ 100% used range.
- Ghi nhận từng lỗi clipping, wrap, merge, border, độ rộng, lệch cột và bố cục.
- Không được kết luận “đã kiểm tra trực quan” nếu chỉ inspect metadata mà chưa xem ảnh render.

Phân biệt rõ hai loại kết luận:

1. STRUCTURE/FORMAT PASS hoặc FAIL: workbook có bám FORM và hiển thị đúng hay không.
2. BUSINESS DATA PASS, FAIL hoặc NOT PROVABLE: dữ liệu có đúng nghiệp vụ hay không. Không kết luận dữ liệu đúng chỉ vì ô có giá trị; nếu không có nguồn database/API để đối chiếu thì ghi NOT PROVABLE.

Không được suy diễn rằng ba file này là file người dùng vừa xuất thủ công từ web. Chỉ ghi đây là các workbook baseline đang có trong outputs, trừ khi tìm được bằng chứng provenance cụ thể.

Kết quả phải tạo:

docs/CODEX_DESKTOP_SPREADSHEET_QA_RESULT_20260717.md

Báo cáo phải gồm:

1. Runtime proof: skill version, kết quả load_workspace_dependencies và xác nhận @oai/artifact-tool thực sự được dùng.
2. Danh sách file đã đọc, size, sheet và used range.
3. Ma trận kiểm tra từng workbook:
   - Structure
   - Merge cells
   - Column widths/row heights
   - Wrap/alignment
   - Borders
   - Formula errors
   - Data alignment
   - Visual render
   - Business data provability
4. Bảng lỗi chi tiết với các cột:
   - Finding ID
   - File/sheet
   - Cell/range
   - Expected
   - Actual
   - Severity: BLOCKER/HIGH/MEDIUM/LOW
   - Evidence image
   - Recommended code area, nhưng không sửa code
5. Đối chiếu APPX-01–APPX-04 và MAP-01–MAP-04; chỉ đóng mục nào có đủ bằng chứng.
6. Kết luận riêng cho PL.01, PL.02, PL.03: PASS/FAIL/NOT PROVABLE.
7. Danh sách acceptance test cụ thể cần bổ sung cho exporter.
8. Danh sách chính xác các file mới hoặc file đã thay đổi.

Lưu ảnh render vào:

outputs/codex-desktop-spreadsheet-qa-20260717/

Không thay đổi:

- backend/
- frontend/
- migrations/
- templates/
- tests/
- ba workbook đầu vào
- các tài liệu audit/decision/roadmap hiện có, ngoại trừ tạo báo cáo kết quả mới nêu trên

Không commit, không push, không xóa artifact hiện có. Chạy git diff --check trước khi báo cáo. Dừng sau khi tạo báo cáo QA và ảnh render.

Kết quả cuối trả lời ngắn:

- Runtime Spreadsheets có hoạt động đúng hay không.
- Ba workbook nào PASS/FAIL/NOT PROVABLE.
- Có lỗi lệch cột, merge, width, wrap, border hoặc clipping nào.
- Những MAP/APPX nào có thể đóng.
- Các file đã tạo/thay đổi.
```

## Tiêu chí nhận bàn giao

- Có bằng chứng `load_workspace_dependencies` và `@oai/artifact-tool`, không chỉ tuyên bố bằng lời.
- Có ảnh render bao phủ 100% used range của tất cả sheet trong ba workbook.
- Mỗi lỗi định dạng hoặc lệch dữ liệu có cell/range và ảnh bằng chứng.
- Không lấy việc “có số liệu” làm bằng chứng rằng số liệu đúng nghiệp vụ.
- Không có thay đổi code, schema, template hoặc workbook đầu vào.
- Báo cáo đủ cụ thể để chuyển từng finding thành acceptance test và thay đổi exporter.
