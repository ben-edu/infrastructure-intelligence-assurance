from infra_assurance.kubernetes_event_intelligence import _safe_reason


def test_event_reason_rejects_url_like_values():
    assert _safe_reason("FailedMount") == "FailedMount"
    assert _safe_reason("https://secret.example.invalid/path") == "REDACTED_REASON"
    assert _safe_reason("scheme:value") == "REDACTED_REASON"
