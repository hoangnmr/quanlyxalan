from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_wizard_steps_use_native_keyboard_controls():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert 'class="wizard-step-button"' in app_js
    assert 'aria-current="step"' in app_js
    assert '<nav aria-label="Các bước khai báo">' in app_js
    assert "data-wizard-dot" in app_js


def test_local_draft_status_explains_storage_boundary():
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")

    assert 'id="draft-state"' in index_html
    assert 'role="status" aria-live="polite"' in index_html
    assert "Nháp cục bộ" in index_html
    assert "chưa lưu lên hệ thống" in index_html
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
    assert "input.checked = suggestion.crew_ids.includes" in app_js


def test_role_dashboard_layout():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "function applyRoleDashboardLayout(" in app_js
    assert "dashboard-role-" in app_js
    assert 'id="dashboard-container"' in index_html


def test_terminology_standardized():
    app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "Nhập dữ liệu Excel" in app_js
    assert "Nhập Excel" in index_html
    assert "Sao lưu ngay" in index_html
    assert "NHẬP DỮ LIỆU" in app_js
    assert "SAO LƯU" in app_js


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


def test_preview_preserves_customer_submit_language():
    preview_html = (ROOT / "frontend" / "preview.html").read_text(encoding="utf-8")

    assert "Kiểm tra & nộp" in preview_html
    assert "Khách hàng nộp phiếu" in preview_html
    assert "Khách hàng duyệt phiếu" not in preview_html
