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
    assert "Nháp cục bộ trên thiết bị này" in index_html
    assert "chưa lưu lên hệ thống" in index_html
    assert "tanthuan-declaration-draft-saved-at" in app_js
    assert "function updateLocalDraftStatus(" in app_js
