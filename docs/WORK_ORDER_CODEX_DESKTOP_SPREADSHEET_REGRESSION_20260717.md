# Work Order — Codex Desktop Spreadsheet Regression sau sửa

Dán phần dưới đây vào Codex Desktop:

```text
Làm việc tại repo:

D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu-recovery-ux

Dùng đúng skill Spreadsheets, load_workspace_dependencies và @oai/artifact-tool để kiểm tra hai bộ workbook do application exporter mới tạo.

Bộ A — operational review từ DB hiện tại:

- outputs/appendix-operational-review-20260717/PL.01_operational_review.xlsx
- outputs/appendix-operational-review-20260717/PL.02_operational_review.xlsx
- outputs/appendix-operational-review-20260717/PL.03_operational_review.xlsx
- outputs/appendix-operational-review-20260717/manifest.json

Bộ B — positive fixture synthetic:

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

1. Bộ A/PL.01 có đúng 47 dòng Salan; cột hồ sơ A:H và P giữ dữ liệu hiện có; vùng hoạt động I:O trống vì DB có 0 declaration APPROVED. Không được coi dòng tĩnh là hoạt động giả.
2. Bộ A/PL.02 có toàn bộ chỉ tiêu C:P trống, không phải zero, vì không có hoạt động APPROVED.
3. Bộ A/PL.03 có đúng 47 dòng Salan; B:H giữ dữ liệu hồ sơ hiện có; I:AI trống. Không có dòng trùng hoặc dữ liệu tĩnh rơi vào cột hoạt động.
4. Bộ B/PL.01 có đầy đủ title, ngày, tên doanh nghiệp, ghi chú, bảng 16 cột và khối ký; H là sức chở thiết kế, O là thực tế; I/K/đích không lệch và K là departure berth.
5. Bộ B/PL.02 có title, `Tháng 07 năm 2046`, đơn vị báo cáo và đúng cụm `Thực hiện tháng báo cáo` / `Lũy kế đến tháng báo cáo`; số tháng 7 khác số lũy kế tháng 1–7; blank không bị đổi thành zero giả.
6. Bộ B/PL.03 có đúng 35 cột, chỉ một dòng cho phương tiện QA dù có hai declaration; cargo/tấn/TEUs/TEUs rỗng được cộng đúng; cargo name, ngày, cảng và Đại lý PTND giữ giá trị distinct theo thứ tự trong cùng cell.
7. Tất cả nhãn là `TEUs`, `TEUs Rỗng`, `Quá cảnh`; không còn `Teus` hoặc `Tues`.
8. Cột D PL.03 không clipping; kiểm tra wrap, row height, width, border, merge và alignment.
9. Không có formula error, cột kỹ thuật hoặc dữ liệu lệch cột.

Phân biệt fixture synthetic với dữ liệu vận hành. Không dùng fixture này để khẳng định dữ liệu khách hàng thật đúng; chỉ dùng nó để chứng minh mapping/exporter positive path.

Tạo:

docs/CODEX_DESKTOP_SPREADSHEET_REGRESSION_RESULT_20260717.md

Lưu render tại:

outputs/codex-desktop-spreadsheet-regression-20260717/

Báo cáo từng APPX-01–04 và MAP-01–05 theo hai lớp:

- Implementation evidence: PASS/FAIL
- Live business data evidence: PROVEN/NOT PROVABLE

Chỉ đề xuất đóng implementation item nếu cả Bộ A và Bộ B đều PASS. Có thể xác nhận implementation bằng fixture synthetic, nhưng phải giữ `Live business data evidence = NOT PROVABLE` cho đến khi có declaration thật được duyệt. Không commit, không push. Chạy git diff --check và báo chính xác file tạo/thay đổi.
```
