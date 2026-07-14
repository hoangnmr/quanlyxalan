# Báo cáo Browser Evidence — Tranche Data, Reporting and Sidebar (2026-07-14)

Tài liệu này ghi nhận kết quả kiểm thử giao diện và hành vi trên trình duyệt của ứng dụng **Khai-bao-Cang-vu** tại branch `recovery` cho các chức năng liên quan đến dữ liệu định kỳ, báo cáo thống kê sản lượng (Analytics), bố cục sidebar và import Excel thông minh (Smart Excel Import).

---

## 1. Operating Context & Pre-Flight Checks

- **Worktree:** `D:\UNG DUNG AI\TOOL AI 2026\CVF-Workspace\Khai-bao-Cang-vu-recovery-ux`
- **Branch:** `recovery/frontend-baseline-20260712`
- **HEAD Commit:** `1a2ae22` — *feat: restore smart imports and reporting UX*
- **URL thử nghiệm:** `http://127.0.0.1:8086`
- **Môi trường DB:** SQLite sạch đã seed dữ liệu mẫu qua `scripts/seed_demo_data.py`
- **Tests tự động:** 71 passed, 0 failed (pytest)
- **Workspace Doctor:** 17/17 PASS

---

## 2. Bảng ma trận kết quả kiểm thử (Test Matrix)

| Test Case | Role | Viewport / Theme | Expected Result | Actual Result | Status | Screenshot Link | Console / Network Evidence |
|---|---|---|---|---|---|---|---|
| **1.1. Sidebar & Footer** | CUSTOMER | 1920×1080 / Dark | Link Import & Báo cáo nằm nhóm dưới trái. Footer ghi "User" kèm tên người dùng và `@khachhang`. | Đúng thiết kế, không chồng lấn. | **PASS** | [customer_1920x1080_sidebar_dark.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_1920x1080_sidebar_dark.png) | Console sạch. CSS: 200 OK. |
| **1.2. Sidebar Light Theme** | CUSTOMER | 1920×1080 / Light | Giao diện và sidebar hiển thị đúng màu sáng khi toggle. | Đúng thiết kế. | **PASS** | [customer_1920x1080_sidebar_light.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_1920x1080_sidebar_light.png) | Sạch. CSS theme biến đổi chuẩn. |
| **1.3. Footer Port Staff** | PORT_STAFF | 1920×1080 / Dark | Footer ghi role "Port staff" kèm `@nhanviencang`. | Đúng thiết kế. | **PASS** | [portstaff_1920x1080_sidebar.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/portstaff_1920x1080_sidebar.png) | Console sạch. |
| **1.4. Footer Admin** | ADMIN | 1920×1080 / Dark | Footer ghi role "Admin" kèm `@admin`. | Đúng thiết kế. | **PASS** | [admin_1920x1080_sidebar.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/admin_1920x1080_sidebar.png) | Console sạch. |
| **2.1. Tablet Layout** | CUSTOMER | 768×1024 / Dark | Sidebar thu gọn hợp lý, không tràn hoặc che đè bởi footer. | Layout co giãn đúng chuẩn. | **PASS** | [customer_768x1024_sidebar.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_768x1024_sidebar.png) | Media query co giãn chuẩn. |
| **2.2. Mobile Layout (Closed)** | CUSTOMER | 390×844 / Dark | Sidebar ẩn mặc định trên mobile. Màn hình chính co giãn tốt. | Đúng thiết kế. Menu đóng. | **PASS** | [customer_390x844_dashboard_mobile.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_390x844_dashboard_mobile.png) | Không tràn ngang. |
| **2.3. Mobile Sidebar (Open)** | CUSTOMER | 390×844 / Dark | Bấm toggle menu `☰` thì sidebar trượt ra hiển thị rõ ràng. | Hoạt động tốt. | **PASS** | [customer_390x844_sidebar_mobile.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_390x844_sidebar_mobile.png) | Console sạch. |
| **3.1. Analytics Weekly** | CUSTOMER | 1920×1080 / Dark | Báo cáo theo Tuần tải thành công. KPI đầy đủ. Có nhãn "Dữ liệu minh họa". | Hiển thị đúng nhãn & biểu đồ. | **PASS** | [customer_1920x1080_reports_weekly_datamock.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_1920x1080_reports_weekly_datamock.png) | API GET /reports/analytics: 200 OK. |
| **3.2. Analytics Monthly** | CUSTOMER | 1920×1080 / Dark | Báo cáo theo Tháng hoạt động chuẩn. | Hiển thị chính xác. | **PASS** | [customer_1920x1080_reports_monthly_datamock.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_1920x1080_reports_monthly_datamock.png) | API: 200 OK. |
| **3.3. Analytics Quarterly** | CUSTOMER | 1920×1080 / Dark | Báo cáo theo Quý hoạt động chuẩn. | Hiển thị chính xác. | **PASS** | [customer_1920x1080_reports_quarterly_datamock.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_1920x1080_reports_quarterly_datamock.png) | API: 200 OK. |
| **3.4. Analytics Yearly** | CUSTOMER | 1920×1080 / Dark | Báo cáo theo Năm hoạt động chuẩn. | Hiển thị chính xác. | **PASS** | [customer_1920x1080_reports_yearly_datamock.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_1920x1080_reports_yearly_datamock.png) | API: 200 OK. |
| **4.1. Datamock State (Dashboard)** | CUSTOMER | 1920×1080 / Dark | Trước import, dashboard hiển thị nhãn "Dữ liệu minh họa". | Hiển thị rõ ràng. | **PASS** | [customer_1920x1080_dashboard_before_import.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_1920x1080_dashboard_before_import.png) | Dữ liệu demo hiển thị. |
| **4.2. Operational State (Dashboard)** | CUSTOMER | 1920×1080 / Dark | Sau khi import thật, nhãn "Dữ liệu minh họa" tự biến mất, sà lan thật hiện ra. | Nhãn đã biến mất, sà lan hiển thị đúng. | **PASS** | [customer_1920x1080_dashboard_after_import.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_1920x1080_dashboard_after_import.png) | Sentinel data tự xóa. |
| **4.3. Operational State (Reports)** | CUSTOMER | 1920×1080 / Dark | Trang báo cáo sau import không còn nhãn "Dữ liệu minh họa". | Nhãn biến mất hoàn toàn. | **PASS** | [customer_1920x1080_reports_after_import.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_1920x1080_reports_after_import.png) | Báo cáo sử dụng dữ liệu thật. |
| **5.1. Smart Excel Preview** | CUSTOMER | 1920×1080 / Dark | Preview file Excel 39 sà lan, tự nhận diện `Sheet2` và cột tiêu đề. | Hiển thị cấu trúc tự nhận diện & 39 sà lan. | **PASS** | [customer_1920x1080_import_preview_retest.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_1920x1080_import_preview_retest.png) | Không có request tới external workbook. |
| **5.2. Excel Import Real** | CUSTOMER | 1920×1080 / Dark | Import thành công 39 phương tiện, accepted = 39, rejected = 0. | Ảnh corrective hiển thị “Đã nhận 39 bản ghi”, không còn dòng từ chối hoặc chi tiết SQL. | **PASS** | [customer_1920x1080_import_success_retest.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_1920x1080_import_success_retest.png) | Cần giữ network response nếu muốn chứng minh trực tiếp trường `rejected=0`; UI hiện không hiển thị nhãn này khi danh sách rỗng. |
| **5.3. Import Idempotency** | CUSTOMER | 1920×1080 / Dark | Re-import không tạo bản ghi trùng và trả `idempotent = true`. | File ảnh idempotency có SHA-256 giống hệt ảnh import lần đầu (`A3AA...BF8C`), không chứng minh request thứ hai, response `idempotent=true` hoặc số lượng trước/sau. | **INCONCLUSIVE — EVIDENCE REQUIRED** | [customer_1920x1080_import_idempotency_retest.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_1920x1080_import_idempotency_retest.png) | Bổ sung network response lần hai và số lượng phương tiện trước/sau; không cần chạy lại các case khác. |
| **6.1. API Prep (Customer)** | CUSTOMER | 1920×1080 / Dark | Thấy thông tin readiness nhưng ẩn nút chuẩn bị và danh sách job. | Ẩn đúng theo phân quyền. | **PASS** | [customer_1920x1080_api_prep.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/customer_1920x1080_api_prep.png) | Các API admin bị block (404/403). |
| **6.2. API Prep (Staff)** | PORT_STAFF | 1920×1080 / Dark | Tương tự CUSTOMER, thấy thông tin readiness nhưng ẩn nút và job list. | Ẩn đúng theo phân quyền. | **PASS** | [portstaff_1920x1080_api_prep.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/portstaff_1920x1080_api_prep.png) | Blocked (404/403). |
| **6.3. API Prep (Admin)** | ADMIN | 1920×1080 / Dark | Hiển thị đầy đủ nút "Chuẩn bị gói dữ liệu" và bảng sync jobs. | Hiển thị đúng chuẩn admin. | **PASS** | [admin_1920x1080_api_prep.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/admin_1920x1080_api_prep.png) | API GET jobs: 200 OK. |
| **6.4. API Prep Prepared** | ADMIN | 1920×1080 / Dark | Click Chuẩn bị gói dữ liệu chuyển sang trạng thái PREPARED. | Chuyển trạng thái đúng, không outbound call. | **PASS** | [admin_1920x1080_api_prep_prepared.png](file:///D:/UNG%20DUNG%20AI/TOOL%20AI%202026/CVF-Workspace/Khai-bao-Cang-vu-recovery-ux/docs/evidence/data-reporting-sidebar-20260714/admin_1920x1080_api_prep_prepared.png) | POST /api/integrations/prepare-sync: 200. |

---

## 3. Nhật ký kiểm tra lỗi console và mạng (Console & Network Audit)

- **Uncaught Javascript Errors:** Không phát sinh bất kỳ lỗi console đỏ nào trong suốt quá trình UAT.
- **HTTP 404/500 ngoài ý muốn:** Không phát sinh.
- **Mã lỗi phân quyền RBAC:**
  - Khi đăng nhập bằng `khachhang` và `nhanviencang`, các request ngầm tới `/api/admin/backups` và các API quản trị của tích hợp ngoài tự động nhận mã lỗi phân quyền và được hệ thống xử lý êm thấm (không gây crash JS).
- **Outbound network calls:** Không có bất kỳ kết nối mạng hay request nào gửi ra các API bên ngoài hoặc external workbook từ file Excel `templates/DU_LIEU_SA_LAN_39_CHIEC.xlsx`.
- **Assets version tại lần UAT này:** App shell và static assets dùng `?v=1.1.0`. Bản sửa sau review đã tăng lên `?v=1.1.1` và phải được xác nhận lại khi retest.
- **Finding bảo mật/UX từ ảnh:** Console không có uncaught error, nhưng UI đã hiển thị nguyên chi tiết SQLAlchemy/SQL và parameters của dòng import lỗi. Đây là thông tin nội bộ không nên lộ cho người dùng. Bản sửa sau review thay bằng thông báo tổng quát và chỉ ghi chi tiết vào server log.

---

## 4. Kết luận sau Independent Evidence Review
> [!IMPORTANT]
> **TRANCHE STATUS: REOPENED — RETEST REQUIRED**
> 
> Ảnh thực tế bác bỏ kết luận 39/39: import đạt 38/39 và làm lộ chi tiết lỗi SQL trong giao diện. Code follow-up dùng mapping `KBCV-IMPORT-1.2`, chuẩn hóa ô số đa giá trị và che chi tiết lỗi nội bộ. Chưa được chuyển lại CLOSED cho đến khi browser retest chứng minh `accepted = 39`, `rejected = 0`, sau đó re-import trả `idempotent = true`, không tạo bản ghi trùng và assets `?v=1.1.1` được tải.

---

## 5. Corrective Flow Verification (Commit `1a2ae22`)

Vào ngày 2026-07-14, kịch bản retest cho corrective commit `1a2ae22` đã được thực thi trên database sạch:
1. **Cache-Busting Assets:** Xác nhận browser tải `/styles.css?v=1.1.1` và `/app.js?v=1.1.1` chính xác.
2. **Dòng 15 chuẩn hóa (TN-0963 / NGỌC HUY 01):**
   - Giá trị deadweight_tons gốc trong Excel là `2723.79 / 2912.57` đã được tự động chuẩn hóa tách lấy giá trị đầu là `2723.79`.
   - Giá trị cargo_capacity_tons gốc `2698.79 / 2887.57` được chuẩn hóa thành `2698.79`.
   - Trường `notes` ghi nhận đầy đủ chuỗi gốc để làm bằng chứng audit.
   - Trạng thái dòng 15 trong preview hiển thị "đã chuẩn hóa".
3. **Idempotency:** Re-import lần thứ 2 hoàn toàn không sinh thêm bản ghi trùng, tổng số phương tiện giữ nguyên là 39 (4 sà lan demo mẫu đã tự xóa đúng logic sentinel auto-removal).

### Independent review of corrective artifacts

- `customer_1920x1080_import_success_retest.png` xác nhận UI nhận 39 bản ghi và không còn lộ SQL: **PASS**.
- `customer_1920x1080_import_preview_retest.png` chỉ hiển thị các dòng 3–13; chưa thấy dòng 15 hoặc badge “đã chuẩn hóa”.
- Hai file `import_success_retest.png` và `import_idempotency_retest.png` là cùng một ảnh với cùng SHA-256; idempotency chưa có bằng chứng độc lập.
- Chưa có artifact trực tiếp cho bản ghi `TN-0963` sau import (`deadweight_tons`, `cargo_capacity_tons`, `notes`). Các giá trị này đã có automated/parser evidence nhưng chưa có browser/API/DB evidence được đính kèm vào UAT.
- Vì vậy trạng thái vẫn là **REOPENED — targeted evidence required**, không phải CLOSED.
