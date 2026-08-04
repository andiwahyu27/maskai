"""CR-012: Block real HTTP + set test env vars (pre-import)"""
import os

# Set test env vars BEFORE any module imports config
os.environ.setdefault("BOT_TOKEN", "test-bot-token-for-tests")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-supabase-key-for-tests")
os.environ.setdefault("DAHONO_KEY", "test-dahono-key-for-tests")

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
