"""CR-012: Block real HTTP in tests"""
import pytest


@pytest.fixture(autouse=True)
def block_real_http(monkeypatch):
    """Fail any test that makes real HTTP requests"""
    import requests

    def fail_real_request(*args, **kwargs):
        raise AssertionError(
            f"Real HTTP request blocked in test: {args[0] if args else 'unknown'}"
        )

    monkeypatch.setattr(
        "requests.sessions.Session.request",
        fail_real_request,
    )
