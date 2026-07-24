# Roadmap: Xử lý tại cảng (Bảo vệ / Giao nhận / Hủy phiếu)

> **Trạng thái: ĐÃ TRIỂN KHAI đầy đủ 4/4 giai đoạn** (PR
> [Blackbird081/quanlyxalan#... → hoangnmr/quanlyxalan#5](https://github.com/hoangnmr/quanlyxalan/pull/5)).
> Tài liệu này giữ nguyên làm hồ sơ quyết định nghiệp vụ đã chốt trước khi code —
> mọi mục "Giai đoạn 1-4" bên dưới mô tả **kế hoạch gốc**, đã được implement đúng
> như vậy trừ khi có ghi chú "✅ Đã làm" / thay đổi trong mục **"Nhật ký triển
> khai & điều chỉnh sau khi implement"** ở cuối file. Đọc mục đó trước nếu chỉ
> quan tâm trạng thái hiện tại, không cần đọc lại toàn bộ kế hoạch.

## Findings đánh giá độc lập (đã xử lý trong tài liệu)

Rà soát đối chiếu với mã nguồn thực tế; mọi số dòng/tên hằng đã được kiểm chứng.

| # | Finding | Quyết định |
| --- | --- | --- |
| 1 | Cột `actual_arrival_time`/`_time` đề xuất **trùng** với `actual_arrival_at`/`actual_departure_at` đã có (`models.py:149`) → chia đôi nguồn ATB/ATD. | Tái dùng cột có sẵn, bỏ cột mới. Xem Quyết định + Giai đoạn 1. |
| 2 | Thuật ngữ "arrival"/"ATA" gây nhầm *đến vùng nước cảng* với *cập cầu*. | Thống nhất ETB/ETD·ATB/ATD ở nhãn hiển thị (đã áp dụng); giữ tên cột DB. |
| 3 | `DeclarationEvent.to_status` là `NOT NULL` (`models.py:198`) — sự kiện cảng không đổi status vẫn phải điền. | Quy ước `to_status = from_status`, phân biệt qua `action`. Xem Giai đoạn 2. |
| 4 | Timeline (`app.js:1718`) render mọi event bằng `workflowLabel(to_status)` → sự kiện cảng lọt vào lịch sử duyệt với nhãn sai. | Tách 2 timeline riêng (duyệt thủ tục / hoạt động cảng). Xem Giai đoạn 2. |
| 5 | `_attention_queue` (`app.py:1654`) lọc cứng theo `workflow_status` — không tái dùng cho hàng đợi hủy (trục lọc `cancel_requested_at`). | Viết hàm độc lập. Xem Giai đoạn 4. |
| 6 | Đếm "đã gửi" (`app.py:1707`) tái dùng `submitted_q` qua nhiều nhánh scope. | Rà toàn bộ nơi lọc `workflow_status` khi thêm `CANCELLED`. Xem Giai đoạn 1. |
| 7 | `PLATFORM_ADMIN` không có `staff_function` (`resolve_scope` không lookup membership cho Admin). | Admin thao tác được mọi cổng, không gate. `staff_function` chỉ gate `PORT_STAFF`. Xem Giai đoạn 1. |

## Bối cảnh nghiệp vụ

Sau khi phiếu khai báo được Admin duyệt (`workflow_status = APPROVED`), thông
tin cập/rời cầu, sản lượng vẫn chỉ là "kế hoạch". Nghiệp vụ thực tế tại cảng
gồm 2 bộ phận độc lập:

1. **Bảo vệ**: cần biết phiếu đã được Admin duyệt, ghi nhận giờ cập/rời thực
   tế (ATB/ATD), xác nhận đã thu phí cầu bến.
2. **Giao nhận**: kiểm soát việc giao/nhận hàng thực tế (có thể 2 chiều nếu
   salan vừa nhập vừa xuất), chỉ được xác nhận sau khi Bảo vệ đã xác nhận thu
   phí.

Đây là 2 trục trạng thái **độc lập** với trục duyệt thủ tục của Admin — không
gộp chung enum.

## Quyết định đã chốt

- **Thuật ngữ thời gian**: toàn ứng dụng thống nhất **ETB/ETD** (dự kiến
  cập/rời cầu) và **ATB/ATD** (thực tế cập/rời cầu) — không dùng "arrival"/ATA
  (dễ nhầm "đến vùng nước cảng" với "cập cầu"). Chỉ sửa **nhãn hiển thị** tiếng
  Việt và tên cột Excel; **giữ nguyên** tên cột DB (`eta`, `etd`,
  `actual_arrival_at`, `actual_departure_at`) và field API — tầng kỹ thuật
  không lộ ra giao diện nên end user không cần biết. (Đã thực hiện: nhãn form
  `frontend/app.js:1443`, alias Excel `backend/xlsx_io.py:569`, bỏ alias "ATA".)
- **Tái dùng cột ATB/ATD có sẵn**: `Declaration` đã có `actual_arrival_at` /
  `actual_departure_at` (`models.py:149`). Luồng Bảo vệ/Giao nhận ghi trực tiếp
  vào 2 cột này — **không tạo cột `_time` mới** để tránh chia đôi nguồn dữ liệu.
  Lưu ý phân biệt: import TOS ghi ATB/ATD vào `HistoricalPortCall`
  (`models.py:596`, dữ liệu đối soát báo cáo PL.03) — **khác** với ATB/ATD vận
  hành trên `Declaration`; tuyệt đối không trộn 2 luồng.
- Thủ tục (Admin duyệt) và Giao/nhận hàng là hai trục trạng thái độc lập —
  trục sau chỉ mở khi phiếu đã `APPROVED`.
- ATB/ATD do cả Bảo vệ và Giao nhận cùng sửa được — ghi đè tự do, lưu lịch sử
  qua sự kiện phiếu (`DeclarationEvent`), không cảnh báo xung đột.
- Bảo vệ xác nhận thu phí cầu bến là điều kiện tiên quyết — Giao nhận chỉ xác
  nhận được sau đó (không phải ngược lại).
- Giao nhận có thể tự thêm chiều nhập/xuất phát sinh ngoài kế hoạch ngay tại
  chỗ, không cần quay lại sửa hồ sơ / không cần Admin duyệt lại.
- "Hoàn tất một chu trình cập→rời" gắn với thời điểm ghi nhận ATD — không suy
  luận từ trạng thái các nút xác nhận khác.
- Có thêm tab mới **"Kế hoạch làm hàng"** cho toàn bộ nhân viên Cảng (không
  phân biệt Bảo vệ/Giao nhận) xem toàn cảnh 5 mốc: đăng ký → Admin duyệt →
  thu phí → giao/nhận hàng → rời cầu.
- **Sổ theo dõi Salan giữ nguyên chức năng hiện tại** (danh mục vessel cố
  định của đơn vị báo cáo) — không "chuyển" record giữa 2 tab, vì Sổ theo dõi
  lưu theo **phương tiện** (vĩnh viễn), còn phiếu khai báo là theo **lượt**
  (một lần). Tab Kế hoạch làm hàng chỉ ẩn dòng khi có ATD; Sổ theo dõi có thể
  join thêm 1 cột nhỏ "lượt gần nhất" để tham khảo.
- Hủy phiếu là trạng thái riêng (`CANCELLED`), không phải xóa (DELETE) — giữ
  lại để Admin thống kê số lượt bị hủy.
- Chỉ **Admin** được hủy thật, từ cả `APPROVED` và `PENDING_REVIEW` (khách đổi
  ý trước khi kịp duyệt). Nhân viên khác (Port staff) bấm "Hủy" **không** đổi
  `workflow_status` — chỉ ẩn dòng đó cục bộ cho họ + gửi thông báo cho Admin
  duyệt mới thực sự là hủy.

## Giai đoạn 1 — Nền dữ liệu & phân quyền

Không tạo tính năng mới cho người dùng thấy — chỉ mở rộng schema và phân
quyền để 3 giai đoạn sau xây lên trên. Rủi ro thấp nhất, nên làm trước.

| Việc | Vị trí | Chi tiết |
|---|---|---|
| ~~Cột ATB/ATD thực tế~~ **Tái dùng cột có sẵn** | `backend/models.py:149` | **Không tạo cột mới.** `Declaration.actual_arrival_at` / `actual_departure_at` đã tồn tại — Bảo vệ/Giao nhận ghi trực tiếp vào đây. Nhãn hiển thị ATB/ATD; cột DB giữ tên cũ (xem "Thuật ngữ thời gian" ở phần Quyết định). |
| Cột cổng Bảo vệ | `backend/models.py` | `berth_fee_status` (PENDING/CONFIRMED), `berth_fee_confirmed_at`, `berth_fee_confirmed_by_user_id`. |
| Cột Giao nhận 2 chiều | `backend/models.py` | `unload_status`, `load_status` (PENDING/CONFIRMED) + `unload_is_adhoc`, `load_is_adhoc` cho chiều phát sinh ngoài kế hoạch. |
| Cột hủy phiếu | `backend/models.py` | `cancel_requested_at`, `cancel_requested_by_user_id` — yêu cầu hủy, tách khỏi `workflow_status` thật. |
| Giá trị workflow mới | `backend/app.py:202` (`WORKFLOW_TRANSITIONS`) | Thêm `CANCELLED` + 2 rule chuyển trạng thái (từ `PENDING_REVIEW`, từ `APPROVED`). Không cần migration CHECK constraint — cột hiện là String tự do. |
| Sửa đếm dashboard | `backend/app.py:1707` **và mọi nơi tái dùng** | Thêm `CANCELLED` vào danh sách loại trừ ở phép đếm "đã gửi" (`notin_(...)`). **Cảnh báo**: `submitted_q` được tái dùng qua nhiều nhánh scope (`app.py:1718`, `1727`) — sửa 1 chỗ khai báo là đủ nếu tất cả nhánh cùng lọc từ `submitted_q`, nhưng phải rà lại toàn bộ nơi lọc `workflow_status` cho phép đếm để không sót. Nếu bỏ qua, phiếu hủy bị đếm nhầm vào "đã gửi". |
| Phân loại nghiệp vụ nhân viên | `backend/tenant.py` (`ReportingUnitUser`, `models.py:381`) | `staff_function` (`SECURITY` / `CARGO_OPS` / `None`) — gắn theo **đơn vị báo cáo** (cột trên bảng membership `reporting_unit_users`), vì 1 người có thể giữ vai trò khác nhau ở cảng khác nhau. |
| Expose qua Scope | `backend/tenant.py` | `Scope.staff_function` để 3 endpoint mới ở Giai đoạn 2–4 kiểm tra quyền. **Chốt quyền Admin**: `PLATFORM_ADMIN` thao tác được **mọi** cổng (Bảo vệ + Giao nhận) — không gate theo `staff_function`, đúng pattern hiện tại (Admin duyệt được mọi phiếu). `staff_function` chỉ gate `PORT_STAFF`. `resolve_scope` **không** cần lookup membership cho Admin — giữ nguyên hành vi `tenant.py:142`. |

**Lưu ý**: không có CHECK constraint nào trên `workflow_status` hiện nay (xác
nhận qua rà soát code) — thêm giá trị mới không cần migration ràng buộc,
nhưng cũng không có gì tự chặn giá trị sai chính tả. Nên cân nhắc thêm CHECK
constraint cùng đợt này, theo đúng pattern đã dùng cho các bảng lịch sử
(`HistoricalImportBatch.status` v.v.).

## Giai đoạn 2 — Cổng Bảo vệ & xác nhận Giao nhận

Tính năng người dùng đầu tiên thấy được. Một panel duy nhất trong màn chi
tiết phiếu, chỉ hiện khi phiếu đã `APPROVED`, chia theo `staff_function`.

Luồng:
1. Bảo vệ ghi ATB khi salan cập bến, xác nhận đã thu phí cầu bến.
2. Giao nhận chỉ thấy nút xác nhận khi phí đã được xác nhận; xác nhận từng
   chiều nhập/xuất theo kế hoạch đã khai.
3. Nếu phát sinh chiều ngoài kế hoạch, Giao nhận bấm "+ Thêm xác nhận" —
   không cần Admin duyệt lại.
4. Bảo vệ/Giao nhận ghi ATD khi salan rời bến — đánh dấu hoàn tất chu trình.

Cổng cứng duy nhất trong luồng: Giao nhận không xác nhận được nếu phí cầu
bến chưa `CONFIRMED`.

| Endpoint | Quyền | Điều kiện & hành vi |
|---|---|---|
| `POST /api/declarations/{id}/atb-atd` | Bảo vệ + Giao nhận + Admin | Ghi đè trực tiếp `actual_arrival_at`/`actual_departure_at` (cột có sẵn, không tạo mới). Mỗi lần sửa ghi 1 `DeclarationEvent` để audit — xem "Quy ước ghi sự kiện cảng" bên dưới. |
| `POST /api/declarations/{id}/berth-fee` | Bảo vệ + Admin | Yêu cầu `workflow_status = APPROVED`. Set `berth_fee_status = CONFIRMED`. |
| `POST /api/declarations/{id}/cargo-ops` | Giao nhận + Admin | Body `{direction, adhoc?}`. Chặn 400/409 nếu phí cầu bến chưa xác nhận. Set trạng thái chiều tương ứng. |

### Quy ước ghi sự kiện cảng vào `DeclarationEvent`

`DeclarationEvent.to_status` là `NOT NULL` (`models.py:198`) — sự kiện cảng
không đổi `workflow_status`, nên ghi `to_status = from_status = workflow_status`
hiện tại (giữ nguyên), phân biệt qua cột `action` (`ATB_UPDATED`, `ATD_UPDATED`,
`BERTH_FEE_CONFIRMED`, `CARGO_LOAD_CONFIRMED`, `CARGO_UNLOAD_CONFIRMED`,
`CANCEL_REQUESTED`). Giá trị cũ/mới của ATB/ATD lưu trong `note`.

### Tách 2 timeline trong màn chi tiết phiếu

Timeline hiện tại (`app.js:1718`) render **mọi** event bằng
`workflowLabel(event.to_status)` — nếu để nguyên, sự kiện cảng sẽ hiện thành
"Đã duyệt" lặp lại vô nghĩa (vì `to_status` giữ nguyên `APPROVED`). Quyết định:
**tách 2 timeline riêng biệt**.

| Việc | Vị trí | Chi tiết |
|---|---|---|
| Timeline "Lịch sử duyệt thủ tục" | `frontend/app.js:1718` | Giữ nguyên render hiện có nhưng **lọc** chỉ các `action` thuộc workflow duyệt (`PORT_APPROVE`, `REQUEST_CHANGES`, và các action nộp/gửi lại). |
| Timeline "Hoạt động tại cảng" (mới) | `frontend/app.js` | Danh sách riêng cho các `action` cảng ở trên — hiển thị bằng nhãn theo `action`, **không** dùng `workflowLabel` (vốn chỉ biết 4 status workflow). |
| Nguồn dữ liệu | `GET /api/declarations/{id}/events` | Cùng endpoint; frontend phân loại theo `action`. Không cần endpoint mới. |

## Giai đoạn 3 — Tab "Kế hoạch làm hàng"

Toàn cảnh cho mọi nhân viên Cảng — không phân biệt Bảo vệ/Giao nhận. Danh
sách các lượt đang trong chu trình cập→rời, không phải công cụ tìm kiếm hồ sơ
(khác với trang "Phiếu khai báo" hiện có).

| Việc | Vị trí | Chi tiết |
|---|---|---|
| Route & nav mới | `frontend/index.html` | `#work-schedule` — hiện cho mọi `PORT_STAFF`, không gate theo `staff_function`. |
| Điều kiện lọc | `backend/app.py` (endpoint mới) | Tất cả trạng thái workflow **trừ `CANCELLED`**, và `actual_departure_at IS NULL` (tên cột thật, tái dùng — xem finding #1) — loại trừ hủy tường minh để không kẹt vĩnh viễn trên tab. |
| Cột hiển thị | `frontend/app.js` | 5 mốc trên một dòng: đăng ký · duyệt Admin · thu phí · giao/nhận hàng · ATD — mỗi mốc là 1 chip trạng thái. |
| Sổ theo dõi Salan | giữ nguyên | Không "chuyển" record — chỉ join thêm 1 cột nhỏ "lượt gần nhất" từ Declaration mới nhất của vessel đó. |

## Giai đoạn 4 — Hủy phiếu hai cấp

Phụ thuộc nhiều nhất vào hạ tầng có sẵn — tận dụng pipeline email đang chạy
thật (`backend/notifications.py`), không xây hệ thống thông báo mới.

Luồng:
1. **Admin**: hủy trực tiếp từ `APPROVED` hoặc `PENDING_REVIEW` →
   `workflow_status = CANCELLED` ngay lập tức.
2. **Nhân viên khác**: bấm "Hủy" → không đổi `workflow_status`. Chỉ ghi yêu
   cầu + ẩn dòng đó trên máy của họ (`localStorage`, theo username).
3. **Hệ thống**: gửi email cho Admin — tái dùng pipeline
   `backend/notifications.py` đang chạy cho nộp phiếu/duyệt.
4. **Admin**: duyệt → hủy thật. Từ chối → xóa yêu cầu, phiếu trở lại bình
   thường cho mọi người.

| Việc | Loại | Chi tiết |
|---|---|---|
| Nhãn & màu badge | Mới | `workflowLabel`/`workflowTone` (`frontend/app.js:815`) thêm `CANCELLED: "Đã hủy"` + tone màu riêng, tránh trùng màu xám của "Nháp". |
| `POST /api/declarations/{id}/cancel-request` | Mới | Nhân viên không phải Admin gọi. Set 2 cột yêu cầu hủy, ghi sự kiện `CANCEL_REQUESTED` theo "Quy ước ghi sự kiện cảng" (Giai đoạn 2): `to_status = from_status`, phân biệt qua `action`. Sự kiện này thuộc timeline "Hoạt động tại cảng", không phải timeline duyệt thủ tục. |
| Resolver email Admin | Mới | Chưa có sẵn — cần 1 truy vấn lấy toàn bộ user role `PLATFORM_ADMIN`, khác với resolver hiện có (theo tổ chức/đơn vị). |
| Hàng đợi Admin duyệt hủy | Mới (hàm độc lập) | Thêm nhánh riêng vào dashboard cho `PLATFORM_ADMIN` — lọc theo `cancel_requested_at IS NOT NULL` (**trục lọc khác hẳn** `workflow_status`: phiếu chờ hủy vẫn đang `APPROVED`/`PENDING_REVIEW`). `_attention_queue` (`app.py:1654`) lọc cứng theo `workflow_status.in_(statuses)` — **không tái dùng thẳng được**; viết hàm mới song song, không phải "thêm nhánh vào hàm cũ". |
| Ẩn cục bộ theo nhân viên | Tái dùng | `localStorage` theo username — đúng pattern đang dùng cho nháp/theme/đơn vị đang chọn. Không cần bảng mới trừ khi cần đồng bộ nhiều thiết bị. |
| Gửi email yêu cầu hủy | Tái dùng | `backend/notifications.py` — thêm 1 hàm theo đúng khuôn `notify_declaration_submitted`/`notify_declaration_workflow` đã có, dùng lại `_dispatch`/SMTP/background task. |

**Quyết định trước khi implement**: Admin **từ chối** yêu cầu hủy thì
dòng đó có tự động hiện lại (xóa luôn state ẩn cục bộ khi yêu cầu bị từ chối) để
tránh mất dấu phiếu đang hoạt động.

## Thứ tự triển khai

Bốn giai đoạn độc lập theo thứ tự nền tảng trước, tính năng sau — mỗi giai
đoạn merge riêng, không giai đoạn nào chặn giai đoạn kế nếu cần dừng giữa
chừng để đánh giá.

## Nhật ký triển khai & điều chỉnh sau khi implement

**Cả 4 giai đoạn đã code, test và merge đúng như kế hoạch mô tả ở trên.**
43 test mới trong `tests/test_port_operations.py`, kiểm chứng UI thật qua
Playwright cho từng giai đoạn (không chỉ dựa vào test suite). Migration:
`alembic/versions/u20f0f000020_port_operations_phase1.py`.

**Xác nhận lại các quyết định gây tranh cãi trong quá trình tự test UI** —
không phải bug, giữ nguyên theo đúng kế hoạch gốc:
- "Cổng cứng" Giao nhận chỉ xác nhận được **sau khi** Bảo vệ xác nhận thu phí
  cầu bến (không có chiều ngược lại) — đúng chủ đích, xem "Quyết định đã chốt"
  dòng 57-58 và Giai đoạn 2. Đã hỏi lại trực tiếp và được xác nhận giữ nguyên.

**Các điều chỉnh UI/UX phát sinh ngoài kế hoạch gốc**, sau khi user tự test
giao diện thật và phản hồi từng vòng — không đổi luồng nghiệp vụ, chỉ đổi cách
trình bày:
- Bỏ hẳn nhãn "Vào cảng"/"Rời cảng" khỏi mọi nơi hiển thị (bảng danh sách, tab
  Kế hoạch làm hàng, form tạo phiếu, chi tiết phiếu) — làm rõ **không có khái
  niệm "2 loại phiếu"**, chỉ có 1 loại phiếu khai báo ghi cả 2 mốc đến/rời.
  `Declaration.movement_type` (ARRIVAL/DEPARTURE) vẫn giữ trong DB (dùng cho
  báo cáo Phụ lục 2 và `_declaration_operating_date()`) nhưng không còn lộ ra
  giao diện — cân nhắc dọn kỹ thuật nhưng quyết định giữ nguyên vì rủi ro dọn
  cao hơn giá trị mang lại, miễn không hiện trên UI là đạt yêu cầu.
- Đổi nhãn trạng thái "Chờ Cảng xử lý" → "Chờ duyệt".
- Bỏ bộ lọc "Loại phiếu" khỏi thanh filter (ẩn, không xóa hẳn — JS còn tham
  chiếu), mở rộng ô "Thuyền trưởng".
- Lỗi validate 422 hiện rõ tên field thay vì chỉ "Field required" chung chung.
- `master_phone` không còn bị bắt buộc khi để trống (thiếu default khiến
  Pydantic coi là field bị thiếu thay vì chuỗi rỗng).
- Log "Hoạt động tại cảng" format ngày giờ theo chuẩn Việt Nam
  (`dd/mm/yyyy hh:mm`) thay vì in nguyên chuỗi ISO thô.
- Tách nút "Lưu ATB/ATD" gộp chung thành 2 nút độc lập ("Lưu ATB" / "Lưu ATD")
  — ATB và ATD thường cách nhau nhiều ngày, gộp chung dễ hiểu lầm phải điền đủ
  cả hai mới lưu được. Layout 2 field xếp ngang hàng thay vì xếp dọc chiếm hết
  chiều rộng dialog.
- Sửa màu badge "Tiến trình" (approval dot) từ xám nhạt gần như vô hình sang
  tông vàng cảnh báo, đồng bộ với badge "Chờ duyệt"; khối "Bảo vệ"/"Giao nhận"
  trong dialog chi tiết phiếu thêm viền để tách bạch thay vì nhòe vào nhau.
- Sửa lỗi CSS Grid khiến nút "Ghi nhận thao tác" bị đè lên khung ghi chú khi
  người dùng kéo giãn tay ô textarea (`grid-auto-rows: min-content`).

**Nợ kỹ thuật đã biết, cố ý không xử lý ngay**: migration `u20f0f000020`
idempotent và an toàn chạy lại, nhưng **chưa từng được chạy trên DB `cangvu`
thật** — chỉ chạy trên Postgres throwaway dùng để test trong nhánh này. Người
merge PR cần chạy `alembic upgrade head` trên bản backup/staging của DB thật
trước, xác nhận ổn rồi mới áp dụng production.
