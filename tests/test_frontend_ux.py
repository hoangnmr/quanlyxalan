from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_wizard_steps_use_native_keyboard_controls():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert 'class="wizard-step-button"' in app_js
    assert 'aria-current="step"' in app_js
    assert '<nav class="wizard-progress-wrap" aria-label="Các bước khai báo">' in app_js
    assert "data-wizard-dot" in app_js


def test_local_draft_status_explains_storage_boundary():
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert 'id="draft-state"' in index_html
    assert 'role="status" aria-live="polite"' in index_html
    assert "Nháp cục bộ" in index_html
    assert "Nháp cục bộ · chưa gửi" in index_html
    assert "tanthuan-declaration-draft-saved-at" in app_js
    assert "function updateLocalDraftStatus(" in app_js


def test_inline_error_recovery():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "function showStepErrors(" in app_js
    assert "function showFieldError(" in app_js
    assert "function clearFieldError(" in app_js
    assert "step-error-summary" in app_js
    assert "aria-invalid" in app_js
    assert "field-error" in app_js
    assert "showFieldError(el," in app_js
    assert "function validateWizardForm(" in app_js
    assert "showStepErrors([error.message]" in app_js


def test_crew_checklist_replaces_select_multiple():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert "function crewChecklistHtml(" in app_js
    assert "crew-checklist" in app_js
    assert 'type="checkbox"' in app_js
    assert 'name="crew_ids"' in app_js
    # declaration-crew-container is used instead of native select in wizard
    assert "declaration-crew-container" in app_js
    assert "crewContainer.querySelectorAll" in app_js
    assert "suggestion.crew_ids.includes(Number(input.value))" in app_js


def test_role_dashboard_layout():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "function roleLabel(role)" in app_js
    assert "const isCustomer = state.currentUser.role === 'CUSTOMER'" in app_js
    assert "const isAdmin = state.currentUser.role === 'PLATFORM_ADMIN'" in app_js
    assert "const isReviewer = state.currentUser.role === 'PORT_STAFF'" in app_js
    assert 'id="admin-operations"' in index_html
    assert 'id="integration-admin-actions"' in index_html
    assert "btn.hidden = !canCreateDeclaration" in app_js
    assert "$('#import-declaration-card').hidden = !isAdmin" in app_js
    assert "$('#admin-operations').hidden = true" in app_js
    assert "api('/api/admin/operations-summary')" not in app_js


def test_crew_form_keeps_readable_controls_with_compact_two_column_layout():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    styles_css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert "field('full_name','Họ và tên',item.full_name,'text','required')" in app_js
    assert '#crew-fields { grid-template-columns: repeat(2, minmax(0, 1fr)); }' in styles_css
    assert '#crew-fields label { gap: 4px; font-size: 10px; }' not in styles_css
    assert '#crew-fields input, #crew-fields select { min-height: 34px' not in styles_css


def test_terminology_standardized():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "Import dữ liệu" in app_js
    assert "Import dữ liệu" in index_html
    assert "Backup ngay" in index_html
    assert "NHẬP DỮ LIỆU CÓ KIỂM SOÁT" in index_html
    assert "Xác nhận import" in app_js


def test_historical_import_is_visually_and_semantically_separate_from_live_import():
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    styles_css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert 'id="operational-import-tab"' in index_html
    assert 'id="historical-import-tab"' in index_html
    assert 'role="tabpanel" aria-labelledby="historical-import-tab"' in index_html
    assert "Không sửa phiếu khai báo gốc" in index_html
    assert "không dựa vào tên file" in index_html
    assert "Giữ bản đang dùng" in index_html
    assert "Dùng file mới · tạo revision" in app_js
    assert "function setImportMode(" in app_js
    assert "function previewHistoricalImport(" in app_js
    assert "function loadHistoricalImportHistory(" in app_js
    assert ".historical-import-steps" in styles_css
    assert "@media (max-width: 760px)" in styles_css


def test_report_dashboard_makes_source_coverage_and_overlap_explicit():
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    styles_css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert 'role="group" aria-label="Nguồn số liệu thống kê"' in index_html
    assert 'data-source="live" class="active"' in index_html
    assert 'data-source="historical"' in index_html
    assert 'data-source="combined"' in index_html
    assert 'id="analytics-coverage" class="analytics-coverage" aria-live="polite"' in index_html
    assert 'id="analytics-combined-blocked"' in index_html
    assert "const allowedSource = ['PORT_STAFF', 'PLATFORM_ADMIN'].includes" in app_js
    assert "data.combinedAllowed === false" in app_js
    assert "Chưa đủ độ phủ để tính" in app_js
    assert ".coverage-period.overlap" in styles_css


def test_wizard_step_order_customer_friendly():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    # Verify B (Hành trình) appears before E (Thuyền trưởng) in DECLARATION_STEPS
    steps_start = app_js.index("const DECLARATION_STEPS")
    steps_end = app_js.index("];", steps_start)
    steps_section = app_js[steps_start:steps_end]

    idx_journey = steps_section.index("Hành trình")
    idx_crew = steps_section.index("Thuyền trưởng")
    assert idx_journey < idx_crew, (
        "Hành trình (B) phải đứng trước Thuyền trưởng (E) trong wizard steps"
    )


def test_preview_uses_customer_confirmation_language():
    preview_html = (ROOT / "frontend" / "preview.html").read_text(encoding="utf-8")

    assert "Kiểm tra trước khi xác nhận" in preview_html
    assert "Xác nhận & gửi" in preview_html
    assert "Khách hàng xác nhận gửi phiếu" in preview_html
    assert "Khách hàng nộp phiếu" not in preview_html
    assert "Khách hàng duyệt phiếu" not in preview_html


def test_data_navigation_stays_with_primary_navigation():
    styles_css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert ".data-nav { margin-top: 0; padding-top: 0; }" in styles_css
    assert ".data-nav { margin-top: auto;" not in styles_css
    assert ".sidebar-footer { margin-top: auto;" in styles_css
