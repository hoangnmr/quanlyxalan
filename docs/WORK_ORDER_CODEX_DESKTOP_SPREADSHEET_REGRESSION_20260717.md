# Work Order — Codex Desktop Spreadsheet Regression sau sửa

Dán phần dưới đây vào Codex Desktop:

```text
Làm việc tại repo:

D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu-recovery-ux

Dùng đúng skill Spreadsheets, load_workspace_dependencies và @oai/artifact-tool để kiểm tra ba workbook positive fixture do application exporter mới tạo:

- outputs/appendix-positive-fixture-20260717/PL.01_positive_fixture.xlsx
- outputs/appendix-positive-fixture-20260717/PL.02_positive_fixture.xlsx
- outputs/appendix-positive-fixture-20260717/PL.03_positive_fixture.xlsx

Không dùng openpyxl, pandas, xlsxwriter, LibreOffice, Excel COM hoặc unzip/OOXML. Nếu runtime không hoạt động thì dừng BLOCKED. Không sửa code, template hoặc workbook.

Đọc và đối chiếu:

- docs/CODEX_DESKTOP_SPREADSHEET_QA_RESULT_20260717.md
- docs/APPENDIX_BUSINESS_DECISION_REGISTER_20260717.md
- docs/DATA_FIELD_CATALOG.md
- docs/DATA_INHERITANCE_RULES.md
- docs/REPORT_IMPLEMENTATION_PLAN_20260717.md

Kiểm tra toàn bộ used range và render 100% tất cả sheet. Xác minh:

1. PL.01 có đầy đủ title, ngày, tên doanh nghiệp, ghi chú, bảng 16 cột và khối ký; H là sức chở thiết kế, O là thực tế; I/K/đích không lệch và K là departure berth.
2. PL.02 có title, `Tháng 07 năm 2046`, đơn vị báo cáo và đúng cụm `Thực hiện tháng báo cáo` / `Lũy kế đến tháng báo cáo`; số tháng 7 khác số lũy kế tháng 1–7; blank không bị đổi thành zero giả.
3. PL.03 có đúng 35 cột, chỉ một dòng cho phương tiện QA dù có hai declaration; cargo/tấn/TEUs/TEUs rỗng được cộng đúng; cargo name, ngày, cảng và Đại lý PTND giữ giá trị distinct theo thứ tự trong cùng cell.
4. Tất cả nhãn là `TEUs`, `TEUs Rỗng`, `Quá cảnh`; không còn `Teus` hoặc `Tues`.
5. Cột D PL.03 không clipping; kiểm tra wrap, row height, width, border, merge và alignment.
6. Không có formula error, cột kỹ thuật hoặc dữ liệu lệch cột.

Phân biệt fixture synthetic với dữ liệu vận hành. Không dùng fixture này để khẳng định dữ liệu khách hàng thật đúng; chỉ dùng nó để chứng minh mapping/exporter positive path.

Tạo:

docs/CODEX_DESKTOP_SPREADSHEET_REGRESSION_RESULT_20260717.md

Lưu render tại:

outputs/codex-desktop-spreadsheet-regression-20260717/

Báo cáo từng APPX-01–04 và MAP-01–05 theo hai lớp:

- Implementation evidence: PASS/FAIL
- Live business data evidence: PROVEN/NOT PROVABLE

Chỉ đề xuất đóng implementation item nếu workbook và render đều PASS. Không commit, không push. Chạy git diff --check và báo chính xác file tạo/thay đổi.
```
