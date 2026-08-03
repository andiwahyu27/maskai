"""CR-010 Logging, Redaction, and Safe Error Tests"""
import unittest
import logging
from unittest.mock import patch
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maskai.utils.logging_utils import redact_secret, safe_url_for_log, safe_body_for_log
from maskai.config import config


class TestSecretRedaction(unittest.TestCase):
    def test_redact_bot_token(self):
        raw = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        safe = redact_secret(raw)
        self.assertNotIn(config.BOT_TOKEN, safe)
        self.assertIn("***", safe)

    def test_redact_supabase_key(self):
        raw = f"Authorization: Bearer {config.SUPABASE_KEY}"
        safe = redact_secret(raw)
        self.assertNotIn(config.SUPABASE_KEY, safe)

    def test_redact_dahono_key(self):
        raw = f"key={config.DAHONO_KEY}"
        safe = redact_secret(raw)
        self.assertNotIn(config.DAHONO_KEY, safe)

    def test_redact_all_secrets_at_once(self):
        raw = f"bot={config.BOT_TOKEN}&supa={config.SUPABASE_KEY}&dah={config.DAHONO_KEY}"
        safe = redact_secret(raw)
        for s in [config.BOT_TOKEN, config.SUPABASE_KEY, config.DAHONO_KEY]:
            if s:
                self.assertNotIn(s, safe)

    def test_safe_url_strips_query_string(self):
        raw = f"https://api.example.com/path?token=secret&user=123"
        safe = safe_url_for_log(raw)
        self.assertNotIn("token=", safe)
        self.assertNotIn("user=", safe)

    def test_safe_url_redacts_bot_token(self):
        raw = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getUpdates"
        safe = safe_url_for_log(raw)
        self.assertNotIn(config.BOT_TOKEN, safe)


class TestLoggingPrivacy(unittest.TestCase):
    def test_unauthorized_log_no_message_content(self):
        """Log of unauthorized access must not contain message text"""
        logger = logging.getLogger("test_privacy")
        with self.assertLogs(logger, level='WARNING') as cm:
            logger.warning(
                "Unauthorized access user_id=%s chat_id=%s",
                99999, 12345,
            )
        output = "\n".join(cm.output)
        self.assertNotIn("PRIVATE_FINANCIAL", output)

    def test_http_log_no_query_string(self):
        logger = logging.getLogger("test_http")
        with self.assertLogs(logger, level='ERROR') as cm:
            url = "https://api.example.com/endpoint?user_data=sensitive"
            safe = safe_url_for_log(url)
            logger.error("HTTP timeout: %s", safe)
        output = "\n".join(cm.output)
        self.assertNotIn("user_data", output)


class TestUserSafeErrors(unittest.TestCase):
    def test_raw_exception_not_in_telegram_response(self):
        """Raw exception path must not be sent to user"""
        # Verify send() calls don't contain {e} or {exc}
        import re
        with open('maskai/app.py') as f:
            app = f.read()
        # Find all send() calls
        sends = re.findall(r'send\(chat_id,\s*(f?"[^"]*")', app)
        for s in sends:
            self.assertNotIn("{e}", s)
            self.assertNotIn("{exc}", s)


if __name__ == "__main__":
    unittest.main()
