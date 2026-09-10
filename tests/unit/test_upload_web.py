from pathlib import Path

_WEB = Path(__file__).resolve().parents[2] / "apps" / "web"
_PAGE = (_WEB / "app" / "(shell)" / "documents" / "page.tsx").read_text()
_UPLOAD = (_WEB / "components" / "DocumentUpload.tsx").read_text()
_PRESIGN_PROXY = (_WEB / "app" / "api" / "uploads" / "presign" / "route.ts").read_text()
_COMPLETE_PROXY = (
    _WEB
    / "app"
    / "api"
    / "uploads"
    / "[attachmentId]"
    / "complete"
    / "route.ts"
).read_text()


def test_documents_page_renders_direct_upload_component() -> None:
    assert "<DocumentUpload />" in _PAGE
    assert 'type="file"' in _UPLOAD
    assert ".pdf,.jpg,.jpeg,.png,.webp" in _UPLOAD


def test_browser_upload_uses_presign_s3_and_complete_sequence() -> None:
    presign = _UPLOAD.index('fetch("/api/uploads/presign"')
    direct = _UPLOAD.index("fetch(grant.url")
    complete = _UPLOAD.index("/complete")
    assert presign < direct < complete
    assert 'uploadBody.append("file", file)' in _UPLOAD
    assert 'purpose: "document"' in _UPLOAD


def test_next_routes_only_proxy_authorized_api_calls() -> None:
    assert 'proxyFastApi("/v1/uploads/presign"' in _PRESIGN_PROXY
    assert "proxyFastApi(`/v1/uploads/${encodeURIComponent(attachmentId)}/complete`" in (
        _COMPLETE_PROXY
    )
    assert "AWS_SECRET_ACCESS_KEY" not in _UPLOAD
    assert "AWS_ACCESS_KEY_ID" not in _UPLOAD


def test_upload_ui_handles_progress_success_and_error() -> None:
    assert 'setPhase("authorizing")' in _UPLOAD
    assert 'setPhase("uploading")' in _UPLOAD
    assert 'setPhase("verifying")' in _UPLOAD
    assert 'setPhase("complete")' in _UPLOAD
    assert 'setPhase("error")' in _UPLOAD
    assert 'role="alert"' in _UPLOAD
    assert 'role="status"' in _UPLOAD
