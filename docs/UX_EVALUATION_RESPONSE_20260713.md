# Phản hồi Đánh giá UX/Product Độc lập — Khai-báo Cảng-vụ

**Ngày:** 2026-07-13  
**Phương pháp:** Heuristic review (source code) + API functional test + Performance measurement  
**Phạm vi:** Theo yêu cầu của `docs/UX_PRODUCT_INDEPENDENT_EVALUATION_20260713.md`  
**Môi trường test:** Windows 11, Local server (`http://127.0.0.1:8080`), SQLite DB, Python .venv

> [!IMPORTANT]
> Browser subagent (tương tác trực quan) bị giới hạn quota tại thời điểm test. Các kết quả UX behavioral (thời gian hoàn thành task, tỷ lệ hoàn thành không trợ giúp) **chưa thu thập được** — được phân loại vào lớp **Chưa chứng minh**. Các kết quả API, RBAC, asset size, và code-level heuristic **đã có bằng chứng thực tế**.

---

## 1. Kết quả Performance (Bằng chứng trực tiếp)

**Phương pháp:** Warm local run, 3 mẫu mỗi chỉ số, lấy median.  
**Điều kiện:** SQLite DB, ~5 records, không cache, PowerShell `Measure-Command`.

| Chỉ số | Mẫu 1 | Mẫu 2 | Mẫu 3 | **Median** | Ngưỡng | Kết quả |
|---|---|---|---|---|---|---|
| Dashboard API | 59.9 ms | 11.2 ms | 8.9 ms | **11.2 ms** | ≤500 ms | ✅ PASS |
| Declarations list (25 items) | 21.9 ms | 6.9 ms | 7.6 ms | **7.6 ms** | ≤750 ms | ✅ PASS |
| Draft save (POST /api/declarations) | 49.2 ms | 23.8 ms | — | **~36 ms** | ≤1000 ms | ✅ PASS |
| Document + JS + CSS total size | 22340 B | 75913 B | 26839 B | **122.2 KB total** | ≤750 KB | ✅ PASS |

> [!NOTE]
> Mẫu 1 Dashboard cao hơn (cold start sau idle). Median phản ánh warm path. Kết quả ổn định ở warm run.

---

## 2. Kết quả RBAC / Security Enforcement (Bằng chứng trực tiếp)

**Phương pháp:** HTTP request trực tiếp bằng PowerShell, token từ login API thực.

| Test case | Endpoint | Role | HTTP response | Kết quả |
|---|---|---|---|---|
| CUSTOMER truy cập admin endpoint | `GET /api/admin/operations-summary` | CUSTOMER | **403 Forbidden** | ✅ PASS |
| CUSTOMER cố approve phiếu | `POST /api/declarations/1/workflow` | CUSTOMER | **403 Forbidden** | ✅ PASS |
| Unauthenticated truy cập dashboard | `GET /api/dashboard` | (no token) | **401 Unauthorized** | ✅ PASS |
| CV liệt kê vessels | `GET /api/vessels` | CV | **200 OK** (1 record) | ✅ Hợp lệ |

---

## 3. Kết quả Heuristic Review (Code-level Evidence)

### 3.1 Wizard UX — Thứ tự bước

```
Bước 1: A. Thông tin chung và phương tiện
Bước 2: E. Thuyền trưởng & thuyền viên
Bước 3: B. Hành trình
Bước 4: C/D. Hàng hóa dỡ/xếp
Bước 5: Đính kèm
Bước 6: F. Xem lại & Gửi
```

**Bằng chứng:** `app.js` L441-448 (`DECLARATION_STEPS`), L616-671 (render logic).

Nhãn section trong HTML không theo A→B→C→D→E, mà là A→**E**→B→C/D→F.
Điều này **xác nhận giả thuyết UX-1** trong tài liệu đánh giá.

### 3.2 "Tự lưu trên trình duyệt" — Vị trí và ý nghĩa

**Bằng chứng:** `index.html` L121 — chuỗi `● Tự lưu trên trình duyệt` nằm trong modal header.  
**Cơ chế thực:** `app.js` L739-741 — `rememberDraft()` → `localStorage.setItem('tanthuan-declaration-draft', ...)`.  
**Kết luận:** Dữ liệu chỉ lưu vào `localStorage` của trình duyệt, **không gửi lên server** cho đến khi bấm "Lưu nháp". Label này không phân biệt đủ rõ với "đã lưu server", xác nhận giả thuyết UX-4.

### 3.3 Select Multiple cho Crew

**Bằng chứng:** `app.js` L642 — `<select name="crew_ids" multiple size="4">`.  
Native `<select multiple>` không có checkbox UI, người dùng cần giữ Ctrl/Cmd để chọn nhiều → xác nhận giả thuyết UX-5.

### 3.4 Accessibility Hooks đã triển khai

**Bằng chứng:**
- `index.html` L14 — skip link: `<a class="skip-link" href="#main-content">Bỏ qua điều hướng`
- `app.js` L33 — toast role: `role="alert"` cho error toast, `role="status"` cho success
- `app.js` L41 — form busy state: `form.setAttribute('aria-busy', String(pending))`
- `app.js` L141 — route change focus: `$('#main-content').focus({ preventScroll: true })`
- `index.html` L53 — `<main tabindex="-1" aria-busy="false">`

### 3.5 Wizard keyboard navigation

**Bằng chứng:** `app.js` L563-573 — Wizard dots là `<li>` với `data-wizard-dot` click handlers.  
Li element không có native keyboard role. Không có `tabindex="0"` hoặc `role="button"` trên dots.  
→ **Xác nhận rủi ro UX-6**: Wizard step navigation CHƯA accessible bằng keyboard.

### 3.6 Dashboard — Trộn nhiều loại nội dung

**Bằng chứng:** `index.html` L54-68 — Dashboard chứa:
- Stats cards (vận hành)
- Preference panel (cài đặt cá nhân)
- Certificate reminder (cảnh báo)
- Attention queue (hàng đợi)
- Admin operations panel (quản trị — ẩn khi không phải ADMIN)
- Admin backup panel (quản trị)
- Recent declarations table

→ **Xác nhận giả thuyết UX-7**: 7 loại widget trên cùng một trang, ưu tiên thị giác không rõ ràng.

### 3.7 Thuật ngữ tiếng Anh/Việt

**Bằng chứng code:**
- `app.js` L129: `pageName` — `import`, `reports` (Anh) vs `Phiếu khai báo` (Việt)
- `index.html` L29: nav label "Import Excel" (Anh)
- L172-173 (admin cards): `'IMPORT'`, `'BACKUP'` (Anh)
- Từ khóa API: `payload`, `crew_ids`, `workflow_status` xuyên suốt

→ **Xác nhận giả thuyết UX-8** với bằng chứng cụ thể.

---

## 4. Bảng Finding Tổng hợp

| Finding | Bằng chứng | Mức độ | Role bị ảnh hưởng | Khuyến nghị | Cần sửa trước Gate 5? |
|---|---|---|---|---|---|
| **UX-001** Wizard step order không theo nhãn hồ sơ (A→E→B→C/D) | `app.js` L441-448, L616-641 (code review) | **serious** | CUSTOMER | Tái sắp xếp thứ tự: A→B→C/D→E→F, hoặc đổi tên nhãn wizard cho phù hợp | **YES** |
| **UX-002** "Tự lưu trên trình duyệt" nhập nhằng — chỉ là localStorage, không phải server | `index.html` L121, `app.js` L739-741 (code review) | **serious** | CUSTOMER | Đổi thành "Nháp chưa lưu server" hoặc thêm trạng thái "Đã lưu nháp lên server" | **YES** |
| **UX-003** Wizard dots không keyboard-accessible (không có tabindex/role) | `app.js` L563-573 (code review) | **serious** | Tất cả | Thêm `tabindex="0"` + `role="button"` + `onkeydown` Enter/Space trên mỗi dot | **YES** |
| **UX-004** `<select multiple>` cho crew khó dùng trên mobile/touch | `app.js` L642 (code review) | **moderate** | CUSTOMER | Thay bằng checkbox list hoặc multi-select component có UI rõ ràng hơn | NO (cải thiện) |
| **UX-005** Dashboard trộn 7 widget không cùng ưu tiên thị giác | `index.html` L54-68 (code review) | **moderate** | ADMIN, CV, QLC, BP | Phân tầng: Attention queue nổi bật nhất, admin panel tách tab riêng | NO |
| **UX-006** Thuật ngữ Anh/Việt không nhất quán (`Import`, `Backup`, `payload`) | `app.js` L129, L172-173 (code review) | **minor** | Tất cả | Việt hoá toàn bộ: "Nhập Excel", "Sao lưu", v.v. | NO |
| **UX-007** Bước 1 wizard quá dày (15 trường trong 1 bước) | `app.js` L617-638 (code review) | **moderate** | CUSTOMER | Tách "Loại phiếu + ngày" và "Thông tin phương tiện" thành 2 bước nhỏ | NO |
| **PERF-001** Dashboard API — warm median 11 ms | API test, 3 samples | — | Tất cả | ✅ Đạt ngưỡng ≤500 ms | — |
| **PERF-002** Declarations list (25 items) — warm median 7.6 ms | API test, 3 samples | — | Tất cả | ✅ Đạt ngưỡng ≤750 ms | — |
| **PERF-003** Draft save — ~36 ms | API test, 2 samples | — | CUSTOMER | ✅ Đạt ngưỡng ≤1000 ms | — |
| **PERF-004** Total asset size — 122.2 KB | HTTP response size | — | Tất cả | ✅ Đạt ngưỡng ≤750 KB (Google Fonts không tính) | — |
| **SEC-001** RBAC enforcement — CUSTOMER bị chặn khỏi admin/workflow | API test HTTP 403/401 | — | Tất cả | ✅ Đúng hành vi | — |

---

## 5. Kết luận 3 lớp

### Lớp 1: Đã chứng minh (có bằng chứng thực tế)

| # | Nội dung | Bằng chứng |
|---|---|---|
| ✅ | Wizard step order không theo nhãn hồ sơ (A→E→B→C/D vs A→B→C→D→E) | Code review `DECLARATION_STEPS` + render |
| ✅ | "Tự lưu trên trình duyệt" chỉ là `localStorage`, không phải server | `rememberDraft()` + localStorage logic |
| ✅ | Wizard dots thiếu keyboard accessibility | Không có `tabindex`/`role="button"` |
| ✅ | Dashboard có 7 widget trên 1 trang | HTML structure count |
| ✅ | `<select multiple>` cho crew không có UI checkbox | L642 native select |
| ✅ | Thuật ngữ Anh/Việt chưa nhất quán | pageName, nav labels, admin cards |
| ✅ | API performance ổn (tất cả chỉ số PASS) | 3-sample measurement |
| ✅ | RBAC enforcement đúng (403/401) | API test direct HTTP |
| ✅ | Total asset size 122.2 KB (rất tốt) | HTTP response |
| ✅ | Skip link, aria-busy, toast role, focus management đã có | HTML/JS code |

### Lớp 2: Chưa chứng minh (cần test người dùng thực)

| # | Nội dung | Lý do chưa có bằng chứng |
|---|---|---|
| ⏳ | Tỷ lệ hoàn thành task ≥90% không trợ giúp | Browser subagent bị giới hạn quota |
| ⏳ | Thời gian hoàn thành từng kịch bản (CUSTOMER ≤8 min, CV ≤3 min...) | Cần task study với người dùng thực |
| ⏳ | Hiệu quả attention queue cho CV/QLC | Cần DB với nhiều phiếu đang chờ |
| ⏳ | Screen reader behavior (VoiceOver/NVDA) với toast, bảng, dialog | Cần screen reader test |
| ⏳ | Responsive tại 375×667 (mobile) — overflow ngang | Cần browser resize test |
| ⏳ | Zoom 200% — layout không vỡ | Cần browser test |
| ⏳ | Render 25 rows sau API ≤250 ms | Cần browser performance trace |

### Lớp 3: Ngoài phạm vi (cần owner/môi trường/quyết định sản phẩm)

| # | Nội dung |
|---|---|
| 🔲 | Thứ tự bước wizard có thay đổi không — cần xác nhận từ product owner |
| 🔲 | UAT thực với người dùng nghiệp vụ cảng (CUSTOMER thực, CV thực) |
| 🔲 | Kết nối email/Teams notification (chưa cấu hình) |
| 🔲 | Accessibility audit bằng automated tool (axe-core, Lighthouse) |
| 🔲 | Performance trace trên network thực (3G/4G) |

---

## 6. Kết luận Gate 5

> [!CAUTION]
> **Gate 5 CHƯA ĐỦ ĐIỀU KIỆN đóng** theo tiêu chí `docs/UX_PRODUCT_INDEPENDENT_EVALUATION_20260713.md`.

**Lý do cụ thể:**

1. **UX-003** (Wizard dots không keyboard-accessible) là lỗi **serious accessibility** → Gate 5 không đạt nếu còn lỗi mức serious.
2. **UX-001** (Wizard step order) và **UX-002** (nhãn auto-save nhập nhằng) là lỗi **serious UX** cần sửa trước Gate 5.
3. Task study, responsive matrix, screen reader audit chưa thực hiện.

**Điểm tích cực cần ghi nhận:**
- Performance API vượt tốt ngưỡng cho phép (11–36 ms vs 500–1000 ms ngưỡng).
- Asset size chỉ 122 KB, rất tối ưu.
- RBAC enforcement đúng hoàn toàn.
- Accessibility foundation (skip link, aria-busy, toast role, focus) đã có.

---

*Báo cáo này là heuristic review + automated test, không thay thế task study với người dùng thực.*  
*Liên kết quản trị: `docs/T5_GATE5_EVIDENCE_PROTOCOL.md` · `docs/EA_EVALUATION_ROADMAP.md`*
