# Phản hồi Đánh giá UX/Product Độc lập — Quản Lý Xalan

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

---

## 7. Đánh giá độc lập sau khi đối chiếu bằng chứng

Phần này được bổ sung sau khi review lại bằng chứng trong báo cáo. Nó không phủ
nhận kết quả API/RBAC đã ghi, nhưng hiệu chỉnh mức chắc chắn và thứ tự xử lý.

### 7.1 Kết luận có thể hành động ngay

| Ưu tiên | Hành động đề xuất | Cơ sở | Điều kiện đóng |
|---|---|---|---|
| P0 | Thay wizard dots bằng phần tử `<button>` có accessible name, trạng thái bước hiện tại và trạng thái disabled phù hợp | Thiếu keyboard semantics được chứng minh trực tiếp từ mã | Tab tới được từng bước hợp lệ; Enter/Space hoạt động; screen reader đọc tên và trạng thái; regression test PASS |
| P0 | Phân biệt rõ “nháp cục bộ trên thiết bị” và “nháp đã lưu trên hệ thống”; hiển thị thời điểm/trạng thái lưu | Cơ chế `localStorage` đã được chứng minh, nhưng mức độ người dùng hiểu sai chưa được đo | Reload/đổi bước/đóng mở dialog không làm mất dữ liệu ngoài mô tả; nhãn phản ánh đúng nơi lưu; test comprehension PASS |
| P0 — cần owner xác nhận | Giữ mã mục hồ sơ A/B/C/D/E/F nếu đây là mapping pháp lý, nhưng sắp xếp hoặc đặt tên bước theo tiến trình người dùng | Sự lệch A→E→B→C/D đã được chứng minh; tác động usability và quyền thay đổi thứ tự chưa được chứng minh | Product/domain owner xác nhận mapping; task study so sánh phương án; không làm sai báo cáo/phụ lục |
| P1 | Thay native `<select multiple>` bằng danh sách checkbox/searchable picker có trạng thái chứng chỉ và thuyền trưởng rõ ràng | Cấu trúc control đã chứng minh; khó sử dụng thực tế chưa được đo | Mobile/keyboard task PASS; không chọn nhầm; selection được giữ khi quay lại bước |
| P1 | Tách dashboard theo role và đưa hàng đợi cần xử lý lên trước | Dashboard trộn nhiều widget đã chứng minh; tác động completion time chưa được đo | CV/QLC/BP tìm đúng phiếu trong ngưỡng; CUSTOMER không thấy nhiễu quản trị; ADMIN vẫn truy cập đủ vận hành |
| P1 | Bổ sung lỗi inline, error summary và focus tới lỗi đầu tiên trong wizard | Báo cáo hiện chưa kiểm chứng giả thuyết về khả năng phục hồi sau lỗi | Kịch bản lỗi ở từng bước được hoàn thành không trợ giúp; screen reader đọc được lỗi; dữ liệu đã nhập không mất |

### 7.2 Hiệu chỉnh mức bằng chứng hiện tại

- `UX-003` có bằng chứng code-level đủ mạnh để xác nhận lỗi keyboard semantics;
  vẫn cần browser + screen reader test để xác nhận hành vi sau khi sửa.
- `UX-001` xác nhận được sự lệch thứ tự nhãn, nhưng mức **serious** đối với người
  dùng chưa được chứng minh bằng task study. Không tự ý đổi thứ tự các mục hồ sơ
  nếu chưa có domain/product owner xác nhận.
- `UX-002` xác nhận được nháp chỉ nằm trong `localStorage`, nhưng mức độ người
  dùng hiểu nhầm chưa được chứng minh. Nên sửa wording sớm vì thay đổi nhỏ và giảm
  rủi ro kỳ vọng sai.
- `UX-004`, `UX-005`, `UX-006`, `UX-007` vẫn là heuristic findings; chưa được
  nâng thành lỗi hành vi người dùng.
- Performance hiện chứng minh **API local với dataset rất nhỏ**, không chứng minh
  browser rendering, mobile/network performance hoặc tải gần production.

## 8. Phần còn thiếu — yêu cầu Claude test bổ sung

### 8.1 P0 — Keyboard, screen reader và error recovery

1. Dùng keyboard-only hoàn tất một khai báo: mở wizard, chuyển bước, quay lại,
   chọn thuyền viên, đính kèm file, xem lại và nộp.
2. Ghi video hoặc chuỗi screenshot/focus trace cho wizard dots. Kiểm tra Tab,
   Shift+Tab, Enter, Space và focus visible.
3. Chạy NVDA hoặc screen reader tương đương cho: tên bước, bước hiện tại, lỗi
   bắt buộc, toast, busy state, dialog và bảng.
4. Tạo lỗi tại mỗi bước, đặc biệt lỗi nằm ngoài viewport. Ghi nhận focus đi đâu,
   lỗi có còn hiển thị hay tự biến mất, và dữ liệu đã nhập có bị mất không.
5. Thử đóng/mở dialog, reload trang và đăng nhập trên browser khác để xác minh
   chính xác ranh giới của nháp cục bộ so với nháp server.

Evidence bắt buộc: browser/version, account role, viewport, từng phím đã dùng,
screenshot/video, expected/actual và severity.

### 8.2 P0 — Task study và comprehension test

Tối thiểu một người đại diện cho mỗi role CUSTOMER, CV, QLC, BP và ADMIN; ưu
tiên người không tham gia phát triển ứng dụng.

- CUSTOMER: tạo mới, lưu nháp, quay lại, sửa lỗi và nộp phiếu.
- CV: tìm phiếu chờ CV và yêu cầu bổ sung.
- QLC: tìm và duyệt đúng phiếu chờ QLC.
- BP: tìm, duyệt/cấp phép và kiểm tra timeline.
- ADMIN: tìm attention queue, vận hành và backup mà không nhầm với nghiệp vụ.

Đặt câu hỏi comprehension riêng:

- “Tự lưu trên trình duyệt” theo bạn dữ liệu đang nằm ở đâu?
- Nếu đổi máy hoặc xóa dữ liệu trình duyệt, nháp còn hay mất?
- A/E/B/C/D/F có ý nghĩa gì và bước tiếp theo bạn dự đoán là gì?
- Công việc nào trên dashboard cần bạn xử lý ngay?

Thu thập thời gian, completion without assistance, số lỗi, số lần quay lại, số
lần hỏi “tiếp theo làm gì?”, confidence 1–5 và câu nói nguyên văn ngắn.

### 8.3 P1 — Responsive và mobile interaction

Chạy tại 375×667, 768×1024 và 1440×900; thêm zoom 200% và reduced motion.

- kiểm tra overflow ngang, sidebar, modal, sticky footer và bàn phím ảo;
- chọn nhiều thuyền viên trên touch/mobile;
- bảng responsive phải giữ được nhãn và hành động;
- nút chính không bị che, mất hoặc nằm ngoài viewport;
- focus không bị kẹt sau khi đóng dialog.

### 8.4 P1 — Performance cần đo lại

Các khoảng trống của phép đo hiện tại:

- báo cáo ghi database khoảng 5 records nhưng đo endpoint với page size 25;
  chưa chứng minh render thực tế 25 dòng;
- draft save mới có 2 mẫu và là HTTP API timing, chưa phải click-to-visible UI;
- chưa có browser render trace, cache state, CPU/device profile hoặc network
  profile;
- asset size chưa tính external font/network dependencies và chưa ghi rõ
  compressed transfer size so với uncompressed resource size.

Claude cần bổ sung:

1. Seed ít nhất 25 phiếu hiển thị được cho role đang test và ghi row counts.
2. Đo ba mẫu, lấy median cho browser render 25 dòng sau API.
3. Đo ba mẫu click “Lưu nháp” tới thông báo/trạng thái nhìn thấy được.
4. Đo dashboard và danh sách ở cold cache và warm cache.
5. Ghi total transferred bytes gồm document, JS, CSS, font và ảnh; tách rõ
   compressed/uncompressed.
6. Nếu có thể, chạy thêm một mobile throttling profile; không dùng kết quả local
   warm API để suy rộng thành production performance.

### 8.5 P1 — RBAC/role UX cần mở rộng

RBAC hiện đã chứng minh một số denial cơ bản, chưa phải ma trận đầy đủ. Test thêm:

- CUSTOMER A không đọc/sửa dữ liệu CUSTOMER B;
- CV chỉ làm hành động CV, QLC chỉ làm hành động QLC, BP chỉ làm hành động BP;
- ADMIN bị từ chối thay đổi workflow;
- action bị ẩn trên UI nhưng request trực tiếp vẫn bị API từ chối;
- sau 403/409/422, UI giải thích được lỗi và giữ dữ liệu/ngữ cảnh;
- attention queue của từng role chỉ chứa trạng thái role đó có quyền xử lý.

### 8.6 Điều kiện đánh giá lại

Chỉ cập nhật severity hoặc đóng finding khi evidence có expected/actual, môi
trường, dữ liệu, role và artifact lặp lại được. Gate 5 vẫn **OPEN** cho tới khi:

- không còn accessibility finding mức critical/serious;
- task study đạt tiêu chí hoặc có remediation được duyệt;
- responsive matrix và browser performance evidence hoàn tất;
- product owner xác nhận quyết định liên quan thứ tự/mapping hồ sơ.

## 9. Implementation checkpoint after owner approval

Status: **LOCAL IMPLEMENTATION COMPLETE — GATE 5 EVIDENCE PENDING**.

- UX-001: IMPLEMENTED — owner approved A -> B -> C/D -> E -> attachments -> F;
  browser/task-study verification pending.
- UX-002: IMPLEMENTED — local draft boundary and local save time are explicit;
  comprehension test pending.
- UX-003: IMPLEMENTED — wizard steps use native buttons and current-step
  semantics; keyboard/screen-reader verification pending.
- UX-004: IMPLEMENTED — crew selection uses a checkbox checklist and the
  prior-trip suggestion path supports the new control; mobile evidence pending.
- UX-005: IMPLEMENTED LOCALLY — role dashboard hierarchy/classes added; role
  task-time evidence pending.
- UX-006: IMPLEMENTED LOCALLY — primary terminology standardized; final
  content-language review pending.
- UX-007: PARTIALLY MITIGATED — wizard reordered, but step-density usability
  still requires task study before the finding can be closed.

The implementation status above is not Gate 5 closure. Browser task study,
screen-reader, responsive/zoom and browser performance evidence remain deferred
by owner direction.
