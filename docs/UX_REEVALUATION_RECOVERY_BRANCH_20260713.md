# Đánh giá lại UX — Recovery Checkpoint

> Bản gốc do Claude lập tại checkpoint `cfc2d84`. Các kết luận dưới đây được
> giữ lại làm dấu vết đánh giá; phần đính chính này là kết quả đối chiếu và xử
> lý tiếp theo trên cùng branch.

## Đính chính và trạng thái xử lý — 2026-07-13

- **CRIT-001 — hợp lệ, đã xử lý:** API chỉ còn `PORT_APPROVE` và
  `REQUEST_CHANGES`. Năm action cũ trả HTTP 410. Migration `g06f0f000006` đổi
  role CV/QLC/BP thành `PORT_STAFF`, đưa PENDING_QLC/PENDING_BP về
  PENDING_REVIEW, ISSUED về APPROVED, REVOKED về CHANGES_REQUESTED, đổi
  `cv_approval` thành `port_approval` và bỏ các cột legacy khác. Phiếu demo id
  8 đã được giải phóng bằng `PORT_APPROVE` sau khi
  xác nhận action cũ trả 410.
- **UX-101 — kết luận FAIL ban đầu không hợp lệ:** kiểm tra API lặp lại cho thấy
  `q=Bạch` và `q=Tân Thuận` có khớp `vessel_name`; `master_name` đã có bộ lọc
  riêng. Trường hợp `Hai` không khớp `Hải` chỉ chứng minh chưa có tìm kiếm bỏ
  dấu, không chứng minh thiếu trường `master_name` trong toàn bộ khả năng lọc.
- **UX-102 — kết luận FAIL ban đầu không hợp lệ:** khi gửi `page=1&page_size=2`,
  API trả envelope phân trang với 2 items, tổng số và tổng số trang. Gọi không
  có `page` cố ý giữ response mảng tương thích ngược theo API contract.
- **UX-103, UX-105, UX-106 — đã xử lý:** audit dùng “xác nhận gửi”; wizard có
  error summary, `aria-invalid` và focus tới lỗi đầu tiên; nội dung “Crew List”
  đã Việt hóa.
- **UX-004 — đã xử lý ở commit hiện tại:** control chọn thuyền viên dùng nhóm
  checkbox có vùng chạm tối thiểu thay cho native `select multiple`.
- **Analytics và kiểm thử trực quan đa viewport — vẫn chờ bằng chứng riêng.**
  Analytics không được gộp vào tranche sửa workflow/UX này.

## Sổ trạng thái sau thi công

| Mã | Trạng thái hiện tại | Đã xử lý / kết luận | Còn thiếu hoặc cần chờ |
|---|---|---|---|
| CRIT-001 | **ĐÃ XỬ LÝ** | Commit `0b2ba72` vô hiệu hóa năm action workflow cũ bằng HTTP 410, chuyển role sang `PORT_STAFF`, đổi `cv_approval` thành `port_approval`, migration dữ liệu cũ và giải phóng phiếu demo id 8. | Cần kiểm tra migration trên bản sao dữ liệu staging trước khi triển khai production; hiện chưa có staging/owner triển khai. |
| UX-101 | **ĐÍNH CHÍNH — KHÔNG PHẢI LỖI NHƯ BÁO CÁO GỐC** | API thực khớp `vessel_name`; thuyền trưởng có filter `master_name` riêng. Không cần sửa theo đề xuất mở rộng trường tìm kiếm ban đầu. | Tìm kiếm không dấu (`Hai` → `Hải`) chưa có. Chờ Product Owner xác nhận đây có phải yêu cầu nghiệp vụ hay không trước khi mở task mới. |
| UX-102 | **ĐÍNH CHÍNH — ĐÃ CÓ SẴN** | Phân trang hoạt động khi gửi `page`; `page_size=2` trả đúng hai items và metadata tổng. Response mảng khi không có `page` là tương thích ngược có chủ ý. | Không còn việc code trong checkpoint này. Chỉ cần performance test với tập dữ liệu tham chiếu khi Gate 5 được tổ chức. |
| UX-103 | **ĐÃ XỬ LÝ** | Audit/runtime dùng “Khách hàng xác nhận gửi phiếu khai báo”; UI và preview bỏ “Nộp/nộp”. | Chờ browser/UAT xác nhận tất cả thông điệp nhìn thấy đúng ngữ cảnh. |
| UX-104 | **CHƯA ĐÓNG** | Dashboard đã ẩn chức năng theo role và có attention queue theo vai trò. | Chờ task study hoặc UAT với khách hàng và nhân viên Cảng để xác định thứ tự ưu tiên widget; chưa đủ bằng chứng để tái cấu trúc dashboard. |
| UX-105 | **ĐÃ THI CÔNG, CHỜ BẰNG CHỨNG UX** | Wizard có error summary, `aria-invalid`, mô tả lỗi theo field và focus về lỗi đầu tiên. Static/regression test đã PASS. | Chờ kiểm thử bàn phím thật, screen reader hoặc axe-core trong browser; chưa được dùng kết quả static để đóng Gate 5. |
| UX-106 | **ĐÃ XỬ LÝ** | “Crew List” đã được Việt hóa trong app và preview. | Chỉ còn rà soát nội dung bằng mắt trong lượt browser/UAT. |
| UX-107 | **PASS** | Không còn role/stage CV/QLC/BP trong UI hay schema/runtime hiện hành; các tên action cũ chỉ còn trong deny-list và regression test để bảo đảm trả 410. | Không xóa deny-list/test vì đó là hàng rào chống client cũ gọi nhầm. |
| UX-002 cũ | **ĐÃ XỬ LÝ** | Nhãn được đổi thành “Nháp cục bộ · chưa gửi”, có thời điểm lưu cục bộ khi phát sinh. | Chờ quan sát bằng mắt để xác nhận người dùng hiểu đúng; không được mô tả là đồng bộ server. |
| UX-004 cũ | **ĐÃ THI CÔNG, CHỜ BẰNG CHỨNG UX** | Native `select multiple` đã được thay bằng checkbox checklist thân thiện bàn phím/mobile. | Chờ browser test ở desktop và mobile, kiểm tra vùng chạm và Tab/Space. |
| Analytics | **CHƯA XỬ LÝ — NGOÀI TRANCHE** | Đã xác nhận frontend gọi endpoint chưa tồn tại và xử lý 404 bằng toast, không làm vỡ trang. | Cần một tranche riêng gồm định nghĩa chỉ số, API contract, quyền truy cập, dữ liệu tham chiếu và thiết kế biểu đồ trước khi code. |
| Responsive/Gate 5 | **CHƯA CÓ BẰNG CHỨNG** | CSS breakpoint và cấu trúc responsive tồn tại; unit/static test xanh. | Chờ ảnh và thao tác thật tối thiểu tại 1920×1080, 1366×768, 390×844; cần kiểm thử bàn phím, accessibility và task completion. |

## Cập nhật lỗi runtime — 2026-07-14

| Mã | Trạng thái | Bằng chứng trước sửa | Xử lý tại `5e74643` |
|---|---|---|---|
| RUNTIME-001 | **ĐÃ XỬ LÝ** | Khách hàng mở trang Báo cáo làm frontend gọi `/api/reports/analytics?period=month` và nhận HTTP 404. | Trang không còn gọi endpoint Analytics chưa có contract. Khu vực thống kê hiển thị trạng thái “chưa khả dụng”, vô hiệu hóa kỳ và export; PL.01–PL.03 vẫn hoạt động độc lập. |
| RUNTIME-002 | **ĐÃ XỬ LÝ** | Cùng thao tác trên làm frontend gọi integration Admin-only và nhận HTTP 403. | Integration ẩn mặc định, chỉ hiện và tải khi role là `ADMIN`; nội dung được đổi thành “Kết nối dữ liệu bên ngoài”, không mô tả Cảng là Cảng vụ. |
| RUNTIME-003 | **ĐÃ XỬ LÝ** | Admin vẫn thấy nút “Tạo phiếu”, trong khi chỉ CUSTOMER được xác nhận gửi; thao tác cuối có thể dẫn đến 403. | Nút tạo phiếu chỉ hiện cho `CUSTOMER`. Admin vẫn quản trị hồ sơ phương tiện/thuyền viên nhưng không thực hiện khai báo thay khách hàng qua UI. |

Regression sau sửa: `67 passed`; `node --check frontend/app.js` và
`git diff --check` PASS. Phiên in-app browser không khả dụng ngày 2026-07-14,
do đó chưa bổ sung ảnh hoặc tuyên bố Gate 5.

### Điều kiện để tiếp tục

1. **Claude/browser tester** chạy lại đúng worktree và branch ghi trong
   `docs/SESSION_HANDOFF_RECOVERY_UX_20260713.md`; không đánh giá bản `main` hay
   restore copy.
2. **Product Owner** quyết định có yêu cầu tìm kiếm không dấu và có cho phép
   tái cấu trúc thứ tự dashboard dựa trên UAT hay không.
3. **Analytics** chỉ được mở khi có work order/contract riêng; không ghép vào
   commit workflow recovery.
4. **Gate 5** chỉ được đóng sau bằng chứng browser/UAT thực, không dùng static
   DOM/CSS hay mock làm bằng chứng trải nghiệm hoàn chỉnh.

## Báo cáo gốc (giữ nguyên để truy vết)

Đánh giá độc lập · Không sửa code · Không commit

Đánh giá lại UX — Recovery Checkpoint
Ngày: 2026-07-13
Branch: recovery/frontend-baseline-20260712
Checkpoint: cfc2d84
App: http://127.0.0.1:8086
Phương pháp bằng chứng. Không có trình duyệt tương tác trực tiếp trong phiên đánh giá này. Bằng chứng thu thập qua: (1) HTTP request thật tới server đang chạy bằng 3 tài khoản demo, (2) tệp index.html/app.js/styles.css tải trực tiếp từ server đang chạy (as‑served, không phải đọc nguồn tĩnh trong worktree), (3) đối chiếu với backend/app.py khi cần xác minh logic phân quyền. Mọi kết luận có nhãn PASS/FAIL đều có evidence block đi kèm. Các mục cần quan sát bằng mắt (render thực tế, animation, độ rõ focus ring, mobile touch) được xếp vào lớp Chưa chứng minh — không được tính là đóng Gate 5.
Phát hiện mới nghiêm trọng nhất trong đợt này (CRIT‑001): hành động API cũ CV_APPROVE vẫn được backend chấp nhận và có thể đưa một phiếu vào trạng thái PENDING_QLC — trạng thái mà giao diện hiện tại (chỉ có "Xác nhận hoàn tất" / "Yêu cầu bổ sung") không có đường xử lý tiếp, kể cả với tài khoản Quản trị. Đã tái hiện bằng thực nghiệm, phiếu TT-20260713-165411-572542 (id=8) hiện đang kẹt ở PENDING_QLC trong database demo tại thời điểm nộp báo cáo này. Xem chi tiết ở mục CRIT‑001 bên dưới.
§1Kết luận theo từng tiêu chí kiểm tra tối thiểu
#	Tiêu chí	Kết luận	Ghi chú ngắn
1	Dashboard theo từng vai trò	PARTIAL	Dữ liệu/attention queue đúng theo role qua API; nhưng 1 trang HTML vẫn gộp 7 widget (ẩn/hiện bằng hidden), chưa tách khu vực
2	Danh sách và bộ lọc phiếu	PARTIAL	workflow_status/movement_type lọc đúng; q không match vessel_name; page_size bị bỏ qua hoàn toàn
3	Toàn bộ sáu bước wizard	PASS	6 bước tồn tại, render đúng theo DECLARATION_STEPS
4	Thứ tự bước và khả năng quay lại	PASS	Phương tiện→Hành trình→Hàng hóa→Thuyền trưởng&Thuyền viên→Đính kèm→Xem lại&Gửi; nút "← Quay lại" luôn khả dụng trừ bước 1
5	Trường phương tiện có sẵn phải chỉ đọc	PASS	readonly/data-locked trên toàn bộ field hồ sơ khi chọn "Phương tiện đã có hồ sơ"
6	Dùng "Xác nhận & gửi", không dùng "Nộp"	PARTIAL	Nút UI đúng; nhưng audit log backend vẫn ghi cứng "Nộp phiếu khai báo" — lệch thuật ngữ ở tầng vết tích
7	Duyệt trực tiếp và yêu cầu bổ sung	PARTIAL	Luồng UI 1 bước hoạt động đúng; nhưng route API cũ song song gây kẹt phiếu — xem CRIT‑001
8	Phản hồi/timeline cho khách hàng	PASS	Khách hàng xem được lý do yêu cầu bổ sung, actor role hiển thị "Nhân viên Cảng" (đã Việt hóa)
9	Desktop / laptop / mobile	PARTIAL — Chưa chứng minh bằng mắt	CSS có breakpoint 760px/1000px/1180px hợp lý; không có render thực tế
10	Keyboard, focus, validation, thông báo lỗi	PARTIAL	Wizard dots đã là <button>; validation vẫn 100% dựa vào reportValidity() native, chưa có error summary/focus-to-error
11	Còn nội dung CV/QLC/BP hiển thị?	PASS (UI) / FAIL (API)	DOM/text hiển thị: sạch. Nhưng field cv_approval/qlc_approval/bp_approval và action CV_APPROVE/QLC_APPROVE/BP_APPROVE vẫn sống trong API — xem CRIT‑001
12	Analytics — không PASS nếu backend chưa có endpoint	FAIL (đúng như dự đoán)	GET /api/reports/analytics → 404 xác nhận bằng HTTP thật; frontend bắt lỗi bằng toast, không vỡ layout
§2Finding — chi tiết đầy đủ bằng chứng
CRIT-001
Route workflow 3 bước cũ (CV→QLC→BP) vẫn sống trong API và có thể khiến phiếu kẹt vĩnh viễn
FAIL — nghiêm trọng
URL/endpoint
POST /api/declarations/{id}/workflow
Vai trò
Nhân viên Cảng (nhanviencang, role="CV" trong JWT/DB) và Quản trị (admin)
Thao tác tái hiện
1. Đăng nhập khachhang, tạo phiếu mới, gửi bằng POST /api/declarations?submit=true → phiếu id 8, trạng thái PENDING_REVIEW.
2. Đăng nhập nhanviencang, gọi trực tiếp POST /api/declarations/8/workflow với body {"action":"CV_APPROVE"} (action này không xuất hiện trên UI, nhưng backend vẫn chấp nhận vì user.role == "CV" đúng điều kiện cho cả PORT_APPROVE lẫn CV_APPROVE).
3. Kết quả: workflow_status chuyển thành PENDING_QLC (HTTP 200).
4. Thử PORT_APPROVE trên phiếu này → 400 (yêu cầu PENDING_REVIEW, hiện là PENDING_QLC).
5. Thử REQUEST_CHANGES bằng nhanviencang → 403 ("Chỉ QLC mới có quyền yêu cầu chỉnh sửa ở giai đoạn này").
6. Thử mọi hành động bằng admin → 403 ("Bạn không có quyền thực hiện hành động này").
Bằng chứng API
POST /declarations/8/workflow {"action":"CV_APPROVE"}
→ 200 { "workflow_status": "PENDING_QLC", "cv_approval": "APPROVED", ... }

POST /declarations/8/workflow {"action":"PORT_APPROVE"}
→ 400 "Không thể thực hiện 'PORT_APPROVE' từ trạng thái 'PENDING_QLC'."

POST /declarations/8/workflow {"action":"REQUEST_CHANGES"} (role CV)
→ 403 "Chỉ QLC mới có quyền yêu cầu chỉnh sửa ở giai đoạn này."

POST /declarations/8/workflow {"action":"PORT_APPROVE"} (role ADMIN)
→ 403 "Bạn không có quyền thực hiện hành động này."
Mã nguồn xác nhận chủ ý (backend/app.py dòng 152–163, 1271–1277): comment ghi rõ "legacy staged actions remain readable... but are no longer presented by the application UI" — nhưng chỉ ẩn ở UI, endpoint vẫn nhận và xử lý action cũ, và vai trò lưu trong DB (CV) trùng khớp điều kiện cho cả hai route nên không có rào cản kỹ thuật nào ngăn việc gọi nhầm/gọi trực tiếp.
Trạng thái hiện tại
Phiếu TT-20260713-165411-572542 (id=8) đang thực sự kẹt ở PENDING_QLC trong database tại thời điểm viết báo cáo — chưa được dọn dẹp để giữ làm bằng chứng tái kiểm chứng. Đây là dữ liệu do đánh giá tạo ra trong môi trường demo cô lập, không phải dữ liệu nghiệp vụ thật.
Mức độ ảnh hưởng: Nghiêm trọng (Critical). Đây không phải lỗi hiển thị — là lỗi toàn vẹn nghiệp vụ có thể làm phiếu của khách hàng thật bị treo vô thời hạn, không role nào trong hệ thống hiện tại (kể cả Admin) xử lý được qua giao diện chuẩn. Nguyên nhân gốc: field role lưu trong DB vẫn dùng mã cũ ("CV") làm khóa phân quyền cho cả action mới và action cũ, nên không thể tắt route cũ chỉ bằng ẩn UI.

Đề xuất sửa (không thi công trong lượt này): Vô hiệu hóa hoàn toàn các action CV_APPROVE/QLC_APPROVE/BP_APPROVE ở endpoint (trả 410/400 rõ ràng "hành động đã ngừng hỗ trợ"), hoặc giới hạn chúng chỉ đọc (audit/migration script), không nhận qua API động. Đồng thời cần script rà soát và khắc phục các phiếu đã lỡ rơi vào PENDING_QLC/PENDING_BP trước khi lên production.
UX-101
Tìm kiếm phiếu theo q không khớp tên phương tiện/thuyền trưởng
FAIL
URL/endpoint
GET /api/declarations?q=...
Vai trò
Khách hàng (áp dụng mọi vai trò vì cùng query logic)
Thao tác tái hiện
Gọi GET /api/declarations?q=Tân Thuận — chuỗi này khớp chính xác với company_name và một phần vessel_name của dữ liệu demo hiện có.
Bằng chứng API
q=Bạch          → 0 kết quả  (tên tàu: "Tàu kéo Bạch Đằng")
q=Tân Thuận     → 0 kết quả  (company_name và vessel_name đều chứa "Tân Thuận")
q=Hai           → 0 kết quả  (master_name: "Nguyễn Văn Hải")
q=KB-DEMO       → 6 kết quả  (khớp reference_no)
q=SG-DEMO-001   → 2 kết quả  (khớp registration_no)
q=container     → 2 kết quả  (khớp vessel_type)
Mức độ ảnh hưởng: Trung bình–nghiêm trọng cho vận hành thật. Nhân viên Cảng tìm phiếu bằng tên tàu hoặc tên thuyền trưởng — hai trường phổ biến nhất trong giao tiếp thực tế — sẽ luôn ra 0 kết quả, chỉ tìm được nếu nhớ đúng mã phiếu hoặc số đăng ký.

Đề xuất sửa: Mở rộng điều kiện ILIKE/full-text ở backend để bao gồm vessel_name và master_name.
UX-102
page_size không được backend áp dụng
FAIL
URL/endpoint
GET /api/declarations?page=1&page_size=2
Bằng chứng API
GET /api/declarations?page=1&page_size=2
→ 200, mảng trả về có 7 phần tử (toàn bộ dữ liệu hiện có), không giới hạn 2
→ Không có header X-Total-Count / Link phân trang
Mức độ ảnh hưởng: Trung bình. Với dữ liệu demo nhỏ chưa lộ hậu quả, nhưng ở quy mô thật (hàng trăm/nghìn phiếu) toàn bộ danh sách sẽ tải về client trong một lần — rủi ro hiệu năng và không đúng hợp đồng OpenAPI đã khai (page_size có maximum:100, default:25).

Đề xuất sửa: Áp dụng LIMIT/OFFSET theo page/page_size ở tầng truy vấn backend; trả kèm tổng số bản ghi.
UX-103
Thuật ngữ "Nộp" vẫn còn ở audit log backend dù UI đã đổi
PARTIAL
URL/endpoint
backend/app.py, hàm xử lý POST /api/declarations?submit=true
Bằng chứng mã nguồn
event = DeclarationEvent(
    action="SUBMIT",
    ...
    note="Nộp phiếu khai báo",   # hard-coded, không đổi theo UI wording
)
Xác nhận qua GET /api/declarations/5/events thực tế: sự kiện SUBMIT ghi note "Khách hàng xác nhận gửi phiếu minh họa." trong dữ liệu demo được seed sẵn (khác với note hard-code ở code path submit thật) — cho thấy hai nguồn dữ liệu (seed script vs. runtime code) đang không nhất quán với nhau.
Mức độ ảnh hưởng: Thấp — không hiển thị trực tiếp cho người dùng cuối trong luồng chuẩn, nhưng nếu note này từng lộ ra ở timeline/audit export, thuật ngữ sẽ lệch với UI.

Đề xuất sửa: Đổi note hard-code thành "Khách hàng xác nhận gửi phiếu khai báo." cho khớp thuật ngữ UI.
UX-104
Dashboard vẫn gộp 7 widget trong 1 trang (mitigated bằng ẩn/hiện theo role, chưa tách khu vực)
PARTIAL — kế thừa từ UX-005 cũ
URL/màn hình
#dashboard, mọi vai trò
Bằng chứng DOM (as-served)
<section data-page="dashboard">
  dashboard-search / stats / demo-data-notice /
  preference-panel (cá nhân) / certificate-reminder /
  attention-queue / admin-operations (hidden trừ ADMIN) /
  admin-backup (hidden trừ ADMIN) / recent-table
</section>
Mức độ ảnh hưởng: Trung bình. So với báo cáo cũ, mitigation thực tế là dùng hidden để ẩn panel Admin khỏi vai trò khác — đúng hướng nhưng chưa phải "tách theo role" như checkpoint tự nhận IMPLEMENTED; cấu trúc HTML và độ ưu tiên thị giác giữa "Cần chú ý" và "Cài đặt cá nhân" vẫn ngang hàng.

Đề xuất sửa: Cần task study đo thời gian tìm "việc cần xử lý" trước khi hạ mức độ nghiêm trọng thấp hơn PARTIAL.
UX-105
Validation vẫn 100% dựa vào reportValidity() native, chưa có error summary / focus-to-error
PARTIAL — chưa khắc phục từ khuyến nghị P1 cũ
Bằng chứng mã nguồn (as-served app.js)
function validateStep(step) {
  for (const el of activeStepFields(step)) {
    if (el.disabled || el.type === 'hidden' || el.hidden) continue;
    if (!el.reportValidity()) return false;
  }
  return true;
}
Không tìm thấy aria-invalid, error-summary component, hay focus điều hướng tới field lỗi đầu tiên trong toàn bộ app.js (as-served).
Mức độ ảnh hưởng: Trung bình cho accessibility/screen reader — đúng như khuyến nghị P1 trong UX_EVALUATION_RESPONSE_20260713.md mục 7.1, nhưng chưa được triển khai ở checkpoint này (checkpoint không liệt kê hạng mục này là đã làm).

Đề xuất sửa: Bổ sung error summary ở đầu mỗi bước wizard, focus tới field lỗi đầu tiên, aria-invalid="true" trên field lỗi.
UX-106
Nhãn "CREW LIST" (tiếng Anh) còn sót trong modal thuyền viên
PARTIAL — kế thừa từ UX-006 cũ
URL/màn hình
Dialog "Thông tin và chứng chỉ chuyên môn" (mở từ trang Thuyền viên)
Bằng chứng DOM (as-served index.html, dòng 119)
<p class="eyebrow">CREW LIST</p><h2>Thông tin và chứng chỉ chuyên môn</h2>
Mức độ ảnh hưởng: Thấp. Không sai nghiệp vụ, chỉ là tồn đọng Việt hóa chưa hoàn tất mà checkpoint tự nhận "IMPLEMENTED LOCALLY... final content-language review pending".

Đề xuất sửa: Đổi "CREW LIST" → "DANH SÁCH THUYỀN VIÊN".
UX-107
Mã vai trò cũ CV/QLC/BP không rò rỉ ra UI hiển thị — xác nhận PASS
PASS
Bằng chứng mã nguồn (as-served app.js)
function roleLabel(role) {
  return ({CUSTOMER:'Khách hàng / Chủ phương tiện',
           CV:'Nhân viên Cảng', QLC:'Nhân viên Cảng', BP:'Nhân viên Cảng',
           ADMIN:'Quản trị hệ thống'})[role] || role;
}
function approvalDot(status, label) {
  return `<span class="approval ${'${'}String(status).toLowerCase()${'}'}" aria-hidden="true">
    ${'${'}status === 'APPROVED' ? '✓' : ''${'}'}</span>`;
  // tham số `label` (vd. 'CV') được truyền vào nhưng KHÔNG render ra text —
  // chỉ dùng làm class CSS ẩn (aria-hidden), không xuất hiện trong nội dung nhìn thấy được
}
Grep toàn bộ served DOM
Không tìm thấy "Chờ CV", "Chờ QLC", "Chờ BP", "CV → QLC → BP" trong index.html as-served. Text "CV" xuất hiện duy nhất như literal string tham số hàm trong app.js, không render ra DOM.
Mức độ ảnh hưởng: Không có — đây là điểm PASS thực chất. Ghi nhận riêng vì đối lập trực tiếp với CRIT-001 (API vẫn lộ mã cũ dù UI đã sạch) — hai lớp bằng chứng khác nhau cho cùng một chủ đề.

§3Phân lớp kết luận
Đã chứng minh (có trace HTTP/DOM lặp lại được)
6 bước wizard đúng thứ tự Phương tiện→Hành trình→Hàng hóa→Thuyền trưởng&Thuyền viên→Đính kèm→Xem lại&Gửi, có nút quay lại
Field phương tiện khóa readonly/data-locked khi chọn hồ sơ có sẵn
Nút chính đúng là "Xác nhận & gửi", không phải "Nộp"
Luồng UI chuẩn 1 bước (Xác nhận hoàn tất / Yêu cầu bổ sung) hoạt động đúng khi dùng qua route PORT_APPROVE/REQUEST_CHANGES
Khách hàng xem được timeline + lý do yêu cầu bổ sung, actor role hiển thị đã Việt hóa
RBAC 403/401 vẫn đúng (CUSTOMER bị chặn khỏi admin/workflow)
Text CV/QLC/BP không còn xuất hiện trong DOM hiển thị
CRIT-001: route API cũ CV_APPROVE vẫn hoạt động và có thể gây kẹt phiếu vĩnh viễn — tái hiện được, phiếu id=8 hiện vẫn đang kẹt
UX-101/102: search theo tên tàu/thuyền trưởng không hoạt động; page_size bị bỏ qua
/api/reports/analytics trả 404 — xác nhận đúng tuyên bố checkpoint, không tính PASS
Chưa chứng minh (không có browser tương tác trong phiên này)
Render thực tế ở 1920×1080, 1366×768, 390×844 — chỉ xác minh qua CSS media query tĩnh (760px/1000px/1180px breakpoints tồn tại và hợp lý)
Hành vi bàn phím thực (Tab/Shift+Tab/Enter/Space) trên wizard dots — chỉ xác nhận cấu trúc <button>+aria-label đúng, chưa quan sát focus ring/screen reader thật
Chất lượng thông báo lỗi khi validate — chỉ xác nhận cơ chế native reportValidity(), chưa quan sát trải nghiệm thực tế người dùng gặp lỗi
Task study/thời gian hoàn thành theo role — ngoài phạm vi phiên đánh giá này
Ngoài phạm vi
Screen reader test thực (NVDA/VoiceOver)
UAT với người dùng nghiệp vụ cảng thật
Accessibility audit tự động (axe-core/Lighthouse)
Performance trace trên thiết bị/network thực
Finding cũ không còn hợp lệ / đã đổi bản chất
UX-001 (thứ tự bước A→E→B→C/D) — OBSOLETE do đã tái cấu trúc: thứ tự mới hợp lý theo mô hình tư duy người khai, xác nhận PASS
UX-002 (nhãn "Tự lưu trên trình duyệt" nhập nhằng) — cần xem lại: dòng chữ "● Tự lưu trên trình duyệt" trong header dialog vẫn còn nguyên văn giống báo cáo cũ đã phê phán; checkpoint tự nhận IMPLEMENTED nhưng bằng chứng DOM as-served chưa cho thấy thay đổi nhãn rõ rệt — đề nghị hạ xuống PARTIAL, không đóng
UX-003 (wizard dots thiếu keyboard semantics) — PASS: nay là <button> thật với aria-label
UX-004 (select multiple khó dùng) — cần browser thật để xác nhận đã đổi sang checkbox như checkpoint tuyên bố; DOM as-served bước 4 vẫn cho thấy <select ... multiple size="4"> — đây là điểm mâu thuẫn với tuyên bố "IMPLEMENTED" của checkpoint
§4Mâu thuẫn cần đối chiếu thêm trước khi phê duyệt báo cáo
ĐỐI CHIẾU
Checkpoint tuyên bố UX-004 "crew selection uses a checkbox checklist" — DOM as-served không khớp
Cần làm rõ
Tuyên bố checkpoint
UX_EVALUATION_RESPONSE_20260713.md §9: "UX-004: IMPLEMENTED — crew selection uses a checkbox checklist..."
Bằng chứng DOM thực tế (as-served app.js dòng 670)
<select name="crew_ids" id="declaration-crew" multiple size="4">...</select>
Đây vẫn là native <select multiple>, không phải checkbox list.
Mức độ ảnh hưởng: Cao đối với độ tin cậy báo cáo — một mục checkpoint tự nhận "IMPLEMENTED" không khớp bằng chứng runtime thực tế. Có thể do nhánh code khác hoặc thay đổi bị revert. Cần Đội phát triển xác nhận trước khi Gate 5 xem xét đóng mục UX-004.

§5Khuyến nghị ưu tiên xử lý (chỉ để tham khảo lập work order — chưa thi công)
Ưu tiên	Việc cần làm	Vì sao
P0	Vô hiệu hóa route CV_APPROVE/QLC_APPROVE/BP_APPROVE ở API, rà soát phiếu đã kẹt	CRIT-001 — lỗi toàn vẹn nghiệp vụ, có thể khóa vĩnh viễn phiếu khách hàng thật
P0	Sửa search backend để match vessel_name/master_name	UX-101 — chức năng tìm kiếm cốt lõi không hoạt động
P1	Áp dụng page_size/page thật ở backend	UX-102 — rủi ro hiệu năng khi dữ liệu lớn lên
P1	Xác minh lại UX-004 (crew checkbox) bằng browser thật, đối chiếu tuyên bố checkpoint	Mâu thuẫn tài liệu vs runtime cần làm rõ trước khi đóng Gate 5
P1	Error summary + focus-to-error trong wizard	UX-105 — khuyến nghị P1 cũ vẫn chưa triển khai
P2	Đồng bộ audit note "Nộp" → "Xác nhận & gửi"; đổi "CREW LIST" sang tiếng Việt	UX-103, UX-106 — tồn đọng nhỏ
Báo cáo đánh giá độc lập · Không thi công trong lượt này · Dữ liệu test id=7,8 được giữ nguyên trong DB demo làm bằng chứng tái kiểm chứng CRIT‑001, chưa dọn dẹp.
