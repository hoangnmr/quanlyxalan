# EA Remediation Roadmap — Khai-bao-Cang-vu

> Baseline review: 2026-07-11  
> Scope: working tree hiện tại  
> Assessment phase: REVIEW  
> Risk: R1 cho tài liệu; thay đổi authentication, dữ liệu và external API là R2  
> Production readiness: NOT READY

## 1. Executive decision

Ứng dụng có mô hình nghiệp vụ và UX MVP tốt, nhưng lần chuyển đổi từ backend
Python stdlib sang FastAPI đang dở dang. Frontend, backend, test, dependency và
runbook không còn cùng một contract. Ưu tiên hiện tại là phục hồi baseline chạy
được và kiểm soát truy cập; không thêm UI hoặc integration mới trước khi Gate 1
và Gate 2 đạt.

Điểm baseline EA: **3.5/10**.

## 2. Verified baseline

- CVF Workspace Doctor: PASS 17/17 sau khi đưa Git vào PATH của tiến trình.
- Python compile: PASS.
- Automated tests: FAIL/NOT RUNNABLE; virtual environment thiếu dependency và
  test suite vẫn tham chiếu API backend cũ.
- Frontend gọi nhiều API chưa tồn tại trong FastAPI hiện tại.
- `run-dev.ps1` vẫn chạy backend theo entry point cũ.
- Working tree có nhiều thay đổi chưa commit; `backend/app.py` và
  `backend/database.py` đã mất phần lớn chức năng của bản đã commit.
- JWT đã được thêm nhưng chưa có RBAC và tenant isolation thực sự.
- Không có bằng chứng Alembic migration hoạt động dù dependency đã được khai báo.

## 3. Architecture target

Giữ mô hình **modular monolith** trong giai đoạn này:

```text
Browser
  -> HTTPS reverse proxy
  -> FastAPI modular monolith
       -> Identity and RBAC
       -> Organizations / Vessels / Crew
       -> Declarations / Permit workflow
       -> Import / Reports / Attachments
       -> Integration adapters (disabled by default)
  -> PostgreSQL (production) / SQLite (local only)
  -> Object storage + malware scanning (production attachments)
  -> Structured audit and operational telemetry
```

Không tách microservices trước khi tải, ownership và nhu cầu scaling chứng minh
sự cần thiết.

## 4. Delivery roadmap

### Tranche T0 — Baseline recovery and contract freeze (P0)

Mục tiêu: đưa repository về trạng thái cài được, test được và chạy end-to-end.

- Quyết định FastAPI là backend đích; đối chiếu các chức năng còn ở commit
  `29ef124` để port có kiểm soát, không sao chép mù quáng.
- Lập API contract inventory giữa `frontend/app.js` và FastAPI.
- Khôi phục toàn bộ endpoint frontend đang dùng hoặc chủ động loại bỏ tính năng
  khỏi UI và product scope.
- Sửa entry point thành `python -m uvicorn backend.app:app`.
- Khóa dependency theo phiên bản; thêm dependency dành cho test.
- Viết lại test theo FastAPI/SQLAlchemy, dùng database tạm riêng.
- Không sửa hoặc xóa dữ liệu người dùng trong `data/`.

Gate 0:

- Fresh environment cài thành công từ tài liệu.
- Một lệnh chạy test; toàn bộ test PASS.
- Một lệnh khởi động; health, frontend và critical workflow smoke PASS.
- Không còn API frontend gọi mà backend trả 404 ngoài các feature được ghi rõ là
  disabled.
- Working tree được review trước khi commit; không trộn thay đổi ngoài tranche.

### Tranche T1 — Identity, RBAC and tenant isolation (P0)

Mục tiêu: danh tính server-side và dữ liệu giữa khách hàng không bị lộ chéo.

- Xác định role matrix: `CUSTOMER`, `CV`, `QLC`, `BP`, `ADMIN`.
- Gắn user với organization; mọi truy vấn customer phải có organization scope.
- Actor name/role của workflow lấy từ user đã xác thực, không nhận từ form.
- Endpoint-level authorization và negative tests cho từng role.
- Bỏ JWT secret mặc định; ứng dụng fail-fast nếu thiếu secret ở môi trường không
  phải local/test.
- CORS allowlist theo môi trường; thiết kế session/token an toàn hơn
  `localStorage`.
- Password policy, bootstrap admin an toàn, rate limit login và audit đăng nhập.

Gate 1:

- CUSTOMER A không thể đọc/sửa dữ liệu CUSTOMER B.
- Không role nào có thể bỏ qua CV -> QLC -> BP -> ISSUE.
- Client không thể giả actor hoặc role.
- Test authorization cả đường thành công và bị từ chối đều PASS.
- Human review bắt buộc vì tranche là R2.

### Tranche T2 — Domain integrity and persistence (P0/P1)

Mục tiêu: workflow và dữ liệu có tính toàn vẹn, có thể nâng cấp schema an toàn.

- Dùng Pydantic request/response models thay cho `payload: dict`.
- Validate required fields, enum, số không âm, ETA < ETD, certificate dates và
  identifier format.
- Transaction boundary một request/một unit of work; rollback và map lỗi DB.
- Xử lý not-found, duplicate và optimistic concurrency rõ ràng.
- Hoàn thiện SQLAlchemy relationships và timestamp update.
- Tạo Alembic baseline/migrations; cấm dùng `create_all()` làm production
  migration.
- Chuẩn hóa state machine, immutable snapshot và append-only audit events.

Gate 2:

- Migration upgrade từ database baseline và rollback rehearsal PASS.
- State transition tests, validation tests và transaction failure tests PASS.
- Không thể sửa phiếu đã nộp ngoài luồng điều chỉnh được phê duyệt.
- Audit ghi user, action, entity, timestamp và correlation id.

### Tranche T3 — Files, imports and reports (P1)

Mục tiêu: khôi phục đầy đủ nghiệp vụ Excel/chứng từ với kiểm soát an toàn.

- Giới hạn dung lượng, extension, magic bytes, filename và decompression ratio.
- Quarantine và malware scanning cho production attachments.
- Import có preview, row-level validation, accepted/rejected result và
  idempotency.
- Version hóa Excel template/mapping.
- Golden-file tests cho Appendix 1/2/3 và đối chiếu nghiệp vụ có người duyệt.
- Large export chạy bất đồng bộ khi đạt ngưỡng cấu hình.

Gate 3:

- Malformed/oversized/malicious files bị từ chối an toàn.
- Import lặp lại không tạo dữ liệu trùng ngoài quy tắc đã định.
- Báo cáo khớp golden dataset và được nghiệp vụ ký xác nhận.

### Tranche T4 — Operability and production foundation (P1/R2)

Mục tiêu: triển khai lặp lại được, quan sát được và phục hồi được.

Local-first profile: `docs/T4_LOCAL_OPERATING_PROFILE.md`. Until hosting,
domain and staging are assigned, T4 can pass a local gate but cannot claim
production readiness.

- Dockerfile/container runtime non-root và environment configuration.
- CI: lint, type check, unit, integration, contract, security scan.
- Structured logs, request/correlation id, metrics, readiness/liveness và alert.
- PostgreSQL production; backup mã hóa, retention và restore drill.
- HTTPS/security headers/reverse proxy hardening.
- Runbook deploy, rollback, incident và data recovery.

Gate 4:

- CI bắt buộc PASS trước merge.
- Restore drill chứng minh RPO/RTO đã thống nhất.
- Staging smoke/regression/security checks PASS.
- Human release approval bắt buộc.

### Tranche T5 — Product professionalization (P2)

Mục tiêu: nâng UX sau khi nền tảng an toàn và ổn định.

- Dashboard theo role và work queue theo SLA.
- Server-side pagination/filter/sort.
- Form validation nhất quán, loading/empty/error states và draft recovery.
- Accessibility keyboard/focus/contrast; responsive regression.
- Certificate expiry notifications và operational reminders.
- Quyết định giữ Vanilla JS hay chuyển framework bằng ADR, không đổi chỉ vì
  thẩm mỹ.

Gate 5:

- Task-based usability test đạt tiêu chí đã duyệt.
- Accessibility audit không còn lỗi nghiêm trọng.
- Performance budget và mobile/desktop regression PASS.

### Tranche T6 — External authority integrations (P2/R2)

Chỉ bắt đầu khi có API contract, endpoint, credential, data-sharing approval,
rate limit, sandbox và quy tắc receipt chính thức.

- Adapter boundary, outbound allowlist, credential vault.
- Idempotency key, retry/backoff, dead-letter handling và reconciliation.
- Preview/approval trước khi gửi; receipt lưu bất biến.
- Không dùng mock để tuyên bố CVF governance hoặc integration production-ready.

Gate 6:

- Contract test với sandbox thật PASS.
- Security/privacy review và human approval hoàn tất.
- Live provider/API evidence được lưu theo CVF khi có tuyên bố quản trị hoặc
  release-quality integration.

## 5. Priority and dependency

```text
T0 Baseline
  -> T1 Identity/RBAC
  -> T2 Domain/Data
  -> T3 Files/Reports
  -> T4 Operations
  -> T5 UX
  -> T6 External Integration
```

T1 và T2 có thể thiết kế song song nhưng phải tích hợp tuần tự. T5 không được
lấy nguồn lực khỏi P0. T6 bị khóa bởi thẩm quyền và contract bên ngoài.

## 6. Definition of done for every tranche

- Scope và acceptance criteria được truy vết tới issue/test.
- Không có secret hoặc production data trong repository/log/evidence.
- Test liên quan PASS; regression suite PASS.
- Tài liệu kiến trúc, deployment và handoff phản ánh đúng code thực tế.
- Có human review cho R2/R3.
- Commit chỉ chứa thay đổi của tranche.
- Không tuyên bố CLOSED khi còn test fail, artifact thiếu hoặc gate chưa đạt.

## 7. Open architecture decisions

- ADR-001: FastAPI migration strategy và feature parity boundary.
- ADR-002: JWT bearer so với secure cookie/BFF session.
- ADR-003: SQLite-to-PostgreSQL cutover point.
- ADR-004: Attachment storage/quarantine provider.
- ADR-005: Vanilla JS modularization so với React/Vue migration.
- ADR-006: Reporting template ownership và signed mapping version.
