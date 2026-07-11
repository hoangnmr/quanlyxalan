from pathlib import Path

import pytest

from backend.storage import LocalQuarantineStorage, ScannerNotConfigured, get_attachment_storage


def test_local_quarantine_storage_and_fail_closed_scanner(tmp_path: Path):
    storage = LocalQuarantineStorage(tmp_path)
    key = storage.put_quarantined("safe.pdf", b"payload")
    assert (tmp_path / key).read_bytes() == b"payload"
    assert ScannerNotConfigured().scan(key) == "QUARANTINED"


def test_local_storage_rejects_path_escape(tmp_path: Path):
    storage = LocalQuarantineStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.put_quarantined("../escape.pdf", b"payload")


def test_storage_defaults_to_local(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("OBJECT_STORAGE_MODE", raising=False)
    assert get_attachment_storage(tmp_path).backend_name == "LOCAL_QUARANTINE"
