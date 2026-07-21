# Work Order — Codex Desktop focused Spreadsheet recheck

Dán phần dưới đây vào Codex Desktop:

```text
Làm việc tại repo:

D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu-recovery-ux

Nhiệm vụ: recheck trực quan lỗi REG-01 sau khi exporter PL.03 đã đổi chiều cao
dòng theo wrapped content.

Yêu cầu bắt buộc:

1. Dùng đúng skill Spreadsheets, `load_workspace_dependencies` và
   `@oai/artifact-tool`.
2. Không dùng openpyxl, pandas, xlsxwriter, LibreOffice, Excel COM hoặc
   unzip/OOXML. Nếu runtime không hoạt động thì dừng BLOCKED.
3. Không sửa code, template, workbook hoặc tài liệu hiện có. Không commit/push.
4. Đọc:
   - docs/CODEX_DESKTOP_SPREADSHEET_REGRESSION_RESULT_20260717.md
   - docs/CANONICAL_DATA_AND_APPENDIX_ASSURANCE_ROADMAP_20260716.md
   - docs/AGENT_HANDOFF.md
5. Workbook chính:
   - outputs/appendix-positive-fixture-20260717/PL.03_positive_fixture.xlsx
6. Workbook guardrail:
   - outputs/appendix-operational-review-20260717/PL.03_operational_review.xlsx

Đối với positive fixture:

- Inspect toàn bộ used range và xác nhận vẫn là `A1:AI10`, đúng 35 cột.
- Xác nhận `AG10` và `AH10` mỗi ô vẫn có hai timestamp distinct theo thứ tự
  tháng 1 rồi tháng 7; không đổi value hoặc lệch cột.
- Xác nhận row 10 cao tối thiểu 108 pt.
- Render toàn bộ `A1:AI10` và crop tập trung `Y1:AI10` ở scale đủ đọc.
- Kiểm tra trực quan cả hai timestamp trong `AG10:AH10` hiển thị đầy đủ,
  không cắt đáy, không đè border và không tràn sang ô bên cạnh.
- Xác nhận `AC10`, `AE10`, `AI10` vẫn wrap đầy đủ; cột D vẫn đọc trọn loại
  phương tiện; border, alignment, merge header và print layout không bị vỡ.
- Scan formula/display errors và nhãn sai `Teus|Tues|Quá cảng|sum_total`.

Đối với operational guardrail:

- Inspect `A1:AI56`; xác nhận 47 dòng Salan, `I10:AI56` trống, không trùng
  registration và không phát sinh dữ liệu hoạt động giả.
- Render full sheet và ít nhất crop `Y1:AI20`; xác nhận tăng chiều cao động
  không làm vỡ bố cục các dòng tĩnh, border hoặc header.

Tạo file mới:

docs/CODEX_DESKTOP_SPREADSHEET_REGRESSION_RECHECK_RESULT_20260717.md

Lưu inspect và render tại:

outputs/codex-desktop-spreadsheet-regression-recheck-20260717/

Báo cáo rõ:

- REG-01: CLOSED hoặc OPEN.
- Positive PL.03 visual gate: PASS/FAIL.
- Operational PL.03 guardrail: PASS/FAIL.
- Overall Spreadsheet implementation gate: PASS/FAIL.
- Live business data evidence: vẫn NOT PROVABLE; không được dùng fixture
  synthetic để khẳng định dữ liệu khách hàng thật.
- Danh sách chính xác file tạo/thay đổi và kết quả `git diff --check`.

Chỉ đề xuất đóng Spreadsheet implementation gate nếu cả positive PL.03 và
operational PL.03 guardrail đều PASS. Không tự sửa bất kỳ lỗi nào phát hiện.
```
