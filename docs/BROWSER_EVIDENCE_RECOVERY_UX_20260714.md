# Báo cáo Browser Evidence — Recovery UX (2026-07-14)

Tài liệu này ghi nhận kết quả kiểm thử trực tiếp giao diện và hành vi trên trình duyệt của ứng dụng **Khai-bao-Cang-vu** tại branch `recovery`.

---

## 1. Môi trường và bối cảnh kiểm thử

- **Worktree:** `D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu-recovery-ux`
- **Branch:** `recovery/frontend-baseline-20260712`
- **HEAD Commit:** `e5601c7` (docs: record recovery runtime fixes)
- **Kiểm tra lịch sử:** Đầy đủ các commit `0b2ba72`, `5e74643`, `e5601c7`.
- **URL thử nghiệm:** `http://127.0.0.1:8086`
- **Thời gian thực hiện:** 2026-07-14 (Giờ hệ thống)
- **Môi trường DB:** Database SQLite sạch (`data/cang_vu.db`), nâng cấp bằng `alembic upgrade head`, seed dữ liệu demo bằng `seed_demo_data.py`, bootstrap tài khoản admin bằng `bootstrap_admin.py`.
- **Tài khoản sử dụng:**
  - Khách hàng: `khachhang` / `demo123`
  - Nhân viên Cảng: `nhanviencang` / `demo123`
  - Quản trị viên: `admin` / `demo123`

---

## 2. Ma trận Viewport × Role × Scenario

| Role | Viewport | Kịch bản / Luồng chính | Kết quả | Chi tiết / Screenshot |
|---|---|---|---|---|
| **CUSTOMER** | Desktop (1920×1080) | Đăng nhập & xem Dashboard | **PASS** | `customer_1920x1080_dashboard_pass.png` |
| | | Tạo phiếu / Mở wizard | **FAIL** | **JS Crash!** `customer_1920x1080_wizard-crash_fail.png` |
| | | Trang Báo cáo | **PARTIAL** | Thống kê sản lượng báo chưa khả dụng tốt; nhưng khu vực Kết nối ngoài vẫn hiện. `customer_1920x1080_reports-no-errors_pass.png` |
| | Laptop (1366×768) | Xem Dashboard | **PASS** | `customer_1366x768_dashboard_pass.png` |
| | | Trang Báo cáo | **PARTIAL** | Giống Desktop. `customer_1366x768_reports-no-errors_pass.png` |
| | Mobile (390×844) | Xem Dashboard | **PASS** | `customer_390x844_dashboard_pass.png` |
| | | Menu điều hướng (hamburger) | **PASS** | Menu mở rộng tốt. `customer_390x844_menu-open_pass.png` |
| | | Trang Báo cáo | **PARTIAL** | Giống Desktop. `customer_390x844_reports_pass.png` |
| **PORT_STAFF**| Desktop (1920×1080) | Xem Dashboard & Menu ẩn | **PASS** | Không thấy nút tạo phiếu/import. `port-staff_1920x1080_dashboard_pass.png` |
| | | Chi tiết & timeline phiếu | **PASS** | Thấy timeline và form thao tác Cảng. |
| | | Thao tác Yêu cầu bổ sung | **PASS** | Chặn nếu note rỗng (`port-staff_1920x1080_request-changes_fail.png`); lưu được nếu điền note (`port-staff_1920x1080_request-changes_pass.png`). |
| | | Khách hàng xem lại lý do | **PASS** | Khách hàng thấy lý do phản hồi. `customer_1920x1080_view-changes-request_pass.png` |
| | Laptop (1366×768) | Chi tiết phiếu | **PASS** | `port-staff_1366x768_details_pass.png` |
| | Mobile (390×844) | Chi tiết phiếu | **PASS** | Layout modal co giãn phù hợp. `port-staff_390x844_details_pass.png` |
| **ADMIN** | Desktop (1920×1080) | Dashboard quản trị & backup | **PASS** | `admin_1920x1080_dashboard_pass.png` |
| | | Quyền hạn & Giới hạn duyệt | **PASS** | Không thấy nút tạo phiếu, không duyệt thay Port Staff. |
| | | Trang Báo cáo | **PASS** | Tích hợp ngoài xuất hiện cho Admin & gọi API thành công không bị 403. `admin_1920x1080_reports_pass.png` |

---

## 3. Danh sách Screenshot Evidence

Tất cả các screenshot được lưu trữ tại thư mục:
`docs/evidence/recovery-ux-20260714/`

1. [customer_1920x1080_dashboard_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_1920x1080_dashboard_pass.png)
2. [customer_1920x1080_wizard-crash_fail.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_1920x1080_wizard-crash_fail.png)
3. [customer_1920x1080_reports-no-errors_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_1920x1080_reports-no-errors_pass.png)
4. [customer_1366x768_dashboard_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_1366x768_dashboard_pass.png)
5. [customer_1366x768_reports-no-errors_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_1366x768_reports-no-errors_pass.png)
6. [customer_390x844_dashboard_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_390x844_dashboard_pass.png)
7. [customer_390x844_menu-open_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_390x844_menu-open_pass.png)
8. [customer_390x844_reports_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_390x844_reports_pass.png)
9. [port-staff_1920x1080_dashboard_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/port-staff_1920x1080_dashboard_pass.png)
10. [port-staff_1920x1080_request-changes_fail.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/port-staff_1920x1080_request-changes_fail.png)
11. [port-staff_1920x1080_request-changes_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/port-staff_1920x1080_request-changes_pass.png)
12. [customer_1920x1080_view-changes-request_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/customer_1920x1080_view-changes-request_pass.png)
13. [port-staff_1366x768_details_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/port-staff_1366x768_details_pass.png)
14. [port-staff_390x844_details_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/port-staff_390x844_details_pass.png)
15. [admin_1920x1080_dashboard_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/admin_1920x1080_dashboard_pass.png)
16. [admin_1920x1080_reports_pass.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/recovery-ux-20260714/admin_1920x1080_reports_pass.png)

---

## 4. Console & Network Evidence

### A. Lỗi Console và sự cố Crash Wizard
- **Mô tả:** Khi bấm nút **"+ Tạo phiếu"** hoặc **"Mở phiếu"** (đối với nháp), toàn bộ wizard không thể hiển thị và Console báo lỗi:
  ```
  TypeError: Cannot read properties of null (reading 'querySelectorAll')
      at $$ (http://127.0.0.1:8086/app.js:9:52)
      at reviewSummaryHtml (http://127.0.0.1:8086/app.js:681:23)
      at renderDeclarationWizard (http://127.0.0.1:8086/app.js:759:9)
      at openDeclaration (http://127.0.0.1:8086/app.js:485:3)
  ```
- **Nguyên nhân gốc:** Hàm `renderDeclarationWizard` gọi `reviewSummaryHtml(d)` để tạo chuỗi HTML của Bước 6 trong khi toàn bộ chuỗi HTML này chưa được gán vào `#declaration-fields` (đang nằm trong template literal). Lúc này, `reviewSummaryHtml` gọi `$$('input[name="crew_ids"]:checked', $('#declaration-crew-container'))` nhằm đếm thuyền viên đã chọn ở Bước 4. Do `#declaration-crew-container` chưa được render ra DOM thực tế nên `$('#declaration-crew-container')` trả về `null`, làm hàm `$$` crash khi cố gọi `.querySelectorAll()` trên `null`.

### B. Network Requests
- **Đăng ký/Login:** Trả về mã thông báo JWT thành công.
- **GET /api/reports/analytics:** Bị chặn ở frontend (không gọi), hiển thị "Thống kê sản lượng chưa khả dụng". Không phát sinh lỗi mạng 404.
- **GET /api/integrations/maritime-authority:** 
  - CUSTOMER/PORT_STAFF: Không gọi ở frontend, do đó không phát sinh lỗi 403.
  - ADMIN: Gọi thành công, nhận dữ liệu trạng thái kết nối tích hợp bình thường.

---

## 5. Keyboard & Accessibility Evidence

- **Tab/Shift+Tab:** Hoạt động tốt trên navigation menu và trường form. Thao tác chuyển focus rõ ràng.
- **Focus Ring:** Vòng focus có viền màu xanh (teal) hiển thị rõ ràng trên các nút và input nhờ CSS selector `:focus-visible` trong `styles.css`.
- **Keyboard Trap:** Không phát sinh keyboard trap nào ngoài vùng các modal dialog đang hoạt động.
- **Accessibility trên Mobile:** Do lỗi sidebar mobile menu bị che khuất / thiếu khả năng cuộn dọc ở phía cuối (scrolling/overflow constraint), nút **Đăng xuất** bị kẹt ở vùng khuất màn hình và không thể focus bằng Tab/Shift+Tab hay click được trên mobile layout chuẩn (390x844). Phải chuyển đổi rộng hơn để click.

---

## 6. Danh sách Findings và Phân lớp Kết luận

### Finding 1: Wizard bị Crash JavaScript khi mở (CRITICAL - FAIL)
- **Severity:** Critical
- **Tái hiện:** Đăng nhập `khachhang` -> Bấm nút "+ Tạo phiếu" hoặc bấm "Mở phiếu" đối với một phiếu ở trạng thái Nháp.
- **Expected:** Giao diện Dialog mở ra và hiển thị Wizard 6 bước bắt đầu từ bước 1.
- **Actual:** Giao diện đơ, dialog đen mờ bao phủ nhưng form trống rỗng không xuất hiện. F12 Console hiển thị lỗi `TypeError: Cannot read properties of null (reading 'querySelectorAll')` ở `app.js:681`.

### Finding 2: Khu vực "Kết nối dữ liệu bên ngoài" vẫn hiển thị cho Khách hàng/Staff do CSS ghi đè HTML `hidden` (SERIOUS - FAIL)
- **Severity:** Serious
- **Tái hiện:** Đăng nhập `khachhang` hoặc `nhanviencang` -> Vào trang Báo cáo hoạt động Cảng.
- **Expected:** Khu vực tích hợp bên ngoài (external integration panel) bị ẩn đối với vai trò phi Admin (theo cam kết sửa lỗi của commit `5e74643`).
- **Actual:** Khách hàng vẫn nhìn thấy khu vực "KẾT NỐI DỮ LIỆU BÊN NGOÀI" cùng nút "Chuẩn bị gói dữ liệu".
- **Nguyên nhân gốc:** Thuộc tính `hidden` của HTML5 chỉ định `display: none` mặc định. Tuy nhiên, class `.integration-panel` và `.panel` trong `styles.css` có CSS rules chỉ định `display: grid;` hoặc `display: block;`. Do độ ưu tiên (specificity) của class selector cao hơn attribute selector của trình duyệt, thuộc tính `hidden` bị ghi đè hoàn toàn, làm phần tử luôn luôn hiển thị bất kể thuộc tính `hidden` được đặt là gì bằng JS.

### Finding 3: Không thể cuộn menu sidebar trên Mobile để Đăng xuất (MODERATE - FAIL)
- **Severity:** Moderate
- **Tái hiện:** Resize màn hình sang viewport mobile (390×844) -> Bấm nút '☰' để mở menu -> Cố gắng cuộn xuống dưới cùng để bấm nút "Đăng xuất".
- **Expected:** Menu sidebar có thanh cuộn và có thể cuộn xuống dưới cùng để tương tác với nút Đăng xuất.
- **Actual:** Menu sidebar bị giới hạn chiều cao cố định và thiếu thuộc tính `overflow-y: auto`, nút Đăng xuất bị đẩy xuống dưới mép màn hình và không thể cuộn tới để nhấn.

---

## 7. Phân lớp Kết luận và Trạng thái Gate 5

### Phân lớp trạng thái:
- **ĐÃ CHỨNG MINH (PASS):**
  - Dashboard phân vai trò chuẩn (Dashboard stats, Admin operations, Admin backup).
  - Reports title đổi thành "Báo cáo hoạt động Cảng" và fallback "Thống kê sản lượng chưa khả dụng" chạy đúng, không phát sinh lỗi 404/403 trên mạng đối với khách hàng/staff.
  - Quy trình xử lý của Nhân viên Cảng (duyệt/yêu cầu bổ sung) có timeline, bắt buộc ghi chú khi trả lại phiếu và khách hàng nhìn thấy lý do.
  - Quyền Admin: xem tích hợp ngoài không bị 403, xem dashboard backup/operations hoạt động bình thường.
- **FAIL — TÁI HIỆN ĐƯỢC:**
  - Finding 1: Crash Wizard khi mở phiếu / tạo phiếu.
  - Finding 2: CSS ghi đè HTML `hidden` làm lộ panel Kết nối ngoài cho Khách hàng/Staff.
  - Finding 3: Không cuộn được menu Mobile để Đăng xuất.
- **CHƯA CHỨNG MINH:** Không có (tất cả các scenario đã được thử nghiệm thực tế trong browser).
- **BLOCKED:**
  - Kiểm thử Accessibility tự động (Axe-core/Lighthouse): **NOT RUN** (không khả dụng trong môi trường).
  - Kiểm thử Wizard sâu hơn (các trường tự điền, checklist thuyền viên Tab/Space, validation aria-invalid): **BLOCKED** do lỗi Crash Wizard ngăn cản việc tải form.

### Kết luận Gate 5:
> [!WARNING]
> **GATE 5 STATUS: NOT READY (FAIL)**
> 
> Do phát sinh lỗi nghiêm trọng **Crash Wizard (Finding 1)** ngăn chặn hoàn toàn luồng nghiệp vụ tạo/sửa phiếu của Khách hàng, và lỗi bảo mật/hiển thị **Lộ panel Kết nối ngoài cho Khách hàng/Staff do lỗi CSS (Finding 2)**, dự án recovery **CHƯA ĐỦ ĐIỀU KIỆN** để đóng Gate 5. Cần sửa các lỗi giao diện/CSS này trước khi tổ chức UAT chính thức.
